<script setup lang="ts">
// EF1(변압기) 상세 본문 — Stage 8-5에 EquipmentDetailPanel.vue에서 그대로 옮겼다(내용 무변경).
// part="compact": 패널 왼쪽 요약 4줄 / part="raw": "원본 데이터 전체 보기" 펼침 영역.
// 스타일은 부모 패널이 :deep()으로 입힌다(compact-row, raw-* 클래스).
import type { Ef1TypeDetail } from "../../types/equipment";

defineProps<{ typeDetail: Ef1TypeDetail; part: "compact" | "raw" }>();
</script>

<template>
  <template v-if="part === 'compact'">
            <div class="compact-row">
              <span class="compact-label">DGA(유중가스)</span>
              <span class="compact-value mono">{{ typeDetail.score_detail.dga_tcg }}ppm · {{ typeDetail.score_detail.dga_diag }}</span>
            </div>
            <div class="compact-row">
              <span class="compact-label">부하·온도</span>
              <span class="compact-value mono">{{ typeDetail.load.load_percent }}% · {{ typeDetail.load.coil_max_temp }}℃</span>
            </div>
            <div class="compact-row">
              <span class="compact-label">절연·유중시험</span>
              <span class="compact-value mono">{{ typeDetail.score_detail.dielec_str_te_avg.toFixed(1) }}kV · {{ typeDetail.score_detail.acid_measure_desc }}</span>
            </div>
            <div class="compact-row">
              <span class="compact-label">설계속성</span>
              <span class="compact-value mono">예비화 {{ typeDetail.design.redundancy }} · 자동전환 {{ typeDetail.design.ato }}</span>
            </div>
  </template>
  <template v-else>
          <div class="raw-group">
            <div class="raw-title">POF 구성</div>
            <div class="raw-subgrid">
              <div class="raw-subgroup">
                <div class="raw-subtitle">경과연수</div>
                <div class="raw-fields">
                  <div class="raw-field"><span>가동연수</span><b>{{ typeDetail.score_detail.operation_year }}년</b></div>
                  <div class="raw-field"><span>경과연수 감점</span><b class="neg">{{ typeDetail.score_detail.age_minus }}</b></div>
                </div>
              </div>

              <div class="raw-subgroup">
                <div class="raw-subtitle">DGA (유중가스)</div>
                <div class="raw-fields">
                  <div class="raw-field"><span>진단일</span><b>{{ typeDetail.dga.diag_time }}</b></div>
                  <div class="raw-field"><span>H2</span><b>{{ typeDetail.dga.dga_h2 }}</b></div>
                  <div class="raw-field"><span>C2H2</span><b>{{ typeDetail.dga.dga_c2h2 }}</b></div>
                  <div class="raw-field"><span>C2H4</span><b>{{ typeDetail.dga.dga_c2h4 }}</b></div>
                  <div class="raw-field"><span>C2H6</span><b>{{ typeDetail.dga.dga_c2h6 }}</b></div>
                  <div class="raw-field"><span>CH4</span><b>{{ typeDetail.dga.dga_ch4 }}</b></div>
                  <div class="raw-field"><span>C3H8</span><b>{{ typeDetail.dga.dga_c3h8 }}</b></div>
                  <div class="raw-field"><span>CO</span><b>{{ typeDetail.dga.dga_co }}</b></div>
                  <div class="raw-field"><span>CO2</span><b>{{ typeDetail.dga.dga_co2 }}</b></div>
                  <div class="raw-field"><span>O2</span><b>{{ typeDetail.dga.dga_o2 }}</b></div>
                  <div class="raw-field"><span>N2</span><b>{{ typeDetail.dga.dga_n2 }}</b></div>
                  <div class="raw-field"><span>변동</span><b>{{ typeDetail.dga.dga_fluc }}</b></div>
                  <div class="raw-field"><span>TCG</span><b>{{ typeDetail.score_detail.dga_tcg }}</b></div>
                  <div class="raw-field"><span>판정</span><b>{{ typeDetail.score_detail.dga_diag }}</b></div>
                  <div class="raw-field"><span>감점</span><b class="neg">{{ typeDetail.score_detail.dga_minus }}</b></div>
                </div>
              </div>

              <div class="raw-subgroup">
                <div class="raw-subtitle">Furan</div>
                <div class="raw-fields">
                  <div class="raw-field"><span>진단일</span><b>{{ typeDetail.furan.diag_time }}</b></div>
                  <div class="raw-field"><span>5H2F</span><b>{{ typeDetail.furan.furan_5h2f }}</b></div>
                  <div class="raw-field"><span>2FOL</span><b>{{ typeDetail.furan.furan_2fol }}</b></div>
                  <div class="raw-field"><span>2FAL</span><b>{{ typeDetail.furan.furan_2fal }}</b></div>
                  <div class="raw-field"><span>2ACF</span><b>{{ typeDetail.furan.furan_2acf }}</b></div>
                  <div class="raw-field"><span>5M2F</span><b>{{ typeDetail.furan.furan_5m2f }}</b></div>
                  <div class="raw-field"><span>합계</span><b>{{ typeDetail.score_detail.furan_total }}</b></div>
                  <div class="raw-field"><span>연간환산</span><b>{{ typeDetail.score_detail.furan_total_per_year.toFixed(2) }}</b></div>
                  <div class="raw-field"><span>판정</span><b>{{ typeDetail.score_detail.furan_desc }}</b></div>
                  <div class="raw-field"><span>감점</span><b class="neg">{{ typeDetail.score_detail.furan_minus }}</b></div>
                </div>
              </div>

              <div class="raw-subgroup">
                <div class="raw-subtitle">절연내력시험</div>
                <div class="raw-fields">
                  <div class="raw-field"><span>1차</span><b>{{ typeDetail.dielectric.dielec_str_te_1 }}</b></div>
                  <div class="raw-field"><span>2차</span><b>{{ typeDetail.dielectric.dielec_str_te_2 }}</b></div>
                  <div class="raw-field"><span>3차</span><b>{{ typeDetail.dielectric.dielec_str_te_3 }}</b></div>
                  <div class="raw-field"><span>4차</span><b>{{ typeDetail.dielectric.dielec_str_te_4 }}</b></div>
                  <div class="raw-field"><span>5차</span><b>{{ typeDetail.dielectric.dielec_str_te_5 }}</b></div>
                  <div class="raw-field"><span>6차</span><b>{{ typeDetail.dielectric.dielec_str_te_6 }}</b></div>
                  <div class="raw-field"><span>평균</span><b>{{ typeDetail.score_detail.dielec_str_te_avg.toFixed(1) }}</b></div>
                  <div class="raw-field"><span>판정</span><b>{{ typeDetail.score_detail.dielec_str_te_diag }}</b></div>
                  <div class="raw-field"><span>감점</span><b class="neg">{{ typeDetail.score_detail.dielec_str_te_minus }}</b></div>
                </div>
              </div>

              <div class="raw-subgroup">
                <div class="raw-subtitle">유중시험</div>
                <div class="raw-fields">
                  <div class="raw-field"><span>산가도</span><b>{{ typeDetail.oil.acid_measure_val }}</b></div>
                  <div class="raw-field"><span>산가도 판정</span><b>{{ typeDetail.score_detail.acid_measure_desc }}</b></div>
                  <div class="raw-field"><span>산가도 감점</span><b class="neg">{{ typeDetail.score_detail.acid_measure_minus }}</b></div>
                  <div class="raw-field"><span>수분</span><b>{{ typeDetail.oil.moisture_rslt }}</b></div>
                  <div class="raw-field"><span>수분 판정</span><b>{{ typeDetail.score_detail.moisture_desc }}</b></div>
                  <div class="raw-field"><span>수분 감점</span><b class="neg">{{ typeDetail.score_detail.moisture_minus }}</b></div>
                </div>
              </div>

              <div class="raw-subgroup">
                <div class="raw-subtitle">부하상태</div>
                <div class="raw-fields">
                  <div class="raw-field"><span>측정일</span><b>{{ typeDetail.load.measured_at }}</b></div>
                  <div class="raw-field"><span>부하율</span><b>{{ typeDetail.load.load_percent }}%</b></div>
                  <div class="raw-field"><span>권선최고온도</span><b>{{ typeDetail.load.coil_max_temp }}℃</b></div>
                  <div class="raw-field"><span>부하 감점</span><b class="neg">{{ typeDetail.score_detail.load_minus }}</b></div>
                  <div class="raw-field"><span>온도 감점</span><b class="neg">{{ typeDetail.score_detail.temp_minus }}</b></div>
                </div>
              </div>

              <div class="raw-subgroup">
                <div class="raw-subtitle">점검진단</div>
                <div class="raw-fields">
                  <div class="raw-field"><span>측정일</span><b>{{ typeDetail.inspection.measured_at }}</b></div>
                  <div class="raw-field"><span>부분방전</span><b>{{ typeDetail.inspection.part_discharge_diag }}</b></div>
                  <div class="raw-field"><span>부분방전 감점</span><b class="neg">{{ typeDetail.score_detail.part_discharge_minus }}</b></div>
                  <div class="raw-field"><span>96T진단</span><b>{{ typeDetail.inspection.oltc_96t_diag }}</b></div>
                  <div class="raw-field"><span>96T 감점</span><b class="neg">{{ typeDetail.score_detail.oltc_96t_minus }}</b></div>
                  <div class="raw-field"><span>탭절환횟수</span><b>{{ typeDetail.inspection.oltc_rslt }}</b></div>
                  <div class="raw-field"><span>탭절환타입</span><b>{{ typeDetail.inspection.oltc_type }}</b></div>
                  <div class="raw-field"><span>OLTC진단</span><b>{{ typeDetail.score_detail.oltc_diag }}</b></div>
                  <div class="raw-field"><span>OLTC 감점</span><b class="neg">{{ typeDetail.score_detail.oltc_minus }}</b></div>
                  <div class="raw-field"><span>열화상</span><b>{{ typeDetail.inspection.thermal_img_temp }}</b></div>
                  <div class="raw-field"><span>열화상 감점</span><b class="neg">{{ typeDetail.score_detail.thermal_img_minus }}</b></div>
                  <div class="raw-field"><span>이상소음</span><b>{{ typeDetail.inspection.noise_diag }}</b></div>
                  <div class="raw-field"><span>소음 감점</span><b class="neg">{{ typeDetail.score_detail.noise_minus }}</b></div>
                </div>
              </div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">COF 구성</div>
            <div class="raw-fields">
              <div class="raw-field"><span>1차전압</span><b>{{ typeDetail.score_detail.first_voltage.toLocaleString() }}</b></div>
              <div class="raw-field"><span>1차전압 감점</span><b class="neg">{{ typeDetail.score_detail.first_voltage_minus }}</b></div>
              <div class="raw-field"><span>용량×부하율</span><b>{{ typeDetail.score_detail.capa_times_load.toFixed(1) }}</b></div>
              <div class="raw-field"><span>생산성 감점</span><b class="neg">{{ typeDetail.score_detail.productivity_minus }}</b></div>
              <div class="raw-field"><span>화재취약성</span><b>{{ typeDetail.design.fire_vul_type }}</b></div>
              <div class="raw-field"><span>화재취약성 감점</span><b class="neg">{{ typeDetail.score_detail.fire_minus }}</b></div>
              <div class="raw-field"><span>화재확산장소</span><b>{{ typeDetail.design.fire_spread_loc }}</b></div>
              <div class="raw-field"><span>화재확산 감점</span><b class="neg">{{ typeDetail.score_detail.fire_spread_minus }}</b></div>
              <div class="raw-field"><span>비상대응</span><b>{{ typeDetail.design.emerge_response_1s }}</b></div>
              <div class="raw-field"><span>비상대응 감점</span><b class="neg">{{ typeDetail.score_detail.emerge_response_minus }}</b></div>
              <div class="raw-field"><span>교체비용</span><b>{{ typeDetail.score_detail.rep_cost }}</b></div>
              <div class="raw-field"><span>교체비용 감점</span><b class="neg">{{ typeDetail.score_detail.rep_cost_minus }}</b></div>
              <div class="raw-field"><span>교체기간</span><b>{{ typeDetail.score_detail.rep_time }}</b></div>
              <div class="raw-field"><span>교체기간 감점</span><b class="neg">{{ typeDetail.score_detail.rep_time_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">DOF 구성</div>
            <div class="raw-fields">
              <div class="raw-field"><span>예비화</span><b>{{ typeDetail.design.redundancy }}</b></div>
              <div class="raw-field"><span>예비화 감점</span><b class="neg">{{ typeDetail.score_detail.redundancy_minus }}</b></div>
              <div class="raw-field"><span>계통자동전환</span><b>{{ typeDetail.design.ato }}</b></div>
              <div class="raw-field"><span>자동전환 감점</span><b class="neg">{{ typeDetail.score_detail.ato_minus }}</b></div>
              <div class="raw-field"><span>온라인 유중가스</span><b>{{ typeDetail.design.online_og_chk }}</b></div>
              <div class="raw-field"><span>유중가스 감점</span><b class="neg">{{ typeDetail.score_detail.online_og_minus }}</b></div>
              <div class="raw-field"><span>안전공사 정밀점검</span><b>{{ typeDetail.design.offline_safety_chk }}</b></div>
              <div class="raw-field"><span>정밀점검 감점</span><b class="neg">{{ typeDetail.score_detail.offline_safety_minus }}</b></div>
              <div class="raw-field"><span>보호요소수</span><b>{{ typeDetail.design.sec_num }}</b></div>
              <div class="raw-field"><span>보호요소 감점</span><b class="neg">{{ typeDetail.score_detail.sec_minus }}</b></div>
              <div class="raw-field"><span>알람요소수</span><b>{{ typeDetail.design.alarm_num }}</b></div>
              <div class="raw-field"><span>알람요소 감점</span><b class="neg">{{ typeDetail.score_detail.alarm_minus }}</b></div>
              <div class="raw-field"><span>절연1단계상승</span><b>{{ typeDetail.design.insul_1st_lvup }}</b></div>
              <div class="raw-field"><span>권선 감점</span><b class="neg">{{ typeDetail.score_detail.winding_minus }}</b></div>
              <div class="raw-field"><span>고밀도절연지</span><b>{{ typeDetail.design.high_insul_adt }}</b></div>
              <div class="raw-field"><span>수명향상 감점</span><b class="neg">{{ typeDetail.score_detail.prod_life_minus }}</b></div>
              <div class="raw-field"><span>이중절연</span><b>{{ typeDetail.design.double_insul }}</b></div>
              <div class="raw-field"><span>접속부 감점</span><b class="neg">{{ typeDetail.score_detail.connect_part_minus }}</b></div>
              <div class="raw-field"><span>온도상승한도</span><b>{{ typeDetail.design.install_55k }}</b></div>
              <div class="raw-field"><span>온도한도 감점</span><b class="neg">{{ typeDetail.score_detail.temp_inc_limit_minus }}</b></div>
              <div class="raw-field"><span>SFRA시험</span><b>{{ typeDetail.design.sfra_test }}</b></div>
              <div class="raw-field"><span>SFRA 감점</span><b class="neg">{{ typeDetail.score_detail.test_reliability_minus }}</b></div>
              <div class="raw-field"><span>부싱</span><b>{{ typeDetail.design.rip_install }}</b></div>
              <div class="raw-field"><span>부싱 감점</span><b class="neg">{{ typeDetail.score_detail.bushing_minus }}</b></div>
              <div class="raw-field"><span>OLTC(진공식)</span><b>{{ typeDetail.design.vacuum_set }}</b></div>
              <div class="raw-field"><span>OLTC 감점</span><b class="neg">{{ typeDetail.score_detail.oltc2_minus }}</b></div>
            </div>
          </div>
  </template>
</template>
