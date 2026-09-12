"""EF1(변압기) 설비유형 계산기.

`ref_data/schema_eflms.py`의 INPUT_COLUMNS/CALCULATED_COLUMNS 로직을 그대로 이식했다.
다른 설비유형(EF2~)이 추가되면 이 파일과 같은 패턴으로 별도 모듈을 추가하고,
이 파일은 변경하지 않는다.

공개 인터페이스:
- generate_input_row() -> dict      : mock 입력 1건 생성 (시드용)
- calculate(input_row) -> dict      : 입력 dict 하나로 전체 계산 컬럼을 산출
"""
import itertools
import math
import random
from datetime import date, timedelta

EF_CODE = "EF1"
EF_NAME = "변압기"

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


INPUT_COLUMNS = [
    {"name": "factory_code", "dtype": "str", "generator": lambda: random.choice(["H1", "H2", "K1", "P1"])},
    {"name": "EF_code", "dtype": "str", "generator": lambda: EF_CODE},
    {"name": "transformer_name", "dtype": "str", "generator": _gen_transformer_name},
    {"name": "voltage", "dtype": "int", "generator": lambda: random.choice([22900, 154000])},
    {"name": "ONAN_val", "dtype": "int", "generator": lambda: random.choice([25, 30, 35, 80])},
    {"name": "ONAF_val", "dtype": "float", "generator": lambda: random.choice([30, 37.5, 43.75, 100])},
    {
        "name": "operation_start_time",
        "dtype": "date",
        "generator": lambda: date(2015, 1, 1) + timedelta(days=random.randint(0, 3650)),
    },
    {"name": "dga_diag_time", "dtype": "date", "generator": lambda: date(2020, 6, 1)},
    {"name": "dga_h2", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "dga_c2h2", "dtype": "float", "generator": lambda: random.choice([0])},
    {"name": "dga_c2h4", "dtype": "int", "generator": lambda: random.randint(0, 99)},
    {"name": "dga_c2h6", "dtype": "int", "generator": lambda: random.choice([0, 288, 394])},
    {"name": "dga_ch4", "dtype": "int", "generator": lambda: random.randint(0, 100)},
    {"name": "dga_c3h8", "dtype": "int", "generator": lambda: random.randint(0, 100)},
    {"name": "dga_co", "dtype": "int", "generator": lambda: random.randint(50, 650)},
    {"name": "dga_co2", "dtype": "int", "generator": lambda: random.randint(500, 3000)},
    {"name": "dga_o2", "dtype": "int", "generator": lambda: random.randint(9100, 30000)},
    {"name": "dga_n2", "dtype": "int", "generator": lambda: random.randint(30000, 100000)},
    {"name": "dga_fluc", "dtype": "int", "generator": lambda: random.choice([1, -1, -17, 30, 60])},
    {"name": "load_percent", "dtype": "float", "generator": lambda: random.randint(0, 1000) / 10},
    {"name": "coil_max_temp", "dtype": "int", "generator": lambda: random.randint(40, 60)},
    {"name": "dielec_str_te_1", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_2", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_3", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_4", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_5", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "dielec_str_te_6", "dtype": "float", "generator": lambda: random.randint(300, 600) / 10},
    {"name": "acid_measure_val", "dtype": "float", "generator": lambda: random.choice([0.02, 0.03])},
    {"name": "moisture_rslt", "dtype": "float", "generator": lambda: random.randint(150, 350) / 10},
    {"name": "furan_diag_time", "dtype": "date", "generator": lambda: date(2020, 6, 1)},
    {"name": "furan_5H2F", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "furan_2FOL", "dtype": "float", "generator": lambda: random.choice([0])},
    {"name": "furan_2FAL", "dtype": "int", "generator": lambda: random.randint(0, 20)},
    {"name": "furan_2ACF", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "furan_5M2F", "dtype": "int", "generator": lambda: random.choice([0])},
    {"name": "part_discharge_diag", "dtype": "str", "generator": lambda: random.choice(["양호", "이상"])},
    {"name": "oltc_96T_diag", "dtype": "str", "generator": lambda: random.choice(["정상", "이상"])},
    {"name": "oltc_rslt", "dtype": "int", "generator": lambda: random.choice([0, 6000, 9000, 13000, 18000])},
    {"name": "oltc_type", "dtype": "str", "generator": lambda: random.choice(["Vaccum", "Oil"])},
    {"name": "thermal_img_temp", "dtype": "str", "generator": lambda: random.choice(["정상", "이상"])},
    {"name": "noise_diag", "dtype": "str", "generator": lambda: random.choice(["정상", "이상"])},
    {"name": "fire_vul_type", "dtype": "str", "generator": lambda: random.choice(["유입", "몰드"])},
    {"name": "fire_spread_loc", "dtype": "str", "generator": lambda: random.choice(["옥내", "옥외"])},
    {"name": "emerge_response_1s", "dtype": "str", "generator": lambda: random.choice(["가능", "불가"])},
    {"name": "redundancy", "dtype": "str", "generator": _gen_redundancy},
    {"name": "ato", "dtype": "str", "generator": _gen_applied},
    {"name": "online_og_chk", "dtype": "str", "generator": _gen_applied},
    {"name": "offline_safety_chk", "dtype": "str", "generator": _gen_applied},
    {"name": "sec_num", "dtype": "int", "generator": lambda: random.choice([4])},
    {"name": "alarm_num", "dtype": "int", "generator": lambda: random.choice([5])},
    {"name": "insul_1st_lvup", "dtype": "str", "generator": _gen_applied},
    {"name": "high_insul_adt", "dtype": "str", "generator": _gen_applied},
    {"name": "double_insul", "dtype": "str", "generator": _gen_applied},
    {"name": "55k_install", "dtype": "str", "generator": _gen_applied},
    {"name": "sfra_test", "dtype": "str", "generator": _gen_applied},
    {"name": "rip_install", "dtype": "str", "generator": _gen_applied},
    {"name": "vacuum_set", "dtype": "str", "generator": _gen_applied},
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
    {"name": "today", "formula": lambda row: date.today()},
    {"name": "operation_year", "formula": lambda row: round((date.today() - row["operation_start_time"]).days / 365, 1)},
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


def calculate(input_row: dict) -> dict:
    """input_row(INPUT_COLUMNS 값들)를 받아 전체 계산 컬럼을 더한 dict를 반환한다.
    원본을 바꾸지 않도록 복사본에 계산한다."""
    row = dict(input_row)
    for col in CALCULATED_COLUMNS:
        row[col["name"]] = col["formula"](row)
    return row
