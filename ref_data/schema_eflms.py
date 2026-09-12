"""
컬럼 정의 설정 파일
=====================
엑셀 양식을 보면서 이 파일 하나만 수정하면 됩니다.

구성 3단계
----------
1) INPUT_COLUMNS      : 엑셀에서 "사람이 직접 입력하는" 원본 컬럼 → 랜덤 목업값 생성 대상
2) CALCULATED_COLUMNS  : 엑셀 수식이 들어있던 컬럼 → 파이썬 함수(수식)로 옮겨 적는 곳
3) DISPLAY_COLUMNS     : 위 두 컬럼 중, 실제 웹 화면에 보여줄 컬럼만 순서대로 모음

컬럼을 추가/변경하고 싶으면 아래 리스트에 dict를 추가/수정하기만 하면 되고,
main.py 쪽 코드는 건드릴 필요가 없습니다.
"""
import itertools
import math
import random
from datetime import date, timedelta

# ------------------------------------------------------------------
# 1. INPUT COLUMNS (입력 받는 컬럼)
# ------------------------------------------------------------------
# name       : 코드/DB에서 쓸 컬럼명 (영문 권장)
# label      : 화면에 보여줄 한글 라벨
# dtype      : str / int / float / date / bool / enum
# generator  : 인자 없이 호출하면 랜덤 값 1개를 반환하는 함수
#
# ▶ 새 입력 컬럼 추가 방법: 이 리스트에 dict 하나 더 추가

_tr_name_counters = {"TR": itertools.count(1), "BANK": itertools.count(1)}


def _gen_transformer_name():
    """TR/BANK 접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["TR", "BANK"])
    return f"{prefix}{next(_tr_name_counters[prefix])}"


INPUT_COLUMNS = [
    {
        "name": "factory_code",
        "label": "사업장명",
        "dtype": "str",
        "generator": lambda: random.choice(["H1", "H2", "K1", "P1"]),
    },
    {
        "name": "EF_code",
        "label": "전기설비코드",
        "dtype": "str",
        "generator": lambda: random.choice(["EF1", "EF2", "EF3", "EF4","EF5","EF6","EF7"]),
    },
    {
        "name": "transformer_name",
        "label": "변압기명",
        "dtype": "str",
        "generator": _gen_transformer_name,
    },
    {
        "name": "voltage",
        "label": "전압",
        "dtype": "int",
        "generator": lambda: random.choice([22900, 154000]),
    },
    {
        "name": "ONAN_val",
        "label": "자냉식용량",
        "dtype": "int",
        "generator": lambda: random.choice([25, 30, 35, 80]),
    },
    {
        "name": "ONAF_val",
        "label": "풍냉식용량",
        "dtype": "float",
        "generator": lambda: random.choice([30, 37.5, 43.75, 100]),
    },
    {
        "name": "operation_start_time",
        "label": "가동년월",
        "dtype": "date",
        "generator": lambda: date(2015, 1, 1) + timedelta(days=random.randint(0, 3650)),
    },
    {
        "name": "dga_diag_time",
        "label": "진단일",
        "dtype": "date",
        "generator": lambda: date(2020, 6, 1),
    },
    {
        "name": "dga_h2",
        "label": "dga_h2",
        "dtype": "int",
        "generator": lambda: random.choice([0]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "dga_c2h2",
        "label": "dga_c2h2",
        "dtype": "float",
        "generator": lambda: random.choice([0]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "dga_c2h4",
        "label": "dga_c2h4",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 99),
    },
    {
        "name": "dga_c2h6",
        "label": "dga_c2h6",
        "dtype": "int",
        "generator": lambda: random.choice([0,288,394]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "dga_ch4",
        "label": "dga_ch4",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 100),
    },
    {
        "name": "dga_c3h8",
        "label": "dga_c3h8",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 100),
    },
    {
        "name": "dga_co",
        "label": "dga_co",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(50, 650),
    },
    {
        "name": "dga_co2",
        "label": "dga_co2",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(500, 3000),
    },
    {
        "name": "dga_o2",
        "label": "dga_o2",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(9100, 30000),
    },
    {
        "name": "dga_n2",
        "label": "dga_n2",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(30000, 100000),
    },
    {
        "name": "dga_fluc",
        "label": "dga_fluc",
        "dtype": "int",
        "generator": lambda: random.choice([1,-1,-17,30,60]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "load_percent",
        "label": "부하율",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 1000)/10,
    },
    {
        "name": "coil_max_temp",
        "label": "부하율",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(40, 60),
    },
    {
        "name": "dielec_str_te_1",
        "label": "절연내력시험_1",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(300, 600)/10,
    },
    {
        "name": "dielec_str_te_2",
        "label": "절연내력시험_2",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(300, 600)/10,
    },
    {
        "name": "dielec_str_te_3",
        "label": "절연내력시험_3",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(300, 600)/10,
    },
    {
        "name": "dielec_str_te_4",
        "label": "절연내력시험_4",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(300, 600)/10,
    },
    {
        "name": "dielec_str_te_5",
        "label": "절연내력시험_5",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(300, 600)/10,
    },
    {
        "name": "dielec_str_te_6",
        "label": "절연내력시험_6",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(300, 600)/10,
    },
    {
        "name": "acid_measure_val",
        "label": "산가도시험측정값",
        "dtype": "float",
        "generator": lambda: random.choice([0.02,0.03]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "moisture_rslt",
        "label": "수분시험결과",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(150, 350)/10,
    },
    {
        "name": "furan_diag_time",
        "label": "진단일",
        "dtype": "date",
        "generator": lambda: date(2020, 6, 1),
    },
    {
        "name": "furan_5H2F",
        "label": "furan_5h2f",
        "dtype": "int",
        "generator": lambda: random.choice([0]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "furan_2FOL",
        "label": "dga_2fol",
        "dtype": "float",
        "generator": lambda: random.choice([0]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "furan_2FAL",
        "label": "furan_2FAL",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 20),
    },
    {
        "name": "furan_2ACF",
        "label": "furan_2acf",
        "dtype": "int",
        "generator": lambda: random.choice([0]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "furan_5M2F",
        "label": "furan_5m2f",
        "dtype": "int",
        "generator": lambda: random.choice([0]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "part_discharge_diag",
        "label": "부분방전_진단결과",
        "dtype": "string",
        "generator": lambda: random.choice(["양호","이상"]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "oltc_96T_diag",
        "label": "96T_동작유무",
        "dtype": "string",
        "generator": lambda: random.choice(["정상","이상"]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "oltc_rslt",
        "label": "탭절환회수",
        "dtype": "int",
        "generator": lambda: random.choice([0,6000,9000,13000,18000]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "oltc_type",
        "label": "탭절환회수타입",
        "dtype": "string",
        "generator": lambda: random.choice(["Vaccum","Oil"]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "thermal_img_temp",
        "label": "발열변색여부",
        "dtype": "string",
        "generator": lambda: random.choice(["정상","이상"]),
        # "generator": lambda: random.randint(0, 200),
    },
    {
        "name": "noise_diag",
        "label": "이상소음발생여부",
        "dtype": "str",
        "generator": lambda: random.choice(["정상","이상"]),
    },
    {
        "name": "fire_vul_type",
        "label": "화재취약성타입",
        "dtype": "str",
        "generator": lambda: random.choice(["유입","몰드"]),
    },
    {
        "name": "fire_spread_loc",
        "label": "화재확산장소",
        "dtype": "str",
        "generator": lambda: random.choice(["옥내","옥외"]),
    },
    {
        "name": "emerge_response_1s",
        "label": "비상대응시간",
        "dtype": "str",
        "generator": lambda: random.choice(["가능","불가"]),
    },
    {
        "name": "redundancy",
        "label": "예비화",
        "dtype": "str",
        "generator": lambda: random.choice(["N+N","N+1,N+0"]),
    },
    {
        "name": "ato",
        "label": "계통자동전환",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "online_og_chk",
        "label": "온라인_유중가스",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "offline_safety_chk",
        "label": "안전공사_정밀점검",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "sec_num",
        "label": "보호요소수량",
        "dtype": "int",
        "generator": lambda: random.choice([4]),
    },
    {
        "name": "alarm_num",
        "label": "알람요소수량",
        "dtype": "int",
        "generator": lambda: random.choice([5]),
    },
    {
        "name": "insul_1st_lvup",
        "label": "절연1단계상승",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "high_insul_adt",
        "label": "고밀도절연지",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "double_insul",
        "label": "이중절연",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "55k_install",
        "label": "온도상승한도",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "sfra_test",
        "label": "sfra_시험",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "rip_install",
        "label": "부싱",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },
    {
        "name": "vacuum_set",
        "label": "OLTC",
        "dtype": "str",
        "generator": lambda: random.choice(["적용","미적용"]),
    },    
]


# def post_process_inputs(row: dict) -> dict:
#     """
#     입력 컬럼끼리 서로 값을 맞춰야 하는 경우(예: 완료수량은 전체수량을 넘을 수 없음)
#     여기서 보정합니다. 필요 없으면 그대로 두세요.
#     """
#     if row["completed_quantity"] > row["total_quantity"]:
#         row["completed_quantity"] = row["total_quantity"]
#     return row


