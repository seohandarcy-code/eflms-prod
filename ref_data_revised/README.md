# ref_data_revised — 시스템 계산 수정본 (2026-11-19)

`ref_data/`의 원본 계산 양식(`schema_eflms_####.py`)에 **EFLMS 시스템이 실제로 쓰는 계산 규칙**을 반영한 참고용 수정본이다.

- 원본(`ref_data/`)은 수정 금지 — 그대로 두고, 이 폴더에 같은 이름으로 복사한 뒤 고쳤다.
- 같은 입력이면 시스템 계산기(`backend/app/equipment_types/ef*_*.py`)와 **모든 계산 컬럼이 같다**. `backend/tests/test_reference_revised.py`가 유형마다 무작위 입력 300건 + 경계값 입력으로 대조한다. 시스템 계산을 바꾸면 이 폴더도 함께 고쳐야 테스트가 통과한다.
- 파일 구조(INPUT_COLUMNS → CALCULATED_COLUMNS → DISPLAY_COLUMNS, 맨 아래 엑셀 수식 대조 주석)는 원본 그대로다. 바꾼 줄에는 `# 시스템:` 주석이 있다.

| 파일 | 설비유형 | 시스템 계산기 |
|---|---|---|
| `schema_eflms.py` | EF1 변압기 | `ef1_transformer.py` |
| `schema_eflms_gis.py` | EF2 GIS | `ef2_gis.py` |
| `schema_eflms_cable.py` | EF3 초고압케이블 | `ef3_cable.py` |
| `schema_eflms_subaejeon.py` | EF4 수배전반 | `ef4_switchgear.py` |
| `schema_eflms_ups.py` | EF5 UPS | `ef5_ups.py` |
| `schema_eflms_vdp.py` | EF6 VDP | `ef6_vdp.py` |
| `schema_eflms_battery.py` | EF7 배터리 | `ef7_battery.py` |

## 공통 반영 사항 (모든 파일)

| 항목 | 원본 | 수정본(= 시스템) |
|---|---|---|
| 소수 첫째 자리 | 반올림 없음(또는 정수) | 감점 항목(`_minus`)과 `pof`·`cof`·`dof`·`total_score`를 계산 직후 소수 첫째 자리로 — 엑셀 `ROUND(값, 1)`처럼 5에서 올림(-0.25 → -0.3). 파일 위쪽 `round1()`, CALCULATED_COLUMNS 바로 뒤 `_apply_system_rounding()` |
| 합산 | — | 위에서부터 차례로 계산하므로 합계 감점 = 반올림된 항목 감점의 합(화면의 항목 감점을 더하면 축 감점과 정확히 맞음) |
| 운전년수 | `round(경과일/365, 1)` | `round1(경과일/365)`(엑셀식 반올림) |
| 경과연수 감점 | `-floor(운전년수)` | `-운전년수`(12.7년 → -12.7) |
| 감점 dtype | `int` | `float` |

## 설비유형별 반영 사항

| 유형 | 감점 | 원본 | 수정본 |
|---|---|---|---|
| EF1 변압기 | Furan 연평균 `furan_total_per_year` | 합계 ÷ 오늘까지의 운전년수(해가 갈수록 판정이 좋아짐, 설치 18일 이내 0으로 나눔) | 합계 ÷ **Furan 진단 시점 사용년수**(진단일 - 가동년월, 새 칸 `furan_diag_year`) — 날짜가 지나도 그대로. 진단일 ≤ 가동년월이면 평가 불가(감점 0) |
| EF2 GIS | 차단기·절연 상태 `cb_stat_minus`·`insul_stat_minus` | `round(…)` | 소수 그대로 |
| EF2 GIS | CB 동작특성 기준치 초과 `cb_op_char_over` | 입력 + 감점 -9 | **삭제**(2026-10-19 미사용 결정) |
| EF2 GIS | 전기적 감점 `gis_elec_minus` | 경과연수 미합산 | 경과연수 `age_minus` **합산**(2026-10-19) |
| EF2 GIS | 누적 차단 전류 `cum_trip_current` | `int` | `float`(실데이터에 소수값) |
| EF3 케이블 | 고장률 `failure_rate_minus`, 용량 `risk_mva_minus` | `round(…)` | 소수 그대로 |
| EF4 수배전반 | 차단기 상태 `cb_stat_minus`, 피해규모 `scale_dam_chk_minus` | `round(…)` | 소수 그대로 |
| EF5 UPS·EF6 VDP | 부품 고장확률 5종 `cb`·`cap`·`fan`·`igbt`·`board_stat_minus`, 전기실 온도 `elec_room_max_temp_minus` | `round(…)` | 소수 그대로 |
| EF5 UPS·EF6 VDP | 부하율·모듈 순환전류·모듈 전압차·소음 감점 | `int(…)` | 소수 그대로 |
| EF7 배터리 | (경과연수·소수 첫째 자리 공통 사항만) | | |

일부러 그대로 둔 것(시스템도 같음): EF5·EF6 차단기 교체 횟수 `int(운전년수/7.5)`(횟수), EF7 온도감소계수의 연차 번호 `int(운전년수)`(표 찾기 — 소수 부분은 보간), EF7 중간값 반올림(방전인덱스 `round(…, 3)`, 온도감소계수 `round(…, 1)`).

## 코드에 반영하지 않은 것 (시스템이 데이터를 다루는 방식 — 각 파일 머리말에도 적음)

- **값 없음(N/A)**: 입력파일의 `N/A`는 null로 저장되고, null을 읽는 감점은 0, 그 밖의 파생값은 null(`backend/app/equipment_types/na.py`). 수정본은 원본처럼 값이 다 있는 입력을 전제로 한다.
- **계산 기준일**: 시스템은 기준일을 지정할 수 있다(기본 오늘 = 수정본의 `date.today()`).
- **임포트 허용값**: 원본 판정에 없는 값은 행 오류로 거부(`docs/DATA_DICTIONARY.md` 각 유형 절).
- **전압 0**: EF4~EF7은 원본에 전압 입력이 없어 시스템이 공통 `voltage`에 0을 채운다.
- **EF7 참고표**: 방전이력·온도감소계수 표는 시스템에서 DB 참고표로 관리(사업장별). 수정본은 원본처럼 파일 안의 표를 쓴다.

자세한 결정 배경은 `docs/DATA_DICTIONARY.md` "감점 소수 계산", 각 유형 절의 "원본 그대로 유지하는 판단".
