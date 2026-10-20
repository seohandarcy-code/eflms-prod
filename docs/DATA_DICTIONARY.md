# 데이터 사전 (EF1 · 변압기 / EF2 · GIS)

설비유형별 출처(INPUT_COLUMNS / CALCULATED_COLUMNS) — 컬럼 상세는 원본 파일의 `label`/`dtype`을 그대로 따른다. 아래는 각 컬럼이 어느 도메인 테이블로 들어가는지의 매핑이다.

| 설비유형 | 원본(참고자료, 수정 금지) | 시스템 계산기 |
|---|---|---|
| EF1 변압기 | `ref_data/schema_eflms.py` | `backend/app/equipment_types/ef1_transformer.py` |
| EF2 GIS | `ref_data/schema_eflms_gis.py` | `backend/app/equipment_types/ef2_gis.py` |

## 공통 테이블

| 테이블 | 컬럼 |
|---|---|
| `equipment_type` | `ef_code`(PK), `name`, `description` |
| `equipment` | `equipment_id`(PK), `factory_code`, `ef_code`(FK), `equipment_name`, `voltage`, `operation_start_time`, `created_at` — `UNIQUE(factory_code, ef_code, equipment_name)`. `equipment_name`에는 설비유형 원본의 이름 컬럼이 들어간다(EF1 `transformer_name`, EF2 `gis_name`) |
| `score_snapshot` | `equipment_id`(FK), `pof_minus`, `pof`, `cof_minus`, `cof`, `dof_minus`, `dof`, `total_score`, `computed_at` |

> **Stage 8-1(2026-10-16, 마이그레이션 `8a1c4e2f9b70`)**: `equipment`에서 변압기 전용 요소를 걷어냈다 — `transformer_name` → `equipment_name`, `onan_val`/`onaf_val`은 EF1 전용 `transformer_spec`으로 값 이관. 사내 EF1 입력파일 헤더는 그대로 `transformer_name`/`ONAN_val`/`ONAF_val`이다(적재 시 매핑). 이 1회성 예외 이후로는 공통 레이어를 바꾸지 않는다.

## EF1 입력 도메인 테이블

| 테이블 | INPUT_COLUMNS 매핑 | 시점 컬럼 |
|---|---|---|
| `transformer_spec` | `ONAN_val` → `onan_val`, `ONAF_val` → `onaf_val` (Stage 8-1에 `equipment`에서 분리) | `updated_at` |
| `dga_reading` | `dga_h2`, `dga_c2h2`, `dga_c2h4`, `dga_c2h6`, `dga_ch4`, `dga_c3h8`, `dga_co`, `dga_co2`, `dga_o2`, `dga_n2`, `dga_fluc` | `diag_time` (= `dga_diag_time`) |
| `furan_reading` | `furan_5H2F`, `furan_2FOL`, `furan_2FAL`, `furan_2ACF`, `furan_5M2F` | `diag_time` (= `furan_diag_time`) |
| `dielectric_test` | `dielec_str_te_1`~`dielec_str_te_6` | `measured_at` (신규 — 원본 mock엔 날짜 없음) |
| `oil_test` | `acid_measure_val`, `moisture_rslt` | `measured_at` (신규) |
| `load_condition` | `load_percent`, `coil_max_temp` | `measured_at` (신규) |
| `periodic_inspection` | `part_discharge_diag`, `oltc_96T_diag`, `oltc_rslt`, `oltc_type`, `thermal_img_temp`, `noise_diag` | `measured_at` (신규) |
| `design_attribute` | `fire_vul_type`, `fire_spread_loc`, `emerge_response_1s`, `redundancy`, `ato`, `online_og_chk`, `offline_safety_chk`, `sec_num`, `alarm_num`, `insul_1st_lvup`, `high_insul_adt`, `double_insul`, `55k_install`, `sfra_test`, `rip_install`, `vacuum_set` | `updated_at` |

## EF1 계산 도메인 테이블 — `transformer_score_detail`

`score_snapshot`(공통)에 들어가는 `pof_minus/pof/cof_minus/cof/dof_minus/dof/total_score`를 제외한 나머지 CALCULATED_COLUMNS 전부:

`today`, `operation_year`, `age_minus`, `dga_tcg`, `dga_diag`, `dga_minus`, `load_minus`, `temp_minus`, `dielec_str_te_avg`, `dielec_str_te_diag`, `dielec_str_te_minus`, `acid_measure_desc`, `acid_measure_minus`, `moisture_desc`, `moisture_minus`, `furan_total`, `furan_total_per_year`, `furan_desc`, `furan_minus`, `part_discharge_minus`, `oltc_96T_minus`, `oltc_diag`, `oltc_minus`, `thermal_img_minus`, `noise_minus`, `1st_voltage`, `1st_voltage_minus`, `capa_times_load`, `productivity_minus`, `fire_minus`, `fire_spread_minus`, `emerge_response_minus`, `rep_cost`, `rep_cost_minus`, `rep_time`, `rep_time_minus`, `redundancy_minus`, `ato_minus`, `online_og_minus`, `offline_safety_minus`, `sec_minus`, `alarm_minus`, `winding_minus`, `prod_life_minus`, `connect_part_minus`, `temp_inc_limit_minus`, `test_reliability_minus`, `bushing_minus`, `oltc2_minus`

## 산출 파이프라인 요약

1. 경과연수: `today` → `operation_year` → `age_minus`
2. PoF 구성요소(DGA/부하·온도/절연내력/산가도/수분/Furan/부분방전·OLTC·열화상·소음) → `pof_minus` → `pof = 100 + pof_minus`
3. CoF 구성요소(1차전압/생산성/화재/비상대응/교체비용·기간) → `cof_minus` → `cof = 100 + cof_minus`
4. DoF 구성요소(예비화/자동전환/보호·알람/설계보강 항목들) → `dof_minus` → `dof = 100 + dof_minus`
5. `total_score = 0.5*pof + 0.3*cof + 0.2*dof`

## EF2(GIS) — Stage 8-3 구현(2026-10-16, 마이그레이션 `b3f7d2a8c615`)

출처: `ref_data/schema_eflms_gis.py`(2026-10-16 수정본). 시스템 계산기(`ef2_gis.py`)는 **원본 공식을 그대로** 옮겼다(아래 "원본 그대로 유지하는 판단" 참고) — `backend/tests/test_ef2_gis.py`가 같은 입력으로 원본과 전 계산 컬럼을 대조한다. 원본에 섞여 있는 `dtype: "string"`은 `str`로 통일했다. 예외: `cb_op_char_over` 미사용, `age_minus` 전기적 감점 합산, `cum_trip_current` 소수 허용(아래 "원본과 다르게 바꾼 것").

### 공통 테이블 매핑

| 원본 컬럼 | 들어가는 곳 |
|---|---|
| `factory_code`, `EF_code`, `voltage`, `operation_start_time` | `equipment` (공통) |
| `gis_name`(차단기명) | `equipment.equipment_name` |
| `pof_minus`, `pof`, `cof_minus`, `cof`, `dof_minus`, `dof`, `total_score` | `score_snapshot` (공통) |

### EF2 입력 도메인 테이블

| 테이블 | INPUT_COLUMNS 매핑 | 시점 컬럼 | 축 |
|---|---|---|---|
| `gis_operation` | `op_type`, `cb_op_num`, `rated_trip_count`, `cum_trip_current`, `load_percent`, `leakage_curr` | `measured_at` (신규 — 원본 mock엔 날짜 없음) | PoF 기계·전기 |
| `gis_diagnosis` | `part_dischar_pat`, `elec_room_max_temp` | `measured_at` (신규) | PoF 화학 |
| `gis_sf6_reading` | `sf6_so2`, `sf6_leak`, `sf6_h2o`, `sf6_purity` | `diag_time` (= `sf6_diag_time`) | PoF 화학 |
| `gis_consequence_attribute` | `in_vol`, `capa_times_load`, `fire_spread`, `env_loc`, `emerge_resp_pat`, `rep_cost`, `rep_time` | `updated_at` | CoF |
| `gis_design_attribute` | `in_line_num`, `ato`, `reliability`, `online_diag`, `offline_diag`, `tbm`, `conn_rev`, `leak_str`, `insul_str`, `vt_la_str` | `updated_at` | DoF |