# ------------------------------------------------------------------
# 2. CALCULATED COLUMNS (계산되는 컬럼 = 엑셀 수식 옮겨 적는 영역)
# ------------------------------------------------------------------
# 각 계산 컬럼은 dict 하나로 표현하며, 4개의 key를 가집니다.
#
#   name     : 컬럼명 (코드에서 쓸 영문 이름 — 02번 정의서의 코드명과 반드시 일치시킬 것)
#   label    : 화면 라벨 (한글)
#   dtype    : 결과 타입 (int/float/str/bool/date 등 — 문서화 목적, 자동 타입 검증은 안 함)
#   formula  : row(dict) 하나만 인자로 받아 "계산된 값 하나"를 반환하는 함수
#
# ── formula가 실제로 동작하는 원리 (main.py의 generate_row 참고) ──────────
#
#   for col in CALCULATED_COLUMNS:
#       row[col["name"]] = col["formula"](row)
#
# 1) 리스트를 "위에서 아래 순서"로 순회하면서 각 컬럼의 formula(row)를 호출하고,
#    반환값을 즉시 row[그 컬럼명]에 저장합니다. 그 다음 컬럼의 formula는 이미 갱신된
#    row를 넘겨받으므로, 앞서 계산된 값을 바로 참조할 수 있습니다.
# 2) 그래서 다른 계산 컬럼(row["다른_계산_컬럼명"])을 참조하려면, 그 컬럼이 지금 컬럼보다
#    "리스트 위쪽"에 있어야 합니다. 엑셀에서 다른 셀의 계산 결과를 참조할 때 그 셀이 먼저
#    계산되어 있어야 하는 것과 같은 원리입니다. 순서를 반대로 두면 KeyError가 납니다.
# 3) formula는 인자를 딱 1개(row)만 받습니다. 필요한 값이 여러 개여도 전부 row["컬럼명"]으로
#    꺼내 쓰면 되므로 인자 개수를 늘릴 필요가 없습니다. (row는 INPUT 값 + 이전 CALCULATED 값을
#    전부 담고 있는 "그 행 전체의 스냅샷"이라고 생각하면 됩니다)
# 4) 로직이 한 줄이면 람다(`lambda row: ...`)로 충분하지만, 조건 분기가 여러 단계이거나
#    중간 변수가 필요하면 `def`로 일반 함수를 만들고 그 함수 이름을 formula에 그대로
#    등록하면 됩니다 (`post_process_inputs`와 동일한 패턴). 억지로 람다 한 줄에 욱여넣지 마세요.
# 5) 반환값은 반드시 "스칼라 값 하나"여야 합니다 (숫자/문자열/불리언/날짜 등 하나).
#    list나 dict를 반환하면 안 됩니다 — 컬럼 하나에는 값 하나만 들어갑니다.
# 6) 0으로 나누기, 값 없음(None) 같은 예외는 엑셀의 IFERROR/IF(분모=0,...) 패턴과 동일하게
#    formula 함수 안에서 조건문으로 직접 처리합니다. main.py는 이 예외를 대신 처리해주지
#    않습니다.
# 7) DISPLAY_COLUMNS에 없어도, 다른 계산 컬럼이 참조하기 위한 "중간 계산용" 컬럼을
#    CALCULATED_COLUMNS에 추가하는 것도 가능합니다 (화면에는 안 보이고 계산에만 쓰임).
#
# ▶ 새 계산 컬럼(엑셀 수식) 추가 방법:
#   1. 엑셀에서 그 컬럼의 수식을 확인
#   2. 아래 리스트에 dict 추가, formula에 그 수식을 파이썬으로 옮겨 적기
#   3. 다른 계산 컬럼을 참조해야 하면, 참조당하는 컬럼을 리스트에서 "더 위쪽"에 둘 것
#      (계산은 리스트에 적힌 순서대로 진행됩니다)
#
# ▶ 엑셀 수식 → 파이썬 변환 예시 100선은 이 파일 맨 아래 "부록" 섹션 참고
def dga_tcg_cal(row):
    return (
        # row["age_minus"]+row["dga_minus"]+row["load_minus"]+row["temp_minus"] 
        row["dga_h2"]+row["dga_c2h2"]+row["dga_c2h4"] 
        + row["dga_c2h6"] + row["dga_ch4"] + row["dga_c3h8"]
    )
