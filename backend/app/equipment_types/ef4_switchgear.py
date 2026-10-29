"""EF4(수배전반) 설비유형 계산기 (Stage 10-2).

`ref_data/schema_eflms_subaejeon.py`(2026-10-29 수정본)의 INPUT_COLUMNS/CALCULATED_COLUMNS 공식을
**그대로** 이식했다 — 공식을 원본과 다르게 해석한 곳은 없다(관통형CT 미적용 -1, 피해규모 감점의
Python round(.5는 짝수 쪽), 음수 점수 허용 모두 원본대로, docs/DATA_DICTIONARY.md EF4 절).
tests/test_ef4_switchgear.py가 같은 입력으로 원본과 결과를 대조한다.

원본과 다른 점:
- 계산 기준일을 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과). EF1~EF3과 같다.
- 원본에 전압 입력이 없어 calculate()가 voltage=0을 채운다 — 공통 equipment.voltage가 필수라서다.
  공통 화면은 전압을 표시하지 않는다(Stage 10-0). 원본·실데이터 파일에는 전압 컬럼이 필요 없다.
- 임포트 허용값(choices/min/required) 추가 — 원본은 모르는 문자열을 조용히 감점/무감점으로 처리하므로,
  오타가 점수에 섞이지 않게 원본 판정에 쓰이는 값만 받는다(2026-10-29 사용자 결정, 권장안).
  mock 생성기는 원본 그대로 쓰고, 생성값도 이 검증을 통과한다.
- 화면 라벨(BREAKDOWN): 원본 계산 라벨에서 "감점"만 뗀다. 그룹은 원본 소계(내구성·열적·물리적 /
  계통·비용·기간 / 계통·비용·복구시간)에서 접두어를 뗀 이름이다.

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
    SwitchgearCondition,
    SwitchgearConsequenceAttribute,
    SwitchgearDesignAttribute,
    SwitchgearScoreDetail,
    SwitchgearSpec,
)
from app.equipment_types.na import evaluate
from app.schemas.ef4 import (
    Ef4Detail,
    SwitchgearConditionOut,
    SwitchgearConsequenceAttributeOut,
    SwitchgearDesignAttributeOut,
    SwitchgearScoreDetailOut,
    SwitchgearSpecOut,
)

EF_CODE = "EF4"
EF_NAME = "수배전반"
# 설비 담당자가 설비코드로 검색하므로 eqp_id를 공통 설비명으로 쓴다(2026-10-29 사용자 결정).
NAME_FIELD = "eqp_id"
DOMAIN_TABLES = [
    SwitchgearScoreDetail,
    SwitchgearSpec,
    SwitchgearCondition,
    SwitchgearConsequenceAttribute,
    SwitchgearDesignAttribute,
]

# ------------------------------------------------------------------
# 1. INPUT COLUMNS
# ------------------------------------------------------------------
# 허용값(임포트 검증용, app/services/import_service.py):
#   choices  : 이 값 중 하나여야 함 / min, max : 수치 범위 / required : 빈 문자열 거부
_GOOD_BAD = ["양호", "불량"]
_INSTALL_BUILDINGS = ["FAB동", "UT동", "GCS동", "변전소", "그린동", "사무동", "기타"]

_eqp_id_counters = {"eqp": itertools.count(1)}
_eqp_name_counters = {"tie": itertools.count(1), "hvcb": itertools.count(1)}


def _gen_eqp_id():
    """접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["eqp"])
    return f"{prefix}{next(_eqp_id_counters[prefix])}"


