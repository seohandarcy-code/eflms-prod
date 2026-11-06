"""EF5(UPS) 설비유형 계산기 (Stage 13-1).

`ref_data/schema_eflms_ups.py`(2026-11-06 수정본)의 INPUT_COLUMNS/CALCULATED_COLUMNS 공식을
**그대로** 이식했다 — 온도 보정 와이블(척도 × 2^((25−T)/10)), 차단기 7.5년 1회 교체 가정, 팬 사용수명
max(0, …), 전기실 온도 가점(25℃ 미만이면 +), 원본 안의 정수 반올림(round()/int())은 모두 원본대로다.
tests/test_ef5_ups.py가 같은 입력으로 원본과 결과를 대조한다.

원본과 다른 점:
- 소수 첫째 자리(2026-11-06 사용자 결정): 원본이 소수를 내는 사고영향성·열화상·외함 감점을 round1()
  (엑셀 ROUND식, -0.25 → -0.3)로 반올림한다. POF·COF·DOF와 종합점수는 na.evaluate()가 공통으로 반올림한다.
- 계산 기준일을 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과). EF1~EF4와 같다.
- 원본에 전압 입력이 없어 calculate()가 voltage=0을 채운다(EF4와 같음 — 공통 equipment.voltage 필수).
- 임포트 허용값(choices/min/required) 추가 — 원본 판정에 쓰이는 값만 받는다(2026-11-06 사용자 결정, 권장안).
  mock 생성기는 원본 그대로 쓰고, 생성값도 이 검증을 통과한다.
- 화면 라벨(BREAKDOWN): 원본 계산 라벨에서 "감점"만 뗀다. 원본에 소계가 없어 그룹 없이 나열한다(EF3과 같음).

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
    UpsCondition,
    UpsConsequenceAttribute,
    UpsDesignAttribute,
    UpsScoreDetail,
    UpsSpec,
)
from app.equipment_types.na import evaluate
from app.equipment_types.rounding import round1
from app.schemas.ef5 import (
    Ef5Detail,
    UpsConditionOut,
    UpsConsequenceAttributeOut,
    UpsDesignAttributeOut,
    UpsScoreDetailOut,
    UpsSpecOut,
)

EF_CODE = "EF5"
EF_NAME = "UPS"
# 설비 담당자가 설비코드로 검색하므로 eqp_id를 공통 설비명으로 쓴다(EF4와 같음).
NAME_FIELD = "eqp_id"
DOMAIN_TABLES = [
    UpsScoreDetail,
    UpsSpec,
    UpsCondition,
    UpsConsequenceAttribute,
    UpsDesignAttribute,
]

# ------------------------------------------------------------------
# 1. INPUT COLUMNS
# ------------------------------------------------------------------
# 허용값(임포트 검증용, app/services/import_service.py):
#   choices  : 이 값 중 하나여야 함 / min, max : 수치 범위 / required : 빈 문자열 거부
_NORMAL_ABNORMAL = ["정상", "이상"]
_ABC = ["A", "B", "C"]

_eqp_id_counters = {"ups": itertools.count(1)}


def _gen_eqp_id():
    """접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["ups"])
    return f"{prefix}{next(_eqp_id_counters[prefix])}"