def dga_diag_cal(row):
    a = row["dga_h2"]
    b = row["dga_c2h2"]
    c = row["dga_c2h4"]
    d = row["dga_c2h6"]
    e = row["dga_ch4"]
    f = row["dga_c3h8"]
    g = row["dga_co"]
    h = row["dga_co2"]
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
    s = row["dielec_str_te_avg"]
    if s >= 20: return "적합"
    return "부적합"

def dielec_str_te_minus_cal(row):
    s = row["dielec_str_te_diag"]
    if s == '적합': return 0
    return -8

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
    return (
        row["furan_5H2F"]+row["furan_2FOL"]+row["furan_2FAL"] 
        + row["furan_2ACF"] + row["furan_5M2F"]
    )

def furan_total_per_year_cal(row):
    return (
        row["furan_total"] / row["operation_year"]
    )

def furan_desc_cal(row):
    s = row["furan_total_per_year"]
    if s > 5: return "이상"
    return "정상"

def furan_minus_cal(row):
    if row["furan_desc"] == '정상': return 0
    return -24

def part_discharge_minus_cal(row):
    s = row["part_discharge_diag"]
    if s == '양호': return 0
    return -20

def oltc_96T_minus_cal(row):
    if row["oltc_96T_diag"] == '정상': return 0
    return -12

def oltc_diag_cal(row):
    if row["oltc_type"] == 'Oil' and row["oltc_rslt"] >= 50000: return '이상'
    if row["oltc_type"] == 'Vacuum' and row["oltc_rslt"] >= 300000: return '이상'
    return '정상'

def oltc_minus_cal(row):
    if row["oltc_diag"] == '정상': return 0
    return -12

def thermal_img_minus_cal(row):
    s = row["thermal_img_temp"]
    if s == '정상': return 0
    return -8

def noise_minus_cal(row):
    if row["noise_diag"] == '정상': return 0
    return -2

def pof_minus_cal(row):
    return (
        # row["age_minus"]+row["dga_minus"]+row["load_minus"]+row["temp_minus"] 
        row["age_minus"]+row["load_minus"]+row["temp_minus"] 
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
    if row["fire_vul_type"] == '유입': return -8
    return 0

def fire_spread_minus_cal(row):
    if row["fire_spread_loc"] == '옥외': return -12
    if row["fire_spread_loc"] == '미분리': return -8
    if row["fire_spread_loc"] == '미설치': return -4
    return 0

def emerge_response_minus_cal(row):
    if row["emerge_response_1s"] == '불가': return -6
    return 0

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
        row["1st_voltage_minus"]+row["productivity_minus"]+row["fire_minus"] 
        + row["fire_spread_minus"] + row["emerge_response_minus"] + row["rep_cost_minus"]
        + row["rep_time_minus"]
    )

def redundancy_minus_cal(row):
    s = row["redundancy"]
    if s == 'N+N': return 0
    if s == 'N+1': return -18
    return -36

def ato_minus_cal(row):
    if row["ato"] == '미적용': return -36
    return 0

def online_og_minus_cal(row):
    if row["online_og_chk"] == '미적용': return -30
    return 0

def offline_safety_minus_cal(row):
    if row["offline_safety_chk"] == '미적용': return -25
    return 0

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
    if row["insul_1st_lvup"] == '미적용': return -16
    return 0

def prod_life_minus_cal(row):
    if row["high_insul_adt"] == '미적용': return -6
    return 0

def connect_part_minus_cal(row):
    if row["double_insul"] == '미적용': return -2
    return 0

def temp_inc_limit_minus_cal(row):
    if row["55k_install"] == '미적용': return -9
    return 0

def test_reliability_minus_cal(row):
    if row["sfra_test"] == '미적용': return -8
    return 0

def bushing_minus_cal(row):
    if row["rip_install"] == '미적용': return -8
    return 0

def oltc2_minus_cal(row):
    if row["vacuum_set"] == '미적용': return -8
    return 0

