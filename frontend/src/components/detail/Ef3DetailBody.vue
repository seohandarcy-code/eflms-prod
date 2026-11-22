<script setup lang="ts">
// EF3(초고압케이블) 상세 본문 (Stage 9-4, Stage 22 횡전개 개정 2026-11-20). Ef1/Ef2DetailBody.vue와 같은 틀:
// 패널의 "원본 데이터 전체 보기" 펼침 영역(요약 4줄은 2026-10-29 패널에서 뺐다 — 그 자리는 POF·COF·DOF 막대).
// 원본 계산 툴에 PoF 그룹 구분이 없어 축별로 나열한다. 계산에 안 쓰는 진단 측정값(PD신호·이론치·누설전류 등)은
// 맨 아래 "진단 측정값" 묶음. 스타일은 부모 패널이 :deep()으로 입힌다.
import type { Ef3TypeDetail } from "../../types/equipment";
import { na } from "../../utils/formatValue";

defineProps<{ typeDetail: Ef3TypeDetail }>();
</script>

<template>
  <div class="raw-group">
    <div class="raw-title">POF(설비상태) 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>안전공사최근진단일</span><b>{{ na(typeDetail.condition.recent_diag_date) }}</b></div>
      <div class="raw-field"><span>측정값 반영일</span><b>{{ na(typeDetail.condition.measured_at) }}</b></div>
      <div class="raw-field"><span>사용연수</span><b>{{ na(typeDetail.score_detail.operation_year, { unit: "년" }) }}</b></div>
      <div class="raw-field"><span>경과연수 감점</span><b class="neg">{{ na(typeDetail.score_detail.age_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>최대부하</span><b>{{ na(typeDetail.condition.max_load) }}</b></div>
      <div class="raw-field"><span>회선별용량</span><b>{{ na(typeDetail.spec.cable_mva) }}</b></div>
      <div class="raw-field"><span>부하율</span><b>{{ na(typeDetail.score_detail.load_percent, { digits: 1, unit: "%" }) }}</b></div>
      <div class="raw-field"><span>부하율 감점</span><b class="neg">{{ na(typeDetail.score_detail.load_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>최고온도</span><b>{{ na(typeDetail.condition.max_temp, { unit: "℃" }) }}</b></div>
      <div class="raw-field"><span>온도 감점</span><b class="neg">{{ na(typeDetail.score_detail.temp_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>상간온도차</span><b>{{ na(typeDetail.condition.diff_temp, { unit: "℃" }) }}</b></div>
      <div class="raw-field"><span>열화상 감점</span><b class="neg">{{ na(typeDetail.score_detail.diff_temp_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>온도기반손상률(계산)</span><b>{{ na(typeDetail.score_detail.failure_rate, { digits: 5 }) }}</b></div>
      <div class="raw-field"><span>온도기반손상률 감점</span><b class="neg">{{ na(typeDetail.score_detail.failure_rate_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>PD진단결과</span><b>{{ na(typeDetail.condition.pd_diag_rslt) }}</b></div>
      <div class="raw-field"><span>부분방전 감점</span><b class="neg">{{ na(typeDetail.score_detail.pd_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>시스순환전류진단결과</span><b>{{ na(typeDetail.condition.sys_cycle_curr_diag) }}</b></div>
      <div class="raw-field"><span>시스템순환전류 감점</span><b class="neg">{{ na(typeDetail.score_detail.sys_cycle_curr_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>SVL누설전류진단결과</span><b>{{ na(typeDetail.condition.svl_leak_curr_diag) }}</b></div>
      <div class="raw-field"><span>SVL누설전류 감점</span><b class="neg">{{ na(typeDetail.score_detail.svl_leak_curr_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>피뢰기누설전류진단결과</span><b>{{ na(typeDetail.condition.la_leak_curr_diag) }}</b></div>
      <div class="raw-field"><span>피뢰기누설전류 감점</span><b class="neg">{{ na(typeDetail.score_detail.la_leak_curr_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>접속함외관손상여부</span><b>{{ na(typeDetail.condition.joint_ex_damage) }}</b></div>
      <div class="raw-field"><span>접속함외관 감점</span><b class="neg">{{ na(typeDetail.score_detail.joint_ex_damage_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>케이블이동량</span><b>{{ na(typeDetail.condition.cable_move) }}</b></div>
      <div class="raw-field"><span>케이블이동량 감점</span><b class="neg">{{ na(typeDetail.score_detail.cable_move_minus, { digits: 1 }) }}</b></div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">COF(고장영향성) 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>사고영향성용량</span><b>{{ na(typeDetail.score_detail.risk_mva) }}</b></div>
      <div class="raw-field"><span>사고영향성(용량) 감점</span><b class="neg">{{ na(typeDetail.score_detail.risk_mva_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>타T/L공동포설여부</span><b>{{ na(typeDetail.spec.tl_apply) }}</b></div>
      <div class="raw-field"><span>타T/L회선수</span><b>{{ na(typeDetail.spec.tl_num, { unit: "회선" }) }}</b></div>
      <div class="raw-field"><span>사고영향성(공동포설) 감점</span><b class="neg">{{ na(typeDetail.score_detail.tl_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>포설방법1 / 2</span><b>{{ na(typeDetail.spec.laying_type) }} / {{ na(typeDetail.spec.laying_type2) }}</b></div>
      <div class="raw-field"><span>포설방법 감점(나쁜 값)</span><b class="neg">{{ na(typeDetail.score_detail.laying_type_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>중간접속함개수</span><b>{{ na(typeDetail.spec.mid_joint, { unit: "개" }) }}</b></div>
      <div class="raw-field"><span>중간접속함 감점</span><b class="neg">{{ na(typeDetail.score_detail.mid_joint_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>종단접속함종류1 / 2</span><b>{{ na(typeDetail.spec.end_joint) }} / {{ na(typeDetail.spec.end_joint2) }}</b></div>
      <div class="raw-field"><span>종단접속함 감점(나쁜 값)</span><b class="neg">{{ na(typeDetail.score_detail.end_joint_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>비상대응시간</span><b>{{ na(typeDetail.consequence.emerge_resp) }}</b></div>
      <div class="raw-field"><span>비상대응시간 감점</span><b class="neg">{{ na(typeDetail.score_detail.emerge_resp_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>사고복구비용</span><b>{{ na(typeDetail.consequence.rep_cost) }}</b></div>
      <div class="raw-field"><span>사고복구비용 감점</span><b class="neg">{{ na(typeDetail.score_detail.rep_cost_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>정상화기간</span><b>{{ na(typeDetail.consequence.rep_time) }}</b></div>
      <div class="raw-field"><span>정상화기간 감점</span><b class="neg">{{ na(typeDetail.score_detail.rep_time_minus, { digits: 1 }) }}</b></div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">DOF(고장예방력) 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>공급신뢰도회선수</span><b>{{ na(typeDetail.design.reliability) }}</b></div>
      <div class="raw-field"><span>공급신뢰도 감점</span><b class="neg">{{ na(typeDetail.score_detail.reliability_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>열화상진단여부</span><b>{{ na(typeDetail.design.temp_diag) }}</b></div>
      <div class="raw-field"><span>열화상진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.temp_diag_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>PD진단여부</span><b>{{ na(typeDetail.design.pd_diag) }}</b></div>
      <div class="raw-field"><span>PD진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.pd_diag_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>활선진단여부</span><b>{{ na(typeDetail.design.live_line_diag) }}</b></div>
      <div class="raw-field"><span>활선진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.live_line_diag_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>이동량여부</span><b>{{ na(typeDetail.design.cable_move_diag) }}</b></div>
      <div class="raw-field"><span>케이블이동량여부 감점</span><b class="neg">{{ na(typeDetail.score_detail.cable_move_diag_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>오프라인진단여부</span><b>{{ na(typeDetail.design.offline_diag) }}</b></div>
      <div class="raw-field"><span>오프라인진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.offline_diag_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>장수명절연물여부</span><b>{{ na(typeDetail.design.longlife_insul) }}</b></div>
      <div class="raw-field"><span>장수명절연물 감점</span><b class="neg">{{ na(typeDetail.score_detail.longlife_insul_minus, { digits: 1 }) }}</b></div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">진단 측정값(점수 계산에 안 씀)</div>
    <div class="raw-fields">
      <div class="raw-field"><span>온도진단결과</span><b>{{ na(typeDetail.condition.max_temp_diag) }}</b></div>
      <div class="raw-field"><span>열화상진단결과</span><b>{{ na(typeDetail.condition.diff_temp_diag) }}</b></div>
      <div class="raw-field"><span>PD신호크기(3/6/10Mhz)</span><b>{{ na(typeDetail.condition.pd_signal_3Mhz) }} / {{ na(typeDetail.condition.pd_signal_6Mhz) }} / {{ na(typeDetail.condition.pd_signal_10Mhz) }}</b></div>
      <div class="raw-field"><span>부분방전발생횟수</span><b>{{ na(typeDetail.condition.pd_num, { unit: "회" }) }}</b></div>
      <div class="raw-field"><span>시스순환전류 이론치 / 실측치</span><b>{{ na(typeDetail.condition.sys_cycle_theo_curr) }} / {{ na(typeDetail.condition.sys_cycle_curr) }}</b></div>
      <div class="raw-field"><span>SVL누설전류</span><b>{{ na(typeDetail.condition.svl_leak_curr) }}</b></div>
      <div class="raw-field"><span>기본파누설전류</span><b>{{ na(typeDetail.condition.basic_leak_curr) }}</b></div>
      <div class="raw-field"><span>3고조파누설전류</span><b>{{ na(typeDetail.condition.third_har_leak_curr) }}</b></div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">케이블 사양</div>
    <div class="raw-fields">
      <div class="raw-field"><span>굵기</span><b>{{ na(typeDetail.spec.cable_sq, { unit: "sq" }) }}</b></div>
      <div class="raw-field"><span>phase당케이블</span><b>{{ na(typeDetail.spec.cable_per_phase) }}</b></div>
      <div class="raw-field"><span>회선별용량</span><b>{{ na(typeDetail.spec.cable_mva) }}</b></div>
      <div class="raw-field"><span>사양 갱신일</span><b>{{ na(typeDetail.spec.updated_at) }}</b></div>
    </div>
  </div>
</template>
