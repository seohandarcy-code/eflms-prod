"""EF3(초고압케이블) 설비유형 계산기 (Stage 9-2).

`ref_data/schema_eflms_cable.py`(2026-10-20 수정본)의 INPUT_COLUMNS/CALCULATED_COLUMNS 공식을
**그대로** 이식했다 — 공식을 원본과 다르게 해석한 곳은 없다(경과연수 PoF 합산, 공급신뢰도 1회선 -20,
사고복구비용 최소 -2, 음수 점수 허용 모두 원본대로, docs/DATA_DICTIONARY.md EF3 절).
tests/test_ef3_cable.py가 같은 입력으로 원본과 결과를 대조한다.

원본과 다른 점:
- 계산 기준일을 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과). EF1·EF2와 같다.
- 임포트 허용값(choices/min/required) 추가 — 원본은 모르는 문자열을 조용히 감점 0으로 처리하므로,
  오타가 0점으로 섞이지 않게 원본 판정에 쓰이는 값만 받는다. 회선별용량은 부하율의 분모라 1 이상.
  mock 생성기는 원본 범위를 그대로 쓰고, 생성값도 이 검증을 통과한다.
- 화면 라벨(BREAKDOWN): 원본 계산 라벨에서 "감점"만 뗀다. 단 age_minus는 원본 라벨 "경과일"이
  실제로는 연수라 EF1·EF2와 같은 "경과연수"로 쓴다(2026-10-20 사용자 결정).

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

# ------------------------------------------------------------------
# 1. INPUT COLUMNS
# ------------------------------------------------------------------
# 허용값(임포트 검증용, app/services/import_service.py):
#   choices  : 이 값 중 하나여야 함 / min, max : 수치 범위 / required : 빈 문자열 거부
_OX = ["O", "X"]

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
    {"name": "operation_start_time", "label": "가동년월", "dtype": "date",
     "generator": lambda: date(2005, 1, 1) + timedelta(days=random.randint(0, 3650))},
    {"name": "max_load", "label": "최대부하", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(80, 200)},
    {"name": "max_temp", "label": "최고온도", "dtype": "float",
     "generator": lambda: random.randint(200, 300) / 10},
    {"name": "diff_temp", "label": "상간온도차", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(5, 40) / 10},
    {"name": "failure_rate", "label": "온도기반손상률", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(60, 700) / 100000},
    {"name": "pd_num", "label": "부분방전발생횟수", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(0, 3)},
    {"name": "sys_cycle_curr", "label": "시스순환전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(20, 400) / 10},
    {"name": "svl_leak_curr", "label": "SVL누설전류", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 150) / 1000},
    {"name": "joint_ex_damage", "label": "접속함외관손상여부", "dtype": "str", "choices": ["양호", "이상"],
     "generator": lambda: random.choice(["양호", "이상"])},
    {"name": "cable_move", "label": "케이블이동량", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 100) / 10},
    {"name": "cable_length", "label": "케이블길이", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(300, 15000)},
    {"name": "laying_type", "label": "포설방법", "dtype": "str", "choices": ["철탑", "공동구", "관로구", "전력구"],
     "generator": lambda: random.choice(["관로구", "전력구", "공동구"])},
    {"name": "mid_joint", "label": "중간접속함개수", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(0, 10)},
    # "DEBG, EBA"는 쉼표가 들어간 값 하나다(원본 표기 그대로).
    {"name": "end_joint", "label": "종단접속함종류", "dtype": "str", "choices": ["WEBG", "DEBG, EBA", "DEBG"],
     "generator": lambda: random.choice(["DEBG, EBA", "DEBG", "WEBG"])},
    {"name": "emerge_resp", "label": "비상대응시간", "dtype": "str",
     "choices": ["24시간이하", "12시간이하", "1시간이하", "1초내"],
     "generator": lambda: random.choice(["1초내"])},
    {"name": "rep_time", "label": "정상화기간_설비교체", "dtype": "str", "choices": ["3개월초과", "3개월이하"],
     "generator": lambda: random.choice(["3개월이하"])},
    {"name": "reliability", "label": "공급신뢰도회선수", "dtype": "int", "min": 1,
     "generator": lambda: random.choice([2, 3, 4])},
    {"name": "temp_diag", "label": "열화상진단여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["O"])},
    {"name": "pd_diag", "label": "PD진단여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["O"])},
    {"name": "live_line_diag", "label": "활선진단여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["X"])},
    {"name": "cable_move_diag", "label": "이동량여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["X"])},
    {"name": "offline_diag", "label": "오프라인진단여부", "dtype": "str", "choices": ["미실시", "3년이내", "1년이내"],
     "generator": lambda: random.choice(["1년이내"])},
    {"name": "longlife_insul", "label": "장수명절연물여부", "dtype": "str", "choices": _OX,
     "generator": lambda: random.choice(["X"])},
]


def generate_input_row() -> dict:
    return {col["name"]: col["generator"]() for col in INPUT_COLUMNS}


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (원본 공식 그대로)
# ------------------------------------------------------------------
def load_minus_cal(row):
    s = row["load_percent"]
    if s > 100: return -20
    if s > 90: return -10
    if s > 80: return -5
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


def pd_minus_cal(row):
    s = row["pd_num"]
    if s >= 3: return -20
    if s >= 1: return -10
    return 0


def sys_cycle_curr_minus_cal(row):
    s = row["sys_cycle_curr"]
    if s > 100: return -10
    if s > 50: return -5
    return 0


def svl_leak_curr_minus_cal(row):
    s = row["svl_leak_curr"]
    if s > 1: return -10
    if s > 0.5: return -5
    return 0


def joint_ex_damage_minus_cal(row):
    return 0 if row["joint_ex_damage"] == "양호" else -5


def cable_move_minus_cal(row):
    s = row["cable_move"]
    if s > 10: return -20
    if s > 5: return -15
    if s > 3: return -10
    if s > 1: return -5
    return 0


def pof_minus_cal(row):
    return (
        row["age_minus"] + row["load_minus"] + row["temp_minus"]
        + row["diff_temp_minus"] + row["failure_rate_minus"] + row["pd_minus"]
        + row["sys_cycle_curr_minus"] + row["svl_leak_curr_minus"] + row["joint_ex_damage_minus"]
        + row["cable_move_minus"]
    )


_LAYING_TYPE = {"철탑": -30, "공동구": -20, "관로구": -10, "전력구": 0}
_END_JOINT = {"WEBG": -30, "DEBG, EBA": -5, "DEBG": 0}
_EMERGE_RESP = {"24시간이하": -10, "12시간이하": -5, "1시간이하": -3, "1초내": 0}
_REP_TIME = {"3개월초과": -10, "3개월이하": 0}


def rep_cost_minus_cal(row):
    s = row["rep_cost"]
    if s > 100: return -12
    if s > 50: return -10
    if s > 20: return -8
    if s > 10: return -6
    if s > 5: return -4
    return -2


def cof_minus_cal(row):
    return (
        row["risk_mva_minus"] + row["laying_type_minus"] + row["mid_joint_minus"]
        + row["end_joint_minus"] + row["emerge_resp_minus"] + row["rep_cost_minus"]
        + row["rep_time_minus"]
    )


def reliability_minus_cal(row):
    # 원본: 4·3회선 0, 그 외(2회선·1회선) -20
    return 0 if row["reliability"] in (3, 4) else -20


def _ox_minus(field):
    return lambda row: -10 if row[field] == "X" else 0


_OFFLINE_DIAG = {"미실시": -20, "3년이내": -10, "1년이내": 0}


def dof_minus_cal(row):
    return (
        row["reliability_minus"] + row["temp_diag_minus"] + row["pd_diag_minus"]
        + row["live_line_diag_minus"] + row["cable_move_diag_minus"] + row["offline_diag_minus"]
        + row["longlife_insul_minus"]
    )


CALCULATED_COLUMNS = [
    # 계산 기준일은 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과).
    {"name": "today", "formula": lambda row: row["_as_of"]},
    {"name": "operation_year", "formula": lambda row: round((row["today"] - row["operation_start_time"]).days / 365, 1)},
    {"name": "age_minus", "formula": lambda row: -(math.floor(row["operation_year"]))},
    {"name": "load_percent", "formula": lambda row: row["max_load"] / row["cable_mva"] * 100},
    {"name": "load_minus", "formula": load_minus_cal},
    {"name": "temp_minus", "formula": temp_minus_cal},
    {"name": "diff_temp_minus", "formula": diff_temp_minus_cal},
    {"name": "failure_rate_minus", "formula": lambda row: round(row["failure_rate"] * (-1000))},
    {"name": "pd_minus", "formula": pd_minus_cal},
    {"name": "sys_cycle_curr_minus", "formula": sys_cycle_curr_minus_cal},
    {"name": "svl_leak_curr_minus", "formula": svl_leak_curr_minus_cal},
    {"name": "joint_ex_damage_minus", "formula": joint_ex_damage_minus_cal},
    {"name": "cable_move_minus", "formula": cable_move_minus_cal},
    {"name": "pof_minus", "formula": pof_minus_cal},
    {"name": "pof", "formula": lambda row: 100 + row["pof_minus"]},
    {"name": "risk_mva", "formula": lambda row: row["cable_mva"]},
    {"name": "risk_mva_minus", "formula": lambda row: round(row["cable_mva"] * 0.01 * (-1))},
    {"name": "laying_type_minus", "formula": lambda row: _LAYING_TYPE.get(row["laying_type"], 0)},
    {"name": "mid_joint_minus", "formula": lambda row: (-1) * row["mid_joint"]},
    {"name": "end_joint_minus", "formula": lambda row: _END_JOINT.get(row["end_joint"], 0)},
    {"name": "emerge_resp_minus", "formula": lambda row: _EMERGE_RESP.get(row["emerge_resp"], 0)},
    {"name": "rep_cost", "formula": lambda row: row["cable_length"] * 0.0135},
    {"name": "rep_cost_minus", "formula": rep_cost_minus_cal},
    {"name": "rep_time_minus", "formula": lambda row: _REP_TIME.get(row["rep_time"], 0)},
    {"name": "cof_minus", "formula": cof_minus_cal},
    {"name": "cof", "formula": lambda row: 100 + row["cof_minus"]},
    {"name": "reliability_minus", "formula": reliability_minus_cal},
    {"name": "temp_diag_minus", "formula": _ox_minus("temp_diag")},
    {"name": "pd_diag_minus", "formula": _ox_minus("pd_diag")},
    {"name": "live_line_diag_minus", "formula": _ox_minus("live_line_diag")},
    {"name": "cable_move_diag_minus", "formula": _ox_minus("cable_move_diag")},
    {"name": "offline_diag_minus", "formula": lambda row: _OFFLINE_DIAG.get(row["offline_diag"], 0)},
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
    CableSpec: ("cable_sq", "cable_per_phase", "cable_mva", "cable_length", "laying_type", "mid_joint", "end_joint"),
    CableCondition: (
        "max_load", "max_temp", "diff_temp", "failure_rate", "pd_num",
        "sys_cycle_curr", "svl_leak_curr", "joint_ex_damage", "cable_move",
    ),
    CableConsequenceAttribute: ("emerge_resp", "rep_time"),
    CableDesignAttribute: (
        "reliability", "temp_diag", "pd_diag", "live_line_diag", "cable_move_diag", "offline_diag", "longlife_insul",
    ),
}
_TIME_COLUMN = {CableSpec: "updated_at", CableCondition: "measured_at",
                CableConsequenceAttribute: "updated_at", CableDesignAttribute: "updated_at"}


async def ingest_domain(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """calculate()가 만든 flat dict에서 EF3 전용 테이블들에 upsert한다. commit하지 않는다."""
    for model, names in _INPUTS_BY_MODEL.items():
        await session.merge(
            model(equipment_id=equipment_id, **{_TIME_COLUMN[model]: row["today"]}, **{n: row[n] for n in names})
        )
    # 계산 컬럼 이름 = 테이블 컬럼 이름이라 그대로 옮긴다.
    await session.merge(
        CableScoreDetail(equipment_id=equipment_id, **{name: row[name] for name in _SCORE_DETAIL_FIELDS})
    )


# ------------------------------------------------------------------
# 4. 조회
# ------------------------------------------------------------------
# 감점 항목 메타데이터 — 원본 계산 라벨에서 "감점"을 뗀 표현. 원본에 PoF 그룹 구분이 없어 group은 두지 않는다.
BREAKDOWN = {
    "pof": [
        {"field": "age_minus", "label": "경과연수"},
        {"field": "load_minus", "label": "부하율"},
        {"field": "temp_minus", "label": "온도"},
        {"field": "diff_temp_minus", "label": "열화상"},
        {"field": "failure_rate_minus", "label": "온도기반손상률"},
        {"field": "pd_minus", "label": "부분방전발생횟수"},
        {"field": "sys_cycle_curr_minus", "label": "시스템순환전류"},
        {"field": "svl_leak_curr_minus", "label": "SVL누설전류"},
        {"field": "joint_ex_damage_minus", "label": "접속함외관"},
        {"field": "cable_move_minus", "label": "케이블이동량"},
    ],
    "cof": [
        {"field": "risk_mva_minus", "label": "사고영향성"},
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
        row.update({name: getattr(by_model[model], name) for name in names})
    return row, by_model[CableScoreDetail].today


async def last_diag_dates(session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
    """화면의 '최근 진단일' — 원본에 진단일 입력이 없어 EF3는 상태값 측정일(반영 기준일)."""
    if not equipment_ids:
        return {}
    stmt = select(CableCondition.equipment_id, CableCondition.measured_at).where(CableCondition.equipment_id.in_(equipment_ids))
    return dict((await session.execute(stmt)).all())


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