def dof_minus_cal(row):
    return (
        row["redundancy_minus"]+row["ato_minus"]+row["online_og_minus"] 
        + row["offline_safety_minus"] + row["sec_minus"] + row["alarm_minus"]
        + row["winding_minus"] + row["prod_life_minus"] + row["connect_part_minus"]
        + row["temp_inc_limit_minus"] + row["test_reliability_minus"] + row["bushing_minus"]
        + row["oltc2_minus"]
    )

CALCULATED_COLUMNS = [
    {
        "name": "today",
        "label": "오늘",
        "dtype": "date",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": lambda row: date.today(),
    },
    {
        "name": "operation_year",
        "label": "경과일",
        "dtype": "float",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": lambda row: round((date.today() - row["operation_start_time"]).days/365,1),
    },
    {
        "name": "age_minus",
        "label": "경과일",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula":lambda row: -(math.floor(row["operation_year"])),
    },
    {
        "name": "dga_tcg",
        "label": "dga_tcg",
        "dtype": "float",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": dga_tcg_cal,
    },
    {
        "name": "dga_diag",
        "label": "dga_판단",
        "dtype": "str",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": dga_diag_cal,
    },
    {
        "name": "dga_minus",
        "label": "dga감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": dga_minus_cal,
    },
    {
        "name": "load_minus",
        "label": "소음감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": load_minus_cal,
    },
    {
        "name": "temp_minus",
        "label": "운전온도감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": temp_minus_cal,
    },
    {
        "name": "dielec_str_te_avg",
        "label": "절연내력시험_평균",
        "dtype": "float",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": lambda row: (row["dielec_str_te_1"] + row["dielec_str_te_2"] + row["dielec_str_te_3"] 
                                + row["dielec_str_te_4"] + row["dielec_str_te_5"] + row["dielec_str_te_6"]) / 6
    },
    {
        "name": "dielec_str_te_diag",
        "label": "절연내력시험_판정",
        "dtype": "str",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": dielec_str_te_diag_cal,
    },
    {
        "name": "dielec_str_te_minus",
        "label": "절연내력시험_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": dielec_str_te_minus_cal,
    },
    {
        "name": "acid_measure_desc",
        "label": "산가도시험_판정",
        "dtype": "str",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": acid_measure_desc_cal,
    },
    {
        "name": "acid_measure_minus",
        "label": "산가도시험_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": acid_measure_minus_cal,
    },
    {
        "name": "moisture_desc",
        "label": "수분_판정",
        "dtype": "str",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": moisture_desc_cal,
    },
    {
        "name": "moisture_minus",
        "label": "수분_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": moisture_minus_cal,
    },
    {
        "name": "furan_total",
        "label": "furan_total",
        "dtype": "float",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": furan_total_cal,
    },
    {
        "name": "furan_total_per_year",
        "label": "furan_total",
        "dtype": "float",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": furan_total_per_year_cal,
    },
    {
        "name": "furan_desc",
        "label": "furan_판정",
        "dtype": "str",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": furan_desc_cal,
    },
    {
        "name": "furan_minus",
        "label": "furan_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": furan_minus_cal,
    },
    {
        "name": "part_discharge_minus",
        "label": "부분방전_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": part_discharge_minus_cal,
    },
    {
        "name": "oltc_96T_minus",
        "label": "oltc_96T_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": oltc_96T_minus_cal,
    },
    {
        "name": "oltc_diag",
        "label": "oltc_diag",
        "dtype": "str",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": oltc_diag_cal,
    },
    {
        "name": "oltc_minus",
        "label": "oltc_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": oltc_minus_cal,
    },
    {
        "name": "thermal_img_minus",
        "label": "열화상_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": thermal_img_minus_cal,
    },
    {
        "name": "noise_minus",
        "label": "소음감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": noise_minus_cal,
    },
    {
        "name": "pof_minus",
        "label": "pof_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": pof_minus_cal,
    },
    {
        "name": "pof",
        "label": "pof",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": lambda row: 100 + row["pof_minus"],
    },

    {
        "name": "1st_voltage",
        "label": "1차전압",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": lambda row: row["voltage"],
    },
    {
        "name": "1st_voltage_minus",
        "label": "1차전압_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": first_voltage_minus_cal,
    },
    {
        "name": "capa_times_load",
        "label": "용량x부하율 ",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": lambda row: (row["ONAN_val"]*row["load_percent"])/100,
    },
    {
        "name": "productivity_minus",
        "label": "1차전압_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": productivity_minus_cal,
    },
    {
        "name": "fire_minus",
        "label": "화재취약성_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": fire_minus_cal,
    },
    {
        "name": "fire_spread_minus",
        "label": "화재확산_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": fire_spread_minus_cal,
    },
    {
        "name": "emerge_response_minus",
        "label": "비상대응시간_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": emerge_response_minus_cal,
    },
    {
        "name": "rep_cost",
        "label": "교체비용",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": rep_cost_cal,
    },
        {
        "name": "rep_cost_minus",
        "label": "교체비용_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": rep_cost_minus_cal,
    },
        {
        "name": "rep_time",
        "label": "교체기간",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": rep_time_cal,
    },
        {
        "name": "rep_time_minus",
        "label": "교체기간_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": rep_time_minus_cal,
    },
    {
        "name": "cof_minus",
        "label": "cof_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": cof_minus_cal,
    },
    {
        "name": "cof",
        "label": "cof",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": lambda row: 100 + row["cof_minus"],
    },
    {
        "name": "redundancy_minus",
        "label": "redundancy_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": redundancy_minus_cal,
    },
    {
        "name": "ato_minus",
        "label": "ato_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": ato_minus_cal,
    },
    {
        "name": "online_og_minus",
        "label": "유중가스_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": online_og_minus_cal,
    },
    {
        "name": "offline_safety_minus",
        "label": "안전공사정밀점검_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": offline_safety_minus_cal,
    },
    {
        "name": "sec_minus",
        "label": "보호요소_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": sec_minus_cal,
    },
    {
        "name": "alarm_minus",
        "label": "알람요소_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": alarm_minus_cal,
    },
    {
        "name": "winding_minus",
        "label": "권선_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": winding_minus_cal,
    },
    {
        "name": "prod_life_minus",
        "label": "수명향상_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": prod_life_minus_cal,
    },
    {
        "name": "connect_part_minus",
        "label": "접속부_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": connect_part_minus_cal,
    },
    {
        "name": "temp_inc_limit_minus",
        "label": "온도상승한도_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": temp_inc_limit_minus_cal,
    },
    {
        "name": "test_reliability_minus",
        "label": "수송신뢰성_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": test_reliability_minus_cal,
    },
    {
        "name": "bushing_minus",
        "label": "온도상승한도_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": bushing_minus_cal,
    },
    {
        "name": "oltc2_minus",
        "label": "수송신뢰성_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": oltc2_minus_cal,
    },
    {
        "name": "dof_minus",
        "label": "dof_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": dof_minus_cal,
    },
    {
        "name": "dof",
        "label": "dof",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": lambda row: 100 + row["dof_minus"],
    },
    {
        "name": "total_score",
        "label": "종합점수",
        "dtype": "float",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": lambda row: 0.5*row["pof"] + 0.3*row["cof"] + 0.2*row["dof"],
    },
]