INPUT_COLUMNS = [
    {"name": "factory_code", "label": "사업장명", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["H1", "H2", "K1", "P1"])},
    {"name": "EF_code", "label": "전기설비코드", "dtype": "str", "choices": [EF_CODE],
     "generator": lambda: EF_CODE},
    {"name": "eqp_id", "label": "eqp_id", "dtype": "str", "required": True,
     "generator": _gen_eqp_id},
    {"name": "line_no", "label": "라인", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["M1L", "S4L"])},
    {"name": "manufacturer", "label": "제작사", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["FUJI", "TMEIC"])},
    {"name": "model_name", "label": "모델명", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["7000HX", "F100"])},
    {"name": "operation_start_time", "label": "설치년월", "dtype": "date",
     "generator": lambda: date(2005, 1, 1) + timedelta(days=random.randint(0, 3650))},
    {"name": "fan_replace_no", "label": "팬교체횟수", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([0])},
    {"name": "elec_room_max_temp", "label": "전기실최대온도", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(220, 280) / 10},
    # 부하율은 % 값(원본 판정 기준 95, 부하량 = 부하율 × 정격용량 / 100).
    {"name": "load", "label": "부하율", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(400, 700) / 10},
    {"name": "mod_cir_curr", "label": "모듈간순환전류", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([3])},
    {"name": "mod_vol_diff", "label": "모듈간출력전압차이", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([3])},
    {"name": "noise", "label": "소음", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([70])},
    {"name": "thermal_img_chk", "label": "열화상", "dtype": "str", "choices": _NORMAL_ABNORMAL,
     "generator": lambda: random.choice(["정상"])},
    {"name": "ex_box_chk", "label": "외함점검", "dtype": "str", "choices": _NORMAL_ABNORMAL,
     "generator": lambda: random.choice(["정상"])},
    {"name": "capa", "label": "정격용량", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([2500])},
    {"name": "ins_build_rank", "label": "설치건물등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["A", "B", "C"])},
    {"name": "fire_spread_rank", "label": "화재확산등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["A", "B", "C"])},
    {"name": "emerge_resp", "label": "전력재공급시간등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["A", "B", "C"])},
    {"name": "rep_time", "label": "정상화기간등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["B"])},
    {"name": "rep_cost", "label": "사고복구비용등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["C"])},
    {"name": "sys_rel", "label": "계통신뢰도등급", "dtype": "str", "choices": ["N", "N+1", "N+N"],
     "generator": lambda: random.choice(["N", "N+1", "N+N"])},
    {"name": "emerge_sys", "label": "비상계통전력공급등급", "dtype": "str", "choices": ["불가", "EMG", "타설비"],
     "generator": lambda: random.choice(["EMG"])},
    {"name": "fac_rel", "label": "설비신뢰도등급", "dtype": "str", "choices": ["N", "N+1"],
     "generator": lambda: random.choice(["N+1"])},
    {"name": "part_shortage", "label": "설비모델단종여부등급", "dtype": "str", "choices": ["공급가능", "단종"],
     "generator": lambda: random.choice(["공급가능", "단종"])},
    {"name": "model_type", "label": "모델type등급", "dtype": "str", "choices": ["변압기", "무변압기"],
     "generator": lambda: random.choice(["무변압기"])},
    {"name": "switching_type", "label": "스위칭동작등급", "dtype": "str", "choices": ["2레벨PWM", "3레벨PWM"],
     "generator": lambda: random.choice(["2레벨PWM", "3레벨PWM"])},
    {"name": "igbt_rev", "label": "igbt개선등급", "dtype": "str", "choices": ["600V", "1200V"],
     "generator": lambda: random.choice(["1200V"])},
    {"name": "online_diag", "label": "온라인진단등급", "dtype": "str", "choices": ["미적용", "적용"],
     "generator": lambda: random.choice(["미적용"])},
]


def generate_input_row() -> dict:
    return {col["name"]: col["generator"]() for col in INPUT_COLUMNS}


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (원본 공식 그대로 + 소수 첫째 자리)
# ------------------------------------------------------------------
def cb_replace_no_cal(row):
    s = int(row["operation_year"] / 7.5)
    if s > 1: return 1
    return s


def load_minus_cal(row):
    s = 95 - row["load"]
    if s > 0: return 0
    return int(s * 0.75)


def mod_cir_curr_minus_cal(row):
    s = 5 - row["mod_cir_curr"]
    if s > 0: return 0
    return int(s * 0.5)


def mod_vol_diff_minus_cal(row):
    s = 5 - row["mod_vol_diff"]
    if s > 0: return 0
    return int(s * 0.5)


def noise_minus_cal(row):
    s = 80 - row["noise"]
    if s > 0: return 0
    return int(s * 0.25)


def _weibull_stat(life_field, scale, shape):
    """원본 부품 고장확률 상태점수 — 척도를 전기실 온도로 보정(25℃ 기준, 10℃ 낮을 때마다 2배)."""
    return lambda row: math.e ** (-1 * ((row[life_field] / (scale * (2 ** ((25 - row["elec_room_max_temp"]) / 10)))) ** shape))


def _stat_minus(stat_field):
    return lambda row: round((row[stat_field] - 1) * 100 * 3)


_INS_BUILD_RANK = {"A": -6, "B": -3, "C": 0}
_FIRE_SPREAD_RANK = {"A": -3, "B": 0}
_ABC_MINUS = {"A": -2, "B": -1, "C": 0}  # 전력재공급시간·정상화기간·사고복구비용
_SYS_REL = {"N": -4, "N+1": -2, "N+N": 0}
_EMERGE_SYS = {"불가": -4, "EMG": -2, "타설비": 0}

CALCULATED_COLUMNS = [
    # 계산 기준일은 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과).
    {"name": "today", "formula": lambda row: row["_as_of"]},
    {"name": "operation_year", "formula": lambda row: round((row["today"] - row["operation_start_time"]).days / 365, 1)},
    {"name": "age_minus", "formula": lambda row: -(math.floor(row["operation_year"]))},
    {"name": "cb_replace_no", "formula": cb_replace_no_cal},
    {"name": "cb_life_year", "formula": lambda row: row["operation_year"] - 7.5 * row["cb_replace_no"]},
    {"name": "cb_stat", "formula": _weibull_stat("cb_life_year", 37.44, 8.55)},
    {"name": "cb_stat_minus", "formula": _stat_minus("cb_stat")},
    {"name": "cap_life_year", "formula": lambda row: row["operation_year"]},
    {"name": "cap_stat", "formula": _weibull_stat("cap_life_year", 25.67, 7.21)},
    {"name": "cap_stat_minus", "formula": _stat_minus("cap_stat")},
    {"name": "fan_life_year", "formula": lambda row: max(0, row["operation_year"] - 7.5 * row["fan_replace_no"])},
    {"name": "fan_stat", "formula": _weibull_stat("fan_life_year", 20.22, 7.9)},
    {"name": "fan_stat_minus", "formula": _stat_minus("fan_stat")},
    {"name": "igbt_life_year", "formula": lambda row: row["operation_year"]},
    {"name": "igbt_stat", "formula": _weibull_stat("igbt_life_year", 311205.69, 0.45)},
    {"name": "igbt_stat_minus", "formula": _stat_minus("igbt_stat")},
    {"name": "board_life_year", "formula": lambda row: row["operation_year"]},
    {"name": "board_stat", "formula": _weibull_stat("board_life_year", 283.18, 0.7)},
    {"name": "board_stat_minus", "formula": _stat_minus("board_stat")},
    # 25℃보다 낮으면 가점(+)이 된다 — 원본대로(2026-11-06 확인).
    {"name": "elec_room_max_temp_minus", "formula": lambda row: round((25 - row["elec_room_max_temp"]) * 1.5)},
    {"name": "load_minus", "formula": load_minus_cal},
    {"name": "mod_cir_curr_minus", "formula": mod_cir_curr_minus_cal},
    {"name": "mod_vol_diff_minus", "formula": mod_vol_diff_minus_cal},
    {"name": "noise_minus", "formula": noise_minus_cal},
    {"name": "thermal_img_chk_minus", "formula": lambda row: round1(-0.5) if row["thermal_img_chk"] == "이상" else 0},
    {"name": "ex_box_chk_minus", "formula": lambda row: round1(-0.25) if row["ex_box_chk"] == "이상" else 0},
    {"name": "pof_minus", "formula": lambda row: (
        row["age_minus"] + row["cb_stat_minus"] + row["cap_stat_minus"]
        + row["fan_stat_minus"] + row["igbt_stat_minus"] + row["board_stat_minus"]
        + row["elec_room_max_temp_minus"] + row["load_minus"] + row["mod_cir_curr_minus"]
        + row["mod_vol_diff_minus"]
        + row["noise_minus"] + row["thermal_img_chk_minus"] + row["ex_box_chk_minus"]
    )},
    {"name": "pof", "formula": lambda row: 100 + row["pof_minus"]},
    {"name": "capa_times_load", "formula": lambda row: (row["load"] * row["capa"]) / 100},
    {"name": "capa_times_load_minus", "formula": lambda row: round1(-9 * row["capa_times_load"] / 500)},
    {"name": "ins_build_rank_minus", "formula": lambda row: _INS_BUILD_RANK.get(row["ins_build_rank"], 0)},
    {"name": "fire_spread_rank_minus", "formula": lambda row: _FIRE_SPREAD_RANK.get(row["fire_spread_rank"], 0)},
    {"name": "emerge_resp_minus", "formula": lambda row: _ABC_MINUS.get(row["emerge_resp"], 0)},
    {"name": "rep_time_minus", "formula": lambda row: _ABC_MINUS.get(row["rep_time"], 0)},
    {"name": "rep_cost_minus", "formula": lambda row: _ABC_MINUS.get(row["rep_cost"], 0)},
    {"name": "cof_minus", "formula": lambda row: (
        row["capa_times_load_minus"] + row["ins_build_rank_minus"] + row["fire_spread_rank_minus"]
        + row["emerge_resp_minus"] + row["rep_time_minus"] + row["rep_cost_minus"]
    )},
    {"name": "cof", "formula": lambda row: 100 + row["cof_minus"]},
    {"name": "sys_rel_minus", "formula": lambda row: _SYS_REL.get(row["sys_rel"], 0)},
    {"name": "emerge_sys_minus", "formula": lambda row: _EMERGE_SYS.get(row["emerge_sys"], 0)},
    {"name": "fac_rel_minus", "formula": lambda row: -9 if row["fac_rel"] == "N" else 0},
    {"name": "part_shortage_minus", "formula": lambda row: -9 if row["part_shortage"] == "단종" else 0},
    {"name": "model_type_minus", "formula": lambda row: -2 if row["model_type"] == "변압기" else 0},
    {"name": "switching_type_minus", "formula": lambda row: -1 if row["switching_type"] == "2레벨PWM" else 0},
    {"name": "igbt_rev_minus", "formula": lambda row: -1 if row["igbt_rev"] == "600V" else 0},
    {"name": "online_diag_minus", "formula": lambda row: -9 if row["online_diag"] == "미적용" else 0},
    {"name": "dof_minus", "formula": lambda row: (
        row["sys_rel_minus"] + row["emerge_sys_minus"] + row["fac_rel_minus"]
        + row["part_shortage_minus"] + row["model_type_minus"] + row["switching_type_minus"]
        + row["igbt_rev_minus"] + row["online_diag_minus"]
    )},
    {"name": "dof", "formula": lambda row: 100 + row["dof_minus"]},
    {"name": "total_score", "formula": lambda row: 0.5 * row["pof"] + 0.3 * row["cof"] + 0.2 * row["dof"]},
]


def calculate(input_row: dict, as_of: date | None = None) -> dict:
    """input_row(INPUT_COLUMNS 값들)를 받아 전체 계산 컬럼을 더한 dict를 반환한다.
    원본을 바꾸지 않도록 복사본에 계산한다. as_of는 계산 기준일(기본 오늘)."""
    # N/A(null) 입력을 읽는 공식은 감점 0 / 파생값 null, 점수 지표는 소수 첫째 자리 — na.evaluate()
    row = evaluate(input_row, CALCULATED_COLUMNS, as_of)
    # 원본에 전압 입력이 없다 — 공통 equipment.voltage(필수)에는 0을 넣는다(EF4와 같음, 화면 미표시).
    row["voltage"] = 0
    return row


# ------------------------------------------------------------------
# 3. DB 적재 (EF5 전용 테이블)
# ------------------------------------------------------------------
_SCORE_DETAIL_FIELDS = [
    c.name for c in UpsScoreDetail.__table__.columns if c.name not in ("equipment_id", "computed_at")
]

# 입력 컬럼 이름 = 테이블 컬럼 이름(원본 → DB 그대로 저장). 시점 컬럼은 계산 기준일(today).
_INPUTS_BY_MODEL = {
    UpsSpec: ("line_no", "manufacturer", "model_name", "capa"),
    UpsCondition: (
        "fan_replace_no", "elec_room_max_temp", "load", "mod_cir_curr", "mod_vol_diff", "noise",
        "thermal_img_chk", "ex_box_chk",
    ),
    UpsConsequenceAttribute: ("ins_build_rank", "fire_spread_rank", "emerge_resp", "rep_time", "rep_cost"),
    UpsDesignAttribute: (
        "sys_rel", "emerge_sys", "fac_rel", "part_shortage", "model_type", "switching_type", "igbt_rev", "online_diag",
    ),
}
_TIME_COLUMN = {UpsSpec: "updated_at", UpsCondition: "measured_at",
                UpsConsequenceAttribute: "updated_at", UpsDesignAttribute: "updated_at"}


async def ingest_domain(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """calculate()가 만든 flat dict에서 EF5 전용 테이블들에 upsert한다. commit하지 않는다."""
    for model, names in _INPUTS_BY_MODEL.items():
        await session.merge(
            model(equipment_id=equipment_id, **{_TIME_COLUMN[model]: row["today"]}, **{n: row[n] for n in names})
        )
    # 계산 컬럼 이름 = 테이블 컬럼 이름이라 그대로 옮긴다.
    await session.merge(
        UpsScoreDetail(equipment_id=equipment_id, **{name: row[name] for name in _SCORE_DETAIL_FIELDS})
    )


# ------------------------------------------------------------------
# 4. 조회
# ------------------------------------------------------------------
# 감점 항목 메타데이터 — 원본 계산 라벨에서 "감점"을 뗀 표현. 원본에 소계가 없어 그룹 없이 나열한다.
BREAKDOWN = {
    "pof": [
        {"field": "age_minus", "label": "경과년수"},
        {"field": "cb_stat_minus", "label": "차단기고장확률"},
        {"field": "cap_stat_minus", "label": "커패시터고장확률"},
        {"field": "fan_stat_minus", "label": "fan고장확률"},
        {"field": "igbt_stat_minus", "label": "igbt고장확률"},
        {"field": "board_stat_minus", "label": "보드고장확률"},
        {"field": "elec_room_max_temp_minus", "label": "전기실최고온도"},
        {"field": "load_minus", "label": "부하율"},
        {"field": "mod_cir_curr_minus", "label": "모듈간순환전류"},
        {"field": "mod_vol_diff_minus", "label": "모듈간전압차이"},
        {"field": "noise_minus", "label": "소음"},
        {"field": "thermal_img_chk_minus", "label": "열화상점검"},
        {"field": "ex_box_chk_minus", "label": "외함점검"},
    ],
    "cof": [
        {"field": "capa_times_load_minus", "label": "사고영향성"},
        {"field": "ins_build_rank_minus", "label": "설치건물등급"},
        {"field": "fire_spread_rank_minus", "label": "화재확산등급"},
        {"field": "emerge_resp_minus", "label": "사고복구시간"},
        {"field": "rep_time_minus", "label": "정상화기간"},
        {"field": "rep_cost_minus", "label": "사고복구비용"},
    ],
    "dof": [
        {"field": "sys_rel_minus", "label": "계통신뢰도"},
        {"field": "emerge_sys_minus", "label": "비상계통전력공급"},
        {"field": "fac_rel_minus", "label": "설비신뢰도"},
        {"field": "part_shortage_minus", "label": "설비모델단종여부"},
        {"field": "model_type_minus", "label": "모델타입"},
        {"field": "switching_type_minus", "label": "스위칭타입"},
        {"field": "igbt_rev_minus", "label": "IGBT개선"},
        {"field": "online_diag_minus", "label": "온라인진단"},
    ],
}

_DOMAIN_MODELS = (UpsSpec, UpsCondition, UpsConsequenceAttribute, UpsDesignAttribute, UpsScoreDetail)


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
        "eqp_id": equipment.equipment_name,
        "operation_start_time": equipment.operation_start_time,
    }
    for model, names in _INPUTS_BY_MODEL.items():
        row.update({name: getattr(by_model[model], name) for name in names})
    return row, by_model[UpsScoreDetail].today


async def last_diag_dates(session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
    """화면의 '최근 진단일' — 원본에 진단일 입력이 없어 EF5는 점검결과 반영 기준일(EF4와 같음)."""
    if not equipment_ids:
        return {}
    stmt = select(UpsCondition.equipment_id, UpsCondition.measured_at).where(
        UpsCondition.equipment_id.in_(equipment_ids)
    )
    return dict((await session.execute(stmt)).all())


async def load_detail(session: AsyncSession, equipment_id: int) -> Ef5Detail | None:
    rows = await _load_rows(session, equipment_id)
    if rows is None:
        return None
    spec, condition, consequence, design, detail = rows
    return Ef5Detail(
        spec=UpsSpecOut.model_validate(spec),
        condition=UpsConditionOut.model_validate(condition),
        consequence=UpsConsequenceAttributeOut.model_validate(consequence),
        design=UpsDesignAttributeOut.model_validate(design),
        score_detail=UpsScoreDetailOut.model_validate(detail),
    )
