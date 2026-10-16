"""EF1(변압기) 설비유형 계산기.

`ref_data/schema_eflms.py`의 INPUT_COLUMNS/CALCULATED_COLUMNS 로직을 그대로 이식했다.
다른 설비유형(EF2~)은 이 파일과 같은 패턴으로 별도 모듈을 추가하고 registry.py에 등록한다
(app/equipment_types/base.py의 EquipmentTypeModule 인터페이스).

공개 인터페이스:
- generate_input_row() -> dict      : mock 입력 1건 생성 (시드용)
- calculate(input_row, as_of=None) -> dict : 입력 dict 하나로 전체 계산 컬럼을 산출(as_of=계산 기준일, 기본 오늘)
- ingest_domain(row, equipment_id, session) : EF1 전용 테이블 upsert (Stage 8-2에 ingest.py에서 이동)
- load_inputs / last_diag_dates / load_detail / BREAKDOWN : 조회용 (Stage 8-4)
"""
import itertools
import math
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DesignAttribute,
    DgaReading,
    DielectricTest,
    Equipment,
    FuranReading,
    LoadCondition,
    OilTest,
    PeriodicInspection,
    TransformerScoreDetail,
    TransformerSpec,
)
from app.schemas.ef1 import (
    DesignAttributeOut,
    DgaReadingOut,
    DielectricTestOut,
    Ef1Detail,
    FuranReadingOut,
    LoadConditionOut,
    OilTestOut,
    PeriodicInspectionOut,
    TransformerScoreDetailOut,
    TransformerSpecOut,
)

EF_CODE = "EF1"
EF_NAME = "변압기"
# 입력 행의 이 컬럼이 공통 equipment.equipment_name으로 들어간다(사내 입력파일 헤더는 그대로).
NAME_FIELD = "transformer_name"
# 유형 단위 리셋 시 지울 EF1 전용 테이블(모두 equipment_id FK).
DOMAIN_TABLES = [
    TransformerScoreDetail,
    TransformerSpec,
    DgaReading,
    FuranReading,
    DielectricTest,
    OilTest,
    LoadCondition,
    PeriodicInspection,
    DesignAttribute,
]

# ------------------------------------------------------------------
# 1. INPUT COLUMNS
# ------------------------------------------------------------------
_tr_name_counters = {"TR": itertools.count(1), "BANK": itertools.count(1)}


def _gen_transformer_name():
    prefix = random.choice(["TR", "BANK"])
    return f"{prefix}{next(_tr_name_counters[prefix])}"


def _gen_applied(applied_ratio=0.8):
    """설계기준 적용/미적용 목업 값. 현실적으로 대부분 적용된 상태를 기본으로 한다(적용 80% : 미적용 20%)."""
    return random.choices(["적용", "미적용"], weights=[applied_ratio, 1 - applied_ratio])[0]


def _gen_redundancy():
    """예비화 등급. N+N(완전이중화) 50% / N+1(부분이중화) 30% / N+0(미이중화) 20%."""
    return random.choices(["N+N", "N+1", "N+0"], weights=[0.5, 0.3, 0.2])[0]