# ------------------------------------------------------------------
# 3. DISPLAY COLUMNS (웹 화면 구성용 최종 컬럼 모음)
# ------------------------------------------------------------------
# INPUT_COLUMNS + CALCULATED_COLUMNS 의 name 중에서
# 실제 웹 화면 테이블에 보여줄 컬럼만, 보여주고 싶은 순서 그대로 나열하세요.
# (여기 없는 컬럼은 .dat 전체 데이터에는 남지만 .yaml 화면용 데이터에는 빠집니다)

DISPLAY_COLUMNS = [
    # input
    "factory_code",
    "EF_code",
    "transformer_name",
    "voltage",
    "ONAN_val",
    "ONAF_val",
    "operation_start_time",
    "dga_diag_time",
    "dga_h2",
    "dga_c2h2",
    "dga_c2h4",
    "dga_c2h6",
    "dga_ch4",
    "dga_co",
    "dga_co2",
    "dga_o2",
    "dga_n2",
    "dga_o2",
    "dga_fluc",
    "load_percent",
    "coil_max_temp",
    "dielec_str_te_1",
    "dielec_str_te_2",
    "dielec_str_te_3",
    "dielec_str_te_4",
    "dielec_str_te_5",
    "dielec_str_te_6",
    "acid_measure_val",
    "moisture_rslt",
    "furan_diag_time",
    "furan_5H2F",
    "furan_2FOL",
    "furan_2FAL",
    "furan_2ACF",
    "furan_5M2F",
    "oltc_96T_diag",
    "oltc_rslt",
    "oltc_type",
    "thermal_img_temp",
    "noise_diag",
    "fire_vul_type",
    "fire_spread_loc",
    "emerge_response_1s",
    "redundancy",
    "ato",
    "online_og_chk",
    "offline_safety_chk",
    "sec_num",
    "alarm_num",
    "insul_1st_lvup",
    "high_insul_adt",
    "double_insul",
    "55k_install",
    "rip_install",
    "vacuum_set",

    # calc
    # pof
    "today",
    "operation_year",
    "age_minus",
    "load_minus",
    "temp_minus",
    "dielec_str_te_avg",
    "dielec_str_te_diag",
    "dielec_str_te_minus",
    "acid_measure_desc",
    "acid_measure_minus",
    "moisture_desc",
    "moisture_minus",
    "part_discharge_minus",
    "thermal_img_minus",
    "noise_minus", 

    #cof
    "fire_minus",
    "fire_spread_minus",
    "emerge_response_minus",


    #dof
    "redundancy_minus",
    "ato_minus",
    "online_og_minus",
    "offline_safety_minus",
    "sec_minus", 
    "alarm_minus",
    "winding_minus", 
    "prod_life_minus", 
    "connect_part_minus",
    "temp_inc_limit_minus", 
    "test_reliability_minus", 
    "bushing_minus",
    "oltc_minus",
    "dof_minus",
    "dof"

]    
# ====================================================================
# 부록. 엑셀 수식 → 파이썬(formula) 변환 예시 100선
# ====================================================================
# 아래는 실행되는 코드가 아니라 "참고용 주석"입니다. CALCULATED_COLUMNS에 새
# 계산 컬럼을 추가할 때, 엑셀 수식과 가장 비슷한 항목을 찾아 formula 자리에
# 옮겨 적는 용도로 쓰세요. row["a"], row["b"] 등은 실제 컬럼명으로 바꿔야 합니다.
# (일부 항목은 "행 하나"만으로 계산할 수 없는 데이터셋 전체 집계이므로,
#  그 경우는 formula가 아니라 별도 후처리/DB 집계 쿼리로 구현해야 한다고 표시해두었습니다)

# ---- A. 산술 연산 (1~10) ----
# 1. 합계          엑셀: =A1+B1                파이썬: lambda row: row["a"] + row["b"]
# 2. 차이          엑셀: =A1-B1                파이썬: lambda row: row["a"] - row["b"]
# 3. 곱셈          엑셀: =A1*B1                파이썬: lambda row: row["a"] * row["b"]
# 4. 나눗셈(0방지)  엑셀: =IF(B1=0,0,A1/B1)     파이썬: lambda row: row["a"] / row["b"] if row["b"] else 0
# 5. 백분율        엑셀: =A1/B1*100            파이썬: lambda row: round(row["a"] / row["b"] * 100, 1) if row["b"] else 0
# 6. 거듭제곱      엑셀: =A1^2                 파이썬: lambda row: row["a"] ** 2
# 7. 제곱근        엑셀: =SQRT(A1)             파이썬: lambda row: math.sqrt(row["a"])  # import math 필요
# 8. 절대값        엑셀: =ABS(A1-B1)           파이썬: lambda row: abs(row["a"] - row["b"])
# 9. 나머지        엑셀: =MOD(A1,B1)           파이썬: lambda row: row["a"] % row["b"]
# 10. 몫           엑셀: =QUOTIENT(A1,B1)      파이썬: lambda row: row["a"] // row["b"]

