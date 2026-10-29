<script setup lang="ts">
// EF2(GIS) 상세 본문 (Stage 8-5). Ef1DetailBody.vue와 같은 틀:
// 패널의 "원본 데이터 전체 보기" 펼침 영역(요약 4줄은 2026-10-29 패널에서 뺐다 — 그 자리는 POF·COF·DOF 막대).
// PoF는 원본 계산 툴의 기계적·전기적·화학적 3그룹으로 나눠 보여준다. 스타일은 부모 패널이 :deep()으로 입힌다.
import type { Ef2TypeDetail } from "../../types/equipment";
import { na } from "../../utils/formatValue";

defineProps<{ typeDetail: Ef2TypeDetail }>();
</script>

<template>
  <div class="raw-group">
    <div class="raw-title">POF 구성</div>
    <div class="raw-subgrid">
      <div class="raw-subgroup">
        <div class="raw-subtitle">기계적 (합계 {{ na(typeDetail.score_detail.gis_mech_minus) }})</div>
        <div class="raw-fields">
          <div class="raw-field"><span>사용연수</span><b>{{ na(typeDetail.score_detail.operation_year, { unit: "년" }) }}</b></div>
          <div class="raw-field"><span>차단기 동작횟수</span><b>{{ na(typeDetail.operation.cb_op_num) }}</b></div>
          <div class="raw-field"><span>동작횟수 감점</span><b class="neg">{{ na(typeDetail.score_detail.cb_op_num_minus) }}</b></div>
          <div class="raw-field"><span>차단기 상태점수</span><b>{{ na(typeDetail.score_detail.cb_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>차단기 고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.cb_stat_minus) }}</b></div>
          <div class="raw-field"><span>절연물 상태점수</span><b>{{ na(typeDetail.score_detail.insul_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>절연물 고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.insul_stat_minus) }}</b></div>
          <div class="raw-field"><span>조작방식</span><b>{{ na(typeDetail.operation.op_type) }}</b></div>
        </div>
      </div>

      <div class="raw-subgroup">
        <div class="raw-subtitle">전기적 (합계 {{ na(typeDetail.score_detail.gis_elec_minus) }})</div>
        <div class="raw-fields">
          <div class="raw-field"><span>측정일</span><b>{{ na(typeDetail.operation.measured_at) }}</b></div>
          <div class="raw-field"><span>정격차단 동작횟수</span><b>{{ na(typeDetail.operation.rated_trip_count) }}</b></div>
          <div class="raw-field"><span>정격차단 감점</span><b class="neg">{{ na(typeDetail.score_detail.rated_trip_count_minus) }}</b></div>
          <div class="raw-field"><span>누적차단전류</span><b>{{ na(typeDetail.operation.cum_trip_current) }}</b></div>
          <div class="raw-field"><span>누적차단전류 감점</span><b class="neg">{{ na(typeDetail.score_detail.cum_trip_current_minus) }}</b></div>
          <div class="raw-field"><span>부하율</span><b>{{ na(typeDetail.operation.load_percent, { unit: "%" }) }}</b></div>
          <div class="raw-field"><span>부하율 감점</span><b class="neg">{{ na(typeDetail.score_detail.load_minus) }}</b></div>
          <div class="raw-field"><span>누설전류</span><b>{{ na(typeDetail.operation.leakage_curr) }}</b></div>
          <div class="raw-field"><span>누설전류 감점</span><b class="neg">{{ na(typeDetail.score_detail.leakage_curr_minus) }}</b></div>
          <div class="raw-field"><span>경과연수 감점</span><b class="neg">{{ na(typeDetail.score_detail.age_minus) }}</b></div>
        </div>
      </div>

      <div class="raw-subgroup">
        <div class="raw-subtitle">화학적 (합계 {{ na(typeDetail.score_detail.gis_chem_minus) }})</div>
        <div class="raw-fields">
          <div class="raw-field"><span>부분방전 이상패턴</span><b>{{ na(typeDetail.diagnosis.part_dischar_pat) }}</b></div>
          <div class="raw-field"><span>부분방전 감점</span><b class="neg">{{ na(typeDetail.score_detail.part_dischar_minus) }}</b></div>
          <div class="raw-field"><span>SF6 진단일</span><b>{{ na(typeDetail.sf6.diag_time) }}</b></div>
          <div class="raw-field"><span>SO2</span><b>{{ na(typeDetail.sf6.sf6_so2) }}</b></div>
          <div class="raw-field"><span>누기</span><b>{{ na(typeDetail.sf6.sf6_leak) }}</b></div>
          <div class="raw-field"><span>수분</span><b>{{ na(typeDetail.sf6.sf6_h2o) }}</b></div>
          <div class="raw-field"><span>순도</span><b>{{ na(typeDetail.sf6.sf6_purity, { unit: "%" }) }}</b></div>
          <div class="raw-field"><span>SF6 감점</span><b class="neg">{{ na(typeDetail.score_detail.sf6_minus) }}</b></div>
          <div class="raw-field"><span>전기실 최대온도</span><b>{{ na(typeDetail.diagnosis.elec_room_max_temp, { unit: "℃" }) }}</b></div>
          <div class="raw-field"><span>전기실 감점</span><b class="neg">{{ na(typeDetail.score_detail.elec_room_minus) }}</b></div>
        </div>
      </div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">COF 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>인입전압 등급</span><b>{{ na(typeDetail.consequence.in_vol) }}</b></div>
      <div class="raw-field"><span>인입전압 감점</span><b class="neg">{{ na(typeDetail.score_detail.in_vol_minus) }}</b></div>
      <div class="raw-field"><span>생산영향성 등급</span><b>{{ na(typeDetail.consequence.capa_times_load) }}</b></div>
      <div class="raw-field"><span>생산영향성 감점</span><b class="neg">{{ na(typeDetail.score_detail.productivity_minus) }}</b></div>
      <div class="raw-field"><span>화재확산 등급</span><b>{{ na(typeDetail.consequence.fire_spread) }}</b></div>
      <div class="raw-field"><span>화재확산 감점</span><b class="neg">{{ na(typeDetail.score_detail.fire_spread_minus) }}</b></div>
      <div class="raw-field"><span>환경_위치 등급</span><b>{{ na(typeDetail.consequence.env_loc) }}</b></div>
      <div class="raw-field"><span>환경_위치 감점</span><b class="neg">{{ na(typeDetail.score_detail.env_minus) }}</b></div>
      <div class="raw-field"><span>비상대응시간 등급</span><b>{{ na(typeDetail.consequence.emerge_resp_pat) }}</b></div>
      <div class="raw-field"><span>비상대응 감점</span><b class="neg">{{ na(typeDetail.score_detail.emerge_resp_minus) }}</b></div>
      <div class="raw-field"><span>사고복구비용 등급</span><b>{{ na(typeDetail.consequence.rep_cost) }}</b></div>
      <div class="raw-field"><span>사고복구비용 감점</span><b class="neg">{{ na(typeDetail.score_detail.rep_cost_minus) }}</b></div>
      <div class="raw-field"><span>정상화기간 등급</span><b>{{ na(typeDetail.consequence.rep_time) }}</b></div>
      <div class="raw-field"><span>정상화기간 감점</span><b class="neg">{{ na(typeDetail.score_detail.rep_time_minus) }}</b></div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">DOF 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>인입선로 등급</span><b>{{ na(typeDetail.design.in_line_num) }}</b></div>
      <div class="raw-field"><span>인입선로 감점</span><b class="neg">{{ na(typeDetail.score_detail.in_line_minus) }}</b></div>
      <div class="raw-field"><span>ATO 구성</span><b>{{ na(typeDetail.design.ato) }}</b></div>
      <div class="raw-field"><span>ATO 감점</span><b class="neg">{{ na(typeDetail.score_detail.ato_minus) }}</b></div>
      <div class="raw-field"><span>공급신뢰도 등급</span><b>{{ na(typeDetail.design.reliability) }}</b></div>
      <div class="raw-field"><span>공급신뢰도 감점</span><b class="neg">{{ na(typeDetail.score_detail.reliability_minus) }}</b></div>
      <div class="raw-field"><span>온라인진단 등급</span><b>{{ na(typeDetail.design.online_diag) }}</b></div>
      <div class="raw-field"><span>온라인진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.online_diag_minus) }}</b></div>
      <div class="raw-field"><span>오프라인진단</span><b>{{ na(typeDetail.design.offline_diag) }}</b></div>
      <div class="raw-field"><span>오프라인진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.offline_diag_minus) }}</b></div>
      <div class="raw-field"><span>TBM 실시</span><b>{{ na(typeDetail.design.tbm) }}</b></div>
      <div class="raw-field"><span>TBM 감점</span><b class="neg">{{ na(typeDetail.score_detail.tbm_minus) }}</b></div>
      <div class="raw-field"><span>도체접속구조개선</span><b>{{ na(typeDetail.design.conn_rev) }}</b></div>
      <div class="raw-field"><span>도체접속 감점</span><b class="neg">{{ na(typeDetail.score_detail.conn_rev_minus) }}</b></div>
      <div class="raw-field"><span>가스기밀강화</span><b>{{ na(typeDetail.design.leak_str) }}</b></div>
      <div class="raw-field"><span>가스기밀 감점</span><b class="neg">{{ na(typeDetail.score_detail.leak_str_minus) }}</b></div>
      <div class="raw-field"><span>절연스펙강화</span><b>{{ na(typeDetail.design.insul_str) }}</b></div>
      <div class="raw-field"><span>절연스펙 감점</span><b class="neg">{{ na(typeDetail.score_detail.insul_str_minus) }}</b></div>
      <div class="raw-field"><span>부품신뢰성강화</span><b>{{ na(typeDetail.design.vt_la_str) }}</b></div>
      <div class="raw-field"><span>부품신뢰성 감점</span><b class="neg">{{ na(typeDetail.score_detail.vt_la_minus) }}</b></div>
    </div>
  </div>
</template>
