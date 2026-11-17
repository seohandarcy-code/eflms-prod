"""EF7(배터리) 설비유형 계산기 (Stage 15-1).

`ref_data/schema_eflms_battery.py`(2026-11-16 작성본)의 INPUT_COLUMNS/CALCULATED_COLUMNS 공식을
**그대로** 이식했다 — 방전인덱스합(같은 사업장 + 설치일 이후), 온도감소계수((1~n년 합 + 소수 보정) × e^d,
d = 1823 × (1/298.15 − 1/(배터리실온도+273.15))), BMS 온도 보정 와이블, 원본 안의 반올림(round(…, 3)/round(…, 1))은
모두 원본대로다. tests/test_ef7_battery.py가 같은 입력으로 원본과 결과를 대조한다.

원본과 다른 점:
- **참고표**(Stage 15-0, 2026-11-16 사용자 결정): 원본 파일에 하드코딩된 방전이력·온도감소계수 표를 DB 테이블로
  옮겼다. 계산에는 DB에 지금 들어 있는 참고표를 쓰고, calculate(row, reference=...)로 받는다 — 호출하는 쪽이
  app/services/reference_data.calc_options()를 넘긴다. 원본의 두 표는 목업 참고표(MOCK_*)로 그대로 둔다.
  표가 비거나 해당 년차가 없으면 원본 수식(합계)대로 0이 된다.
- 소수 첫째 자리(2026-11-16 사용자 결정): 원본이 소수를 내는 감점(SOH·BMS·셀간전압편차·셀간온도편차·
  셀온도범위초과이력·사고영향성)을 round1()(엑셀 ROUND식, -0.25 → -0.3)로 반올림한다. 중간값(방전인덱스합·
  방전감소계수·온도감소계수·BMS 상태점수)은 원본 그대로다. POF·COF·DOF와 종합점수는 na.evaluate()가 반올림한다.
- 계산 기준일을 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과). EF1~EF6과 같다.
- 원본에 전압 입력이 없어 calculate()가 voltage=0을 채운다(EF4~EF6과 같음 — 공통 equipment.voltage 필수).
- 임포트 허용값(choices/min/max/required) 추가 — 원본 판정에 쓰이는 값만 받는다(2026-11-16, 권장안).
  mock 생성기는 원본 그대로 쓰고, 생성값도 이 검증을 통과한다.
- 화면 라벨(BREAKDOWN): 원본 계산 라벨에서 "감점"만 뗀다. 원본에 소계가 없어 그룹 없이 나열한다.

공개 인터페이스는 app/equipment_types/base.py의 EquipmentTypeModule(+ 선택 항목 REFERENCE_TABLES).
"""
import itertools
import math
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BatteryCondition,
    BatteryConsequenceAttribute,
    BatteryDesignAttribute,
    BatteryDischargeHistory,
    BatteryScoreDetail,
    BatterySpec,
    BatteryTempDecayCoef,
    Equipment,
)
from app.equipment_types.na import evaluate
from app.equipment_types.rounding import round1
from app.schemas.ef7 import (
    BatteryConditionOut,
    BatteryConsequenceAttributeOut,
    BatteryDesignAttributeOut,
    BatteryScoreDetailOut,
    BatterySpecOut,
    Ef7Detail,
)

EF_CODE = "EF7"
EF_NAME = "배터리"
# 설비 담당자가 설비코드로 검색하므로 eqp_id를 공통 설비명으로 쓴다(EF4~EF6과 같음).
NAME_FIELD = "eqp_id"
DOMAIN_TABLES = [
    BatteryScoreDetail,
    BatterySpec,
    BatteryCondition,
    BatteryConsequenceAttribute,
    BatteryDesignAttribute,
]

