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

_tl_name_counters = {"tl": itertools.count(1), "htl": itertools.count(1)}

def _gen_tl_name():
    """접두사별로 독립 증가하는 번호를 붙여 행마다 겹치지 않는 이름을 생성"""
    prefix = random.choice(["tl","htl"])
    return f"{prefix}{next(_tl_name_counters[prefix])}"

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
        "generator": lambda: random.choice(["EF3"]),
    },
    {
        "name": "tl_name",
        "label": "T/L명",
        "dtype": "str",
        "generator": _gen_tl_name,
    },
    {
        "name": "voltage",
        "label": "전압",
        "dtype": "int",
        "generator": lambda: random.choice([154000]),
    },
    {
        "name": "cable_sq",
        "label": "굵기",
        "dtype": "int",
        "generator": lambda: random.choice([1200,1600]),
    },
    {
        "name": "cable_per_phase",
        "label": "phase당케이블",
        "dtype": "int",
        "generator": lambda: random.choice([1,2]),
    },
    {
        "name": "cable_mva",
        "label": "회선별용량",
        "dtype": "int",
        "generator": lambda: random.choice([414,984]),
    },
    {
        "name": "operation_start_time",
        "label": "가동년월",
        "dtype": "date",
        "generator": lambda: date(2005, 1, 1) + timedelta(days=random.randint(0, 3650)),
    },
    {
        "name": "max_load",
        "label": "최대부하",
        "dtype": "int",
        "generator": lambda: random.randint(80, 200),
    },
    {
        "name": "max_temp",
        "label": "최고온도",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(200, 300)/10,
    },
    {
        "name": "diff_temp",
        "label": "상간온도차",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(5, 40)/10,
    },
    {
        "name": "failure_rate",
        "label": "온도기반손상률",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(60, 700)/100000,
    },
    {
        "name": "pd_num",
        "label": "부분방전발생횟수",
        "dtype": "int",
        "generator": lambda: random.randint(0, 3),
    },
    {
        "name": "sys_cycle_curr",
        "label": "시스순환전류",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(20, 400)/10,
    },
    {
        "name": "svl_leak_curr",
        "label": "SVL누설전류",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 150)/1000,
    },
    {
        "name": "joint_ex_damage",
        "label": "접속함외관손상여부",
        "dtype": "str",
        "generator": lambda: random.choice(["양호", "이상"]),
    },
    {
        "name": "cable_move",
        "label": "케이블이동량",
        "dtype": "float",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 100)/10,
    },
    {
        "name": "cable_length",
        "label": "케이블길이",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(300, 15000),
    },
    {
        "name": "laying_type",
        "label": "포설방법",
        "dtype": "str",
        "generator": lambda: random.choice(["관로구", "전력구", "공동구"]),
    },
    {
        "name": "mid_joint",
        "label": "중간접속함개수",
        "dtype": "int",
        # "generator": lambda: random.choice(["0", "37.5", "43.75","100"]),
        "generator": lambda: random.randint(0, 10),
    },
    {
        "name": "end_joint",
        "label": "종단접속함종류",
        "dtype": "str",
        "generator": lambda: random.choice(['DEBG, EBA','DEBG', 'WEBG']),
    },
    {
        "name": "emerge_resp",
        "label": "비상대응시간",
        "dtype": "str",
        "generator": lambda: random.choice(["1초내"]),
    },
    {
        "name": "rep_time",
        "label": "정상화기간_설비교체",
        "dtype": "str",
        "generator": lambda: random.choice(["3개월이하"]),
    },


    {
        "name": "reliability",
        "label": "공급신뢰도회선수",
        "dtype": "int",
        "generator": lambda: random.choice([2,3,4]),
    },
    {
        "name": "temp_diag",
        "label": "열화상진단여부",
        "dtype": "str",
        "generator": lambda: random.choice(["O"]),
    },
    {
        "name": "pd_diag",
        "label": "PD진단여부",
        "dtype": "str",
        "generator": lambda: random.choice(["O"]),
    },
    {
        "name": "live_line_diag",
        "label": "활선진단여부",
        "dtype": "str",
        "generator": lambda: random.choice(["X"]),
    },
    {
        "name": "cable_move_diag",
        "label": "이동량여부",
        "dtype": "str",
        "generator": lambda: random.choice(["X"]),
    },
    {
        "name": "offline_diag",
        "label": "오프라인진단여부",
        "dtype": "str",
        "generator": lambda: random.choice(["1년이내"]),
    },
    {
        "name": "longlife_insul",
        "label": "장수명절연물여부",
        "dtype": "str",
        "generator": lambda: random.choice(["X"]),
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
    s = row["joint_ex_damage"]
    if s == '양호': return 0
    return -5

def cable_move_minus_cal(row):
    s = row["cable_move"]
    if s > 10: return -20
    if s > 5: return -15
    if s > 3: return -10
    if s > 1: return -5
    return 0

def pof_minus_cal(row):
    return (
        row["age_minus"]+row["load_minus"]+row["temp_minus"] 
        + row["diff_temp_minus"] + row["failure_rate_minus"] + row["pd_minus"]
        + row["sys_cycle_curr_minus"] + row["svl_leak_curr_minus"] + row["joint_ex_damage_minus"] 
        + row["cable_move_minus"]
    )

def laying_type_minus_cal(row):
    s = row["laying_type"]
    if s == '철탑': return -30
    if s == '공동구': return -20
    if s == '관로구': return -10
    if s == '전력구': return 0
    return 0

def end_joint_minus_cal(row):
    s = row["end_joint"]
    if s == 'WEBG': return -30
    if s == 'DEBG, EBA': return -5
    if s == 'DEBG': return 0
    return 0

def emerge_resp_minus_cal(row):
    s = row["emerge_resp"]
    if s == '24시간이하': return -10
    if s == '12시간이하': return -5
    if s == '1시간이하': return -3
    if s == '1초내': return 0
    return 0

def rep_cost_minus_cal(row):
    s = row["rep_cost"]
    if s > 100: return -12
    if s > 50: return -10
    if s > 20: return -8
    if s > 10: return -6
    if s > 5: return -4
    return -2

def rep_time_minus_cal(row):
    s = row["rep_time"]
    if s == '3개월초과': return -10
    if s == '3개월이하': return 0
    return 0

def cof_minus_cal(row):
    return (
        row["risk_mva_minus"]+row["laying_type_minus"]+row["mid_joint_minus"] 
        + row["end_joint_minus"] + row["emerge_resp_minus"] + row["rep_cost_minus"]
        + row["rep_time_minus"]
    )

def reliability_minus_cal(row):
    s = row["reliability"]
    if s == 4: return 0
    if s == 3: return 0
    if s == 2: return -20
    return -20

def temp_diag_minus_cal(row):
    s = row["temp_diag"]
    if s == 'X': return -10
    if s == 'O': return 0
    return 0

def pd_diag_minus_cal(row):
    s = row["pd_diag"]
    if s == 'X': return -10
    if s == 'O': return 0
    return 0

def live_line_diag_minus_cal(row):
    s = row["live_line_diag"]
    if s == 'X': return -10
    if s == 'O': return 0
    return 0

def cable_move_diag_minus_cal(row):
    s = row["cable_move_diag"]
    if s == 'X': return -10
    if s == 'O': return 0
    return 0

def offline_diag_minus_cal(row):
    s = row["offline_diag"]
    if s == '미실시': return -20
    if s == '3년이내': return -10
    if s == '1년이내': return 0
    return 0

def longlife_insul_minus_cal(row):
    s = row["longlife_insul"]
    if s == 'X': return -10
    if s == 'O': return 0
    return 0

def dof_minus_cal(row):
    return (
        row["reliability_minus"]+row["temp_diag_minus"]+row["pd_diag_minus"] 
        + row["live_line_diag_minus"] + row["cable_move_diag_minus"] + row["offline_diag_minus"]
        + row["longlife_insul_minus"]
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
        "label": "사용년수(년)",
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
        "name": "load_percent",
        "label": "부하율",
        "dtype": "float",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula":lambda row: row["max_load"] / row["cable_mva"] * 100,
    },

    {
        "name": "load_minus",
        "label": "부하율감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": load_minus_cal,
    },
    {
        "name": "temp_minus",
        "label": "온도감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": temp_minus_cal,
    },
    {
        "name": "diff_temp_minus",
        "label": "열화상감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": diff_temp_minus_cal,
    },
    {
        "name": "failure_rate_minus",
        "label": "온도기반손상률감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": lambda row: round(row["failure_rate"] * (-1000)),
    },

    {
        "name": "pd_minus",
        "label": "부분방전발생횟수감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": pd_minus_cal,
    },
    {
        "name": "sys_cycle_curr_minus",
        "label": "시스템순환전류감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": sys_cycle_curr_minus_cal,
    },
    {
        "name": "svl_leak_curr_minus",
        "label": "svl누설전류감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": svl_leak_curr_minus_cal,
    },
    {
        "name": "joint_ex_damage_minus",
        "label": "접속함외관감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": joint_ex_damage_minus_cal,
    },
    {
        "name": "cable_move_minus",
        "label": "케이블이동량감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": cable_move_minus_cal,
    },
    {
        "name": "pof_minus",
        "label": "POF_감점",
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
        "name": "risk_mva",
        "label": "사고영향성용량",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": lambda row: row["cable_mva"],
    },

    {
        "name": "risk_mva_minus",
        "label": "사고영향성감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": lambda row: round(row["cable_mva"]*0.01*(-1)),
    },

    {
        "name": "laying_type_minus",
        "label": "포설방법감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": laying_type_minus_cal,
    },

    {
        "name": "mid_joint_minus",
        "label": "중간접속함감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": lambda row: (-1) * row["mid_joint"],
    },

    {
        "name": "end_joint_minus",
        "label": "종단접속함감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": end_joint_minus_cal,
    },

    {
        "name": "emerge_resp_minus",
        "label": "비상대응시간감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": emerge_resp_minus_cal,
    },

    {
        "name": "rep_cost",
        "label": "사고복구교체비용",
        "dtype": "float",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": lambda row: row["cable_length"]*0.0135,
    },

    {
        "name": "rep_cost_minus",
        "label": "사고복구비용감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": rep_cost_minus_cal,
    },

    {
        "name": "rep_time_minus",
        "label": "정상화기간감점",
        "dtype": "int",
        # 엑셀 수식 예시: =TODAY()-시작일
        "formula": rep_time_minus_cal,
    },
    {
        "name": "cof_minus",
        "label": "COF_감점",
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
        "name": "reliability_minus",
        "label": "공급신뢰도감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": reliability_minus_cal,
    },

    {
        "name": "temp_diag_minus",
        "label": "열화상진단감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": temp_diag_minus_cal,
    },

    {
        "name": "pd_diag_minus",
        "label": "PD진단감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": pd_diag_minus_cal,
    },

    {
        "name": "live_line_diag_minus",
        "label": "활선진단감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": live_line_diag_minus_cal,
    },

    {
        "name": "cable_move_diag_minus",
        "label": "케이블이동량여부_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": cable_move_diag_minus_cal,
    },

    {
        "name": "offline_diag_minus",
        "label": "오프라인진단감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": offline_diag_minus_cal,
    },

    {
        "name": "longlife_insul_minus",
        "label": "장수명절연물_감점",
        "dtype": "int",
        # 엑셀 수식 예시: =IF(진행률=100,"완료",IF(상태="보류","보류","진행중"))
        # progress_rate(위에서 계산됨)를 참조하는 예시
        "formula": longlife_insul_minus_cal,
    },

    {
        "name": "dof_minus",
        "label": "DOF_감점",
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
    "tl_name",
    # calc
    "today",
    "operation_year",
    # pof
    "pof_minus",
    "pof",

    #cof
    "cof_minus",
    "cof",

    #dof
    "dof_minus",
    "dof",
    "total_score",
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