화면의 "최근 진단일"은 EF2에서 `gis_sf6_reading.diag_time`을 쓴다(EF1은 `dga_reading.diag_time`).

### 입력 허용값 (임포트 검증 — 범위 밖이면 행 오류로 파일 전체 반영 안 함)

`ef2_gis.INPUT_COLUMNS`의 `choices`/`min`/`max`/`required`로 선언돼 있고, `app/services/import_service.py`의 `_check_allowed`가 검사한다(허용값을 선언하지 않은 EF1은 검사 대상 아님).

허용값은 mock 생성 범위가 아니라 **공식에 정의된 값 전체**다. mock 생성기는 원본 generator 범위(일부러 좁혀둔 범위)를 그대로 쓰되, 생성값도 이 검증을 통과해야 한다.

| 컬럼 | 라벨 | 허용값 |
|---|---|---|
| `voltage` | 전압 | `154000`, `345000` (누설전류 감점 기준이 이 두 전압만 정의돼 있어 제한) |
| `in_vol`, `env_loc`, `in_line_num` | 인입전압 / 환경_위치 / 인입선로 | `A`, `B`, `C` |
| `capa_times_load`, `emerge_resp_pat`, `rep_cost`, `rep_time` | 생산영향성 / 비상대응시간 / 사고복구비용 / 정상화기간 | `A`~`E` |
| `fire_spread`, `reliability` | 화재확산 / 공급신뢰도 | `A`, `B` |
| `online_diag` | 온라인진단 | `A`~`D` |
| `part_dischar_pat`, `ato`, `offline_diag`, `tbm`, `conn_rev`, `leak_str`, `insul_str`, `vt_la_str` | 부분방전 이상 패턴 / ATO 구성 / 오프라인진단 / TBM 실시 / 도체접속구조개선 / 가스기밀강화 / 절연스펙강화 / 부품신뢰성강화 | `Y`, `N` |
| `sf6_leak` | SF6 누기 | `있음`, `없음` |
| `cb_op_num`, `rated_trip_count`, `cum_trip_current`, `load_percent`, `leakage_curr`, `sf6_so2`, `sf6_h2o` | (수치) | 0 이상 (`cum_trip_current`는 소수 허용) |
| `sf6_purity` | SF6 순도 | 0~100 |
| `elec_room_max_temp` | 전기실 최대온도 | 정수(범위 제한 없음) |
| `factory_code`, `gis_name`, `op_type` | 사업장명 / 차단기명 / 조작방식 | 빈 값만 거부 |

### EF2 계산 도메인 테이블 — `gis_score_detail`

`score_snapshot`(공통)에 들어가는 7개를 제외한 나머지 CALCULATED_COLUMNS 전부:

`today`, `operation_year`, `age_minus`, `cb_op_num_minus`, `cb_op_year`, `cb_stat`, `cb_stat_minus`, `insul_year`, `insul_stat`, `insul_stat_minus`, `gis_mech_minus`, `rated_trip_count_minus`, `cum_trip_current_minus`, `load_minus`, `leakage_curr_minus`, `gis_elec_minus`, `part_dischar_minus`, `sf6_minus`, `elec_room_minus`, `gis_chem_minus`, `in_vol_minus`, `productivity_minus`, `fire_spread_minus`, `env_minus`, `emerge_resp_minus`, `rep_cost_minus`, `rep_time_minus`, `in_line_minus`, `ato_minus`, `reliability_minus`, `online_diag_minus`, `offline_diag_minus`, `tbm_minus`, `conn_rev_minus`, `leak_str_minus`, `insul_str_minus`, `vt_la_minus`

### EF2 산출 파이프라인 요약

