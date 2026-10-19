<script setup lang="ts">
// EF2(GIS) 상세 본문 (Stage 8-5). Ef1DetailBody.vue와 같은 틀:
// part="compact": 패널 왼쪽 요약 4줄 / part="raw": "원본 데이터 전체 보기" 펼침 영역.
// PoF는 원본 계산 툴의 기계적·전기적·화학적 3그룹으로 나눠 보여준다. 스타일은 부모 패널이 :deep()으로 입힌다.
import type { Ef2TypeDetail } from "../../types/equipment";

defineProps<{ typeDetail: Ef2TypeDetail; part: "compact" | "raw" }>();
</script>

<template>
  <template v-if="part === 'compact'">
    <div class="compact-row">
      <span class="compact-label">기계적</span>
      <span class="compact-value mono">동작 {{ typeDetail.operation.cb_op_num }}회 · 감점 {{ typeDetail.score_detail.gis_mech_minus }}</span>
    </div>
    <div class="compact-row">
      <span class="compact-label">전기적</span>
      <span class="compact-value mono">부하율 {{ typeDetail.operation.load_percent }}% · 감점 {{ typeDetail.score_detail.gis_elec_minus }}</span>
    </div>
    <div class="compact-row">
      <span class="compact-label">화학적(SF6)</span>
      <span class="compact-value mono">수분 {{ typeDetail.sf6.sf6_h2o }} · 순도 {{ typeDetail.sf6.sf6_purity }}% · 감점 {{ typeDetail.score_detail.gis_chem_minus }}</span>
    </div>
    <div class="compact-row">
      <span class="compact-label">설계속성</span>
      <span class="compact-value mono">ATO {{ typeDetail.design.ato }} · 공급신뢰도 {{ typeDetail.design.reliability }}</span>
    </div>
  </template>
  <template v-else>
    <div class="raw-group">
      <div class="raw-title">POF 구성</div>
      <div class="raw-subgrid">
        <div class="raw-subgroup">
          <div class="raw-subtitle">기계적 (합계 {{ typeDetail.score_detail.gis_mech_minus }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>사용연수</span><b>{{ typeDetail.score_detail.operation_year }}년</b></div>
            <div class="raw-field"><span>차단기 동작횟수</span><b>{{ typeDetail.operation.cb_op_num }}</b></div>
            <div class="raw-field"><span>동작횟수 감점</span><b class="neg">{{ typeDetail.score_detail.cb_op_num_minus }}</b></div>
            <div class="raw-field"><span>차단기 상태점수</span><b>{{ typeDetail.score_detail.cb_stat.toFixed(4) }}</b></div>
            <div class="raw-field"><span>차단기 고장확률 감점</span><b class="neg">{{ typeDetail.score_detail.cb_stat_minus }}</b></div>
            <div class="raw-field"><span>절연물 상태점수</span><b>{{ typeDetail.score_detail.insul_stat.toFixed(4) }}</b></div>
            <div class="raw-field"><span>절연물 고장확률 감점</span><b class="neg">{{ typeDetail.score_detail.insul_stat_minus }}</b></div>
            <div class="raw-field"><span>조작방식</span><b>{{ typeDetail.operation.op_type }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">전기적 (합계 {{ typeDetail.score_detail.gis_elec_minus }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>측정일</span><b>{{ typeDetail.operation.measured_at }}</b></div>
            <div class="raw-field"><span>정격차단 동작횟수</span><b>{{ typeDetail.operation.rated_trip_count }}</b></div>
            <div class="raw-field"><span>정격차단 감점</span><b class="neg">{{ typeDetail.score_detail.rated_trip_count_minus }}</b></div>
            <div class="raw-field"><span>누적차단전류</span><b>{{ typeDetail.operation.cum_trip_current }}</b></div>
            <div class="raw-field"><span>누적차단전류 감점</span><b class="neg">{{ typeDetail.score_detail.cum_trip_current_minus }}</b></div>
            <div class="raw-field"><span>부하율</span><b>{{ typeDetail.operation.load_percent }}%</b></div>
            <div class="raw-field"><span>부하율 감점</span><b class="neg">{{ typeDetail.score_detail.load_minus }}</b></div>
            <div class="raw-field"><span>누설전류</span><b>{{ typeDetail.operation.leakage_curr }}</b></div>
            <div class="raw-field"><span>누설전류 감점</span><b class="neg">{{ typeDetail.score_detail.leakage_curr_minus }}</b></div>
            <div class="raw-field"><span>경과연수 감점</span><b class="neg">{{ typeDetail.score_detail.age_minus }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">화학적 (합계 {{ typeDetail.score_detail.gis_chem_minus }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>부분방전 이상패턴</span><b>{{ typeDetail.diagnosis.part_dischar_pat }}</b></div>
            <div class="raw-field"><span>부분방전 감점</span><b class="neg">{{ typeDetail.score_detail.part_dischar_minus }}</b></div>
            <div class="raw-field"><span>SF6 진단일</span><b>{{ typeDetail.sf6.diag_time }}</b></div>
            <div class="raw-field"><span>SO2</span><b>{{ typeDetail.sf6.sf6_so2 }}</b></div>
            <div class="raw-field"><span>누기</span><b>{{ typeDetail.sf6.sf6_leak }}</b></div>
            <div class="raw-field"><span>수분</span><b>{{ typeDetail.sf6.sf6_h2o }}</b></div>
            <div class="raw-field"><span>순도</span><b>{{ typeDetail.sf6.sf6_purity }}%</b></div>
            <div class="raw-field"><span>SF6 감점</span><b class="neg">{{ typeDetail.score_detail.sf6_minus }}</b></div>
            <div class="raw-field"><span>전기실 최대온도</span><b>{{ typeDetail.diagnosis.elec_room_max_temp }}℃</b></div>
            <div class="raw-field"><span>전기실 감점</span><b class="neg">{{ typeDetail.score_detail.elec_room_minus }}</b></div>
          </div>
        </div>
      </div>
    </div>

    <div class="raw-group">
      <div class="raw-title">COF 구성</div>
      <div class="raw-fields">
        <div class="raw-field"><span>인입전압 등급</span><b>{{ typeDetail.consequence.in_vol }}</b></div>
        <div class="raw-field"><span>인입전압 감점</span><b class="neg">{{ typeDetail.score_detail.in_vol_minus }}</b></div>
        <div class="raw-field"><span>생산영향성 등급</span><b>{{ typeDetail.consequence.capa_times_load }}</b></div>
        <div class="raw-field"><span>생산영향성 감점</span><b class="neg">{{ typeDetail.score_detail.productivity_minus }}</b></div>
        <div class="raw-field"><span>화재확산 등급</span><b>{{ typeDetail.consequence.fire_spread }}</b></div>
        <div class="raw-field"><span>화재확산 감점</span><b class="neg">{{ typeDetail.score_detail.fire_spread_minus }}</b></div>
        <div class="raw-field"><span>환경_위치 등급</span><b>{{ typeDetail.consequence.env_loc }}</b></div>
        <div class="raw-field"><span>환경_위치 감점</span><b class="neg">{{ typeDetail.score_detail.env_minus }}</b></div>
        <div class="raw-field"><span>비상대응시간 등급</span><b>{{ typeDetail.consequence.emerge_resp_pat }}</b></div>
        <div class="raw-field"><span>비상대응 감점</span><b class="neg">{{ typeDetail.score_detail.emerge_resp_minus }}</b></div>
        <div class="raw-field"><span>사고복구비용 등급</span><b>{{ typeDetail.consequence.rep_cost }}</b></div>
        <div class="raw-field"><span>사고복구비용 감점</span><b class="neg">{{ typeDetail.score_detail.rep_cost_minus }}</b></div>
        <div class="raw-field"><span>정상화기간 등급</span><b>{{ typeDetail.consequence.rep_time }}</b></div>
        <div class="raw-field"><span>정상화기간 감점</span><b class="neg">{{ typeDetail.score_detail.rep_time_minus }}</b></div>
      </div>
    </div>

    <div class="raw-group">
      <div class="raw-title">DOF 구성</div>
      <div class="raw-fields">
        <div class="raw-field"><span>인입선로 등급</span><b>{{ typeDetail.design.in_line_num }}</b></div>
        <div class="raw-field"><span>인입선로 감점</span><b class="neg">{{ typeDetail.score_detail.in_line_minus }}</b></div>
        <div class="raw-field"><span>ATO 구성</span><b>{{ typeDetail.design.ato }}</b></div>
        <div class="raw-field"><span>ATO 감점</span><b class="neg">{{ typeDetail.score_detail.ato_minus }}</b></div>
        <div class="raw-field"><span>공급신뢰도 등급</span><b>{{ typeDetail.design.reliability }}</b></div>
        <div class="raw-field"><span>공급신뢰도 감점</span><b class="neg">{{ typeDetail.score_detail.reliability_minus }}</b></div>
        <div class="raw-field"><span>온라인진단 등급</span><b>{{ typeDetail.design.online_diag }}</b></div>
        <div class="raw-field"><span>온라인진단 감점</span><b class="neg">{{ typeDetail.score_detail.online_diag_minus }}</b></div>
        <div class="raw-field"><span>오프라인진단</span><b>{{ typeDetail.design.offline_diag }}</b></div>
        <div class="raw-field"><span>오프라인진단 감점</span><b class="neg">{{ typeDetail.score_detail.offline_diag_minus }}</b></div>
        <div class="raw-field"><span>TBM 실시</span><b>{{ typeDetail.design.tbm }}</b></div>
        <div class="raw-field"><span>TBM 감점</span><b class="neg">{{ typeDetail.score_detail.tbm_minus }}</b></div>
        <div class="raw-field"><span>도체접속구조개선</span><b>{{ typeDetail.design.conn_rev }}</b></div>
        <div class="raw-field"><span>도체접속 감점</span><b class="neg">{{ typeDetail.score_detail.conn_rev_minus }}</b></div>
        <div class="raw-field"><span>가스기밀강화</span><b>{{ typeDetail.design.leak_str }}</b></div>
        <div class="raw-field"><span>가스기밀 감점</span><b class="neg">{{ typeDetail.score_detail.leak_str_minus }}</b></div>
        <div class="raw-field"><span>절연스펙강화</span><b>{{ typeDetail.design.insul_str }}</b></div>
        <div class="raw-field"><span>절연스펙 감점</span><b class="neg">{{ typeDetail.score_detail.insul_str_minus }}</b></div>
        <div class="raw-field"><span>부품신뢰성강화</span><b>{{ typeDetail.design.vt_la_str }}</b></div>
        <div class="raw-field"><span>부품신뢰성 감점</span><b class="neg">{{ typeDetail.score_detail.vt_la_minus }}</b></div>
      </div>
    </div>
  </template>
</template>