# ------------------------------------------------------------------
# 0. 참고표 (Stage 15-0) — 목업은 원본 파일의 두 표 그대로
# ------------------------------------------------------------------
# 방전이력 목업 — 원본 DISCHARGE_HISTORY(40행) 그대로
MOCK_DISCHARGE_HISTORY = [
    {"disch_date": date(2016, 1, 10), "factory_code": "H1", "volt_change": 11.6, "disch_index": 5.324},
    {"disch_date": date(2016, 5, 11), "factory_code": "H2", "volt_change": 39.7, "disch_index": 18.221},
    {"disch_date": date(2016, 7, 29), "factory_code": "H1", "volt_change": 17.3, "disch_index": 7.94},
    {"disch_date": date(2016, 11, 19), "factory_code": "K1", "volt_change": 15.6, "disch_index": 7.16},
    {"disch_date": date(2017, 3, 28), "factory_code": "H1", "volt_change": 26.4, "disch_index": 12.117},
    {"disch_date": date(2017, 8, 9), "factory_code": "P1", "volt_change": 21.6, "disch_index": 9.914},
    {"disch_date": date(2017, 8, 28), "factory_code": "P1", "volt_change": 9.7, "disch_index": 4.452},
    {"disch_date": date(2018, 1, 31), "factory_code": "H2", "volt_change": 34.7, "disch_index": 15.926},
    {"disch_date": date(2018, 3, 21), "factory_code": "H1", "volt_change": 9.6, "disch_index": 4.406},
    {"disch_date": date(2018, 8, 24), "factory_code": "K1", "volt_change": 31.6, "disch_index": 14.503},
    {"disch_date": date(2018, 10, 13), "factory_code": "H2", "volt_change": 13.0, "disch_index": 5.967},
    {"disch_date": date(2019, 1, 16), "factory_code": "P1", "volt_change": 36.0, "disch_index": 16.523},
    {"disch_date": date(2019, 4, 19), "factory_code": "K1", "volt_change": 17.7, "disch_index": 8.124},
    {"disch_date": date(2019, 9, 9), "factory_code": "K1", "volt_change": 30.7, "disch_index": 14.09},
    {"disch_date": date(2019, 11, 3), "factory_code": "H1", "volt_change": 27.2, "disch_index": 12.484},
    {"disch_date": date(2020, 4, 14), "factory_code": "P1", "volt_change": 36.6, "disch_index": 16.798},
    {"disch_date": date(2020, 5, 27), "factory_code": "K1", "volt_change": 8.2, "disch_index": 3.764},
    {"disch_date": date(2020, 11, 4), "factory_code": "H1", "volt_change": 12.0, "disch_index": 5.508},
    {"disch_date": date(2021, 1, 5), "factory_code": "P1", "volt_change": 5.9, "disch_index": 2.708},
    {"disch_date": date(2021, 3, 9), "factory_code": "H2", "volt_change": 36.3, "disch_index": 16.66},
    {"disch_date": date(2021, 7, 21), "factory_code": "H1", "volt_change": 33.1, "disch_index": 15.192},
    {"disch_date": date(2021, 11, 22), "factory_code": "K1", "volt_change": 38.0, "disch_index": 17.441},
    {"disch_date": date(2021, 12, 29), "factory_code": "P1", "volt_change": 35.7, "disch_index": 16.385},
    {"disch_date": date(2022, 6, 28), "factory_code": "H2", "volt_change": 5.3, "disch_index": 2.433},
    {"disch_date": date(2022, 10, 8), "factory_code": "H2", "volt_change": 13.8, "disch_index": 6.334},
    {"disch_date": date(2023, 1, 24), "factory_code": "K1", "volt_change": 25.8, "disch_index": 11.841},
    {"disch_date": date(2023, 4, 25), "factory_code": "K1", "volt_change": 36.2, "disch_index": 16.615},
    {"disch_date": date(2023, 6, 14), "factory_code": "H2", "volt_change": 39.1, "disch_index": 17.946},
    {"disch_date": date(2023, 10, 17), "factory_code": "P1", "volt_change": 11.9, "disch_index": 5.462},
    {"disch_date": date(2024, 2, 18), "factory_code": "H1", "volt_change": 32.1, "disch_index": 14.733},
    {"disch_date": date(2024, 4, 23), "factory_code": "H2", "volt_change": 15.4, "disch_index": 7.068},
    {"disch_date": date(2024, 7, 9), "factory_code": "P1", "volt_change": 29.8, "disch_index": 13.677},
    {"disch_date": date(2024, 9, 19), "factory_code": "P1", "volt_change": 20.9, "disch_index": 9.592},
    {"disch_date": date(2025, 2, 21), "factory_code": "H2", "volt_change": 38.0, "disch_index": 17.441},
    {"disch_date": date(2025, 7, 5), "factory_code": "K1", "volt_change": 7.7, "disch_index": 3.534},
    {"disch_date": date(2025, 8, 26), "factory_code": "P1", "volt_change": 37.9, "disch_index": 17.395},
    {"disch_date": date(2025, 11, 25), "factory_code": "K1", "volt_change": 32.9, "disch_index": 15.1},
    {"disch_date": date(2026, 4, 18), "factory_code": "H1", "volt_change": 20.7, "disch_index": 9.501},
    {"disch_date": date(2026, 8, 1), "factory_code": "H2", "volt_change": 5.0, "disch_index": 2.295},
    {"disch_date": date(2026, 9, 12), "factory_code": "H1", "volt_change": 34.6, "disch_index": 15.88},
]

