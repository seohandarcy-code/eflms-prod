# 데이터 사전 (EF1 · 변압기)

출처: `ref_data/schema_eflms.py` (INPUT_COLUMNS / CALCULATED_COLUMNS). 컬럼 상세는 원본 파일의 `label`/`dtype`을 그대로 따른다. 아래는 각 컬럼이 어느 도메인 테이블로 들어가는지의 매핑이다.

## 공통 테이블

| 테이블 | 컬럼 |
|---|---|
| `equipment_type` | `ef_code`(PK), `name`, `description` |
| `equipment` | `equipment_id`(PK), `factory_code`, `ef_code`(FK), `transformer_name`, `voltage`, `onan_val`, `onaf_val`, `operation_start_time` — `UNIQUE(factory_code, ef_code, transformer_name)` |
| `score_snapshot` | `equipment_id`(FK), `pof_minus`, `pof`, `cof_minus`, `cof`, `dof_minus`, `dof`, `total_score`, `computed_at` |

## EF1 입력 도메인 테이블

| 테이블 | INPUT_COLUMNS 매핑 | 시점 컬럼 |
|---|---|---|
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
5. `total_score = 0.5*pof_minus + 0.3*cof_minus + 0.2*dof_minus`

## 미확정/자동 캡처 컬럼

사내 입력파일에 위 목록에 없는 헤더가 오면 `equipment_extra_attribute`(equipment_id, column_name, value, inferred_type, source_file, imported_at)에 자동 보관된다 — 정식 컬럼으로 승격하려면 이 문서와 위 테이블 정의를 함께 갱신하는 마이그레이션이 필요하다.
