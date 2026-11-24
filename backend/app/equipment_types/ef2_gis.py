"""EF2(GIS) 설비유형 계산기 (Stage 8-3).

`ref_data/schema_eflms_gis.py`(2026-10-16 수정본)의 INPUT_COLUMNS/CALCULATED_COLUMNS 공식을
**그대로** 이식했다 — 공식을 원본과 다르게 해석한 곳은 없다(아래 "원본과 다른 점" 제외, SF6 판정 순서,
누적차단전류 `> 101`, 음수 점수 허용 모두 원본대로, docs/DATA_DICTIONARY.md "원본 그대로 유지하는
판단"). tests/test_ef2_gis.py가 같은 입력으로 원본과 결과를 대조한다.

원본과 다른 점:
- **감점 소수 계산(2026-11-19, 사용자 결정)**: 원본이 감점을 정수로 만들던 floor()/round()/int()를 빼고 소수 그대로
  계산한다(경과연수 감점 = -운전년수 등). 감점 항목은 na.evaluate()가 float·소수 첫째 자리로 통일한다(rounding.py).
- **`cb_op_char_over`(CB 동작특성 기준치 초과) 미사용(2026-10-19, 사용자 결정)** — 입력 컬럼과
  `cb_op_char_over_minus`(Y면 -9)를 빼고, `gis_elec_minus`는 나머지 4항목만 더한다. 원본에
  "N"(감점 0)을 넣은 결과와 같다(테스트가 그렇게 대조). 실제 파일에 이 컬럼이 있으면
  `IGNORED_COLUMNS`로 임포트에서 건너뛴다.
- **경과연수 감점(`age_minus`)을 전기적 감점에 합산(2026-10-19, 사용자 결정)** — 원본은 계산만 하고
  어디에도 더하지 않는다. `gis_elec_minus`에 더해 PoF·전체 점수에 반영된다(사용 1년당 -1).
  노화는 차단기·절연물 고장확률 감점에도 반영되므로 두 가지가 함께 깎인다.
- `cum_trip_current`(누적 차단 전류) int → float(2026-10-19, 실데이터에 소수값). 감점 기준은 같다.
- dtype "string" → "str" 통일
- 임포트 허용값(choices/min/max/required) 추가 — 오류값이 계산에 조용히 0점으로 섞이는 것을 막는다.
  mock 생성기는 원본의 좁혀둔 범위를 그대로 쓰고, 생성값도 이 검증을 통과한다.

공개 인터페이스는 app/equipment_types/base.py의 EquipmentTypeModule.
"""
import itertools
import math
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Equipment,
    GisConsequenceAttribute,
    GisDesignAttribute,
    GisDiagnosis,
    GisOperation,
    GisScoreDetail,
    GisSf6Reading,
)
from app.equipment_types import formula_docs as fd
from app.equipment_types.na import evaluate
from app.equipment_types.rounding import round1
from app.schemas.ef2 import (
    Ef2Detail,
    GisConsequenceAttributeOut,
    GisDesignAttributeOut,
    GisDiagnosisOut,
    GisOperationOut,
    GisScoreDetailOut,
    GisSf6ReadingOut,
)

EF_CODE = "EF2"
EF_NAME = "GIS"
NAME_FIELD = "gis_name"
# 원본 컬럼이지만 쓰지 않는 입력 — 실제 파일에 있어도 임포트가 저장하지 않고 건너뛴다(import_service).
IGNORED_COLUMNS = ("cb_op_char_over",)
DOMAIN_TABLES = [
    GisScoreDetail,
    GisOperation,
    GisDiagnosis,
    GisSf6Reading,
    GisConsequenceAttribute,
    GisDesignAttribute,
]
# 계산 결과 테이블 — 점수 기준일(today)을 여기서 읽는다(Stage 21-1, 요약 API의 점수 기준일)
SCORE_DETAIL_MODEL = GisScoreDetail

# ------------------------------------------------------------------
# 1. INPUT COLUMNS
# ------------------------------------------------------------------
# 허용값(임포트 검증용, app/services/import_service.py):
#   choices  : 이 값 중 하나여야 함 / min, max : 수치 범위 / required : 빈 문자열 거부
_ABC = ["A", "B", "C"]
_A_TO_E = ["A", "B", "C", "D", "E"]
_YN = ["Y", "N"]