# 온도감소계수 목업 — 원본 TEMP_DECAY_COEF(20행) 그대로
MOCK_TEMP_DECAY_COEF = [
    {"year": 1, "gamma_y": 3.5734},
    {"year": 2, "gamma_y": 3.2413},
    {"year": 3, "gamma_y": 2.9401},
    {"year": 4, "gamma_y": 2.6668},
    {"year": 5, "gamma_y": 2.419},
    {"year": 6, "gamma_y": 2.1942},
    {"year": 7, "gamma_y": 1.9902},
    {"year": 8, "gamma_y": 1.8053},
    {"year": 9, "gamma_y": 1.6375},
    {"year": 10, "gamma_y": 1.4853},
    {"year": 11, "gamma_y": 1.3473},
    {"year": 12, "gamma_y": 1.2221},
    {"year": 13, "gamma_y": 1.1085},
    {"year": 14, "gamma_y": 1.0055},
    {"year": 15, "gamma_y": 0.912},
    {"year": 16, "gamma_y": 0.8273},
    {"year": 17, "gamma_y": 0.7504},
    {"year": 18, "gamma_y": 0.6806},
    {"year": 19, "gamma_y": 0.6174},
    {"year": 20, "gamma_y": 0.56},
]

REFERENCE_TABLES = {
    "discharge_history": {
        "label": "방전이력",
        "model": BatteryDischargeHistory,
        "columns": [
            {"name": "disch_date", "label": "일자", "dtype": "date"},
            {"name": "factory_code", "label": "사업장", "dtype": "str", "required": True},
            # 전압변동은 % 값(11.6% → 11.6)
            {"name": "volt_change", "label": "전압변동(%)", "dtype": "float", "min": 0, "max": 100},
            {"name": "disch_index", "label": "방전인덱스", "dtype": "float", "min": 0},
        ],
        "key": ("factory_code", "disch_date"),
        "mock_rows": MOCK_DISCHARGE_HISTORY,
    },
    "temp_decay_coef": {
        "label": "온도감소계수",
        "model": BatteryTempDecayCoef,
        "columns": [
            {"name": "year", "label": "사용 년차", "dtype": "int", "min": 1},
            {"name": "gamma_y", "label": "온도감소계수", "dtype": "float", "gt": 0},
        ],
        "key": ("year",),
        "mock_rows": MOCK_TEMP_DECAY_COEF,
    },
}

# ------------------------------------------------------------------
# 1. INPUT COLUMNS
# ------------------------------------------------------------------
# 허용값(임포트 검증용, app/services/import_service.py):
#   choices  : 이 값 중 하나여야 함 / min, max : 수치 범위 / required : 빈 문자열 거부
_ABC = ["A", "B", "C"]

_eqp_id_counters = {"bat": itertools.count(1)}


