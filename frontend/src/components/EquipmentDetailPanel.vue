<script setup lang="ts">
import { ref, watch } from "vue";
import { useEquipmentStore } from "../stores/equipment";
import type { EquipmentDetail } from "../types/equipment";

const props = defineProps<{ equipmentId: number }>();

const store = useEquipmentStore();
const detail = ref<EquipmentDetail | null>(store.detailCache[props.equipmentId] ?? null);
const loading = ref(false);
const showRaw = ref(false);

watch(
  () => props.equipmentId,
  async (id) => {
    detail.value = store.detailCache[id] ?? null;
    if (detail.value) return;
    loading.value = true;
    try {
      const fetched = await store.loadDetail(id);
      // 응답이 도착했을 때 사용자가 이미 다른 설비를 선택했다면(더 빠른 최신 요청이 이미 반영된
      // 상태라면) 뒤늦게 도착한 이 응답으로 화면을 덮어쓰지 않는다.
      if (props.equipmentId === id) {
        detail.value = fetched;
      }
    } finally {
      if (props.equipmentId === id) {
        loading.value = false;
      }
    }
  },
  { immediate: true },
);

function clampWidth(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function formatMonth(isoDate: string): string {
  return isoDate.slice(0, 7);
}
</script>

<template>
  <div class="panel">
    <div v-if="loading || !detail" class="loading">불러오는 중...</div>
    <template v-else>
      <div class="eyebrow">선택된 설비</div>
      <div class="panel-head">
        <div class="name-row">
          <span class="name">{{ detail.transformer_name }}</span>
          <span class="chip" :style="{ background: detail.needs_inspection ? '#FBE7E4' : '#E4F3EA', color: detail.needs_inspection ? '#C4392B' : '#1B8A5A' }">
            {{ detail.needs_inspection ? "점검필요" : "정상" }}
          </span>
        </div>
        <div class="meta">
          {{ detail.factory_code }} · {{ detail.voltage.toLocaleString() }}V · ONAN {{ detail.onan_val }}MVA · 가동 {{ formatMonth(detail.operation_start_time) }}
        </div>
      </div>

      <div class="body">
        <div class="score-bars">
          <span>PoF</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.pof) + '%', background: detail.score.pof < 20 ? '#C4392B' : '#3E8E8E' }" /></div>
          <span class="bar-value mono">{{ detail.score.pof }}</span>
          <span>CoF</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.cof) + '%', background: detail.score.cof < 30 ? '#C4392B' : '#3E8E8E' }" /></div>
          <span class="bar-value mono">{{ detail.score.cof }}</span>
          <span>DoF</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.dof) + '%', background: detail.score.dof < 20 ? '#C4392B' : '#3E8E8E' }" /></div>
          <span class="bar-value mono">{{ detail.score.dof }}</span>
        </div>

        <div class="detail-grid">
          <div class="detail-col">
            <div class="detail-title">DGA (유중가스)</div>
            <div class="mono">TCG {{ detail.score_detail.dga_tcg }}ppm</div>
            <div class="muted">판정: {{ detail.score_detail.dga_diag }}</div>
          </div>
          <div class="detail-col">
            <div class="detail-title">부하 · 온도</div>
            <div class="mono">부하율 {{ detail.load.load_percent }}%</div>
            <div class="muted">권선 최고온도 {{ detail.load.coil_max_temp }}℃</div>
          </div>
          <div class="detail-col">
            <div class="detail-title">절연 · 유중시험</div>
            <div class="mono">절연내력 평균 {{ detail.score_detail.dielec_str_te_avg.toFixed(1) }}kV</div>
            <div class="muted">산가도 {{ detail.score_detail.acid_measure_desc }}</div>
          </div>
          <div class="detail-col">
            <div class="detail-title">설계속성</div>
            <div class="muted">예비화 {{ detail.design.redundancy }} · 계통자동전환 {{ detail.design.ato }}</div>
            <div class="muted">온라인 유중가스 {{ detail.design.online_og_chk }} · 안전공사 정밀점검 {{ detail.design.offline_safety_chk }}</div>
          </div>
        </div>

        <button type="button" class="raw-toggle" @click="showRaw = !showRaw">
          {{ showRaw ? "원본 데이터 접기" : "원본 데이터 전체 보기" }}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :style="{ transform: showRaw ? 'rotate(180deg)' : 'none' }">
            <path d="M6 9 L12 15 L18 9" />
          </svg>
        </button>

        <div v-if="showRaw" class="raw-groups">
          <div class="raw-group">
            <div class="raw-title">DGA (유중가스)</div>
            <div class="raw-fields">
              <div class="raw-field"><span>진단일</span><b>{{ detail.dga.diag_time }}</b></div>
              <div class="raw-field"><span>H2</span><b>{{ detail.dga.dga_h2 }}</b></div>
              <div class="raw-field"><span>C2H2</span><b>{{ detail.dga.dga_c2h2 }}</b></div>
              <div class="raw-field"><span>C2H4</span><b>{{ detail.dga.dga_c2h4 }}</b></div>
              <div class="raw-field"><span>C2H6</span><b>{{ detail.dga.dga_c2h6 }}</b></div>
              <div class="raw-field"><span>CH4</span><b>{{ detail.dga.dga_ch4 }}</b></div>
              <div class="raw-field"><span>C3H8</span><b>{{ detail.dga.dga_c3h8 }}</b></div>
              <div class="raw-field"><span>CO</span><b>{{ detail.dga.dga_co }}</b></div>
              <div class="raw-field"><span>CO2</span><b>{{ detail.dga.dga_co2 }}</b></div>
              <div class="raw-field"><span>O2</span><b>{{ detail.dga.dga_o2 }}</b></div>
              <div class="raw-field"><span>N2</span><b>{{ detail.dga.dga_n2 }}</b></div>
              <div class="raw-field"><span>변동</span><b>{{ detail.dga.dga_fluc }}</b></div>
              <div class="raw-field"><span>TCG</span><b>{{ detail.score_detail.dga_tcg }}</b></div>
              <div class="raw-field"><span>판정</span><b>{{ detail.score_detail.dga_diag }}</b></div>
              <div class="raw-field"><span>감점</span><b class="neg">{{ detail.score_detail.dga_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">Furan</div>
            <div class="raw-fields">
              <div class="raw-field"><span>진단일</span><b>{{ detail.furan.diag_time }}</b></div>
              <div class="raw-field"><span>5H2F</span><b>{{ detail.furan.furan_5h2f }}</b></div>
              <div class="raw-field"><span>2FOL</span><b>{{ detail.furan.furan_2fol }}</b></div>
              <div class="raw-field"><span>2FAL</span><b>{{ detail.furan.furan_2fal }}</b></div>
              <div class="raw-field"><span>2ACF</span><b>{{ detail.furan.furan_2acf }}</b></div>
              <div class="raw-field"><span>5M2F</span><b>{{ detail.furan.furan_5m2f }}</b></div>
              <div class="raw-field"><span>합계</span><b>{{ detail.score_detail.furan_total }}</b></div>
              <div class="raw-field"><span>연간환산</span><b>{{ detail.score_detail.furan_total_per_year.toFixed(2) }}</b></div>
              <div class="raw-field"><span>판정</span><b>{{ detail.score_detail.furan_desc }}</b></div>
              <div class="raw-field"><span>감점</span><b class="neg">{{ detail.score_detail.furan_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">절연내력시험</div>
            <div class="raw-fields">
              <div class="raw-field"><span>1차</span><b>{{ detail.dielectric.dielec_str_te_1 }}</b></div>
              <div class="raw-field"><span>2차</span><b>{{ detail.dielectric.dielec_str_te_2 }}</b></div>
              <div class="raw-field"><span>3차</span><b>{{ detail.dielectric.dielec_str_te_3 }}</b></div>
              <div class="raw-field"><span>4차</span><b>{{ detail.dielectric.dielec_str_te_4 }}</b></div>
              <div class="raw-field"><span>5차</span><b>{{ detail.dielectric.dielec_str_te_5 }}</b></div>
              <div class="raw-field"><span>6차</span><b>{{ detail.dielectric.dielec_str_te_6 }}</b></div>
              <div class="raw-field"><span>평균</span><b>{{ detail.score_detail.dielec_str_te_avg.toFixed(1) }}</b></div>
              <div class="raw-field"><span>판정</span><b>{{ detail.score_detail.dielec_str_te_diag }}</b></div>
              <div class="raw-field"><span>감점</span><b class="neg">{{ detail.score_detail.dielec_str_te_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">유중시험</div>
            <div class="raw-fields">
              <div class="raw-field"><span>산가도</span><b>{{ detail.oil.acid_measure_val }}</b></div>
              <div class="raw-field"><span>산가도 판정</span><b>{{ detail.score_detail.acid_measure_desc }}</b></div>
              <div class="raw-field"><span>산가도 감점</span><b class="neg">{{ detail.score_detail.acid_measure_minus }}</b></div>
              <div class="raw-field"><span>수분</span><b>{{ detail.oil.moisture_rslt }}</b></div>
              <div class="raw-field"><span>수분 판정</span><b>{{ detail.score_detail.moisture_desc }}</b></div>
              <div class="raw-field"><span>수분 감점</span><b class="neg">{{ detail.score_detail.moisture_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">부하상태</div>
            <div class="raw-fields">
              <div class="raw-field"><span>측정일</span><b>{{ detail.load.measured_at }}</b></div>
              <div class="raw-field"><span>부하율</span><b>{{ detail.load.load_percent }}%</b></div>
              <div class="raw-field"><span>권선최고온도</span><b>{{ detail.load.coil_max_temp }}℃</b></div>
              <div class="raw-field"><span>부하 감점</span><b class="neg">{{ detail.score_detail.load_minus }}</b></div>
              <div class="raw-field"><span>온도 감점</span><b class="neg">{{ detail.score_detail.temp_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">점검진단</div>
            <div class="raw-fields">
              <div class="raw-field"><span>측정일</span><b>{{ detail.inspection.measured_at }}</b></div>
              <div class="raw-field"><span>부분방전</span><b>{{ detail.inspection.part_discharge_diag }}</b></div>
              <div class="raw-field"><span>부분방전 감점</span><b class="neg">{{ detail.score_detail.part_discharge_minus }}</b></div>
              <div class="raw-field"><span>96T진단</span><b>{{ detail.inspection.oltc_96t_diag }}</b></div>
              <div class="raw-field"><span>96T 감점</span><b class="neg">{{ detail.score_detail.oltc_96t_minus }}</b></div>
              <div class="raw-field"><span>탭절환횟수</span><b>{{ detail.inspection.oltc_rslt }}</b></div>
              <div class="raw-field"><span>탭절환타입</span><b>{{ detail.inspection.oltc_type }}</b></div>
              <div class="raw-field"><span>OLTC진단</span><b>{{ detail.score_detail.oltc_diag }}</b></div>
              <div class="raw-field"><span>OLTC 감점</span><b class="neg">{{ detail.score_detail.oltc_minus }}</b></div>
              <div class="raw-field"><span>열화상</span><b>{{ detail.inspection.thermal_img_temp }}</b></div>
              <div class="raw-field"><span>열화상 감점</span><b class="neg">{{ detail.score_detail.thermal_img_minus }}</b></div>
              <div class="raw-field"><span>이상소음</span><b>{{ detail.inspection.noise_diag }}</b></div>
              <div class="raw-field"><span>소음 감점</span><b class="neg">{{ detail.score_detail.noise_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">설계속성 (DoF)</div>
            <div class="raw-fields">
              <div class="raw-field"><span>예비화</span><b>{{ detail.design.redundancy }}</b></div>
              <div class="raw-field"><span>예비화 감점</span><b class="neg">{{ detail.score_detail.redundancy_minus }}</b></div>
              <div class="raw-field"><span>계통자동전환</span><b>{{ detail.design.ato }}</b></div>
              <div class="raw-field"><span>자동전환 감점</span><b class="neg">{{ detail.score_detail.ato_minus }}</b></div>
              <div class="raw-field"><span>온라인 유중가스</span><b>{{ detail.design.online_og_chk }}</b></div>
              <div class="raw-field"><span>유중가스 감점</span><b class="neg">{{ detail.score_detail.online_og_minus }}</b></div>
              <div class="raw-field"><span>안전공사 정밀점검</span><b>{{ detail.design.offline_safety_chk }}</b></div>
              <div class="raw-field"><span>정밀점검 감점</span><b class="neg">{{ detail.score_detail.offline_safety_minus }}</b></div>
              <div class="raw-field"><span>보호요소수</span><b>{{ detail.design.sec_num }}</b></div>
              <div class="raw-field"><span>보호요소 감점</span><b class="neg">{{ detail.score_detail.sec_minus }}</b></div>
              <div class="raw-field"><span>알람요소수</span><b>{{ detail.design.alarm_num }}</b></div>
              <div class="raw-field"><span>알람요소 감점</span><b class="neg">{{ detail.score_detail.alarm_minus }}</b></div>
              <div class="raw-field"><span>절연1단계상승</span><b>{{ detail.design.insul_1st_lvup }}</b></div>
              <div class="raw-field"><span>권선 감점</span><b class="neg">{{ detail.score_detail.winding_minus }}</b></div>
              <div class="raw-field"><span>고밀도절연지</span><b>{{ detail.design.high_insul_adt }}</b></div>
              <div class="raw-field"><span>수명향상 감점</span><b class="neg">{{ detail.score_detail.prod_life_minus }}</b></div>
              <div class="raw-field"><span>이중절연</span><b>{{ detail.design.double_insul }}</b></div>
              <div class="raw-field"><span>접속부 감점</span><b class="neg">{{ detail.score_detail.connect_part_minus }}</b></div>
              <div class="raw-field"><span>온도상승한도</span><b>{{ detail.design.install_55k }}</b></div>
              <div class="raw-field"><span>온도한도 감점</span><b class="neg">{{ detail.score_detail.temp_inc_limit_minus }}</b></div>
              <div class="raw-field"><span>SFRA시험</span><b>{{ detail.design.sfra_test }}</b></div>
              <div class="raw-field"><span>SFRA 감점</span><b class="neg">{{ detail.score_detail.test_reliability_minus }}</b></div>
              <div class="raw-field"><span>부싱</span><b>{{ detail.design.rip_install }}</b></div>
              <div class="raw-field"><span>부싱 감점</span><b class="neg">{{ detail.score_detail.bushing_minus }}</b></div>
              <div class="raw-field"><span>OLTC(진공식)</span><b>{{ detail.design.vacuum_set }}</b></div>
              <div class="raw-field"><span>OLTC 감점</span><b class="neg">{{ detail.score_detail.oltc2_minus }}</b></div>
            </div>
          </div>

          <div class="raw-group">
            <div class="raw-title">CoF 구성</div>
            <div class="raw-fields">
              <div class="raw-field"><span>1차전압</span><b>{{ detail.score_detail.first_voltage.toLocaleString() }}</b></div>
              <div class="raw-field"><span>1차전압 감점</span><b class="neg">{{ detail.score_detail.first_voltage_minus }}</b></div>
              <div class="raw-field"><span>용량×부하율</span><b>{{ detail.score_detail.capa_times_load.toFixed(1) }}</b></div>
              <div class="raw-field"><span>생산성 감점</span><b class="neg">{{ detail.score_detail.productivity_minus }}</b></div>
              <div class="raw-field"><span>화재취약성</span><b>{{ detail.design.fire_vul_type }}</b></div>
              <div class="raw-field"><span>화재취약성 감점</span><b class="neg">{{ detail.score_detail.fire_minus }}</b></div>
              <div class="raw-field"><span>화재확산장소</span><b>{{ detail.design.fire_spread_loc }}</b></div>
              <div class="raw-field"><span>화재확산 감점</span><b class="neg">{{ detail.score_detail.fire_spread_minus }}</b></div>
              <div class="raw-field"><span>비상대응</span><b>{{ detail.design.emerge_response_1s }}</b></div>
              <div class="raw-field"><span>비상대응 감점</span><b class="neg">{{ detail.score_detail.emerge_response_minus }}</b></div>
              <div class="raw-field"><span>교체비용</span><b>{{ detail.score_detail.rep_cost }}</b></div>
              <div class="raw-field"><span>교체비용 감점</span><b class="neg">{{ detail.score_detail.rep_cost_minus }}</b></div>
              <div class="raw-field"><span>교체기간</span><b>{{ detail.score_detail.rep_time }}</b></div>
              <div class="raw-field"><span>교체기간 감점</span><b class="neg">{{ detail.score_detail.rep_time_minus }}</b></div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.panel {
  background: #fff;
  border: 1px solid #c4392b;
  box-shadow: 0 0 0 2px rgba(196, 57, 43, 0.12);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 20px;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
}
.loading {
  color: #8891a0;
  padding: 16px 0;
}
.eyebrow {
  font: 600 11px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #c4392b;
  margin-bottom: 8px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}
.name-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.name {
  font-size: 18px;
  font-weight: 700;
}
.chip {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.meta {
  font-size: 12px;
  color: #8891a0;
}
.body {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
}
.score-bars {
  display: grid;
  grid-template-columns: 34px 1fr 34px;
  gap: 8px 10px;
  align-items: center;
  font-size: 12px;
  color: #8891a0;
}
.bar-track {
  height: 5px;
  background: #eef0f3;
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
}
.bar-value {
  font-size: 11px;
  color: #4a5361;
  text-align: right;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  font-size: 12.5px;
}
.detail-title {
  font-weight: 600;
  color: #4a5361;
  margin-bottom: 6px;
}
.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.muted {
  color: #8891a0;
}
.raw-toggle {
  grid-column: 1 / -1;
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 6px 12px;
  border: 1px solid #d8dbe2;
  border-radius: 999px;
  background: #f7f8fa;
  color: #4a5361;
  font: 600 12px "IBM Plex Sans", system-ui, sans-serif;
  cursor: pointer;
}
.raw-toggle:hover {
  background: #eef0f3;
}
.raw-toggle svg {
  transition: transform 0.15s ease;
}
.raw-groups {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 4px;
}
.raw-group {
  border: 1px solid #eef0f3;
  border-radius: 8px;
  padding: 10px 12px;
  min-width: 0;
}
.raw-title {
  font-weight: 600;
  font-size: 12px;
  color: #c4392b;
  margin-bottom: 8px;
}
.raw-fields {
  display: grid;
  gap: 4px;
}
.raw-field {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11.5px;
  color: #4a5361;
}
.raw-field span {
  color: #8891a0;
}
.raw-field b {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 600;
  text-align: right;
  white-space: nowrap;
}
.neg {
  color: #c4392b;
}
</style>