1. 경과연수: `today` → `operation_year`(일수/365, 소수 1자리) → `age_minus`(전기적 감점에 합산, 원본은 미합산)
2. 노화(차단기·절연물 상태점수): `cb_stat = e^-((operation_year/72)^3.21)` → `cb_stat_minus = round((cb_stat-1)×100×1)`, `insul_stat = e^-((operation_year/4199)^0.75)` → `insul_stat_minus = round((insul_stat-1)×100×2)`
3. PoF = 100 + 기계적(`cb_op_num` + `cb_stat` + `insul_stat` 감점) + 전기적(정격차단횟수·누적차단전류·부하율·누설전류·경과연수) + 화학적(부분방전·SF6·전기실온도)
4. CoF = 100 + (인입전압·생산영향성·화재확산·환경_위치·비상대응·사고복구비용·정상화기간)
5. DoF = 100 + (인입선로·ATO·공급신뢰도·온라인/오프라인진단·TBM·도체접속·가스기밀·절연스펙·부품신뢰성)
6. `total_score = 0.5*pof + 0.3*cof + 0.2*dof` (EF1과 동일 가중치 — 전체 보기에서 유형 간 통합 정렬 가능, 2026-10-16 승인)

### 원본 그대로 유지하는 판단 (2026-10-16 확정)

| 항목 | 원본 동작 | 처리 |
|---|---|---|
| SF6 감점 | 수분 ≤150이면 순도(≤95/≤97)를 보지 않음 | 원본대로 |
| 누적차단전류 | 중간 구간 기준이 `> 101` | 원본대로 |
| 음수 점수 | 실데이터에선 PoF 약 -67(여기에 경과연수 감점만큼 더), DoF -33까지 이론상 가능(mock 범위에선 2026-10 기준 PoF 약 15~91, CoF 40~99, DoF 39~100 — 경과연수 때문에 해마다 1점씩 내려감) | 계산값은 원본대로 저장(엑셀과 일치), 차트 표시만 0~100으로 클램프. 상태 판정엔 영향 없음 |
| 상태 판정 | — | EF1과 같은 `classify_status` 기준 |

mock 범위에선 감점이 한 번도 발생하지 않는 분기가 8개 있다(`cb_op_num`, `leakage_curr`, `part_dischar`(2026-10-19부터 mock은 `N`만), `sf6`, `elec_room`, `in_line`, `ato`, `tbm`) — 이 분기들은 입력값을 직접 지정하는 정답값 단위테스트(`test_ef2_gis.py`의 `BRANCHES`)로 검증한다.

### 원본과 다르게 바꾼 것

| 날짜 | 항목 | 원본 | 시스템 |
|---|---|---|---|
| 2026-10-19 | `cb_op_char_over`(CB 동작특성 기준치 초과) — 사용자 결정으로 미사용 | 입력 Y면 `cb_op_char_over_minus = -9`, `gis_elec_minus`에 합산 | 입력 컬럼·감점 컬럼·DB 컬럼(마이그레이션 `c4e9a1d7b2f3`)·화면에서 제거. `gis_elec_minus`는 나머지 4항목 합. 결과는 원본에 `"N"`을 넣은 것과 같다(테스트가 그렇게 대조). 실제 파일에 이 컬럼이 있으면 `ef2_gis.IGNORED_COLUMNS`로 임포트가 건너뛴다(저장 안 함, 결과에 "사용 안 하는 컬럼"으로 표시) |
| 2026-10-19 | `age_minus`(경과연수) — 사용자 결정으로 전기적 감점에 합산 | 계산만 하고 어디에도 합산하지 않음 | `gis_elec_minus`에 더해 PoF·`total_score`에 반영(사용 1년당 -1). 노화는 차단기·절연물 고장확률 감점(기계적)에도 반영돼 함께 깎인다. 감점 사유 메타데이터에 "경과연수"(전기적) 추가. 테스트는 원본 결과에 `age_minus`를 더한 값과 대조 |
| 2026-10-19 | `cum_trip_current`(누적 차단 전류) — 실데이터에 소수값 | `dtype: "int"` | `float`(DB 컬럼 마이그레이션 `d7a2c5e8f1b4`). 감점 기준(25 이상·101 초과·500 초과)은 같다. mock 생성 범위는 그대로 |

## EF3(초고압케이블) — Stage 9 구현(2026-10-20, 마이그레이션 `90a898f21182`)