def _gen_eqp_id():
    """접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["bat"])
    return f"{prefix}{next(_eqp_id_counters[prefix])}"


INPUT_COLUMNS = [
    {"name": "factory_code", "label": "사업장명", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["H1", "H2", "K1", "P1"])},
    {"name": "EF_code", "label": "전기설비코드", "dtype": "str", "choices": [EF_CODE],
     "generator": lambda: EF_CODE},
    {"name": "eqp_id", "label": "eqp_id", "dtype": "str", "required": True,
     "generator": _gen_eqp_id},
    {"name": "line_no", "label": "라인", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["11L", "12L"])},
    {"name": "manufacturer", "label": "제작사", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["삼성SDI"])},
    {"name": "model_name", "label": "모델명", "dtype": "str", "required": True,
     "generator": lambda: random.choice(["AVC2", "PCS100"])},
    {"name": "operation_start_time", "label": "설치년월", "dtype": "date",
     "generator": lambda: date(2015, 1, 1) + timedelta(days=random.randint(0, 3650))},
    {"name": "vol_diff", "label": "셀간전압편차", "dtype": "float", "min": 0,
     "generator": lambda: random.choice([0.021, 0.022, 0.023, 0.024, 0.025])},
    {"name": "temp_diff", "label": "셀간온도편차", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(100, 250) / 100},
    {"name": "temp_range_over", "label": "셀온도범위초과이력", "dtype": "float", "min": 0,
     "generator": lambda: random.choice([0.0])},
    {"name": "bat_room_temp", "label": "배터리실온도", "dtype": "float",
     "generator": lambda: random.randint(200, 250) / 10},
    {"name": "bat_room_humid", "label": "배터리실습도", "dtype": "float", "min": 0, "max": 100,
     "generator": lambda: random.randint(400, 600) / 10},
    {"name": "capa", "label": "정격용량", "dtype": "float", "min": 0,
     "generator": lambda: random.choice([500.0, 800.0])},
    # 부하율은 % 값(부하량 = 부하율 × 정격용량 / 100).
    {"name": "load", "label": "부하율", "dtype": "float", "min": 0,
     "generator": lambda: random.randint(400, 600) / 10},
    {"name": "con_rank", "label": "연결설비", "dtype": "str", "choices": ["단독", "공용"],
     "generator": lambda: random.choice(["단독", "공용"])},
    {"name": "ins_build_rank", "label": "설치건물등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["A", "B", "C"])},
    {"name": "fire_spread_rank", "label": "화재확산등급", "dtype": "str", "choices": ["A", "B"],
     "generator": lambda: random.choice(["A", "B"])},
    {"name": "emerge_resp", "label": "전력재공급시간등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["A", "B", "C"])},
    {"name": "rep_time", "label": "정상화기간등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["B"])},
    {"name": "rep_cost", "label": "사고복구비용등급", "dtype": "str", "choices": _ABC,
     "generator": lambda: random.choice(["C"])},
    {"name": "model_gen", "label": "모델세대", "dtype": "int", "choices": [2, 3, 4],
     "generator": lambda: random.choice([2, 3, 4])},
    {"name": "fire_resist", "label": "화재방지", "dtype": "str", "choices": ["O", "X"],
     "generator": lambda: random.choice(["O", "X"])},
    {"name": "ul_auth", "label": "UL인증", "dtype": "str", "choices": ["취득", "미취득"],
     "generator": lambda: random.choice(["취득", "미취득"])},
    {"name": "fac_rel", "label": "설비신뢰도등급", "dtype": "int", "min": 0,
     "generator": lambda: random.randint(4, 12)},
    {"name": "part_stat_diag", "label": "부품상태진단(온라인)", "dtype": "str", "choices": ["미적용", "적용"],
     "generator": lambda: random.choice(["미적용"])},
    {"name": "bat_server", "label": "배터리서버", "dtype": "str", "choices": ["적용", "미적용"],
     "generator": lambda: random.choice(["적용"])},
    {"name": "bat_room_fire_resist", "label": "배터리실소화설비", "dtype": "str", "choices": ["가스계", "수계"],
     "generator": lambda: random.choice(["가스계"])},
]


def generate_input_row() -> dict:
    return {col["name"]: col["generator"]() for col in INPUT_COLUMNS}


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (원본 공식 그대로 + 감점 소수 첫째 자리)
# ------------------------------------------------------------------
def disch_index_cal(row):
    # 같은 사업장 + 설치일 이후 방전인덱스 합(원본 코드대로 날짜 비교)
    install_date = row["operation_start_time"]
    s = sum(
        (h["disch_index"] for h in row["_reference"]["discharge_history"]
         if h["factory_code"] == row["factory_code"]
         and h["disch_date"] >= install_date),
        0.0,
    )
    return round(s, 3)


def temp_dec_coef_cal(row):
    # (1~n년 계수 합 + 소수부분 × (n+1)년 계수) × 배터리실 온도 배율(25℃ = 1배)
    coefs = row["_reference"]["temp_decay_coef"]
    temp_year = int(row["operation_year"])
    a = sum((h["gamma_y"] for h in coefs if h["year"] <= temp_year), 0.0)
    fractionpart = row["operation_year"] % 1
    b = sum((h["gamma_y"] for h in coefs if h["year"] == temp_year + 1), 0.0)
    c = fractionpart * b
    d = math.exp(1823 * (1 / 298.15 - 1 / (row["bat_room_temp"] + 273.15)))
    s = (a + c) * d
    return round(s, 1)


def vol_diff_minus_cal(row):
    s = 0.25 - row["vol_diff"]
    if s > 0: return 0
    return (0.25 - row["vol_diff"]) * 120


def temp_diff_minus_cal(row):
    s = 5 - row["temp_diff"]
    if s > 0: return 0
    return (5 - row["temp_diff"]) * 2.4


def bat_room_temp_minus_cal(row):
    # 18℃ 초과 28℃ 미만이면 0, 경계값(18·28) 포함 그 밖이면 -3 — 원본대로
    s = (28 - row["bat_room_temp"]) * (18 - row["bat_room_temp"])
    if s < 0: return 0
    return -3


def bat_room_humid_minus_cal(row):
    s = 80 - row["bat_room_humid"]
    if s > 0: return 0
    return -3


_INS_BUILD_RANK = {"A": -6, "B": -3, "C": 0}
_FIRE_SPREAD_RANK = {"A": -3, "B": 0}
_ABC_MINUS = {"A": -2, "B": -1, "C": 0}  # 전력재공급시간·정상화기간·사고복구비용
_MODEL_GEN = {2: -12, 3: -6, 4: 0}

CALCULATED_COLUMNS = [
    # 계산 기준일은 calculate(as_of=)로 받는다(기본 오늘 — 원본과 같은 결과).
    {"name": "today", "formula": lambda row: row["_as_of"]},
    {"name": "operation_year", "formula": lambda row: round((row["today"] - row["operation_start_time"]).days / 365, 1)},
    {"name": "age_minus", "formula": lambda row: -(math.floor(row["operation_year"]))},
    {"name": "disch_index", "formula": disch_index_cal},
    {"name": "disch_dec_coef", "formula": lambda row: row["disch_index"] * 0.000579},
    {"name": "temp_dec_coef", "formula": temp_dec_coef_cal},
    {"name": "soh_minus", "formula": lambda row: round1(-2 * (row["disch_dec_coef"] + row["temp_dec_coef"]))},
    {"name": "bms_life", "formula": lambda row: row["operation_year"]},
    {"name": "bms_stat", "formula": lambda row: math.e ** (-1 * (((row["bms_life"] / (7637042774839 * (2 ** ((25 - row["bat_room_temp"]) / 10)))) ** 0.1525)))},
    {"name": "bms_minus", "formula": lambda row: round1((row["bms_stat"] - 1) * 100 * 3)},
    {"name": "vol_diff_minus", "formula": lambda row: round1(vol_diff_minus_cal(row))},
    {"name": "temp_diff_minus", "formula": lambda row: round1(temp_diff_minus_cal(row))},
    {"name": "temp_range_over_minus", "formula": lambda row: round1(row["temp_range_over"] * (-1.5))},
    {"name": "bat_room_temp_minus", "formula": bat_room_temp_minus_cal},
    {"name": "bat_room_humid_minus", "formula": bat_room_humid_minus_cal},
    {"name": "pof_minus", "formula": lambda row: (
        row["age_minus"] + row["soh_minus"] + row["bms_minus"]
        + row["vol_diff_minus"] + row["temp_diff_minus"] + row["temp_range_over_minus"]
        + row["bat_room_temp_minus"] + row["bat_room_humid_minus"]
    )},
    {"name": "pof", "formula": lambda row: 100 + row["pof_minus"]},
    {"name": "capa_times_load", "formula": lambda row: (row["load"] * row["capa"]) / 100},
    {"name": "capa_times_load_minus", "formula": lambda row: round1(-6 * row["capa_times_load"] / 500)},
    {"name": "con_rank_minus", "formula": lambda row: -3 if row["con_rank"] == "공용" else 0},
    {"name": "ins_build_rank_minus", "formula": lambda row: _INS_BUILD_RANK.get(row["ins_build_rank"], 0)},
    {"name": "fire_spread_rank_minus", "formula": lambda row: _FIRE_SPREAD_RANK.get(row["fire_spread_rank"], 0)},
    {"name": "emerge_resp_minus", "formula": lambda row: _ABC_MINUS.get(row["emerge_resp"], 0)},
    {"name": "rep_time_minus", "formula": lambda row: _ABC_MINUS.get(row["rep_time"], 0)},
    {"name": "rep_cost_minus", "formula": lambda row: _ABC_MINUS.get(row["rep_cost"], 0)},
    {"name": "cof_minus", "formula": lambda row: (
        row["capa_times_load_minus"] + row["con_rank_minus"] + row["ins_build_rank_minus"]
        + row["fire_spread_rank_minus"]
        + row["emerge_resp_minus"] + row["rep_time_minus"] + row["rep_cost_minus"]
    )},
    {"name": "cof", "formula": lambda row: 100 + row["cof_minus"]},
    {"name": "model_gen_minus", "formula": lambda row: _MODEL_GEN.get(row["model_gen"], 0)},
    {"name": "fire_resist_minus", "formula": lambda row: -12 if row["fire_resist"] == "X" else 0},
    {"name": "ul_auth_minus", "formula": lambda row: -12 if row["ul_auth"] == "미취득" else 0},
    {"name": "fac_rel_minus", "formula": lambda row: 0 if row["fac_rel"] >= 3 else -8},
    {"name": "part_stat_diag_minus", "formula": lambda row: -4 if row["part_stat_diag"] == "미적용" else 0},
    {"name": "bat_server_minus", "formula": lambda row: -2 if row["bat_server"] == "미적용" else 0},
    {"name": "bat_room_fire_resist_minus", "formula": lambda row: -8 if row["bat_room_fire_resist"] == "가스계" else 0},
    {"name": "dof_minus", "formula": lambda row: (
        row["model_gen_minus"] + row["fire_resist_minus"]
        + row["ul_auth_minus"] + row["fac_rel_minus"]
        + row["part_stat_diag_minus"] + row["bat_server_minus"] + row["bat_room_fire_resist_minus"]
    )},
    {"name": "dof", "formula": lambda row: 100 + row["dof_minus"]},
    {"name": "total_score", "formula": lambda row: 0.5 * row["pof"] + 0.3 * row["cof"] + 0.2 * row["dof"]},
]


def calculate(input_row: dict, as_of: date | None = None, reference: dict[str, list[dict]] | None = None) -> dict:
    """input_row(INPUT_COLUMNS 값들)를 받아 전체 계산 컬럼을 더한 dict를 반환한다.

    reference = {"discharge_history": [...], "temp_decay_coef": [...]} — DB의 참고표
    (app/services/reference_data.calc_options). 빠뜨리면 조용히 0으로 계산되지 않도록 오류를 낸다.
    원본을 바꾸지 않도록 복사본에 계산한다. as_of는 계산 기준일(기본 오늘).
    """
    if reference is None:
        raise ValueError("EF7 계산에는 참고표(reference)가 필요함 — reference_data.calc_options()를 넘길 것")
    # N/A(null) 입력을 읽는 공식은 감점 0 / 파생값 null, 점수 지표는 소수 첫째 자리 — na.evaluate()
    row = evaluate({**input_row, "_reference": reference}, CALCULATED_COLUMNS, as_of)
    del row["_reference"]
    # 원본에 전압 입력이 없다 — 공통 equipment.voltage(필수)에는 0을 넣는다(EF4~EF6과 같음, 화면 미표시).
    row["voltage"] = 0
    return row


# ------------------------------------------------------------------
# 3. DB 적재 (EF7 전용 테이블)
# ------------------------------------------------------------------
_SCORE_DETAIL_FIELDS = [
    c.name for c in BatteryScoreDetail.__table__.columns if c.name not in ("equipment_id", "computed_at")
]

# 입력 컬럼 이름 = 테이블 컬럼 이름(원본 → DB 그대로 저장). 시점 컬럼은 계산 기준일(today).
_INPUTS_BY_MODEL = {
    BatterySpec: ("line_no", "manufacturer", "model_name", "capa"),
    BatteryCondition: ("vol_diff", "temp_diff", "temp_range_over", "bat_room_temp", "bat_room_humid", "load"),
    BatteryConsequenceAttribute: ("con_rank", "ins_build_rank", "fire_spread_rank", "emerge_resp", "rep_time", "rep_cost"),
    BatteryDesignAttribute: (
        "model_gen", "fire_resist", "ul_auth", "fac_rel", "part_stat_diag", "bat_server", "bat_room_fire_resist",
    ),
}
_TIME_COLUMN = {BatterySpec: "updated_at", BatteryCondition: "measured_at",
                BatteryConsequenceAttribute: "updated_at", BatteryDesignAttribute: "updated_at"}


async def ingest_domain(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """calculate()가 만든 flat dict에서 EF7 전용 테이블들에 upsert한다. commit하지 않는다."""
    for model, names in _INPUTS_BY_MODEL.items():
        await session.merge(
            model(equipment_id=equipment_id, **{_TIME_COLUMN[model]: row["today"]}, **{n: row[n] for n in names})
        )
    # 계산 컬럼 이름 = 테이블 컬럼 이름이라 그대로 옮긴다.
    await session.merge(
        BatteryScoreDetail(equipment_id=equipment_id, **{name: row[name] for name in _SCORE_DETAIL_FIELDS})
    )


# ------------------------------------------------------------------
# 4. 조회
# ------------------------------------------------------------------
# 감점 항목 메타데이터 — 원본 계산 라벨에서 "감점"을 뗀 표현. 원본에 소계가 없어 그룹 없이 나열한다.
BREAKDOWN = {
    "pof": [
        {"field": "age_minus", "label": "경과년수"},
        {"field": "soh_minus", "label": "SOH"},
        {"field": "bms_minus", "label": "BMS고장확률"},
        {"field": "vol_diff_minus", "label": "셀간전압편차"},
        {"field": "temp_diff_minus", "label": "셀간온도편차"},
        {"field": "temp_range_over_minus", "label": "셀온도범위초과이력"},
        {"field": "bat_room_temp_minus", "label": "배터리실온도"},
        {"field": "bat_room_humid_minus", "label": "배터리실습도"},
    ],
    "cof": [
        {"field": "capa_times_load_minus", "label": "사고영향성"},
        {"field": "con_rank_minus", "label": "연결설비"},
        {"field": "ins_build_rank_minus", "label": "설치건물등급"},
        {"field": "fire_spread_rank_minus", "label": "화재확산등급"},
        {"field": "emerge_resp_minus", "label": "사고복구시간"},
        {"field": "rep_time_minus", "label": "정상화기간"},
        {"field": "rep_cost_minus", "label": "사고복구비용"},
    ],
    "dof": [
        {"field": "model_gen_minus", "label": "모델세대"},
        {"field": "fire_resist_minus", "label": "화재방지"},
        {"field": "ul_auth_minus", "label": "UL인증"},
        {"field": "fac_rel_minus", "label": "설비신뢰도"},
        {"field": "part_stat_diag_minus", "label": "부품상태진단(온라인)"},
        {"field": "bat_server_minus", "label": "배터리서버"},
        {"field": "bat_room_fire_resist_minus", "label": "배터리실소화설비"},
    ],
}

_DOMAIN_MODELS = (BatterySpec, BatteryCondition, BatteryConsequenceAttribute, BatteryDesignAttribute, BatteryScoreDetail)


async def _load_rows(session: AsyncSession, equipment_id: int):
    rows = [await session.get(model, equipment_id) for model in _DOMAIN_MODELS]
    return None if any(r is None for r in rows) else rows


async def load_inputs(session: AsyncSession, equipment_id: int) -> tuple[dict, date] | None:
    """저장된 값으로 calculate() 입력 행을 복원하고, 저장된 점수의 계산 기준일과 함께 돌려준다.
    참고표는 입력이 아니다 — 다시 계산하는 쪽이 calc_options()로 지금 DB의 참고표를 넘긴다."""
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
    return row, by_model[BatteryScoreDetail].today


async def last_diag_dates(session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
    """화면의 '최근 진단일' — 원본에 진단일 입력이 없어 EF7은 점검결과 반영 기준일(EF4~EF6과 같음)."""
    if not equipment_ids:
        return {}
    stmt = select(BatteryCondition.equipment_id, BatteryCondition.measured_at).where(
        BatteryCondition.equipment_id.in_(equipment_ids)
    )
    return dict((await session.execute(stmt)).all())


async def load_detail(session: AsyncSession, equipment_id: int) -> Ef7Detail | None:
    rows = await _load_rows(session, equipment_id)
    if rows is None:
        return None
    spec, condition, consequence, design, detail = rows
    return Ef7Detail(
        spec=BatterySpecOut.model_validate(spec),
        condition=BatteryConditionOut.model_validate(condition),
        consequence=BatteryConsequenceAttributeOut.model_validate(consequence),
        design=BatteryDesignAttributeOut.model_validate(design),
        score_detail=BatteryScoreDetailOut.model_validate(detail),
    )