_cb_name_counters = {"cb": itertools.count(1), "gicb": itertools.count(1)}


def _gen_gis_name():
    """접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["cb", "gicb"])
    return f"{prefix}{next(_cb_name_counters[prefix])}"


INPUT_COLUMNS = [
    {"name": "factory_code", "label": "사업장명", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["H1", "H2", "K1", "P1"])},
    {"name": "EF_code", "label": "전기설비코드", "dtype": "str", "choices": [EF_CODE],
     "generator": lambda: EF_CODE},
    {"name": "gis_name", "label": "차단기명", "dtype": "str", "required": True,
     "generator": _gen_gis_name},
    # 누설전류 감점 기준이 154kV/345kV만 정의돼 있어 그 외 전압은 받지 않는다(2026-10-16 결정).
    {"name": "voltage", "label": "전압", "dtype": "int", "choices": [154000, 345000],
     "generator": lambda: random.choice([154000])},
    {"name": "op_type", "label": "조작방식", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["공압식"])},
    {"name": "cb_op_num", "label": "차단기동작횟수", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(0, 110)},
    {"name": "operation_start_time", "label": "가동년월", "dtype": "date",
     "generator": lambda: date(1999, 10, 1) + timedelta(days=random.randint(0, 7300))},
    {"name": "rated_trip_count", "label": "정격 차단 동작 횟수", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(0, 99)},
    {"name": "cum_trip_current", "label": "누적 차단 전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 99)},
    {"name": "load_percent", "label": "부하율", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 1000) / 10},
    {"name": "leakage_curr", "label": "누설전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 1) / 1000},
    # mock은 화학적 감점이 나오지 않게 "N"만 생성한다(2026-10-19, 사용자 결정 — 실데이터 Y는 그대로 -15).
    {"name": "part_dischar_pat", "label": "부분 방전 이상 패턴", "dtype": "str", "choices": _YN,
     "generator": lambda: "N"},
    {"name": "sf6_diag_time", "label": "진단일", "dtype": "date",
     "generator": lambda: date(2024, 11, 1)},
    {"name": "sf6_so2", "label": "sf6_so2", "dtype": "float", "min": 0,
     "generator": lambda: random.choice([0])},
    {"name": "sf6_leak", "label": "sf6_누기", "dtype": "str", "choices": ["있음", "없음"],
     "generator": lambda: random.choice(["없음"])},
    {"name": "sf6_h2o", "label": "sf6_수분", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(2000, 8000) / 100.0},
    {"name": "sf6_purity", "label": "sf6_순도", "dtype": "float", "min": 0, "max": 100,
     "generator": lambda: random.randint(990, 1000) / 10.00},
    {"name": "elec_room_max_temp", "label": "전기실 최대온도", "dtype": "int",
     "generator": lambda: random.randint(20, 29)},
    {"name": "in_vol", "label": "인입전압", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(_ABC)},
    {"name": "capa_times_load", "label": "생산영향성", "dtype": "str", "choices": _A_TO_E,
     "generator": lambda: random.choice(_A_TO_E)},
    {"name": "fire_spread", "label": "화재확산", "dtype": "str", "choices": ["A", "B"],
     "generator": lambda: random.choice(["A", "B"])},
    {"name": "env_loc", "label": "환경_위치", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(_ABC)},
    {"name": "emerge_resp_pat", "label": "비상대응시간", "dtype": "str", "choices": _A_TO_E,
     "generator": lambda: random.choice(_A_TO_E)},
    {"name": "rep_cost", "label": "사고복구비용", "dtype": "str", "choices": _A_TO_E,
     "generator": lambda: random.choice(_A_TO_E)},
    {"name": "rep_time", "label": "정상화기간", "dtype": "str", "choices": _A_TO_E,
     "generator": lambda: random.choice(_A_TO_E)},
    {"name": "in_line_num", "label": "인입선로", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["C"])},
    {"name": "ato", "label": "ato 구성", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(["Y"])},
    {"name": "reliability", "label": "공급신뢰도", "dtype": "str", "choices": ["A", "B"],
     "generator": lambda: random.choice(["A", "B"])},
    {"name": "online_diag", "label": "온라인진단", "dtype": "str", "choices": ["A", "B", "C", "D"],
     "generator": lambda: random.choice(["A", "B", "C", "D"])},
    {"name": "offline_diag", "label": "오프라인진단", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(_YN)},
    {"name": "tbm", "label": "tbm실시", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(["Y"])},
    {"name": "conn_rev", "label": "도체접속구조개선", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(_YN)},
    {"name": "leak_str", "label": "가스기밀강화", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(_YN)},
    {"name": "insul_str", "label": "절연스펙강화", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(_YN)},
    {"name": "vt_la_str", "label": "부품신뢰성강화", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(_YN)},
]


def generate_input_row() -> dict:
    return {col["name"]: col["generator"]() for col in INPUT_COLUMNS}


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (원본 공식 그대로)
# ------------------------------------------------------------------
def cb_op_num_minus_cal(row):
    s = row["cb_op_num"]
    if s >= 2000: return -8
    if s >= 1000: return -6
    if s >= 500: return -4
    if s >= 300: return -2
    return 0


def gis_mech_minus_cal(row):
    return row["cb_op_num_minus"] + row["cb_stat_minus"] + row["insul_stat_minus"]


def rated_trip_count_minus_cal(row):
    s = row["rated_trip_count"]
    if s >= 10: return -12
    if s >= 5: return -6
    return 0


def cum_trip_current_minus_cal(row):
    s = row["cum_trip_current"]
    if s > 500: return -16
    if s > 101: return -12
    if s >= 25: return -8
    return 0


def load_minus_cal(row):
    s = row["load_percent"]
    if s > 90: return -30
    if s > 80: return -20
    if s > 70: return -10
    return 0


def leakage_curr_minus_cal(row):
    a = row["voltage"]
    b = row["leakage_curr"]
    if a == 154000 and b >= 0.54: return -6
    if a == 345000 and b >= 1.2: return -6
    return 0


def gis_elec_minus_cal(row):
    # 원본과 다른 점 두 가지(2026-10-19, 모듈 docstring): cb_op_char_over_minus는 미사용으로 빼고,
    # 원본이 합산하지 않는 age_minus(경과연수)를 더한다.
    return (
        row["rated_trip_count_minus"] + row["cum_trip_current_minus"]
        + row["load_minus"] + row["leakage_curr_minus"] + row["age_minus"]
    )


def part_dischar_minus_cal(row):
    return -15 if row["part_dischar_pat"] == "Y" else 0


def sf6_minus_cal(row):
    a = row["sf6_so2"]
    b = row["sf6_leak"]
    c = row["sf6_h2o"]
    d = row["sf6_purity"]
    e = -20 if a >= 1 else 0
    f = -12 if b == "있음" else 0
    # 원본 판정 순서 그대로 — 수분 ≤150이면 순도는 보지 않는다.
    if c <= 150:
        g = 0
    elif c > 300 or d <= 95:
        g = -15
    elif c > 150 or d <= 97:
        g = -10
    else:
        g = 0
    return e + f + g


def elec_room_minus_cal(row):
    return -4 if row["elec_room_max_temp"] >= 30 else 0


def gis_chem_minus_cal(row):
    return row["part_dischar_minus"] + row["sf6_minus"] + row["elec_room_minus"]


def pof_minus_cal(row):
    return row["gis_mech_minus"] + row["gis_elec_minus"] + row["gis_chem_minus"]


def _grade(value, table):
    return table.get(value, 0)


def in_vol_minus_cal(row):
    return _grade(row["in_vol"], {"A": -16, "B": -8})


def productivity_minus_cal(row):
    return _grade(row["capa_times_load"], {"A": -16, "B": -12, "C": -8, "D": -4, "E": 0})


def fire_spread_minus_cal(row):
    return _grade(row["fire_spread"], {"A": -6, "B": 0})


def env_minus_cal(row):
    return _grade(row["env_loc"], {"A": -6, "B": -3, "C": 0})


def emerge_resp_minus_cal(row):
    return _grade(row["emerge_resp_pat"], {"A": -6, "B": -4, "C": -2, "D": -1, "E": 0})


def rep_cost_minus_cal(row):
    return _grade(row["rep_cost"], {"A": -8, "B": -6, "C": -4, "D": -2, "E": 0})


def rep_time_minus_cal(row):
    return _grade(row["rep_time"], {"A": -4, "B": -3, "C": -2, "D": -1, "E": 0})


def cof_minus_cal(row):
    return (
        row["in_vol_minus"] + row["productivity_minus"] + row["fire_spread_minus"]
        + row["env_minus"] + row["emerge_resp_minus"] + row["rep_cost_minus"]
        + row["rep_time_minus"]
    )


def in_line_minus_cal(row):
    return _grade(row["in_line_num"], {"A": -30, "B": -15, "C": 0})


def ato_minus_cal(row):
    return _grade(row["ato"], {"Y": 0, "N": -30})


def reliability_minus_cal(row):
    return _grade(row["reliability"], {"A": -16, "B": 0})


def online_diag_minus_cal(row):
    return _grade(row["online_diag"], {"A": -15, "B": -10, "C": -5, "D": 0})


def offline_diag_minus_cal(row):
    return _grade(row["offline_diag"], {"Y": 0, "N": -15})


def tbm_minus_cal(row):
    return _grade(row["tbm"], {"Y": 0, "N": -12})


def conn_rev_minus_cal(row):
    return _grade(row["conn_rev"], {"Y": 0, "N": -4})


def leak_str_minus_cal(row):
    return _grade(row["leak_str"], {"Y": 0, "N": -4})


def insul_str_minus_cal(row):
    return _grade(row["insul_str"], {"Y": 0, "N": -4})


def vt_la_minus_cal(row):
    return _grade(row["vt_la_str"], {"Y": 0, "N": -3})


def dof_minus_cal(row):
    return (
        row["in_line_minus"] + row["ato_minus"] + row["reliability_minus"]
        + row["online_diag_minus"] + row["offline_diag_minus"] + row["tbm_minus"]
        + row["conn_rev_minus"] + row["leak_str_minus"] + row["insul_str_minus"]
        + row["vt_la_minus"]
    )


CALCULATED_COLUMNS = [
    # 계산 기준일은 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과). Stage 8-4, 점수 예측용.
    {"name": "today", "formula": lambda row: row["_as_of"]},
    {"name": "operation_year", "formula": lambda row: round1((row["today"] - row["operation_start_time"]).days / 365)},
    {"name": "age_minus", "formula": lambda row: -row["operation_year"]},
    {"name": "cb_op_num_minus", "formula": cb_op_num_minus_cal},
    {"name": "cb_op_year", "formula": lambda row: row["operation_year"]},
    {"name": "cb_stat", "formula": lambda row: math.e ** (-1 * ((row["operation_year"] / 72) ** 3.21))},
    {"name": "cb_stat_minus", "formula": lambda row: (row["cb_stat"] - 1) * 100 * 1},
    {"name": "insul_year", "formula": lambda row: row["operation_year"]},
    {"name": "insul_stat", "formula": lambda row: math.e ** (-1 * ((row["operation_year"] / 4199) ** 0.75))},
    {"name": "insul_stat_minus", "formula": lambda row: (row["insul_stat"] - 1) * 100 * 2},
    {"name": "gis_mech_minus", "formula": gis_mech_minus_cal},
    {"name": "rated_trip_count_minus", "formula": rated_trip_count_minus_cal},
    {"name": "cum_trip_current_minus", "formula": cum_trip_current_minus_cal},
    {"name": "load_minus", "formula": load_minus_cal},
    {"name": "leakage_curr_minus", "formula": leakage_curr_minus_cal},
    {"name": "gis_elec_minus", "formula": gis_elec_minus_cal},
    {"name": "part_dischar_minus", "formula": part_dischar_minus_cal},
    {"name": "sf6_minus", "formula": sf6_minus_cal},
    {"name": "elec_room_minus", "formula": elec_room_minus_cal},
    {"name": "gis_chem_minus", "formula": gis_chem_minus_cal},
    {"name": "pof_minus", "formula": pof_minus_cal},
    {"name": "pof", "formula": lambda row: 100 + row["pof_minus"]},
    {"name": "in_vol_minus", "formula": in_vol_minus_cal},
    {"name": "productivity_minus", "formula": productivity_minus_cal},
    {"name": "fire_spread_minus", "formula": fire_spread_minus_cal},
    {"name": "env_minus", "formula": env_minus_cal},
    {"name": "emerge_resp_minus", "formula": emerge_resp_minus_cal},
    {"name": "rep_cost_minus", "formula": rep_cost_minus_cal},
    {"name": "rep_time_minus", "formula": rep_time_minus_cal},
    {"name": "cof_minus", "formula": cof_minus_cal},
    {"name": "cof", "formula": lambda row: 100 + row["cof_minus"]},
    {"name": "in_line_minus", "formula": in_line_minus_cal},
    {"name": "ato_minus", "formula": ato_minus_cal},
    {"name": "reliability_minus", "formula": reliability_minus_cal},
    {"name": "online_diag_minus", "formula": online_diag_minus_cal},
    {"name": "offline_diag_minus", "formula": offline_diag_minus_cal},
    {"name": "tbm_minus", "formula": tbm_minus_cal},
    {"name": "conn_rev_minus", "formula": conn_rev_minus_cal},
    {"name": "leak_str_minus", "formula": leak_str_minus_cal},
    {"name": "insul_str_minus", "formula": insul_str_minus_cal},
    {"name": "vt_la_minus", "formula": vt_la_minus_cal},
    {"name": "dof_minus", "formula": dof_minus_cal},
    {"name": "dof", "formula": lambda row: 100 + row["dof_minus"]},
    {"name": "total_score", "formula": lambda row: 0.5 * row["pof"] + 0.3 * row["cof"] + 0.2 * row["dof"]},
]


def calculate(input_row: dict, as_of: date | None = None) -> dict:
    """input_row(INPUT_COLUMNS 값들)를 받아 전체 계산 컬럼을 더한 dict를 반환한다.
    원본을 바꾸지 않도록 복사본에 계산한다. as_of는 계산 기준일(기본 오늘)."""
    # N/A(null) 입력을 읽는 공식은 감점 0 / 파생값 null — app/equipment_types/na.py (Stage 11)
    row = evaluate(input_row, CALCULATED_COLUMNS, as_of)
    return row


# ------------------------------------------------------------------
# 3. DB 적재 (EF2 전용 테이블)
# ------------------------------------------------------------------
_SCORE_DETAIL_FIELDS = [c.name for c in GisScoreDetail.__table__.columns if c.name not in ("equipment_id", "computed_at")]


async def ingest_domain(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """calculate()가 만든 flat dict에서 EF2 전용 테이블들에 upsert한다. commit하지 않는다."""
    await session.merge(
        GisOperation(
            equipment_id=equipment_id,
            measured_at=row["today"],
            op_type=row["op_type"],
            cb_op_num=row["cb_op_num"],
            rated_trip_count=row["rated_trip_count"],
            cum_trip_current=row["cum_trip_current"],
            load_percent=row["load_percent"],
            leakage_curr=row["leakage_curr"],
        )
    )
    await session.merge(
        GisDiagnosis(
            equipment_id=equipment_id,
            measured_at=row["today"],
            part_dischar_pat=row["part_dischar_pat"],
            elec_room_max_temp=row["elec_room_max_temp"],
        )
    )
    await session.merge(
        GisSf6Reading(
            equipment_id=equipment_id,
            diag_time=row["sf6_diag_time"],
            sf6_so2=row["sf6_so2"],
            sf6_leak=row["sf6_leak"],
            sf6_h2o=row["sf6_h2o"],
            sf6_purity=row["sf6_purity"],
        )
    )
    await session.merge(
        GisConsequenceAttribute(
            equipment_id=equipment_id,
            updated_at=row["today"],
            in_vol=row["in_vol"],
            capa_times_load=row["capa_times_load"],
            fire_spread=row["fire_spread"],
            env_loc=row["env_loc"],
            emerge_resp_pat=row["emerge_resp_pat"],
            rep_cost=row["rep_cost"],
            rep_time=row["rep_time"],
        )
    )
    await session.merge(
        GisDesignAttribute(
            equipment_id=equipment_id,
            updated_at=row["today"],
            in_line_num=row["in_line_num"],
            ato=row["ato"],
            reliability=row["reliability"],
            online_diag=row["online_diag"],
            offline_diag=row["offline_diag"],
            tbm=row["tbm"],
            conn_rev=row["conn_rev"],
            leak_str=row["leak_str"],
            insul_str=row["insul_str"],
            vt_la_str=row["vt_la_str"],
        )
    )
    await ingest_scores(row, equipment_id, session)


async def ingest_scores(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """계산 결과 테이블만 upsert한다 — 점수 갱신(app/services/score_refresh_service.py)은 입력 테이블을 건드리지 않고
    이것만 부른다(2026-11-19, Stage 21-1). commit하지 않는다."""
    # 계산 컬럼 이름 = 테이블 컬럼 이름이라 그대로 옮긴다.
    await session.merge(
        GisScoreDetail(equipment_id=equipment_id, **{name: row[name] for name in _SCORE_DETAIL_FIELDS})
    )


# ------------------------------------------------------------------
# 4. 조회 (Stage 8-4)
# ------------------------------------------------------------------
# 감점 항목 메타데이터(원본 라벨 기준). PoF는 원본의 기계적/전기적/화학적 3그룹으로 묶는다.
# age_minus는 전기적 감점에 합산하므로(2026-10-19) 전기적 그룹에 둔다.
BREAKDOWN = {
    "pof": [
        {"field": "cb_op_num_minus", "label": "차단기 동작횟수", "group": "기계적"},
        {"field": "cb_stat_minus", "label": "차단기 고장확률", "group": "기계적"},
        {"field": "insul_stat_minus", "label": "절연물 고장확률", "group": "기계적"},
        {"field": "rated_trip_count_minus", "label": "정격차단 동작횟수", "group": "전기적"},
        {"field": "cum_trip_current_minus", "label": "누적차단전류", "group": "전기적"},
        {"field": "load_minus", "label": "부하율", "group": "전기적"},
        {"field": "leakage_curr_minus", "label": "누설전류", "group": "전기적"},
        {"field": "age_minus", "label": "경과연수", "group": "전기적"},
        {"field": "part_dischar_minus", "label": "부분방전", "group": "화학적"},
        {"field": "sf6_minus", "label": "SF6 가스", "group": "화학적"},
        {"field": "elec_room_minus", "label": "전기실 온도", "group": "화학적"},
    ],
    "cof": [
        {"field": "in_vol_minus", "label": "인입전압"},
        {"field": "productivity_minus", "label": "생산영향성"},
        {"field": "fire_spread_minus", "label": "화재확산"},
        {"field": "env_minus", "label": "환경_위치"},
        {"field": "emerge_resp_minus", "label": "비상대응시간"},
        {"field": "rep_cost_minus", "label": "사고복구비용"},
        {"field": "rep_time_minus", "label": "정상화기간"},
    ],
    "dof": [
        {"field": "in_line_minus", "label": "인입선로"},
        {"field": "ato_minus", "label": "ATO 구성"},
        {"field": "reliability_minus", "label": "공급신뢰도"},
        {"field": "online_diag_minus", "label": "온라인진단"},
        {"field": "offline_diag_minus", "label": "오프라인진단"},
        {"field": "tbm_minus", "label": "TBM 실시"},
        {"field": "conn_rev_minus", "label": "도체접속구조개선"},
        {"field": "leak_str_minus", "label": "가스기밀강화"},
        {"field": "insul_str_minus", "label": "절연스펙강화"},
        {"field": "vt_la_minus", "label": "부품신뢰성강화"},
    ],
}

# 지표설명 상세 페이지의 계산식(Stage 22-11) — 실제 계산과 같은지 tests/test_formula_docs.py가 확인한다.
def _years_ago(n: int) -> date:
    return date(fd.EXAMPLE_AS_OF.year - n, 1, 1)


_SF6_OK = dict(sf6_so2=0, sf6_leak="없음", sf6_h2o=100, sf6_purity=99)
_YN_DOF = [
    ("offline_diag_minus", "offline_diag", -15), ("tbm_minus", "tbm", -12), ("conn_rev_minus", "conn_rev", -4),
    ("leak_str_minus", "leak_str", -4), ("insul_str_minus", "insul_str", -4), ("vt_la_minus", "vt_la_str", -3),
]
FORMULA_DOCS = [
    # POF — 기계적
    fd.steps("cb_op_num_minus", "cb_op_num", [(2000, -8), (1000, -6), (500, -4), (300, -2)], op="ge",
             var_label="차단기동작횟수", unit="회"),
    fd.expr(
        "cb_stat_minus", fd.weibull_tex("72", "3.21", "1"), inputs=["operation_start_time"],
        symbols=[{"sym": "t", "label": "사용년수"}, {"sym": "η, β", "label": "와이블 척도 72년 · 형상 3.21"}],
        examples=[fd.example(f"사용 {n}년 → {fd.signed(v)}", v, as_of=fd.EXAMPLE_AS_OF, operation_start_time=_years_ago(n))
                  for n, v in ((20, -1.6), (30, -5.8), (40, -14.1))],
    ),
    fd.expr(
        "insul_stat_minus", fd.weibull_tex("4199", "0.75", "2"), inputs=["operation_start_time"],
        symbols=[{"sym": "t", "label": "사용년수"}, {"sym": "η, β", "label": "와이블 척도 4,199년 · 형상 0.75"}],
        examples=[fd.example(f"사용 {n}년 → {fd.signed(v)}", v, as_of=fd.EXAMPLE_AS_OF, operation_start_time=_years_ago(n))
                  for n, v in ((10, -2.1), (20, -3.6), (30, -4.9))],
    ),
    # POF — 전기적
    fd.steps("rated_trip_count_minus", "rated_trip_count", [(10, -12), (5, -6)], op="ge", var_label="정격 차단 동작 횟수", unit="회"),
    fd.steps("cum_trip_current_minus", "cum_trip_current", [(500, -16, "gt"), (101, -12, "gt"), (25, -8, "ge")],
             var_label="누적 차단 전류"),
    fd.steps("load_minus", "load_percent", [(90, -30), (80, -20), (70, -10)], var_label="부하율", unit="%"),
    fd.expr(
        "leakage_curr_minus", [r"\text{감점} = \begin{cases} -6 & \text{누설전류} \ge \text{전압별 기준} \\ 0 & \text{그 밖} \end{cases}"],
        inputs=["voltage", "leakage_curr"],
        table={"columns": ["전압", "감점 기준(누설전류)"], "rows": [["154kV", "0.54 이상"], ["345kV", "1.2 이상"]]},
        examples=[
            fd.example("154kV · 0.6 → −6", -6.0, voltage=154000, leakage_curr=0.6),
            fd.example("154kV · 0.5 → 0", 0.0, voltage=154000, leakage_curr=0.5),
            fd.example("345kV · 1.2 → −6", -6.0, voltage=345000, leakage_curr=1.2),
        ],
    ),
    fd.age_item(),
    # POF — 화학적
    fd.mapping("part_dischar_minus", "part_dischar_pat", {"Y": -15, "N": 0}),
    fd.expr(
        "sf6_minus",
        [r"\text{감점} = \text{SO}_2\text{ 감점} + \text{누기 감점} + \text{수분·순도 감점}"],
        inputs=["sf6_so2", "sf6_leak", "sf6_h2o", "sf6_purity"],
        table={
            "columns": ["구분", "조건", "감점"],
            "rows": [
                ["SO₂", "1 이상", "−20"],
                ["누기", "있음", "−12"],
                ["수분·순도", "수분 150 이하(순도는 보지 않음)", "0"],
                ["", "수분 300 초과 또는 순도 95 이하", "−15"],
                ["", "그 밖(수분 150 초과)", "−10"],
            ],
        },
        examples=[
            fd.example("SO₂ 0 · 누기 없음 · 수분 100 · 순도 99 → 0", 0.0, **_SF6_OK),
            fd.example("수분 200 · 순도 99 → −10", -10.0, **{**_SF6_OK, "sf6_h2o": 200}),
            fd.example("수분 200 · 순도 94 → −15", -15.0, **{**_SF6_OK, "sf6_h2o": 200, "sf6_purity": 94}),
            fd.example("수분 100 · 순도 90 → 0(수분이 낮아 순도는 보지 않음)", 0.0, **{**_SF6_OK, "sf6_purity": 90}),
            fd.example("SO₂ 1 · 누기 있음 · 수분 400 → −47", -47.0, sf6_so2=1, sf6_leak="있음", sf6_h2o=400, sf6_purity=99),
        ],
        note="수분·순도는 원본 판정 순서 그대로 수분을 먼저 봅니다.",
    ),
    fd.steps("elec_room_minus", "elec_room_max_temp", [(30, -4)], op="ge", var_label="전기실 최대온도", unit="℃"),
    # COF
    fd.mapping("in_vol_minus", "in_vol", {"A": -16, "B": -8, "C": 0}),
    fd.mapping("productivity_minus", "capa_times_load", {"A": -16, "B": -12, "C": -8, "D": -4, "E": 0}),
    fd.mapping("fire_spread_minus", "fire_spread", {"A": -6, "B": 0}),
    fd.mapping("env_minus", "env_loc", {"A": -6, "B": -3, "C": 0}),
    fd.mapping("emerge_resp_minus", "emerge_resp_pat", {"A": -6, "B": -4, "C": -2, "D": -1, "E": 0}),
    fd.mapping("rep_cost_minus", "rep_cost", {"A": -8, "B": -6, "C": -4, "D": -2, "E": 0}),
    fd.mapping("rep_time_minus", "rep_time", {"A": -4, "B": -3, "C": -2, "D": -1, "E": 0}),
    # DOF
    fd.mapping("in_line_minus", "in_line_num", {"A": -30, "B": -15, "C": 0}),
    fd.mapping("ato_minus", "ato", {"N": -30, "Y": 0}),
    fd.mapping("reliability_minus", "reliability", {"A": -16, "B": 0}),
    fd.mapping("online_diag_minus", "online_diag", {"A": -15, "B": -10, "C": -5, "D": 0}),
    *(fd.mapping(field, var, {"N": minus, "Y": 0}) for field, var, minus in _YN_DOF),
]
FORMULA_NOTES = [
    "경과연수는 원본에서 합산하지 않던 항목으로, 이 시스템은 전기적 감점에 더합니다(2026-10-19 결정). 차단기·절연물 고장확률도 사용년수로 커집니다.",
]

_DOMAIN_MODELS = (GisOperation, GisDiagnosis, GisSf6Reading, GisConsequenceAttribute, GisDesignAttribute, GisScoreDetail)
# 입력 컬럼 이름 = 테이블 컬럼 이름인 항목(원본 → DB 그대로 저장)
_SAME_NAME_INPUTS = {
    GisOperation: ("op_type", "cb_op_num", "rated_trip_count", "cum_trip_current", "load_percent", "leakage_curr"),
    GisDiagnosis: ("part_dischar_pat", "elec_room_max_temp"),
    GisSf6Reading: ("sf6_so2", "sf6_leak", "sf6_h2o", "sf6_purity"),
    GisConsequenceAttribute: ("in_vol", "capa_times_load", "fire_spread", "env_loc", "emerge_resp_pat", "rep_cost", "rep_time"),
    GisDesignAttribute: ("in_line_num", "ato", "reliability", "online_diag", "offline_diag", "tbm", "conn_rev", "leak_str", "insul_str", "vt_la_str"),
}


async def _load_rows(session: AsyncSession, equipment_id: int):
    rows = [await session.get(model, equipment_id) for model in _DOMAIN_MODELS]
    return None if any(r is None for r in rows) else rows


async def load_inputs(session: AsyncSession, equipment_id: int) -> tuple[dict, date] | None:
    """저장된 값으로 calculate() 입력 행을 복원하고, 저장된 점수의 계산 기준일과 함께 돌려준다."""
    equipment = await session.get(Equipment, equipment_id)
    rows = await _load_rows(session, equipment_id)
    if equipment is None or rows is None:
        return None
    by_model = dict(zip(_DOMAIN_MODELS, rows))
    row = {
        "factory_code": equipment.factory_code,
        "EF_code": equipment.ef_code,
        "gis_name": equipment.equipment_name,
        "voltage": equipment.voltage,
        "operation_start_time": equipment.operation_start_time,
        "sf6_diag_time": by_model[GisSf6Reading].diag_time,
    }
    for model, names in _SAME_NAME_INPUTS.items():
        row.update({name: getattr(by_model[model], name) for name in names})
    return row, by_model[GisScoreDetail].today


async def last_diag_dates(session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
    """화면의 '최근 진단일' — EF2는 SF6 진단일."""
    if not equipment_ids:
        return {}
    stmt = select(GisSf6Reading.equipment_id, GisSf6Reading.diag_time).where(GisSf6Reading.equipment_id.in_(equipment_ids))
    return dict((await session.execute(stmt)).all())


async def load_detail(session: AsyncSession, equipment_id: int) -> Ef2Detail | None:
    rows = await _load_rows(session, equipment_id)
    if rows is None:
        return None
    operation, diagnosis, sf6, consequence, design, detail = rows
    return Ef2Detail(
        operation=GisOperationOut.model_validate(operation),
        diagnosis=GisDiagnosisOut.model_validate(diagnosis),
        sf6=GisSf6ReadingOut.model_validate(sf6),
        consequence=GisConsequenceAttributeOut.model_validate(consequence),
        design=GisDesignAttributeOut.model_validate(design),
        score_detail=GisScoreDetailOut.model_validate(detail),
    )
