"""EF3(초고압케이블) 설비유형 계산기 (Stage 9-2, Stage 22 횡전개 개정 2026-11-20).

계산 기준: `ref_data_revised/schema_eflms_cable.py` — 2026-11-20 사용자가 준 횡전개 수정본(`ref_data/` 원본 EF3는 옛 양식).
그 파일의 INPUT_COLUMNS/CALCULATED_COLUMNS 공식을 그대로 옮겼다. tests/test_ef3_cable.py가 경계값을,
tests/test_reference_revised.py가 무작위 입력 300건을 그 파일과 대조한다.

Stage 22 주요 변경(옛 양식 대비, docs/DATA_DICTIONARY.md EF3 절):
- 진단결과 등급 감점: PD(pd_diag_rslt)·시스순환전류·SVL·피뢰기누설전류(이상 -8 / 요주의 -4). 피뢰기 감점은 수정본의
  계산 목록에 빠져 있던 것을 채웠다(POF 합계에는 있었음, 2026-11-20 사용자 확인).
- 온도기반손상률은 입력이 아니라 계산값 — (운전년수/40)·(1+0.005·상간온도차²)/온도가속계수. 운전년수를 쓰므로
  기준일이 지나면 커진다(매일 갱신·5개년 예측에 반영).
- COF: 공동포설(-5 × 타T/L회선수) 추가, 포설방법·종단접속함은 1·2 중 나쁜 값, 비상대응시간·사고복구비용·정상화기간 등급.
  케이블길이(사고복구비용 계산) 삭제. DOF: 공급신뢰도 N+0/N+1/N+N, 오프라인진단 O/X.

원본과 다른 점(시스템 규칙):
- 감점 소수 계산(2026-11-19): 감점은 소수 그대로, na.evaluate()가 float·소수 첫째 자리로 통일(rounding.py).
- 계산 기준일을 calculate(as_of=)로 받는다(기본 오늘).
- 임포트 허용값(choices/min/required) — 원본은 모르는 문자열을 조용히 감점 0으로 처리하므로 판정에 쓰이는 값만 받는다.
  최고온도는 -50 이상(온도가속계수 exp 계산이 넘치지 않게).
- 입력 `3rd_har_leak_curr`는 숫자로 시작해 DB 컬럼은 `third_har_leak_curr`(입력 파일·화면 이름은 그대로).
- 화면 라벨(BREAKDOWN): 원본 계산 라벨에서 "감점"만 뗀다. age_minus는 "경과연수"(2026-10-20 사용자 결정).

공개 인터페이스는 app/equipment_types/base.py의 EquipmentTypeModule.
"""
import itertools
import math
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CableCondition,
    CableConsequenceAttribute,
    CableDesignAttribute,
    CableScoreDetail,
    CableSpec,
    Equipment,
)
from app.equipment_types.na import evaluate
from app.equipment_types.rounding import round1
from app.schemas.ef3 import (
    CableConditionOut,
    CableConsequenceAttributeOut,
    CableDesignAttributeOut,
    CableScoreDetailOut,
    CableSpecOut,
    Ef3Detail,
)

EF_CODE = "EF3"
EF_NAME = "초고압케이블"
NAME_FIELD = "tl_name"
DOMAIN_TABLES = [
    CableScoreDetail,
    CableSpec,
    CableCondition,
    CableConsequenceAttribute,
    CableDesignAttribute,
]
# 계산 결과 테이블 — 점수 기준일(today)을 여기서 읽는다(Stage 21-1, 요약 API의 점수 기준일)
SCORE_DETAIL_MODEL = CableScoreDetail

# ------------------------------------------------------------------
# 1. INPUT COLUMNS
# ------------------------------------------------------------------
# 허용값(임포트 검증용, app/services/import_service.py):
#   choices  : 이 값 중 하나여야 함 / min, max : 수치 범위 / required : 빈 문자열 거부
_OX = ["O", "X"]
_DIAG3 = ["양호", "요주의", "이상"]          # PD·시스순환전류·온도·열화상 진단결과
_DIAG3_NORMAL = ["정상", "요주의", "이상"]   # SVL·피뢰기 누설전류 진단결과(기준 파일 표기 그대로)
_LAYING = ["철탑", "공동구", "관로구", "전력구"]
_END_JOINT = ["WEBG", "철탑EBA", "단독EBA", "DEBG"]