# label: 각 항목이 무엇인지 설명하는 한글 부연 라벨(문서/화면 표시용 메타데이터).
# 사내 입력파일은 영문 헤더로만 오므로 컬럼 매칭에는 쓰이지 않는다 — 매칭은 항상 name
# 기준(app/services/import_service.py 참고). ref_data/schema_eflms.py의 라벨을 그대로
# 이식하되, 그쪽에 있던 중복/오기 3건(coil_max_temp가 "부하율"과 중복, furan_diag_time이
# dga_diag_time과 "진단일" 중복, furan_2FOL이 "dga_2fol"로 오기)은 여기서 바로잡았다.
INPUT_COLUMNS = [
    {"name": "factory_code", "label": "사업장명", "dtype": "str", "generator": lambda: random.choice(["H1", "H2", "K1", "P1"])},
    {"name": "EF_code", "label": "전기설비코드", "dtype": "str", "generator": lambda: EF_CODE},
    {"name": "transformer_name", "label": "변압기명", "dtype": "str", "generator": _gen_transformer_name},
    {"name": "voltage", "label": "전압", "dtype": "int", "generator": lambda: random.choice([22900, 154000])},
    {"name": "ONAN_val", "label": "자냉식용량", "dtype": "int", "generator": lambda: random.choice([25, 30, 35, 80])},
    {"name": "ONAF_val", "label": "풍냉식용량", "dtype": "float", "generator": lambda: random.choice([30, 37.5, 43.75, 100])},
    {
        "name": "operation_start_time",
        "label": "가동년월",
        "dtype": "date",
        "generator": lambda: date(2015, 1, 1) + timedelta(days=random.randint(0, 3650)),
    },
    {"name": "dga_diag_time", "label": "DGA진단일", "dtype": "date", "generator": lambda: date(2020, 6, 1)},
    {"name": "dga_h2", "label": "dga_h2", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "dga_c2h2", "label": "dga_c2h2", "dtype": "float", "generator": lambda: random.choice([0])},
    {"name": "dga_c2h4", "label": "dga_c2h4", "dtype": "int", "generator": lambda: random.randint(0, 99)},
    {"name": "dga_c2h6", "label": "dga_c2h6", "dtype": "int", "generator": lambda: random.choice([0, 288, 394])},
    {"name": "dga_ch4", "label": "dga_ch4", "dtype": "int", "generator": lambda: random.randint(0, 100)},
    {"name": "dga_c3h8", "label": "dga_c3h8", "dtype": "int", "generator": lambda: random.randint(0, 100)},
    {"name": "dga_co", "label": "dga_co", "dtype": "int", "generator": lambda: random.randint(50, 650)},
    {"name": "dga_co2", "label": "dga_co2", "dtype": "int", "generator": lambda: random.randint(500, 3000)},
    {"name": "dga_o2", "label": "dga_o2", "dtype": "int", "generator": lambda: random.randint(9100, 30000)},
    {"name": "dga_n2", "label": "dga_n2", "dtype": "int", "generator": lambda: random.randint(30000, 100000)},
    {"name": "dga_fluc", "label": "dga_fluc", "dtype": "int", "generator": lambda: random.choice([1, -1, -17, 30, 60])},
    {"name": "load_percent", "label": "부하율", "dtype": "float", "generator": lambda: random.randint(0, 1000) / 10},
    {"name": "coil_max_temp", "label": "권선최고온도", "dtype": "int", "generator": lambda: random.randint(40, 60)},
    {"name": "dielec_str_te_1", "label": "절연내력시험_1", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_2", "label": "절연내력시험_2", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_3", "label": "절연내력시험_3", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_4", "label": "절연내력시험_4", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_5", "label": "절연내력시험_5", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_6", "label": "절연내력시험_6", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "acid_measure_val", "label": "산가도시험측정값", "dtype": "float", "generator": lambda: random.choice([0.02, 0.03])},
    {"name": "moisture_rslt", "label": "수분시험결과", "dtype": "float", "generator": lambda: random.randint(150, 350) / 10},
    {"name": "furan_diag_time", "label": "Furan진단일", "dtype": "date", "generator": lambda: date(2020, 6, 1)},
    {"name": "furan_5H2F", "label": "furan_5h2f", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "furan_2FOL", "label": "furan_2fol", "dtype": "float", "generator": lambda: random.choice([0])},
    {"name": "furan_2FAL", "label": "furan_2FAL", "dtype": "int", "generator": lambda: random.randint(0, 20)},
    {"name": "furan_2ACF", "label": "furan_2acf", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "furan_5M2F", "label": "furan_5m2f", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "part_discharge_diag", "label": "부분방전_진단결과", "dtype": "str", "generator": lambda: random.choice(["양호", "이상"])},
    {"name": "oltc_96T_diag", "label": "96T_동작유무", "dtype": "str", "generator": lambda: random.choice(["정상", "이상"])},
    {"name": "oltc_rslt", "label": "탭절환회수", "dtype": "int", "generator": lambda: random.choice([0, 6000, 9000, 13000, 18000])},
    {"name": "oltc_type", "label": "탭절환회수타입", "dtype": "str", "generator": lambda: random.choice(["Vaccum", "Oil"])},
    {"name": "thermal_img_temp", "label": "발열변색여부", "dtype": "str", "generator": lambda: random.choice(["정상", "이상"])},
    {"name": "noise_diag", "label": "이상소음발생여부", "dtype": "str", "generator": lambda: random.choice(["정상", "이상"])},
    {"name": "fire_vul_type", "label": "화재취약성타입", "dtype": "str", "generator": lambda: random.choice(["유입", "몰드"])},
    {"name": "fire_spread_loc", "label": "화재확산장소", "dtype": "str", "generator": lambda: random.choice(["옥내", "옥외"])},
    {"name": "emerge_response_1s", "label": "비상대응시간", "dtype": "str", "generator": lambda: random.choice(["가능", "불가"])},
    {"name": "redundancy", "label": "예비화", "dtype": "str", "generator": _gen_redundancy},
    {"name": "ato", "label": "계통자동전환", "dtype": "str", "generator": _gen_applied},
    {"name": "online_og_chk", "label": "온라인_유중가스", "dtype": "str", "generator": _gen_applied},
    {"name": "offline_safety_chk", "label": "안전공사_정밀점검", "dtype": "str", "generator": _gen_applied},
    {"name": "sec_num", "label": "보호요소수량", "dtype": "int", "generator": lambda: random.choice([4])},
    {"name": "alarm_num", "label": "알람요소수량", "dtype": "int", "generator": lambda: random.choice([5])},
    {"name": "insul_1st_lvup", "label": "절연1단계상승", "dtype": "str", "generator": _gen_applied},
    {"name": "high_insul_adt", "label": "고밀도절연지", "dtype": "str", "generator": _gen_applied},
    {"name": "double_insul", "label": "이중절연", "dtype": "str", "generator": _gen_applied},
    {"name": "55k_install", "label": "온도상승한도", "dtype": "str", "generator": _gen_applied},
    {"name": "sfra_test", "label": "sfra_시험", "dtype": "str", "generator": _gen_applied},
    {"name": "rip_install", "label": "부싱", "dtype": "str", "generator": _gen_applied},
    {"name": "vacuum_set", "label": "OLTC", "dtype": "str", "generator": _gen_applied},
]


def generate_input_row() -> dict:
    return {col["name"]: col["generator"]() for col in INPUT_COLUMNS}


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (ref_data/schema_eflms.py 그대로)
# ------------------------------------------------------------------
def dga_tcg_cal(row):
    return row["dga_h2"] + row["dga_c2h2"] + row["dga_c2h4"] + row["dga_c2h6"] + row["dga_ch4"] + row["dga_c3h8"]


def dga_diag_cal(row):
    a, b, c = row["dga_h2"], row["dga_c2h2"], row["dga_c2h4"]
    d, e, f = row["dga_c2h6"], row["dga_ch4"], row["dga_c3h8"]
    g, h = row["dga_co"], row["dga_co2"]
    i = row["dga_co2"] / row["dga_co"]
    if a > 800: return '이상'
    if a > 400: return '추적관리2'
    if a > 200: return '추적관리1'
    if b > 1: return '이상'
    if c > 500: return '이상'
    if c > 200: return '추적관리2'
    if c > 100: return '추적관리1'
    if d > 750: return '이상'
    if d > 350: return '추적관리2'
    if d > 200: return '추적관리1'
    if e > 750: return '이상'
    if e > 250: return '추적관리2'
    if e > 150: return '추적관리1'
    if f > 750: return '이상'
    if f > 250: return '추적관리2'
    if f > 150: return '추적관리1'
    if g > 1200: return '추적관리2'
    if g > 800: return '추적관리1'
    if h > 7000: return '추적관리2'
    if h > 5000: return '추적관리1'
    if i < 3: return '추적관리1'
    return '정상'


def dga_minus_cal(row):
    s = row["dga_diag"]
    if s == '정상': return 0
    if s == '추적관리1': return -12
    if s == '추적관리2': return -24
    return -36


def load_minus_cal(row):
    s = row["load_percent"]
    if s >= 81: return -20
    if s >= 71: return -15
    if s >= 61: return -10
    if s >= 51: return -5
    return 0


def temp_minus_cal(row):
    s = row["coil_max_temp"]
    if s > 90: return -36
    if s > 80: return -24
    if s > 70: return -12
    return 0


def dielec_str_te_diag_cal(row):
    return "적합" if row["dielec_str_te_avg"] >= 20 else "부적합"


def dielec_str_te_minus_cal(row):
    return 0 if row["dielec_str_te_diag"] == '적합' else -8


def acid_measure_desc_cal(row):
    s = row["acid_measure_val"]
    if s >= 0.4: return "부적합"
    if s >= 0.2: return "요주의"
    return "적합"


def acid_measure_minus_cal(row):
    s = row["acid_measure_desc"]
    if s == '적합': return 0
    if s == '요주의': return -4
    return -8


def moisture_desc_cal(row):
    s = row["moisture_rslt"]
    if s > 50: return "이상"
    if s >= 40: return "요주의"
    return "정상"


def moisture_minus_cal(row):
    s = row["moisture_desc"]
    if s == '정상': return 0
    if s == '요주의': return -4
    return -8


def furan_total_cal(row):
    return row["furan_5H2F"] + row["furan_2FOL"] + row["furan_2FAL"] + row["furan_2ACF"] + row["furan_5M2F"]


def furan_total_per_year_cal(row):
    return row["furan_total"] / row["operation_year"]


def furan_desc_cal(row):
    return "이상" if row["furan_total_per_year"] > 5 else "정상"


def furan_minus_cal(row):
    return 0 if row["furan_desc"] == '정상' else -24


def part_discharge_minus_cal(row):
    return 0 if row["part_discharge_diag"] == '양호' else -20


def oltc_96T_minus_cal(row):
    return 0 if row["oltc_96T_diag"] == '정상' else -12


def oltc_diag_cal(row):
    if row["oltc_type"] == 'Oil' and row["oltc_rslt"] >= 50000: return '이상'
    if row["oltc_type"] == 'Vacuum' and row["oltc_rslt"] >= 300000: return '이상'
    return '정상'


def oltc_minus_cal(row):
    return 0 if row["oltc_diag"] == '정상' else -12


def thermal_img_minus_cal(row):
    return 0 if row["thermal_img_temp"] == '정상' else -8


def noise_minus_cal(row):
    return 0 if row["noise_diag"] == '정상' else -2


def pof_minus_cal(row):
    return (
        row["age_minus"] + row["load_minus"] + row["temp_minus"]
        + row["dielec_str_te_minus"] + row["acid_measure_minus"] + row["moisture_minus"]
        + row["furan_minus"] + row["part_discharge_minus"] + row["oltc_96T_minus"]
        + row["oltc_minus"] + row["thermal_img_minus"] + row["noise_minus"]
    )


def first_voltage_minus_cal(row):
    s = row["1st_voltage"]
    if s > 154000: return -24
    if s > 22900: return -18
    if s > 6600: return -12
    if s > 440: return -6
    return 0


def productivity_minus_cal(row):
    s = row["capa_times_load"]
    if s > 100: return -36
    if s > 50: return -30
    if s > 20: return -24
    if s > 10: return -18
    if s > 5: return -12
    if s > 1: return -6
    return 0


def fire_minus_cal(row):
    return -8 if row["fire_vul_type"] == '유입' else 0


def fire_spread_minus_cal(row):
    s = row["fire_spread_loc"]
    if s == '옥외': return -12
    if s == '미분리': return -8
    if s == '미설치': return -4
    return 0


def emerge_response_minus_cal(row):
    return -6 if row["emerge_response_1s"] == '불가' else 0


def rep_cost_cal(row):
    s = row["1st_voltage"]
    if s > 154000: return 30
    if s > 22900: return 20
    if s > 11000: return 8
    if s > 6600: return 1.5
    return 1


def rep_cost_minus_cal(row):
    s = row["rep_cost"]
    if s > 50: return -8
    if s > 20: return -6
    if s > 10: return -4
    if s > 5: return -2
    return 0


def rep_time_cal(row):
    s = row["1st_voltage"]
    if s > 154000: return 10
    if s > 22900: return 8
    if s > 11000: return 6
    if s > 6600: return 3
    return 3


def rep_time_minus_cal(row):
    s = row["rep_cost"]
    if s > 12: return -8
    if s > 6: return -6
    if s > 3: return -4
    if s > 1: return -2
    return 0


def cof_minus_cal(row):
    return (
        row["1st_voltage_minus"] + row["productivity_minus"] + row["fire_minus"]
        + row["fire_spread_minus"] + row["emerge_response_minus"] + row["rep_cost_minus"]
        + row["rep_time_minus"]
    )


def redundancy_minus_cal(row):
    s = row["redundancy"]
    if s == 'N+N': return 0
    if s == 'N+1': return -18
    return -36


def ato_minus_cal(row):
    return -36 if row["ato"] == '미적용' else 0


def online_og_minus_cal(row):
    return -30 if row["online_og_chk"] == '미적용' else 0


def offline_safety_minus_cal(row):
    return -25 if row["offline_safety_chk"] == '미적용' else 0


def sec_minus_cal(row):
    s = row["sec_num"]
    if s >= 4: return 0
    if s >= 3: return -2
    return -4


def alarm_minus_cal(row):
    s = row["alarm_num"]
    if s >= 5: return 0
    if s >= 4: return -1
    if s >= 3: return -2
    return -3


def winding_minus_cal(row):
    return -16 if row["insul_1st_lvup"] == '미적용' else 0


def prod_life_minus_cal(row):
    return -6 if row["high_insul_adt"] == '미적용' else 0


def connect_part_minus_cal(row):
    return -2 if row["double_insul"] == '미적용' else 0


def temp_inc_limit_minus_cal(row):
    return -9 if row["55k_install"] == '미적용' else 0


def test_reliability_minus_cal(row):
    return -8 if row["sfra_test"] == '미적용' else 0


def bushing_minus_cal(row):
    return -8 if row["rip_install"] == '미적용' else 0


def oltc2_minus_cal(row):
    return -8 if row["vacuum_set"] == '미적용' else 0


def dof_minus_cal(row):
    return (
        row["redundancy_minus"] + row["ato_minus"] + row["online_og_minus"]
        + row["offline_safety_minus"] + row["sec_minus"] + row["alarm_minus"]
        + row["winding_minus"] + row["prod_life_minus"] + row["connect_part_minus"]
        + row["temp_inc_limit_minus"] + row["test_reliability_minus"] + row["bushing_minus"]
        + row["oltc2_minus"]
    )


CALCULATED_COLUMNS = [
    # 계산 기준일은 calculate(as_of=)로 받는다(기본 오늘) — Stage 8-4, N년 뒤 점수 예측용. 결과는 이전과 같다.
    {"name": "today", "formula": lambda row: row["_as_of"]},
    {"name": "operation_year", "formula": lambda row: round((row["today"] - row["operation_start_time"]).days / 365, 1)},
    {"name": "age_minus", "formula": lambda row: -(math.floor(row["operation_year"]))},
    {"name": "dga_tcg", "formula": dga_tcg_cal},
    {"name": "dga_diag", "formula": dga_diag_cal},
    {"name": "dga_minus", "formula": dga_minus_cal},
    {"name": "load_minus", "formula": load_minus_cal},
    {"name": "temp_minus", "formula": temp_minus_cal},
    {
        "name": "dielec_str_te_avg",
        "formula": lambda row: (
            row["dielec_str_te_1"] + row["dielec_str_te_2"] + row["dielec_str_te_3"]
            + row["dielec_str_te_4"] + row["dielec_str_te_5"] + row["dielec_str_te_6"]
        ) / 6,
    },
    {"name": "dielec_str_te_diag", "formula": dielec_str_te_diag_cal},
    {"name": "dielec_str_te_minus", "formula": dielec_str_te_minus_cal},
    {"name": "acid_measure_desc", "formula": acid_measure_desc_cal},
    {"name": "acid_measure_minus", "formula": acid_measure_minus_cal},
    {"name": "moisture_desc", "formula": moisture_desc_cal},
    {"name": "moisture_minus", "formula": moisture_minus_cal},
    {"name": "furan_total", "formula": furan_total_cal},
    {"name": "furan_total_per_year", "formula": furan_total_per_year_cal},
    {"name": "furan_desc", "formula": furan_desc_cal},
    {"name": "furan_minus", "formula": furan_minus_cal},
    {"name": "part_discharge_minus", "formula": part_discharge_minus_cal},
    {"name": "oltc_96T_minus", "formula": oltc_96T_minus_cal},
    {"name": "oltc_diag", "formula": oltc_diag_cal},
    {"name": "oltc_minus", "formula": oltc_minus_cal},
    {"name": "thermal_img_minus", "formula": thermal_img_minus_cal},
    {"name": "noise_minus", "formula": noise_minus_cal},
    {"name": "pof_minus", "formula": pof_minus_cal},
    {"name": "pof", "formula": lambda row: 100 + row["pof_minus"]},
    {"name": "1st_voltage", "formula": lambda row: row["voltage"]},
    {"name": "1st_voltage_minus", "formula": first_voltage_minus_cal},
    {"name": "capa_times_load", "formula": lambda row: (row["ONAN_val"] * row["load_percent"]) / 100},
    {"name": "productivity_minus", "formula": productivity_minus_cal},
    {"name": "fire_minus", "formula": fire_minus_cal},
    {"name": "fire_spread_minus", "formula": fire_spread_minus_cal},
    {"name": "emerge_response_minus", "formula": emerge_response_minus_cal},
    {"name": "rep_cost", "formula": rep_cost_cal},
    {"name": "rep_cost_minus", "formula": rep_cost_minus_cal},
    {"name": "rep_time", "formula": rep_time_cal},
    {"name": "rep_time_minus", "formula": rep_time_minus_cal},
    {"name": "cof_minus", "formula": cof_minus_cal},
    {"name": "cof", "formula": lambda row: 100 + row["cof_minus"]},
    {"name": "redundancy_minus", "formula": redundancy_minus_cal},
    {"name": "ato_minus", "formula": ato_minus_cal},
    {"name": "online_og_minus", "formula": online_og_minus_cal},
    {"name": "offline_safety_minus", "formula": offline_safety_minus_cal},
    {"name": "sec_minus", "formula": sec_minus_cal},
    {"name": "alarm_minus", "formula": alarm_minus_cal},
    {"name": "winding_minus", "formula": winding_minus_cal},
    {"name": "prod_life_minus", "formula": prod_life_minus_cal},
    {"name": "connect_part_minus", "formula": connect_part_minus_cal},
    {"name": "temp_inc_limit_minus", "formula": temp_inc_limit_minus_cal},
    {"name": "test_reliability_minus", "formula": test_reliability_minus_cal},
    {"name": "bushing_minus", "formula": bushing_minus_cal},
    {"name": "oltc2_minus", "formula": oltc2_minus_cal},
    {"name": "dof_minus", "formula": dof_minus_cal},
    {"name": "dof", "formula": lambda row: 100 + row["dof_minus"]},
    {"name": "total_score", "formula": lambda row: 0.5 * row["pof"] + 0.3 * row["cof"] + 0.2 * row["dof"]},
]


def calculate(input_row: dict, as_of: date | None = None) -> dict:
    """input_row(INPUT_COLUMNS 값들)를 받아 전체 계산 컬럼을 더한 dict를 반환한다.
    원본을 바꾸지 않도록 복사본에 계산한다. as_of는 계산 기준일(기본 오늘)."""
    row = dict(input_row)
    row["_as_of"] = as_of or date.today()
    for col in CALCULATED_COLUMNS:
        row[col["name"]] = col["formula"](row)
    del row["_as_of"]
    return row


# ------------------------------------------------------------------
# 3. DB 적재 (EF1 전용 테이블)
# ------------------------------------------------------------------
async def ingest_domain(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """calculate()가 만든 flat dict에서 EF1 전용 테이블들에 upsert한다. commit하지 않는다.
    공통 테이블(equipment/score_snapshot)은 app/services/ingest.py가 담당한다."""
    await session.merge(
        TransformerSpec(
            equipment_id=equipment_id,
            updated_at=row["today"],
            onan_val=row["ONAN_val"],
            onaf_val=row["ONAF_val"],
        )
    )

    await session.merge(
        DgaReading(
            equipment_id=equipment_id,
            diag_time=row["dga_diag_time"],
            dga_h2=row["dga_h2"],
            dga_c2h2=row["dga_c2h2"],
            dga_c2h4=row["dga_c2h4"],
            dga_c2h6=row["dga_c2h6"],
            dga_ch4=row["dga_ch4"],
            dga_c3h8=row["dga_c3h8"],
            dga_co=row["dga_co"],
            dga_co2=row["dga_co2"],
            dga_o2=row["dga_o2"],
            dga_n2=row["dga_n2"],
            dga_fluc=row["dga_fluc"],
        )
    )

    await session.merge(
        FuranReading(
            equipment_id=equipment_id,
            diag_time=row["furan_diag_time"],
            furan_5h2f=row["furan_5H2F"],
            furan_2fol=row["furan_2FOL"],
            furan_2fal=row["furan_2FAL"],
            furan_2acf=row["furan_2ACF"],
            furan_5m2f=row["furan_5M2F"],
        )
    )

    await session.merge(
        DielectricTest(
            equipment_id=equipment_id,
            measured_at=row["today"],
            dielec_str_te_1=row["dielec_str_te_1"],
            dielec_str_te_2=row["dielec_str_te_2"],
            dielec_str_te_3=row["dielec_str_te_3"],
            dielec_str_te_4=row["dielec_str_te_4"],
            dielec_str_te_5=row["dielec_str_te_5"],
            dielec_str_te_6=row["dielec_str_te_6"],
        )
    )

    await session.merge(
        OilTest(
            equipment_id=equipment_id,
            measured_at=row["today"],
            acid_measure_val=row["acid_measure_val"],
            moisture_rslt=row["moisture_rslt"],
        )
    )

    await session.merge(
        LoadCondition(
            equipment_id=equipment_id,
            measured_at=row["today"],
            load_percent=row["load_percent"],
            coil_max_temp=row["coil_max_temp"],
        )
    )

    await session.merge(
        PeriodicInspection(
            equipment_id=equipment_id,
            measured_at=row["today"],
            part_discharge_diag=row["part_discharge_diag"],
            oltc_96t_diag=row["oltc_96T_diag"],
            oltc_rslt=row["oltc_rslt"],
            oltc_type=row["oltc_type"],
            thermal_img_temp=row["thermal_img_temp"],
            noise_diag=row["noise_diag"],
        )
    )

    await session.merge(
        DesignAttribute(
            equipment_id=equipment_id,
            updated_at=row["today"],
            fire_vul_type=row["fire_vul_type"],
            fire_spread_loc=row["fire_spread_loc"],
            emerge_response_1s=row["emerge_response_1s"],
            redundancy=row["redundancy"],
            ato=row["ato"],
            online_og_chk=row["online_og_chk"],
            offline_safety_chk=row["offline_safety_chk"],
            sec_num=row["sec_num"],
            alarm_num=row["alarm_num"],
            insul_1st_lvup=row["insul_1st_lvup"],
            high_insul_adt=row["high_insul_adt"],
            double_insul=row["double_insul"],
            install_55k=row["55k_install"],
            sfra_test=row["sfra_test"],
            rip_install=row["rip_install"],
            vacuum_set=row["vacuum_set"],
        )
    )

    await session.merge(
        TransformerScoreDetail(
            equipment_id=equipment_id,
            today=row["today"],
            operation_year=row["operation_year"],
            age_minus=row["age_minus"],
            dga_tcg=row["dga_tcg"],
            dga_diag=row["dga_diag"],
            dga_minus=row["dga_minus"],
            load_minus=row["load_minus"],
            temp_minus=row["temp_minus"],
            dielec_str_te_avg=row["dielec_str_te_avg"],
            dielec_str_te_diag=row["dielec_str_te_diag"],
            dielec_str_te_minus=row["dielec_str_te_minus"],
            acid_measure_desc=row["acid_measure_desc"],
            acid_measure_minus=row["acid_measure_minus"],
            moisture_desc=row["moisture_desc"],
            moisture_minus=row["moisture_minus"],
            furan_total=row["furan_total"],
            furan_total_per_year=row["furan_total_per_year"],
            furan_desc=row["furan_desc"],
            furan_minus=row["furan_minus"],
            part_discharge_minus=row["part_discharge_minus"],
            oltc_96t_minus=row["oltc_96T_minus"],
            oltc_diag=row["oltc_diag"],
            oltc_minus=row["oltc_minus"],
            thermal_img_minus=row["thermal_img_minus"],
            noise_minus=row["noise_minus"],
            first_voltage=row["1st_voltage"],
            first_voltage_minus=row["1st_voltage_minus"],
            capa_times_load=row["capa_times_load"],
            productivity_minus=row["productivity_minus"],
            fire_minus=row["fire_minus"],
            fire_spread_minus=row["fire_spread_minus"],
            emerge_response_minus=row["emerge_response_minus"],
            rep_cost=row["rep_cost"],
            rep_cost_minus=row["rep_cost_minus"],
            rep_time=row["rep_time"],
            rep_time_minus=row["rep_time_minus"],
            redundancy_minus=row["redundancy_minus"],
            ato_minus=row["ato_minus"],
            online_og_minus=row["online_og_minus"],
            offline_safety_minus=row["offline_safety_minus"],
            sec_minus=row["sec_minus"],
            alarm_minus=row["alarm_minus"],
            winding_minus=row["winding_minus"],
            prod_life_minus=row["prod_life_minus"],
            connect_part_minus=row["connect_part_minus"],
            temp_inc_limit_minus=row["temp_inc_limit_minus"],
            test_reliability_minus=row["test_reliability_minus"],
            bushing_minus=row["bushing_minus"],
            oltc2_minus=row["oltc2_minus"],
        )
    )


# ------------------------------------------------------------------
# 4. 조회 (Stage 8-4)
# ------------------------------------------------------------------
# 감점 항목 메타데이터 — 화면의 감점 사유/가이드가 이걸 쓴다(기존 frontend scoreBreakdown.ts 라벨 그대로).
# dga_minus는 원본 공식에서 pof_minus 합산이 주석 처리돼 있어 summed=False로 표시한다.
BREAKDOWN = {
    "pof": [
        {"field": "age_minus", "label": "경과연수"},
        {"field": "dga_minus", "label": "DGA(유중가스)", "summed": False},
        {"field": "load_minus", "label": "부하율"},
        {"field": "temp_minus", "label": "운전온도"},
        {"field": "dielec_str_te_minus", "label": "절연내력시험"},
        {"field": "acid_measure_minus", "label": "산가도시험"},
        {"field": "moisture_minus", "label": "수분시험"},
        {"field": "furan_minus", "label": "Furan"},
        {"field": "part_discharge_minus", "label": "부분방전"},
        {"field": "oltc_96t_minus", "label": "OLTC 96T 동작"},
        {"field": "oltc_minus", "label": "OLTC 동작진단"},
        {"field": "thermal_img_minus", "label": "열화상"},
        {"field": "noise_minus", "label": "이상소음"},
    ],
    "cof": [
        {"field": "first_voltage_minus", "label": "1차전압"},
        {"field": "productivity_minus", "label": "생산성 영향(용량×부하율)"},
        {"field": "fire_minus", "label": "화재취약성"},
        {"field": "fire_spread_minus", "label": "화재확산장소"},
        {"field": "emerge_response_minus", "label": "비상대응시간"},
        {"field": "rep_cost_minus", "label": "교체비용"},
        {"field": "rep_time_minus", "label": "교체기간"},
    ],
    "dof": [
        {"field": "redundancy_minus", "label": "예비화"},
        {"field": "ato_minus", "label": "계통자동전환"},
        {"field": "online_og_minus", "label": "온라인 유중가스"},
        {"field": "offline_safety_minus", "label": "안전공사 정밀점검"},
        {"field": "sec_minus", "label": "보호요소"},
        {"field": "alarm_minus", "label": "알람요소"},
        {"field": "winding_minus", "label": "권선(절연 1단계 상승)"},
        {"field": "prod_life_minus", "label": "수명향상(고밀도 절연지)"},
        {"field": "connect_part_minus", "label": "접속부(이중절연)"},
        {"field": "temp_inc_limit_minus", "label": "온도상승한도"},
        {"field": "test_reliability_minus", "label": "SFRA 시험"},
        {"field": "bushing_minus", "label": "부싱"},
        {"field": "oltc2_minus", "label": "OLTC(진공식)"},
    ],
}

_DOMAIN_MODELS = (TransformerSpec, DgaReading, FuranReading, DielectricTest, OilTest, LoadCondition, PeriodicInspection, DesignAttribute, TransformerScoreDetail)


async def _load_rows(session: AsyncSession, equipment_id: int):
    rows = [await session.get(model, equipment_id) for model in _DOMAIN_MODELS]
    return None if any(r is None for r in rows) else rows


async def load_inputs(session: AsyncSession, equipment_id: int) -> tuple[dict, date] | None:
    """저장된 값으로 calculate() 입력 행을 복원하고, 저장된 점수의 계산 기준일과 함께 돌려준다.
    calculate(입력, as_of=기준일)은 저장된 점수와 같아야 한다(tests/test_type_queries.py)."""
    equipment = await session.get(Equipment, equipment_id)
    rows = await _load_rows(session, equipment_id)
    if equipment is None or rows is None:
        return None
    spec, dga, furan, dielectric, oil, load, inspection, design, detail = rows
    row = {
        "factory_code": equipment.factory_code,
        "EF_code": equipment.ef_code,
        "transformer_name": equipment.equipment_name,
        "voltage": equipment.voltage,
        "ONAN_val": spec.onan_val,
        "ONAF_val": spec.onaf_val,
        "operation_start_time": equipment.operation_start_time,
        "dga_diag_time": dga.diag_time,
        **{f"dga_{k}": getattr(dga, f"dga_{k}") for k in ("h2", "c2h2", "c2h4", "c2h6", "ch4", "c3h8", "co", "co2", "o2", "n2", "fluc")},
        "load_percent": load.load_percent,
        "coil_max_temp": load.coil_max_temp,
        **{f"dielec_str_te_{i}": getattr(dielectric, f"dielec_str_te_{i}") for i in range(1, 7)},
        "acid_measure_val": oil.acid_measure_val,
        "moisture_rslt": oil.moisture_rslt,
        "furan_diag_time": furan.diag_time,
        "furan_5H2F": furan.furan_5h2f,
        "furan_2FOL": furan.furan_2fol,
        "furan_2FAL": furan.furan_2fal,
        "furan_2ACF": furan.furan_2acf,
        "furan_5M2F": furan.furan_5m2f,
        "part_discharge_diag": inspection.part_discharge_diag,
        "oltc_96T_diag": inspection.oltc_96t_diag,
        "oltc_rslt": inspection.oltc_rslt,
        "oltc_type": inspection.oltc_type,
        "thermal_img_temp": inspection.thermal_img_temp,
        "noise_diag": inspection.noise_diag,
        **{
            k: getattr(design, k)
            for k in (
                "fire_vul_type", "fire_spread_loc", "emerge_response_1s", "redundancy", "ato", "online_og_chk",
                "offline_safety_chk", "sec_num", "alarm_num", "insul_1st_lvup", "high_insul_adt", "double_insul",
                "sfra_test", "rip_install", "vacuum_set",
            )
        },
        "55k_install": design.install_55k,
    }
    return row, detail.today


async def last_diag_dates(session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
    """화면의 '최근 진단일' — EF1은 DGA 진단일."""
    if not equipment_ids:
        return {}
    stmt = select(DgaReading.equipment_id, DgaReading.diag_time).where(DgaReading.equipment_id.in_(equipment_ids))
    return dict((await session.execute(stmt)).all())


async def load_detail(session: AsyncSession, equipment_id: int) -> Ef1Detail | None:
    rows = await _load_rows(session, equipment_id)
    if rows is None:
        return None
    spec, dga, furan, dielectric, oil, load, inspection, design, detail = rows
    return Ef1Detail(
        spec=TransformerSpecOut.model_validate(spec),
        dga=DgaReadingOut.model_validate(dga),
        furan=FuranReadingOut.model_validate(furan),
        dielectric=DielectricTestOut.model_validate(dielectric),
        oil=OilTestOut.model_validate(oil),
        load=LoadConditionOut.model_validate(load),
        inspection=PeriodicInspectionOut.model_validate(inspection),
        design=DesignAttributeOut.model_validate(design),
        score_detail=TransformerScoreDetailOut.model_validate(detail),
    )