# ---- B. 반올림/절사 (11~18) ----
# 11. 반올림           엑셀: =ROUND(A1,2)         파이썬: lambda row: round(row["a"], 2)
# 12. 올림             엑셀: =ROUNDUP(A1,0)       파이썬: lambda row: math.ceil(row["a"])
# 13. 내림             엑셀: =ROUNDDOWN(A1,0)     파이썬: lambda row: math.floor(row["a"])
# 14. 정수부분만       엑셀: =INT(A1)             파이썬: lambda row: int(row["a"])
# 15. 소수 첫째자리 절사 엑셀: =TRUNC(A1,1)        파이썬: lambda row: math.trunc(row["a"] * 10) / 10
# 16. 100단위 올림      엑셀: =CEILING(A1,100)    파이썬: lambda row: math.ceil(row["a"] / 100) * 100
# 17. 100단위 내림      엑셀: =FLOOR(A1,100)      파이썬: lambda row: math.floor(row["a"] / 100) * 100
# 18. 정수로 반올림     엑셀: =ROUND(A1,0)        파이썬: lambda row: round(row["a"])

# ---- C. 조건문 IF류 (19~35) ----
# 19. 기본 IF            엑셀: =IF(A1>=80,"합격","불합격")
#                        파이썬: lambda row: "합격" if row["score"] >= 80 else "불합격"
# 20. 중첩 IF(3단계 등급) 엑셀: =IF(A1>=90,"A",IF(A1>=80,"B","C"))
#                        파이썬: lambda row: "A" if row["score"] >= 90 else "B" if row["score"] >= 80 else "C"
# 21. AND 조건            엑셀: =IF(AND(A1>=80,B1>=80),"통과","보류")
#                        파이썬: lambda row: "통과" if row["a"] >= 80 and row["b"] >= 80 else "보류"
# 22. OR 조건             엑셀: =IF(OR(A1="완료",B1="완료"),"완료","진행중")
#                        파이썬: lambda row: "완료" if row["a"] == "완료" or row["b"] == "완료" else "진행중"
# 23. NOT 조건            엑셀: =IF(NOT(A1="완료"),"미완료","완료")
#                        파이썬: lambda row: "미완료" if row["status"] != "완료" else "완료"
# 24. 4단계 등급          엑셀: =IF(A1>=90,"A",IF(A1>=80,"B",IF(A1>=70,"C","D")))
#                        파이썬: def calc_grade(row):
#                                    s = row["score"]
#                                    if s >= 90: return "A"
#                                    if s >= 80: return "B"
#                                    if s >= 70: return "C"
#                                    return "D"
# 25. IF + 문자열 결합    엑셀: =IF(A1>0,"흑자 "&A1,"적자")
#                        파이썬: lambda row: f"흑자 {row['a']}" if row["a"] > 0 else "적자"
# 26. 부호 분류           엑셀: =IF(A1>0,"양수",IF(A1<0,"음수","0"))
#                        파이썬: lambda row: "양수" if row["a"] > 0 else "음수" if row["a"] < 0 else "0"
# 27. 재고 상태           엑셀: =IF(A1<10,"부족",IF(A1>100,"과다","적정"))
#                        파이썬: lambda row: "부족" if row["stock"] < 10 else "과다" if row["stock"] > 100 else "적정"
# 28. 마감일 초과 여부    엑셀: =IF(TODAY()>A1,"지연","정상")
#                        파이썬: lambda row: "지연" if date.today() > row["due_date"] else "정상"
# 29. 예산초과 여부       엑셀: =IF(A1>B1,"초과","이내")
#                        파이썬: lambda row: "초과" if row["actual"] > row["budget"] else "이내"
# 30. 음수 0으로 보정     엑셀: =IF(A1<0,0,A1)
#                        파이썬: lambda row: max(row["a"], 0)
# 31. 100 초과 캡핑       엑셀: =IF(A1>100,100,A1)
#                        파이썬: lambda row: min(row["a"], 100)
# 32. 필수값 누락 체크    엑셀: =IF(A1="","미입력","입력완료")
#                        파이썬: lambda row: "미입력" if not row["a"] else "입력완료"
# 33. 진행률 100%면 자동완료 엑셀: =IF(A1=100,"완료",B1)
#                        파이썬: lambda row: "완료" if row["progress_rate"] >= 100 else row["status"]
# 34. 우선순위 분류       엑셀: =IF(A1="긴급","1순위",IF(A1="보통","2순위","3순위"))
#                        파이썬: lambda row: {"긴급": "1순위", "보통": "2순위"}.get(row["urgency"], "3순위")
# 35. 다중조건 스코어링   엑셀: =IF(AND(A1>=80,B1="완료"),100,IF(A1>=80,80,50))
#                        파이썬: def calc_score(row):
#                                    if row["a"] >= 80 and row["status"] == "완료": return 100
#                                    if row["a"] >= 80: return 80
#                                    return 50