출처: `ref_data/schema_eflms_cable.py`(2026-10-20 수정본 — 첫 검토에서 찾은 실행 오류·로직 의심 9건을 원본 작성자가 고친 뒤 확정). 시스템 계산기(`ef3_cable.py`)는 **원본 공식을 그대로** 옮겼다 — `backend/tests/test_ef3_cable.py`가 같은 입력으로 원본과 전 계산 컬럼을 대조한다. 원본과 다른 점은 계산 기준일(`as_of`)을 받는 것과 입력 허용값뿐이다(EF1·EF2와 같음).

### 공통 테이블 매핑

| 원본 컬럼 | 들어가는 곳 |
|---|---|
| `factory_code`, `EF_code`, `voltage`, `operation_start_time` | `equipment` (공통) |
| `tl_name`(T/L명) | `equipment.equipment_name` |
| `pof_minus`, `pof`, `cof_minus`, `cof`, `dof_minus`, `dof`, `total_score` | `score_snapshot` (공통) |

### EF3 입력 도메인 테이블

| 테이블 | INPUT_COLUMNS 매핑 | 시점 컬럼 | 축 |
|---|---|---|---|
| `cable_spec` | `cable_sq`, `cable_per_phase`, `cable_mva`, `cable_length`, `laying_type`, `mid_joint`, `end_joint` | `updated_at` | 부하율 분모·CoF |
| `cable_condition` | `max_load`, `max_temp`, `diff_temp`, `failure_rate`, `pd_num`, `sys_cycle_curr`, `svl_leak_curr`, `joint_ex_damage`, `cable_move` | `measured_at` (신규 — 원본엔 날짜 없음) | PoF |
| `cable_consequence_attribute` | `emerge_resp`, `rep_time` | `updated_at` | CoF |
| `cable_design_attribute` | `reliability`, `temp_diag`, `pd_diag`, `live_line_diag`, `cable_move_diag`, `offline_diag`, `longlife_insul` | `updated_at` | DoF |

시점 컬럼은 모두 계산 기준일(`today`)이 들어간다. 원본에 진단일 입력이 없어서 화면의 "최근 진단일"은 EF3에서 `cable_condition.measured_at`(반영 기준일)을 쓴다. `cable_sq`·`cable_per_phase`·`voltage`는 계산에 쓰이지 않고 저장·표시만 한다.

### 입력 허용값 (임포트 검증)

원본은 모르는 문자열을 조용히 감점 0으로 처리하므로, 판정에 쓰이는 값만 받는다(오타가 0점으로 섞이지 않게).

| 컬럼 | 라벨 | 허용값 |
|---|---|---|
| `laying_type` | 포설방법 | `철탑`, `공동구`, `관로구`, `전력구` |
| `end_joint` | 종단접속함종류 | `WEBG`, `DEBG, EBA`(쉼표 포함 값 하나 — 탭 구분 파일이라 한 칸), `DEBG` |
| `emerge_resp` | 비상대응시간 | `24시간이하`, `12시간이하`, `1시간이하`, `1초내` |
| `rep_time` | 정상화기간_설비교체 | `3개월초과`, `3개월이하` |
| `offline_diag` | 오프라인진단여부 | `미실시`, `3년이내`, `1년이내` |
| `temp_diag`, `pd_diag`, `live_line_diag`, `cable_move_diag`, `longlife_insul` | 열화상·PD·활선진단 / 이동량 / 장수명절연물 | `O`, `X` |
| `joint_ex_damage` | 접속함외관손상여부 | `양호`, `이상` |
| `cable_mva` | 회선별용량 | 1 이상(부하율 분모) |
| `voltage`, `cable_sq`, `cable_per_phase`, `reliability` | 전압 / 굵기 / phase당케이블 / 공급신뢰도회선수 | 1 이상(전압은 계산에 안 쓰여 값 제한 없음, 2026-10-20 결정) |
| `max_load`, `diff_temp`, `failure_rate`, `pd_num`, `sys_cycle_curr`, `svl_leak_curr`, `cable_move`, `cable_length`, `mid_joint` | (수치) | 0 이상 |
| `max_temp` | 최고온도 | 실수(범위 제한 없음) |
| `factory_code`, `tl_name` | 사업장명 / T/L명 | 빈 값만 거부 |

