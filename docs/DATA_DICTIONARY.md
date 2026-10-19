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

출처: `ref_data/schema_eflms_gis.py`(2026-10-16 수정본). 시스템 계산기(`ef2_gis.py`)는 **원본 공식을 그대로** 옮겼다(아래 "원본 그대로 유지하는 판단" 참고) — `backend/tests/test_ef2_gis.py`가 같은 입력으로 원본과 전 계산 컬럼을 대조한다. 원본에 섞여 있는 `dtype: "string"`은 `str`로 통일했다. 예외: `cb_op_char_over`는 미사용으로 뺐다(아래 "원본과 다르게 바꾼 것").

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
| `cb_op_num`, `rated_trip_count`, `cum_trip_current`, `load_percent`, `leakage_curr`, `sf6_so2`, `sf6_h2o` | (수치) | 0 이상 |
| `sf6_purity` | SF6 순도 | 0~100 |
| `elec_room_max_temp` | 전기실 최대온도 | 정수(범위 제한 없음) |
| `factory_code`, `gis_name`, `op_type` | 사업장명 / 차단기명 / 조작방식 | 빈 값만 거부 |

### EF2 계산 도메인 테이블 — `gis_score_detail`

`score_snapshot`(공통)에 들어가는 7개를 제외한 나머지 CALCULATED_COLUMNS 전부:

`today`, `operation_year`, `age_minus`, `cb_op_num_minus`, `cb_op_year`, `cb_stat`, `cb_stat_minus`, `insul_year`, `insul_stat`, `insul_stat_minus`, `gis_mech_minus`, `rated_trip_count_minus`, `cum_trip_current_minus`, `load_minus`, `leakage_curr_minus`, `gis_elec_minus`, `part_dischar_minus`, `sf6_minus`, `elec_room_minus`, `gis_chem_minus`, `in_vol_minus`, `productivity_minus`, `fire_spread_minus`, `env_minus`, `emerge_resp_minus`, `rep_cost_minus`, `rep_time_minus`, `in_line_minus`, `ato_minus`, `reliability_minus`, `online_diag_minus`, `offline_diag_minus`, `tbm_minus`, `conn_rev_minus`, `leak_str_minus`, `insul_str_minus`, `vt_la_minus`

### EF2 산출 파이프라인 요약

1. 경과연수: `today` → `operation_year`(일수/365, 소수 1자리) → `age_minus`(표시용, PoF 합산엔 미포함)
2. 와이블 노화: `cb_stat = e^-((operation_year/72)^3.21)` → `cb_stat_minus = round((cb_stat-1)×100×1)`, `insul_stat = e^-((operation_year/4199)^0.75)` → `insul_stat_minus = round((insul_stat-1)×100×2)`
3. PoF = 100 + 기계적(`cb_op_num` + `cb_stat` + `insul_stat` 감점) + 전기적(정격차단횟수·누적차단전류·부하율·누설전류) + 화학적(부분방전·SF6·전기실온도)
4. CoF = 100 + (인입전압·생산영향성·화재확산·환경_위치·비상대응·사고복구비용·정상화기간)
5. DoF = 100 + (인입선로·ATO·공급신뢰도·온라인/오프라인진단·TBM·도체접속·가스기밀·절연스펙·부품신뢰성)
6. `total_score = 0.5*pof + 0.3*cof + 0.2*dof` (EF1과 동일 가중치 — 전체 보기에서 유형 간 통합 정렬 가능, 2026-10-16 승인)

### 원본 그대로 유지하는 판단 (2026-10-16 확정)

| 항목 | 원본 동작 | 처리 |
|---|---|---|
| SF6 감점 | 수분 ≤150이면 순도(≤95/≤97)를 보지 않음 | 원본대로 |
| 누적차단전류 | 중간 구간 기준이 `> 101` | 원본대로 |
| `age_minus` | 계산하지만 PoF 합산에 미포함(EF1은 포함) — 노화는 와이블 감점이 담당 | 원본대로, 상세 화면엔 표시 |
| 음수 점수 | 실데이터에선 PoF 약 -67, DoF -33까지 이론상 가능(mock 범위에선 PoF 18~98, CoF 40~99, DoF 39~100) | 계산값은 원본대로 저장(엑셀과 일치), 차트 표시만 0~100으로 클램프. 상태 판정엔 영향 없음 |
| 상태 판정 | — | EF1과 같은 `classify_status` 기준 |

mock 범위에선 감점이 한 번도 발생하지 않는 분기가 7개 있다(`cb_op_num`, `leakage_curr`, `sf6`, `elec_room`, `in_line`, `ato`, `tbm`) — 이 분기들은 입력값을 직접 지정하는 정답값 단위테스트(`test_ef2_gis.py`의 `BRANCHES`)로 검증한다.

### 원본과 다르게 바꾼 것

| 날짜 | 항목 | 원본 | 시스템 |
|---|---|---|---|
| 2026-10-19 | `cb_op_char_over`(CB 동작특성 기준치 초과) — 사용자 결정으로 미사용 | 입력 Y면 `cb_op_char_over_minus = -9`, `gis_elec_minus`에 합산 | 입력 컬럼·감점 컬럼·DB 컬럼(마이그레이션 `c4e9a1d7b2f3`)·화면에서 제거. `gis_elec_minus`는 나머지 4항목 합. 결과는 원본에 `"N"`을 넣은 것과 같다(테스트가 그렇게 대조). 실제 파일에 이 컬럼이 있으면 `ef2_gis.IGNORED_COLUMNS`로 임포트가 건너뛴다(저장 안 함, 결과에 "사용 안 하는 컬럼"으로 표시) |

## 미확정/자동 캡처 컬럼

사내 입력파일에 위 목록에 없는 헤더가 오면 `equipment_extra_attribute`(equipment_id, column_name, value, inferred_type, source_file, imported_at)에 자동 보관된다 — 정식 컬럼으로 승격하려면 이 문서와 위 테이블 정의를 함께 갱신하는 마이그레이션이 필요하다.