# ---- D. 날짜/시간 (36~50) ----
# 36. 오늘날짜         엑셀: =TODAY()              파이썬: lambda row: date.today()
# 37. 경과일           엑셀: =TODAY()-A1           파이썬: lambda row: (date.today() - row["start_date"]).days
# 38. 남은일수         엑셀: =A1-TODAY()           파이썬: lambda row: (row["due_date"] - date.today()).days
# 39. 두 날짜 차이     엑셀: =B1-A1                파이썬: lambda row: (row["end_date"] - row["start_date"]).days
# 40. 연도 추출        엑셀: =YEAR(A1)             파이썬: lambda row: row["date"].year
# 41. 월 추출          엑셀: =MONTH(A1)            파이썬: lambda row: row["date"].month
# 42. 일 추출          엑셀: =DAY(A1)              파이썬: lambda row: row["date"].day
# 43. 요일(1=월요일)   엑셀: =WEEKDAY(A1,2)        파이썬: lambda row: row["date"].isoweekday()
# 44. N일 후           엑셀: =A1+30               파이썬: lambda row: row["date"] + timedelta(days=30)
# 45. N개월 후         엑셀: =EDATE(A1,1)          파이썬: # dateutil.relativedelta 필요
#                                                          lambda row: row["date"] + relativedelta(months=1)
# 46. 그 달의 말일     엑셀: =EOMONTH(A1,0)        파이썬: import calendar
#                                                          lambda row: date(row["date"].year, row["date"].month,
#                                                              calendar.monthrange(row["date"].year, row["date"].month)[1])
# 47. 분기 계산        엑셀: =ROUNDUP(MONTH(A1)/3,0) 파이썬: lambda row: math.ceil(row["date"].month / 3)
# 48. 주말 여부        엑셀: =IF(WEEKDAY(A1,2)>5,"주말","평일")
#                        파이썬: lambda row: "주말" if row["date"].isoweekday() > 5 else "평일"
# 49. 만 나이 계산     엑셀: =DATEDIF(A1,TODAY(),"Y")
#                        파이썬: lambda row: date.today().year - row["birth"].year -
#                                    ((date.today().month, date.today().day) < (row["birth"].month, row["birth"].day))
# 50. D-Day 표시       엑셀: =TEXT(A1-TODAY(),"D-0")
#                        파이썬: lambda row: f"D-{(row['due_date'] - date.today()).days}" \
#                                    if row["due_date"] >= date.today() else f"D+{(date.today() - row['due_date']).days}"

# ---- E. 텍스트 처리 (51~65) ----
# 51. 문자 결합          엑셀: =A1&B1                    파이썬: lambda row: row["a"] + row["b"]
# 52. 구분자 결합        엑셀: =A1&"-"&B1                파이썬: lambda row: f'{row["a"]}-{row["b"]}'
# 53. CONCATENATE       엑셀: =CONCATENATE(A1,B1)        파이썬: lambda row: row["a"] + row["b"]  (51과 동일)
# 54. 왼쪽 N글자         엑셀: =LEFT(A1,3)                파이썬: lambda row: row["a"][:3]
# 55. 오른쪽 N글자       엑셀: =RIGHT(A1,3)               파이썬: lambda row: row["a"][-3:]
# 56. 중간 글자          엑셀: =MID(A1,2,3)               파이썬: lambda row: row["a"][1:4]
# 57. 문자 길이          엑셀: =LEN(A1)                   파이썬: lambda row: len(row["a"])
# 58. 대문자 변환        엑셀: =UPPER(A1)                 파이썬: lambda row: row["a"].upper()
# 59. 소문자 변환        엑셀: =LOWER(A1)                 파이썬: lambda row: row["a"].lower()
# 60. 공백 제거          엑셀: =TRIM(A1)                  파이썬: lambda row: row["a"].strip()
# 61. 문자 치환          엑셀: =SUBSTITUTE(A1,"-","")     파이썬: lambda row: row["a"].replace("-", "")
# 62. 특정 문자 포함 여부 엑셀: =IF(ISNUMBER(SEARCH("긴급",A1)),1,0)
#                        파이썬: lambda row: 1 if "긴급" in row["a"] else 0
# 63. 숫자 천단위 포맷    엑셀: =TEXT(A1,"#,##0")          파이썬: lambda row: f'{row["a"]:,}'
# 64. 텍스트를 숫자로     엑셀: =VALUE(A1)                 파이썬: lambda row: float(row["a"])
# 65. 가운데 마스킹       엑셀: =LEFT(A1,3)&"***"&RIGHT(A1,2)
#                        파이썬: lambda row: row["a"][:3] + "***" + row["a"][-2:]

# ---- F. 집계 (66~78) — 일부는 데이터셋 전체가 필요합니다 (아래 ※ 표시 참고) ----
# 66. 여러 컬럼 합계     엑셀: =SUM(A1:C1)      파이썬: lambda row: row["a"] + row["b"] + row["c"]
# 67. 여러 컬럼 평균     엑셀: =AVERAGE(A1:C1)  파이썬: lambda row: (row["a"] + row["b"] + row["c"]) / 3
# 68. 여러 컬럼 최대     엑셀: =MAX(A1:C1)      파이썬: lambda row: max(row["a"], row["b"], row["c"])
# 69. 여러 컬럼 최소     엑셀: =MIN(A1,B1)      파이썬: lambda row: min(row["a"], row["b"])
# 70. ※조건부 개수(COUNTIF)  엑셀: =COUNTIF(전체범위,"완료")
#     → 행 하나로는 계산 불가. 전체 rows 생성 후: sum(1 for r in rows if r["status"] == "완료")
# 71. ※조건부 합계(SUMIF)    엑셀: =SUMIF(상태범위,"완료",금액범위)
#     → 마찬가지로 데이터셋 전체 대상 후처리 또는 DB의 GROUP BY/SUM 쿼리로 구현
# 72. ※다중조건 합계(SUMIFS) 엑셀: =SUMIFS(금액,상태,"완료",담당자,"김철수")
#     → SQL: SELECT SUM(amount) WHERE status='완료' AND manager='김철수'
# 73. ※중앙값(MEDIAN)        엑셀: =MEDIAN(전체범위)   → statistics.median([r["a"] for r in rows])
# 74. ※표준편차(STDEV)       엑셀: =STDEV(전체범위)    → statistics.stdev([r["a"] for r in rows])
# 75. ※순위(RANK)            엑셀: =RANK(A1,전체범위)  → 전체 정렬 후 순번 부여 (행 단위 formula 불가)
# 76. ※백분위(PERCENTRANK)   엑셀: =PERCENTRANK(전체범위,A1) → scipy.stats.percentileofscore 등 활용
# 77. ※최빈값(MODE)          엑셀: =MODE(전체범위)     → statistics.mode([...])
# 78. ※누적합(런닝토탈)      엑셀: 위쪽 행까지의 누적 =SUM($A$1:A1)
#     → 행 생성 순서대로 running_total += row["a"] 형태의 후처리 루프 필요 (formula 함수 하나로는 표현 불가)

