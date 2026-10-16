"""EF2(GIS) 설비유형 계산기 (Stage 8-3).

`ref_data/schema_eflms_gis.py`(2026-10-16 수정본)의 INPUT_COLUMNS/CALCULATED_COLUMNS 공식을
**그대로** 이식했다 — 원본과 다르게 해석한 곳은 없다(SF6 판정 순서, 누적차단전류 `> 101`,
age_minus 미합산, 음수 점수 허용 모두 원본대로, docs/DATA_DICTIONARY.md "원본 그대로 유지하는
판단"). tests/test_ef2_gis.py가 같은 입력으로 원본과 결과를 대조한다.

원본과 다른 점은 계산 외적인 것뿐이다:
- dtype "string" → "str" 통일
- 임포트 허용값(choices/min/max/required) 추가 — 오류값이 계산에 조용히 0점으로 섞이는 것을 막는다.
  mock 생성기는 원본의 좁혀둔 범위를 그대로 쓰고, 생성값도 이 검증을 통과한다.

공개 인터페이스는 app/equipment_types/base.py의 EquipmentTypeModule.
"""
import itertools
import math
import random
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    GisConsequenceAttribute,
    GisDesignAttribute,
    GisDiagnosis,
    GisOperation,
    GisScoreDetail,
    GisSf6Reading,
)

EF_CODE = "EF2"
EF_NAME = "GIS"
NAME_FIELD = "gis_name"
DOMAIN_TABLES = [
    GisScoreDetail,
    GisOperation,
    GisDiagnosis,
    GisSf6Reading,
    GisConsequenceAttribute,
    GisDesignAttribute,
]

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
    {"name": "cum_trip_current", "label": "누적 차단 전류", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(0, 99)},
    {"name": "cb_op_char_over", "label": "CB 동작특성 기준치 초과", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(_YN)},
    {"name": "load_percent", "label": "부하율", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 1000) / 10},
    {"name": "leakage_curr", "label": "누설전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 1) / 1000},
    {"name": "part_dischar_pat", "label": "부분 방전 이상 패턴", "dtype": "str", "choices": _YN,
     "generator": lambda: random.choice(_YN)},
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


def cb_op_char_over_minus_cal(row):
    return -9 if row["cb_op_char_over"] == "Y" else 0


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
    return (
        row["rated_trip_count_minus"] + row["cum_trip_current_minus"] + row["cb_op_char_over_minus"]
        + row["load_minus"] + row["leakage_curr_minus"]
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
    {"name": "today", "formula": lambda row: date.today()},
    {"name": "operation_year", "formula": lambda row: round((date.today() - row["operation_start_time"]).days / 365, 1)},
    {"name": "age_minus", "formula": lambda row: -(math.floor(row["operation_year"]))},
    {"name": "cb_op_num_minus", "formula": cb_op_num_minus_cal},
    {"name": "cb_op_year", "formula": lambda row: row["operation_year"]},
    {"name": "cb_stat", "formula": lambda row: math.e ** (-1 * ((row["operation_year"] / 72) ** 3.21))},
    {"name": "cb_stat_minus", "formula": lambda row: round((row["cb_stat"] - 1) * 100 * 1)},
    {"name": "insul_year", "formula": lambda row: row["operation_year"]},
    {"name": "insul_stat", "formula": lambda row: math.e ** (-1 * ((row["operation_year"] / 4199) ** 0.75))},
    {"name": "insul_stat_minus", "formula": lambda row: round((row["insul_stat"] - 1) * 100 * 2)},
    {"name": "gis_mech_minus", "formula": gis_mech_minus_cal},
    {"name": "rated_trip_count_minus", "formula": rated_trip_count_minus_cal},
    {"name": "cum_trip_current_minus", "formula": cum_trip_current_minus_cal},
    {"name": "cb_op_char_over_minus", "formula": cb_op_char_over_minus_cal},
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


def calculate(input_row: dict) -> dict:
    """input_row(INPUT_COLUMNS 값들)를 받아 전체 계산 컬럼을 더한 dict를 반환한다.
    원본을 바꾸지 않도록 복사본에 계산한다."""
    row = dict(input_row)
    for col in CALCULATED_COLUMNS:
        row[col["name"]] = col["formula"](row)
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
            cb_op_char_over=row["cb_op_char_over"],
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
    # 계산 컬럼 이름 = 테이블 컬럼 이름이라 그대로 옮긴다.
    await session.merge(
        GisScoreDetail(equipment_id=equipment_id, **{name: row[name] for name in _SCORE_DETAIL_FIELDS})
    )