### EF3 계산 도메인 테이블 — `cable_score_detail`

`score_snapshot`(공통)에 들어가는 7개를 제외한 나머지 CALCULATED_COLUMNS 전부(29개):

`today`, `operation_year`, `age_minus`, `load_percent`, `load_minus`, `temp_minus`, `diff_temp_minus`, `failure_rate_minus`, `pd_minus`, `sys_cycle_curr_minus`, `svl_leak_curr_minus`, `joint_ex_damage_minus`, `cable_move_minus`, `risk_mva`, `risk_mva_minus`, `laying_type_minus`, `mid_joint_minus`, `end_joint_minus`, `emerge_resp_minus`, `rep_cost`, `rep_cost_minus`, `rep_time_minus`, `reliability_minus`, `temp_diag_minus`, `pd_diag_minus`, `live_line_diag_minus`, `cable_move_diag_minus`, `offline_diag_minus`, `longlife_insul_minus`

### EF3 산출 파이프라인 요약

1. 경과연수: `today` → `operation_year` → `age_minus`(사용 1년당 -1, **PoF에 합산** — EF1과 같고 GIS 원본과 다름)
2. 부하율: `load_percent = max_load / cable_mva × 100`
3. PoF = 100 + 경과연수·부하율·최고온도·상간온도차(라벨 "열화상")·온도기반손상률(`round(손상률 × −1000)`)·부분방전횟수·시스순환전류·SVL누설전류·접속함외관·케이블이동량. 원본에 GIS 같은 그룹 구분은 없다
4. CoF = 100 + 사고영향성(`round(cable_mva × −0.01)`)·포설방법·중간접속함(−개수)·종단접속함·비상대응시간·사고복구비용(`rep_cost = cable_length × 0.0135` 구간 판정, 최소 -2)·정상화기간
5. DoF = 100 + 공급신뢰도(3·4회선 0, 그 외 -20)·열화상/PD/활선진단·케이블이동량여부·오프라인진단·장수명절연물
6. `total_score = 0.5*pof + 0.3*cof + 0.2*dof` (EF1·EF2와 동일)

### 원본 그대로 유지하는 판단 (2026-10-20 확정)

| 항목 | 원본 동작 | 처리 |
|---|---|---|
| 사고복구비용 | 가장 낮은 구간도 -2 — 감점 0인 케이블이 없음 | 원본대로 |
| 공급신뢰도 | 1회선도 2회선과 같은 -20 | 원본대로 |
| 사고영향성 | 회선별용량에 비례(414 → -4, 984 → -10) | 원본대로 |
| 음수 점수 | 실데이터에선 이론상 가능(PoF 최악 -55 + 경과연수). mock 범위에선 PoF 32~87, CoF 18~91, DoF 50~70(5,000건 기준) | 계산값 그대로 저장, 차트만 0~100 클램프 |
| 상태 판정 | — | EF1과 같은 `classify_status` 기준 |

mock 범위에선 감점이 한 번도 발생하지 않는 항목이 10개 있다(부하율, 최고온도, 상간온도차, 시스순환전류, SVL누설전류, 비상대응시간, 정상화기간, 열화상·PD·오프라인 진단). mock DoF는 활선진단·이동량진단·장수명절연물이 항상 X라 최대 70이다. 이 분기들은 정답값 단위테스트(`test_ef3_cable.py`의 `BRANCHES`)로 검증한다.

### 화면 라벨

감점 항목 라벨은 원본 계산 라벨에서 "감점"만 뗀다(`diff_temp_minus` → "열화상", `sys_cycle_curr_minus` → "시스템순환전류" 등). 예외: `age_minus`는 원본 라벨 "경과일"이 실제로는 연수라 EF1·EF2와 같은 "경과연수"로 쓴다(2026-10-20 사용자 결정).

## 미확정/자동 캡처 컬럼

사내 입력파일에 위 목록에 없는 헤더가 오면 `equipment_extra_attribute`(equipment_id, column_name, value, inferred_type, source_file, imported_at)에 자동 보관된다 — 정식 컬럼으로 승격하려면 이 문서와 위 테이블 정의를 함께 갱신하는 마이그레이션이 필요하다.