# ---- G. 에러/결측 처리 (79~86) ----
# 79. 에러시 기본값(IFERROR)  엑셀: =IFERROR(A1/B1,0)
#                        파이썬: lambda row: row["a"] / row["b"] if row["b"] else 0
# 80. NA 대체(IFNA)          엑셀: =IFNA(VLOOKUP(...),"없음")
#                        파이썬: lambda row: MAPPING.get(row["code"], "없음")
# 81. 빈칸 여부(ISBLANK)     엑셀: =IF(ISBLANK(A1),"미입력",A1)
#                        파이썬: lambda row: row["a"] if row["a"] not in (None, "") else "미입력"
# 82. 숫자 여부(ISNUMBER)    엑셀: =IF(ISNUMBER(A1),"숫자","숫자아님")
#                        파이썬: lambda row: "숫자" if isinstance(row["a"], (int, float)) else "숫자아님"
# 83. 문자 여부(ISTEXT)      엑셀: =IF(ISTEXT(A1),"텍스트","텍스트아님")
#                        파이썬: lambda row: "텍스트" if isinstance(row["a"], str) else "텍스트아님"
# 84. None이면 기본값        엑셀: =IF(A1="", "N/A", A1)
#                        파이썬: lambda row: row["a"] if row["a"] is not None else "N/A"
# 85. 0이면 기본 문구         엑셀: =IF(A1=0,"데이터없음",A1)
#                        파이썬: lambda row: "데이터없음" if row["a"] == 0 else row["a"]
# 86. 리스트 값 없을 때 기본  엑셀: =IFERROR(INDEX(범위,MATCH(A1,키범위,0)),"미매칭")
#                        파이썬: lambda row: LOOKUP_DICT.get(row["key"], "미매칭")

# ---- H. 조회/매핑 (87~94) ----
# 87. VLOOKUP(단순매핑)      엑셀: =VLOOKUP(A1,매핑표,2,0)
#                        파이썬: CODE_TO_LABEL = {"P1": "1단계", "P2": "2단계"}
#                                lambda row: CODE_TO_LABEL.get(row["code"])
# 88. HLOOKUP              엑셀: =HLOOKUP(A1,가로매핑표,2,0)  → 87과 동일한 dict lookup 패턴
# 89. INDEX/MATCH          엑셀: =INDEX(값범위,MATCH(A1,키범위,0))  → 87과 동일한 dict lookup 패턴
# 90. CHOOSE(인덱스 선택)   엑셀: =CHOOSE(A1,"낮음","보통","높음")
#                        파이썬: lambda row: ["낮음", "보통", "높음"][row["level"] - 1]
# 91. 코드→라벨 변환        엑셀: =VLOOKUP(A1,상태코드표,2,0)
#                        파이썬: STATUS_LABEL = {"S1": "진행중", "S2": "완료", "S3": "보류"}
#                                lambda row: STATUS_LABEL.get(row["status_code"], "알수없음")
# 92. 금액 구간별 등급      엑셀: =IF(A1>=1000000,"대형",IF(A1>=100000,"중형","소형"))
#                        파이썬: def calc_size_grade(row):
#                                    if row["amount"] >= 1_000_000: return "대형"
#                                    if row["amount"] >= 100_000: return "중형"
#                                    return "소형"
# 93. 부서→담당임원 매핑    엑셀: =VLOOKUP(A1,부서매핑표,2,0)
#                        파이썬: DEPT_TO_EXEC = {"개발팀": "김임원", "영업팀": "이임원"}
#                                lambda row: DEPT_TO_EXEC.get(row["dept"], "미지정")
# 94. 기본값 있는 매핑      엑셀: =IFERROR(VLOOKUP(A1,표,2,0),"기타")
#                        파이썬: lambda row: MAPPING.get(row["key"], "기타")

# ---- I. 비율/증감/스코어링 (95~100) ----
# 95. 전월대비 증감률   엑셀: =(이번달-지난달)/지난달*100
#                      파이썬: lambda row: round((row["this_month"] - row["last_month"]) / row["last_month"] * 100, 1) \
#                                  if row["last_month"] else 0
# 96. 전년대비 증감률   엑셀: =(올해-작년)/작년*100  → 95와 동일 패턴, 컬럼명만 교체
# 97. ※누적 비중(%)    엑셀: =A1/SUM(전체범위)*100
#     → 전체 합계가 필요하므로 행 단위 계산 불가. 전체 rows 생성 후 total = sum(r["a"] for r in rows) 계산 뒤
#       각 행에 대해 round(row["a"] / total * 100, 1) 형태로 별도 후처리
# 98. 목표대비 달성률   엑셀: =실적/목표*100
#                      파이썬: lambda row: round(row["actual"] / row["target"] * 100, 1) if row["target"] else 0
# 99. 초과분만 계산     엑셀: =MAX(0,실적-목표)
#                      파이썬: lambda row: max(0, row["actual"] - row["target"])
# 100. 가중합 스코어    엑셀: =A1*0.3+B1*0.4+C1*0.3
#                      파이썬: lambda row: round(row["a"] * 0.3 + row["b"] * 0.4 + row["c"] * 0.3, 1)