def _gen_eqp_name():
    """접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["tie", "hvcb"])
    return f"{prefix}{next(_eqp_name_counters[prefix])}"


INPUT_COLUMNS = [
    {"name": "factory_code", "label": "사업장명", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["H1", "H2", "K1", "P1"])},
    {"name": "EF_code", "label": "전기설비코드", "dtype": "str", "choices": [EF_CODE],
     "generator": lambda: EF_CODE},
    {"name": "eqp_id", "label": "eqp_id", "dtype": "str", "required": True,
     "generator": _gen_eqp_id},
    {"name": "eqp_id_name", "label": "eqp_id_명", "dtype": "str", "required": True,
     "generator": _gen_eqp_name},
    # 실제 건물명(사업장마다 달라 허용값을 두지 않는다). 계산용 분류는 install_building.
    {"name": "eqp_building", "label": "eqp-설치건물", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["화성UT1동", "화성그린1동"])},
    {"name": "operation_start_time", "label": "가동년월", "dtype": "date",
     "generator": lambda: date(2005, 1, 1) + timedelta(days=random.randint(0, 3650))},
    {"name": "part_thermal_chk", "label": "각종부품열화여부점검결과", "dtype": "str", "choices": _GOOD_BAD,
     "generator": lambda: random.choice(["양호"])},
    {"name": "elec_room_avg_temp", "label": "전기실평균온도", "dtype": "int",
     "generator": lambda: random.choice([25])},
    {"name": "temp_diff_chk", "label": "각상별온도편차점검결과", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([0])},
    {"name": "max_temp_chk", "label": "차단기CLIP최고온도(DS접속부)", "dtype": "int",
     "generator": lambda: random.randint(20, 28)},
    # 부하율은 0~1 비율(원본 판정 기준 0.5·0.8).
    {"name": "load_chk", "label": "부하율", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 80) / 100},
    {"name": "ex_box_chk", "label": "외함정상상태확인점검결과", "dtype": "str", "choices": _GOOD_BAD,
     "generator": lambda: random.choice(["양호"])},
    {"name": "noise_chk", "label": "차단기소음", "dtype": "str", "choices": _GOOD_BAD,
     "generator": lambda: random.choice(["양호"])},
    {"name": "bolt_chk", "label": "모선부(접촉부)BOLT풀림점검결과", "dtype": "str", "choices": _GOOD_BAD,
     "generator": lambda: random.choice(["양호"])},
    {"name": "eqp_disting", "label": "설비식별", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["10U", "11U", "12U"])},
    {"name": "eqp_floor", "label": "층", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["1F", "2F", "3F"])},
    {"name": "scale_dam_chk", "label": "피해규모점검결과", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(0, 90000) / 100},
    {"name": "install_building", "label": "설치건물", "dtype": "str", "choices": _INSTALL_BUILDINGS,
     "generator": lambda: random.choice(["그린동", "UT동", "FAB동", "기타", "변전소"])},
    {"name": "sup_sys_chk", "label": "공급계통점검결과", "dtype": "str", "choices": ["일반", "비상"],
     "generator": lambda: random.choice(["일반", "비상"])},
    {"name": "prod_chk", "label": "생산비생산점검결과", "dtype": "str", "choices": ["생산", "비생산"],
     "generator": lambda: random.choice(["생산", "비생산"])},
    {"name": "op_chk", "label": "상시가동여부점검결과", "dtype": "str", "choices": ["가동", "비가동"],
     "generator": lambda: random.choice(["가동", "비가동"])},
    {"name": "replace_chk", "label": "교체비용점검결과", "dtype": "float", "min": 0,
     "generator": lambda: random.choice([0, 0.3, 0.4, 0.8, 1.2])},
    {"name": "recovery_time_chk", "label": "복구시부하정상동작시간점검결과", "dtype": "float", "min": 0,
     "generator": lambda: random.choice([0, 0.5])},
    {"name": "replace_time_chk", "label": "설비교체기간점검결과", "dtype": "int", "min": 0,
     "generator": lambda: random.choice([28])},
    {"name": "reliability", "label": "공급신뢰도(이중화여부)", "dtype": "str", "choices": ["O", "X"],
     "generator": lambda: random.choice(["O", "X"])},
    {"name": "ato", "label": "ato구성여부", "dtype": "str", "choices": ["적용", "미적용"],
     "generator": lambda: random.choice(["적용", "미적용"])},
    {"name": "cb_inspect", "label": "차단기정밀점검", "dtype": "str", "choices": ["미실시", "실시"],
     "generator": lambda: random.choice(["미실시"])},
    {"name": "relay_chk", "label": "계전기점검", "dtype": "str", "choices": ["미실시", "실시"],
     "generator": lambda: random.choice(["미실시"])},
    {"name": "online_diag", "label": "온라인진단", "dtype": "str", "choices": ["미적용", "적용"],
     "generator": lambda: random.choice(["미적용"])},
    {"name": "part_shortage", "label": "부품단종여부", "dtype": "str", "choices": ["공급가능", "단종"],
     "generator": lambda: random.choice(["공급가능"])},
]


def generate_input_row() -> dict:
    return {col["name"]: col["generator"]() for col in INPUT_COLUMNS}


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (원본 공식 그대로)
# ------------------------------------------------------------------
def _good_minus(field, minus):
    """'양호'면 0, 그 외 minus — 원본 *_chk_minus_cal의 공통 형태."""
    return lambda row: 0 if row[field] == "양호" else minus


def elec_room_avg_temp_minus_cal(row):
    s = row["elec_room_avg_temp"]
    if s > 30: return -(s - 30) * 2
    return 0


def temp_diff_chk_minus_cal(row):
    s = row["temp_diff_chk"]
    if s > 5: return -8
    if s > 3: return -4
    return 0


def max_temp_chk_minus_cal(row):
    s = row["max_temp_chk"]
    if s > 40: return -8
    if s > 30: return -4
    return 0


def load_minus_cal(row):
    s = row["load_chk"]
    if s > 0.8: return -8
    if s > 0.5: return -4
    return 0


def scale_dam_chk_minus_cal(row):
    s = row["scale_dam_chk"]
    if s > 5000: return -30
    if s >= 0: return round((-6) * s / 1000)  # 원본대로 Python round(2026-10-29 결정)
    return 0


_INSTALL_BUILDING = {"FAB동": -12, "UT동": -8, "GCS동": -8, "변전소": -8, "그린동": -4, "사무동": 0}


def replace_chk_minus_cal(row):
    s = row["replace_chk"]
    if s > 1: return -6
    if s > 0.5: return -2
    return 0


def recovery_time_chk_minus_cal(row):
    s = row["recovery_time_chk"]
    if s > 5: return -9
    if s > 1: return -6
    if s > 0: return -3
    return 0


def replace_time_chk_minus_cal(row):
    s = row["replace_time_chk"]
    if s > 30: return -6
    if s > 10: return -4
    if s > 1: return -2
    return 0


def spec_use_minus_cal(row):
    if row["longlife_fan_use"] == "적용" and row["lighting_use"] == "적용": return 0
    return -1


CALCULATED_COLUMNS = [
    # 계산 기준일은 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과).
    {"name": "today", "formula": lambda row: row["_as_of"]},
    {"name": "operation_year", "formula": lambda row: round((row["today"] - row["operation_start_time"]).days / 365, 1)},
    {"name": "age_minus", "formula": lambda row: -(math.floor(row["operation_year"]))},
    {"name": "cb_op_year", "formula": lambda row: round((row["today"] - row["operation_start_time"]).days / 365, 1)},
    {"name": "cb_stat", "formula": lambda row: math.e ** (-1 * ((row["cb_op_year"] / 39.24) ** 7.03))},
    {"name": "cb_stat_minus", "formula": lambda row: round((row["cb_stat"] - 1) * 100 * 4.5)},
    {"name": "durability_minus", "formula": lambda row: row["age_minus"] + row["cb_stat_minus"]},
    {"name": "part_thermal_chk_minus", "formula": _good_minus("part_thermal_chk", -4)},
    {"name": "elec_room_avg_temp_minus", "formula": elec_room_avg_temp_minus_cal},
    {"name": "temp_diff_chk_minus", "formula": temp_diff_chk_minus_cal},
    {"name": "max_temp_chk_minus", "formula": max_temp_chk_minus_cal},
    {"name": "load_minus", "formula": load_minus_cal},
    {"name": "thermal_minus", "formula": lambda row: row["part_thermal_chk_minus"] + row["elec_room_avg_temp_minus"]
                                                    + row["temp_diff_chk_minus"] + row["max_temp_chk_minus"]
                                                    + row["load_minus"]},
    {"name": "ex_box_chk_minus", "formula": _good_minus("ex_box_chk", -1)},
    {"name": "noise_chk_minus", "formula": _good_minus("noise_chk", -1)},
    {"name": "bolt_chk_minus", "formula": _good_minus("bolt_chk", -1)},
    {"name": "phy_minus", "formula": lambda row: row["ex_box_chk_minus"] + row["noise_chk_minus"] + row["bolt_chk_minus"]},
    {"name": "pof_minus", "formula": lambda row: row["durability_minus"] + row["thermal_minus"] + row["phy_minus"]},
    {"name": "pof", "formula": lambda row: 100 + row["pof_minus"]},
    {"name": "scale_dam_chk_minus", "formula": scale_dam_chk_minus_cal},
    {"name": "install_building_minus", "formula": lambda row: _INSTALL_BUILDING.get(row["install_building"], 0)},
    {"name": "sup_sys_chk_minus", "formula": lambda row: -3 if row["sup_sys_chk"] == "비상" else 0},
    {"name": "cof_sys_minus", "formula": lambda row: row["scale_dam_chk_minus"] + row["install_building_minus"]
                                                    + row["sup_sys_chk_minus"]},
    {"name": "prod_chk_minus", "formula": lambda row: -4 if row["prod_chk"] == "생산" else 0},
    {"name": "op_chk_minus", "formula": lambda row: -3 if row["op_chk"] == "가동" else 0},
    {"name": "replace_chk_minus", "formula": replace_chk_minus_cal},
    {"name": "cof_cost_minus", "formula": lambda row: row["prod_chk_minus"] + row["op_chk_minus"] + row["replace_chk_minus"]},
    {"name": "recovery_time_chk_minus", "formula": recovery_time_chk_minus_cal},
    {"name": "replace_time_chk_minus", "formula": replace_time_chk_minus_cal},
    {"name": "cof_recov_minus", "formula": lambda row: row["recovery_time_chk_minus"] + row["replace_time_chk_minus"]},
    {"name": "cof_minus", "formula": lambda row: row["cof_sys_minus"] + row["cof_cost_minus"] + row["cof_recov_minus"]},
    {"name": "cof", "formula": lambda row: 100 + row["cof_minus"]},
    {"name": "operation_start_year", "formula": lambda row: row["operation_start_time"].year},
    {"name": "reliability_minus", "formula": lambda row: -4 if row["reliability"] == "X" else 0},
    {"name": "ato_minus", "formula": lambda row: 0 if row["ato"] == "적용" else -4},
    {"name": "dof_sys_minus", "formula": lambda row: row["reliability_minus"] + row["ato_minus"]},
    {"name": "cb_inspect_minus", "formula": lambda row: -2 if row["cb_inspect"] == "미실시" else 0},
    {"name": "relay_chk_minus", "formula": lambda row: -1 if row["relay_chk"] == "미실시" else 0},
    {"name": "online_diag_minus", "formula": lambda row: -2 if row["online_diag"] == "미적용" else 0},
    {"name": "dof_cost_minus", "formula": lambda row: row["cb_inspect_minus"] + row["relay_chk_minus"]
                                                     + row["online_diag_minus"]},
    {"name": "part_shortage_minus", "formula": lambda row: 0 if row["part_shortage"] == "공급가능" else -1},
    {"name": "ct_use", "formula": lambda row: "미적용" if row["operation_start_year"] < 2010 else "적용"},
    {"name": "ct_use_minus", "formula": lambda row: -1 if row["ct_use"] == "미적용" else 0},
    {"name": "longlife_fan_use", "formula": lambda row: "미적용" if row["operation_start_year"] < 2015 else "적용"},
    {"name": "lighting_use", "formula": lambda row: "미적용" if row["operation_start_year"] < 2018 else "적용"},
    {"name": "spec_use_minus", "formula": spec_use_minus_cal},
    {"name": "dof_recov_minus", "formula": lambda row: row["part_shortage_minus"] + row["ct_use_minus"]
                                                      + row["spec_use_minus"]},
    {"name": "dof_minus", "formula": lambda row: row["dof_sys_minus"] + row["dof_cost_minus"] + row["dof_recov_minus"]},
    {"name": "dof", "formula": lambda row: 100 + row["dof_minus"]},
    {"name": "total_score", "formula": lambda row: 0.5 * row["pof"] + 0.3 * row["cof"] + 0.2 * row["dof"]},
]


def calculate(input_row: dict, as_of: date | None = None) -> dict:
    """input_row(INPUT_COLUMNS 값들)를 받아 전체 계산 컬럼을 더한 dict를 반환한다.
    원본을 바꾸지 않도록 복사본에 계산한다. as_of는 계산 기준일(기본 오늘)."""
    # N/A(null) 입력을 읽는 공식은 감점 0 / 파생값 null — app/equipment_types/na.py (Stage 11)
    row = evaluate(input_row, CALCULATED_COLUMNS, as_of)
    # 원본에 전압 입력이 없다 — 공통 equipment.voltage(필수)에는 0을 넣는다(Stage 10-0, 화면 미표시).
    row["voltage"] = 0
    return row


# ------------------------------------------------------------------
# 3. DB 적재 (EF4 전용 테이블)
# ------------------------------------------------------------------
_SCORE_DETAIL_FIELDS = [
    c.name for c in SwitchgearScoreDetail.__table__.columns if c.name not in ("equipment_id", "computed_at")
]

# 입력 컬럼 이름 = 테이블 컬럼 이름(원본 → DB 그대로 저장). 시점 컬럼은 계산 기준일(today).
_INPUTS_BY_MODEL = {
    SwitchgearSpec: ("eqp_id_name", "eqp_building", "eqp_disting", "eqp_floor", "install_building"),
    SwitchgearCondition: (
        "part_thermal_chk", "elec_room_avg_temp", "temp_diff_chk", "max_temp_chk", "load_chk",
        "ex_box_chk", "noise_chk", "bolt_chk",
    ),
    SwitchgearConsequenceAttribute: (
        "scale_dam_chk", "sup_sys_chk", "prod_chk", "op_chk", "replace_chk", "recovery_time_chk", "replace_time_chk",
    ),
    SwitchgearDesignAttribute: ("reliability", "ato", "cb_inspect", "relay_chk", "online_diag", "part_shortage"),
}
_TIME_COLUMN = {SwitchgearSpec: "updated_at", SwitchgearCondition: "measured_at",
                SwitchgearConsequenceAttribute: "updated_at", SwitchgearDesignAttribute: "updated_at"}


async def ingest_domain(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """calculate()가 만든 flat dict에서 EF4 전용 테이블들에 upsert한다. commit하지 않는다."""
    for model, names in _INPUTS_BY_MODEL.items():
        await session.merge(
            model(equipment_id=equipment_id, **{_TIME_COLUMN[model]: row["today"]}, **{n: row[n] for n in names})
        )
    # 계산 컬럼 이름 = 테이블 컬럼 이름이라 그대로 옮긴다.
    await session.merge(
        SwitchgearScoreDetail(equipment_id=equipment_id, **{name: row[name] for name in _SCORE_DETAIL_FIELDS})
    )


# ------------------------------------------------------------------
# 4. 조회
# ------------------------------------------------------------------
# 감점 항목 메타데이터 — 원본 계산 라벨에서 "감점"을 뗀 표현, 그룹은 원본 소계(접두어 제외).
BREAKDOWN = {
    "pof": [
        {"field": "age_minus", "label": "경과년수", "group": "내구성"},
        {"field": "cb_stat_minus", "label": "차단기고장확률", "group": "내구성"},
        {"field": "part_thermal_chk_minus", "label": "각종부품열화여부", "group": "열적"},
        {"field": "elec_room_avg_temp_minus", "label": "전기실온도", "group": "열적"},
        {"field": "temp_diff_chk_minus", "label": "각상별온도편차", "group": "열적"},
        {"field": "max_temp_chk_minus", "label": "차단기CLIP최고온도", "group": "열적"},
        {"field": "load_minus", "label": "부하율", "group": "열적"},
        {"field": "ex_box_chk_minus", "label": "외함정상상태확인", "group": "물리적"},
        {"field": "noise_chk_minus", "label": "차단기소음", "group": "물리적"},
        {"field": "bolt_chk_minus", "label": "모선부(접촉부)BOLT풀림", "group": "물리적"},
    ],
    "cof": [
        {"field": "scale_dam_chk_minus", "label": "피해규모", "group": "계통"},
        {"field": "install_building_minus", "label": "설치건물", "group": "계통"},
        {"field": "sup_sys_chk_minus", "label": "공급계통", "group": "계통"},
        {"field": "prod_chk_minus", "label": "생산/비생산", "group": "비용"},
        {"field": "op_chk_minus", "label": "상시가동여부", "group": "비용"},
        {"field": "replace_chk_minus", "label": "교체비용", "group": "비용"},
        {"field": "recovery_time_chk_minus", "label": "복구시부하정상동작시간", "group": "기간"},
        {"field": "replace_time_chk_minus", "label": "설비교체기간", "group": "기간"},
    ],
    "dof": [
        {"field": "reliability_minus", "label": "공급신뢰도(이중화여부)", "group": "계통"},
        {"field": "ato_minus", "label": "ATO구성여부", "group": "계통"},
        {"field": "cb_inspect_minus", "label": "차단기정밀점검", "group": "비용"},
        {"field": "relay_chk_minus", "label": "계전기점검", "group": "비용"},
        {"field": "online_diag_minus", "label": "온라인진단", "group": "비용"},
        {"field": "part_shortage_minus", "label": "부품단종여부", "group": "복구시간"},
        {"field": "ct_use_minus", "label": "관통형CT적용", "group": "복구시간"},
        {"field": "spec_use_minus", "label": "스펙강화(장수명FAN,조명등)", "group": "복구시간"},
    ],
}

_DOMAIN_MODELS = (
    SwitchgearSpec, SwitchgearCondition, SwitchgearConsequenceAttribute, SwitchgearDesignAttribute, SwitchgearScoreDetail,
)


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
    return row, by_model[SwitchgearScoreDetail].today


async def last_diag_dates(session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
    """화면의 '최근 진단일' — 원본에 진단일 입력이 없어 EF4는 점검결과 반영 기준일."""
    if not equipment_ids:
        return {}
    stmt = select(SwitchgearCondition.equipment_id, SwitchgearCondition.measured_at).where(
        SwitchgearCondition.equipment_id.in_(equipment_ids)
    )
    return dict((await session.execute(stmt)).all())


async def load_detail(session: AsyncSession, equipment_id: int) -> Ef4Detail | None:
    rows = await _load_rows(session, equipment_id)
    if rows is None:
        return None
    spec, condition, consequence, design, detail = rows
    return Ef4Detail(
        spec=SwitchgearSpecOut.model_validate(spec),
        condition=SwitchgearConditionOut.model_validate(condition),
        consequence=SwitchgearConsequenceAttributeOut.model_validate(consequence),
        design=SwitchgearDesignAttributeOut.model_validate(design),
        score_detail=SwitchgearScoreDetailOut.model_validate(detail),
    )