_tl_name_counters = {"tl": itertools.count(1), "htl": itertools.count(1)}


def _gen_tl_name():
    """접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["tl", "htl"])
    return f"{prefix}{next(_tl_name_counters[prefix])}"


INPUT_COLUMNS = [
    {"name": "factory_code", "label": "사업장명", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["H1", "H2", "K1", "P1"])},
    {"name": "EF_code", "label": "전기설비코드", "dtype": "str", "choices": [EF_CODE],
     "generator": lambda: EF_CODE},
    {"name": "tl_name", "label": "T/L명", "dtype": "str", "required": True,
     "generator": _gen_tl_name},
    # 계산에 쓰이지 않아 전압값은 제한하지 않는다(2026-10-20 결정).
    {"name": "voltage", "label": "전압", "dtype": "int", "min": 1,
     "generator": lambda: random.choice([154000])},
    {"name": "cable_sq", "label": "굵기", "dtype": "int", "min": 1,
     "generator": lambda: random.choice([1200, 1600])},
    {"name": "cable_per_phase", "label": "phase당케이블", "dtype": "int", "min": 1,
     "generator": lambda: random.choice([1, 2])},
    {"name": "cable_mva", "label": "회선별용량", "dtype": "int", "min": 1,
     "generator": lambda: random.choice([414, 984])},
    # 화면의 "최근 진단일"(Stage 22) — 계산에는 쓰이지 않는다
    {"name": "recent_diag_date", "label": "안전공사최근진단일", "dtype": "date",
     "generator": lambda: date(2026, 1, 1)},
    {"name": "operation_start_time", "label": "가동년월", "dtype": "date",
     "generator": lambda: date(2005, 1, 1) + timedelta(days=random.randint(0, 3650))},
    {"name": "max_load", "label": "최대부하", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(80, 200)},
    {"name": "max_temp", "label": "최고온도", "dtype": "float", "min": -50,
     "generator": lambda: random.randint(200, 300) / 10},
    {"name": "max_temp_diag", "label": "온도진단결과", "dtype": "str", "choices": _DIAG3,
     "generator": lambda: random.choice(_DIAG3)},
    {"name": "diff_temp", "label": "상간온도차", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(5, 40) / 10},
    {"name": "diff_temp_diag", "label": "열화상진단결과", "dtype": "str", "choices": _DIAG3,
     "generator": lambda: random.choice(_DIAG3)},
    {"name": "pd_signal_3Mhz", "label": "PD신호크기(3Mhz)", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(10, 90)},
    {"name": "pd_signal_6Mhz", "label": "PD신호크기(6Mhz)", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(40, 95)},
    {"name": "pd_signal_10Mhz", "label": "PD신호크기(10Mhz)", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(50, 95)},
    {"name": "pd_diag_rslt", "label": "PD진단결과", "dtype": "str", "choices": _DIAG3,
     "generator": lambda: random.choice(_DIAG3)},
    {"name": "pd_num", "label": "부분방전발생횟수", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(0, 3)},
    {"name": "sys_cycle_theo_curr", "label": "시스순환전류이론치", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(20, 400) / 10},
    {"name": "sys_cycle_curr", "label": "시스순환전류실측치", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(20, 400) / 10},
    {"name": "sys_cycle_curr_diag", "label": "시스순환전류진단결과", "dtype": "str", "choices": _DIAG3,
     "generator": lambda: random.choice(_DIAG3)},
    {"name": "svl_leak_curr", "label": "SVL누설전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 150) / 1000},
    {"name": "svl_leak_curr_diag", "label": "SVL누설전류진단결과", "dtype": "str", "choices": _DIAG3_NORMAL,
     "generator": lambda: random.choice(_DIAG3_NORMAL)},
    {"name": "basic_leak_curr", "label": "기본파누설전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(400, 970) / 1000},
    # 숫자로 시작하는 이름 — DB 컬럼은 third_har_leak_curr(_DB_COLUMN)
    {"name": "3rd_har_leak_curr", "label": "3고조파누설전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 20) / 1000},
    {"name": "la_leak_curr_diag", "label": "피뢰기누설전류진단결과", "dtype": "str", "choices": _DIAG3_NORMAL,
     "generator": lambda: random.choice(_DIAG3_NORMAL)},
    {"name": "joint_ex_damage", "label": "접속함외관손상여부", "dtype": "str", "choices": ["양호", "이상"],
     "generator": lambda: random.choice(["양호", "이상"])},
    {"name": "cable_move", "label": "케이블이동량", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 100) / 10},
    # 계산에는 회선수만 쓴다 — 표기가 정해지지 않아 공동포설여부 값은 제한하지 않는다
    {"name": "tl_apply", "label": "타T/L공동포설여부", "dtype": "str",
     "generator": lambda: random.choice(["단독"])},
    {"name": "tl_num", "label": "타T/L회선수", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([0])},
    {"name": "laying_type", "label": "포설방법1", "dtype": "str", "choices": _LAYING,
     "generator": lambda: random.choice(["철탑"])},
    {"name": "laying_type2", "label": "포설방법2", "dtype": "str", "choices": _LAYING,
     "generator": lambda: random.choice(["관로구"])},
    {"name": "mid_joint", "label": "중간접속함개수", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(0, 10)},
    {"name": "end_joint", "label": "종단접속함종류1", "dtype": "str", "choices": _END_JOINT,
     "generator": lambda: random.choice(["단독EBA"])},
    {"name": "end_joint2", "label": "종단접속함종류2", "dtype": "str", "choices": _END_JOINT,
     "generator": lambda: random.choice(["DEBG", "WEBG"])},
    {"name": "emerge_resp", "label": "비상대응시간", "dtype": "str", "choices": list("ABCDEFG"),
     "generator": lambda: random.choice(["G"])},
    {"name": "rep_cost", "label": "사고복구비용", "dtype": "str", "choices": list("ABCDE"),
     "generator": lambda: random.choice(["A"])},
    {"name": "rep_time", "label": "정상화기간", "dtype": "str", "choices": list("ABCD"),
     "generator": lambda: random.choice(["C"])},
    {"name": "reliability", "label": "공급신뢰도회선수", "dtype": "str", "choices": ["N+0", "N+1", "N+N"],
     "generator": lambda: random.choice(["N+N"])},
    {"name": "temp_diag", "label": "열화상진단여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["O"])},
    {"name": "pd_diag", "label": "PD진단여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["O"])},
    {"name": "live_line_diag", "label": "활선진단여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["X"])},
    {"name": "cable_move_diag", "label": "이동량여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["X"])},
    {"name": "offline_diag", "label": "오프라인진단여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["O"])},
    {"name": "longlife_insul", "label": "장수명절연물여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["X"])},
]


def generate_input_row() -> dict:
    return {col["name"]: col["generator"]() for col in INPUT_COLUMNS}


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (기준 파일 공식 그대로)
# ------------------------------------------------------------------
def load_minus_cal(row):
    s = row["load_percent"]
    if s > 100: return -36
    if s > 90: return -24
    if s > 80: return -12
    return 0


def temp_minus_cal(row):
    s = row["max_temp"]
    if s > 90: return -20
    if s > 80: return -10
    if s > 70: return -5
    return 0


def diff_temp_minus_cal(row):
    s = row["diff_temp"]
    if s > 10: return -10
    if s > 5: return -5
    return 0


def failure_rate_cal(row):
    """온도기반손상률 = (운전년수/40) × (1 + 0.005×상간온도차²) ÷ 온도가속계수.
    온도가속계수 = exp((1.2/0.00008617) × (1/(최고온도+298.15) − 1/363.15)) — 기준 파일 그대로."""
    accel = math.exp((1.2 / 0.00008617) * (1 / (row["max_temp"] + 298.15) - 1 / 363.15))
    return (row["operation_year"] / 40) * ((1 + 0.005 * (row["diff_temp"] ** 2)) / accel)


_DIAG_MINUS = {"이상": -8, "요주의": -4}


def _diag_minus(field):
    # 양호·정상(그 밖) 0 — 기준 파일 판정 그대로
    return lambda row: _DIAG_MINUS.get(row[field], 0)


def joint_ex_damage_minus_cal(row):
    return 0 if row["joint_ex_damage"] == "양호" else -1


def cable_move_minus_cal(row):
    s = row["cable_move"]
    if s > 5: return -8
    if s > 3: return -5
    if s > 1: return -3
    return 0


def pof_minus_cal(row):
    return (
        row["age_minus"] + row["load_minus"] + row["temp_minus"]
        + row["diff_temp_minus"] + row["failure_rate_minus"] + row["pd_minus"]
        + row["sys_cycle_curr_minus"] + row["svl_leak_curr_minus"]
        + row["la_leak_curr_minus"] + row["joint_ex_damage_minus"]
        + row["cable_move_minus"]
    )


_LAYING_MINUS = {"철탑": -24, "공동구": -16, "관로구": -8, "전력구": 0}
_END_JOINT_MINUS = {"WEBG": -24, "철탑EBA": -12, "단독EBA": -6, "DEBG": 0}
_EMERGE_RESP = {"A": -6, "B": -5, "C": -4, "D": -3, "E": -2, "F": -1, "G": 0}
_REP_COST = {"A": -8, "B": -6, "C": -4, "D": -2, "E": 0}
_REP_TIME = {"A": -6, "B": -4, "C": -2, "D": 0}
_RELIABILITY = {"N+0": -24, "N+1": -12, "N+N": 0}


def _worse_of_two(field1, field2, table):
    """1·2 중 나쁜(더 작은) 감점 — 기준 파일의 min(a, b). 어느 한쪽이라도 N/A면 공통 N/A 규칙대로 감점 0(na.py)."""
    return lambda row: min(table.get(row[field1], 0), table.get(row[field2], 0))


def cof_minus_cal(row):
    return (
        row["risk_mva_minus"] + row["tl_minus"]
        + row["laying_type_minus"] + row["mid_joint_minus"]
        + row["end_joint_minus"] + row["emerge_resp_minus"] + row["rep_cost_minus"]
        + row["rep_time_minus"]
    )


def _ox_minus(field):
    return lambda row: -10 if row[field] == "X" else 0


def dof_minus_cal(row):
    return (
        row["reliability_minus"] + row["temp_diag_minus"] + row["pd_diag_minus"]
        + row["live_line_diag_minus"] + row["cable_move_diag_minus"] + row["offline_diag_minus"]
        + row["longlife_insul_minus"]
    )


CALCULATED_COLUMNS = [
    # 계산 기준일은 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과).
    {"name": "today", "formula": lambda row: row["_as_of"]},
    {"name": "operation_year", "formula": lambda row: round1((row["today"] - row["operation_start_time"]).days / 365)},
    {"name": "age_minus", "formula": lambda row: -row["operation_year"]},
    {"name": "load_percent", "formula": lambda row: row["max_load"] / row["cable_mva"] * 100},
    {"name": "load_minus", "formula": load_minus_cal},
    {"name": "temp_minus", "formula": temp_minus_cal},
    {"name": "diff_temp_minus", "formula": diff_temp_minus_cal},
    {"name": "failure_rate", "formula": failure_rate_cal},
    {"name": "failure_rate_minus", "formula": lambda row: row["failure_rate"] * (-1000)},
    {"name": "pd_minus", "formula": _diag_minus("pd_diag_rslt")},
    {"name": "sys_cycle_curr_minus", "formula": _diag_minus("sys_cycle_curr_diag")},
    {"name": "svl_leak_curr_minus", "formula": _diag_minus("svl_leak_curr_diag")},
    {"name": "la_leak_curr_minus", "formula": _diag_minus("la_leak_curr_diag")},
    {"name": "joint_ex_damage_minus", "formula": joint_ex_damage_minus_cal},
    {"name": "cable_move_minus", "formula": cable_move_minus_cal},
    {"name": "pof_minus", "formula": pof_minus_cal},
    {"name": "pof", "formula": lambda row: 100 + row["pof_minus"]},
    {"name": "risk_mva", "formula": lambda row: row["cable_mva"]},
    {"name": "risk_mva_minus", "formula": lambda row: row["cable_mva"] * 0.01 * (-1)},
    {"name": "tl_minus", "formula": lambda row: (-5) * row["tl_num"]},
    {"name": "laying_type_minus", "formula": _worse_of_two("laying_type", "laying_type2", _LAYING_MINUS)},
    {"name": "mid_joint_minus", "formula": lambda row: (-1) * row["mid_joint"]},
    {"name": "end_joint_minus", "formula": _worse_of_two("end_joint", "end_joint2", _END_JOINT_MINUS)},
    {"name": "emerge_resp_minus", "formula": lambda row: _EMERGE_RESP.get(row["emerge_resp"], 0)},
    {"name": "rep_cost_minus", "formula": lambda row: _REP_COST.get(row["rep_cost"], 0)},
    {"name": "rep_time_minus", "formula": lambda row: _REP_TIME.get(row["rep_time"], 0)},
    {"name": "cof_minus", "formula": cof_minus_cal},
    {"name": "cof", "formula": lambda row: 100 + row["cof_minus"]},
    {"name": "reliability_minus", "formula": lambda row: _RELIABILITY.get(row["reliability"], 0)},
    {"name": "temp_diag_minus", "formula": _ox_minus("temp_diag")},
    {"name": "pd_diag_minus", "formula": _ox_minus("pd_diag")},
    {"name": "live_line_diag_minus", "formula": _ox_minus("live_line_diag")},
    {"name": "cable_move_diag_minus", "formula": _ox_minus("cable_move_diag")},
    {"name": "offline_diag_minus", "formula": _ox_minus("offline_diag")},
    {"name": "longlife_insul_minus", "formula": _ox_minus("longlife_insul")},
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
# 3. DB 적재 (EF3 전용 테이블)
# ------------------------------------------------------------------
_SCORE_DETAIL_FIELDS = [c.name for c in CableScoreDetail.__table__.columns if c.name not in ("equipment_id", "computed_at")]

# 입력 컬럼 이름 = 테이블 컬럼 이름(원본 → DB 그대로 저장). 시점 컬럼은 계산 기준일(today).
_INPUTS_BY_MODEL = {
    CableSpec: (
        "cable_sq", "cable_per_phase", "cable_mva", "tl_apply", "tl_num",
        "laying_type", "laying_type2", "mid_joint", "end_joint", "end_joint2",
    ),
    CableCondition: (
        "recent_diag_date", "max_load", "max_temp", "max_temp_diag", "diff_temp", "diff_temp_diag",
        "pd_signal_3Mhz", "pd_signal_6Mhz", "pd_signal_10Mhz", "pd_diag_rslt", "pd_num",
        "sys_cycle_theo_curr", "sys_cycle_curr", "sys_cycle_curr_diag", "svl_leak_curr", "svl_leak_curr_diag",
        "basic_leak_curr", "3rd_har_leak_curr", "la_leak_curr_diag", "joint_ex_damage", "cable_move",
    ),
    CableConsequenceAttribute: ("emerge_resp", "rep_cost", "rep_time"),
    CableDesignAttribute: (
        "reliability", "temp_diag", "pd_diag", "live_line_diag", "cable_move_diag", "offline_diag", "longlife_insul",
    ),
}
# 입력 이름을 파이썬 속성으로 못 쓰는 것만 DB 컬럼 이름이 다르다(EF1 1st_voltage_minus와 같은 방식)
_DB_COLUMN = {"3rd_har_leak_curr": "third_har_leak_curr"}
_TIME_COLUMN = {CableSpec: "updated_at", CableCondition: "measured_at",
                CableConsequenceAttribute: "updated_at", CableDesignAttribute: "updated_at"}


async def ingest_domain(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """calculate()가 만든 flat dict에서 EF3 전용 테이블들에 upsert한다. commit하지 않는다."""
    for model, names in _INPUTS_BY_MODEL.items():
        await session.merge(
            model(equipment_id=equipment_id, **{_TIME_COLUMN[model]: row["today"]},
                  **{_DB_COLUMN.get(n, n): row[n] for n in names})
        )
    await ingest_scores(row, equipment_id, session)


async def ingest_scores(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """계산 결과 테이블만 upsert한다 — 점수 갱신(app/services/score_refresh_service.py)은 입력 테이블을 건드리지 않고
    이것만 부른다(2026-11-19, Stage 21-1). commit하지 않는다."""
    # 계산 컬럼 이름 = 테이블 컬럼 이름이라 그대로 옮긴다.
    await session.merge(
        CableScoreDetail(equipment_id=equipment_id, **{name: row[name] for name in _SCORE_DETAIL_FIELDS})
    )


# ------------------------------------------------------------------
# 4. 조회
# ------------------------------------------------------------------
# 감점 항목 메타데이터 — 기준 파일 계산 라벨에서 "감점"을 뗀 표현. PoF 그룹 구분이 없어 group은 두지 않는다.
BREAKDOWN = {
    "pof": [
        {"field": "age_minus", "label": "경과연수"},
        {"field": "load_minus", "label": "부하율"},
        {"field": "temp_minus", "label": "온도"},
        {"field": "diff_temp_minus", "label": "열화상"},
        {"field": "failure_rate_minus", "label": "온도기반손상률"},
        {"field": "pd_minus", "label": "부분방전"},
        {"field": "sys_cycle_curr_minus", "label": "시스템순환전류"},
        {"field": "svl_leak_curr_minus", "label": "SVL누설전류"},
        {"field": "la_leak_curr_minus", "label": "피뢰기누설전류"},
        {"field": "joint_ex_damage_minus", "label": "접속함외관"},
        {"field": "cable_move_minus", "label": "케이블이동량"},
    ],
    "cof": [
        {"field": "risk_mva_minus", "label": "사고영향성(용량)"},
        {"field": "tl_minus", "label": "사고영향성(공동포설)"},
        {"field": "laying_type_minus", "label": "포설방법"},
        {"field": "mid_joint_minus", "label": "중간접속함"},
        {"field": "end_joint_minus", "label": "종단접속함"},
        {"field": "emerge_resp_minus", "label": "비상대응시간"},
        {"field": "rep_cost_minus", "label": "사고복구비용"},
        {"field": "rep_time_minus", "label": "정상화기간"},
    ],
    "dof": [
        {"field": "reliability_minus", "label": "공급신뢰도"},
        {"field": "temp_diag_minus", "label": "열화상진단"},
        {"field": "pd_diag_minus", "label": "PD진단"},
        {"field": "live_line_diag_minus", "label": "활선진단"},
        {"field": "cable_move_diag_minus", "label": "케이블이동량여부"},
        {"field": "offline_diag_minus", "label": "오프라인진단"},
        {"field": "longlife_insul_minus", "label": "장수명절연물"},
    ],
}

_DOMAIN_MODELS = (CableSpec, CableCondition, CableConsequenceAttribute, CableDesignAttribute, CableScoreDetail)


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
        "tl_name": equipment.equipment_name,
        "voltage": equipment.voltage,
        "operation_start_time": equipment.operation_start_time,
    }
    for model, names in _INPUTS_BY_MODEL.items():
        row.update({name: getattr(by_model[model], _DB_COLUMN.get(name, name)) for name in names})
    return row, by_model[CableScoreDetail].today


async def last_diag_dates(session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
    """화면의 '최근 진단일' — 안전공사최근진단일(Stage 22). 비어 있으면(N/A) 상태값 측정일(반영 기준일)."""
    if not equipment_ids:
        return {}
    stmt = select(CableCondition.equipment_id, CableCondition.recent_diag_date, CableCondition.measured_at).where(
        CableCondition.equipment_id.in_(equipment_ids)
    )
    return {eq_id: diag or measured for eq_id, diag, measured in (await session.execute(stmt)).all()}


async def load_detail(session: AsyncSession, equipment_id: int) -> Ef3Detail | None:
    rows = await _load_rows(session, equipment_id)
    if rows is None:
        return None
    spec, condition, consequence, design, detail = rows
    return Ef3Detail(
        spec=CableSpecOut.model_validate(spec),
        condition=CableConditionOut.model_validate(condition),
        consequence=CableConsequenceAttributeOut.model_validate(consequence),
        design=CableDesignAttributeOut.model_validate(design),
        score_detail=CableScoreDetailOut.model_validate(detail),
    )
