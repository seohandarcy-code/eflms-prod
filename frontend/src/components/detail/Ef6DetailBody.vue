<script setup lang="ts">
// EF6(VDP) 상세 본문 (Stage 14-2). Ef1~Ef5DetailBody.vue와 같은 틀 — 지금은 EF5(UPS)와 같은 구성이지만
// 앞으로 항목이 달라질 수 있어 따로 둔다(2026-11-06 사용자 결정).
// 패널의 "원본 데이터 전체 보기" 펼침 영역 — POF·COF·DOF 구성 세 묶음.
// 원본 계산 툴에 소계가 없어 COF·DOF는 축별로 나열한다(EF3과 같음). POF는 항목이 많아 설비정보(라인·제작사·모델명,
// 계산에는 안 쓰임)를 첫 소그룹으로 두고(EF4 설치위치와 같은 방식), 부품 고장확률과 운전·점검으로 나눠 보여준다.
// 스타일은 부모 패널이 :deep()으로 입힌다.
import type { Ef6TypeDetail } from "../../types/equipment";
import { na } from "../../utils/formatValue";

defineProps<{ typeDetail: Ef6TypeDetail }>();
</script>

<template>
  <div class="raw-group">
    <div class="raw-title">POF 구성</div>
    <div class="raw-subgrid">
      <div class="raw-subgroup">
        <div class="raw-subtitle">설비정보</div>
        <div class="raw-fields">
          <div class="raw-field"><span>라인</span><b>{{ na(typeDetail.spec.line_no) }}</b></div>
          <div class="raw-field"><span>제작사</span><b>{{ na(typeDetail.spec.manufacturer) }}</b></div>
          <div class="raw-field"><span>모델명</span><b>{{ na(typeDetail.spec.model_name) }}</b></div>
        </div>
      </div>

      <div class="raw-subgroup">
        <div class="raw-subtitle">부품 고장확률</div>
        <div class="raw-fields">
          <div class="raw-field"><span>사용년수</span><b>{{ na(typeDetail.score_detail.operation_year, { unit: "년" }) }}</b></div>
          <div class="raw-field"><span>경과년수 감점</span><b class="neg">{{ na(typeDetail.score_detail.age_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>차단기교체횟수</span><b>{{ na(typeDetail.score_detail.cb_replace_no, { unit: "회" }) }}</b></div>
          <div class="raw-field"><span>차단기고장확률사용수명</span><b>{{ na(typeDetail.score_detail.cb_life_year, { digits: 1, unit: "년" }) }}</b></div>
          <div class="raw-field"><span>차단기고장확률상태점수</span><b>{{ na(typeDetail.score_detail.cb_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>차단기고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.cb_stat_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>커패시터고장확률상태점수</span><b>{{ na(typeDetail.score_detail.cap_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>커패시터고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.cap_stat_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>팬교체횟수</span><b>{{ na(typeDetail.condition.fan_replace_no, { unit: "회" }) }}</b></div>
          <div class="raw-field"><span>fan고장확률사용수명</span><b>{{ na(typeDetail.score_detail.fan_life_year, { digits: 1, unit: "년" }) }}</b></div>
          <div class="raw-field"><span>fan고장확률상태점수</span><b>{{ na(typeDetail.score_detail.fan_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>fan고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.fan_stat_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>igbt고장확률상태점수</span><b>{{ na(typeDetail.score_detail.igbt_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>igbt고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.igbt_stat_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>보드고장확률상태점수</span><b>{{ na(typeDetail.score_detail.board_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>보드고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.board_stat_minus, { digits: 1 }) }}</b></div>
        </div>
      </div>

      <div class="raw-subgroup">
        <div class="raw-subtitle">운전·점검</div>
        <div class="raw-fields">
          <div class="raw-field"><span>점검결과 반영일</span><b>{{ na(typeDetail.condition.measured_at) }}</b></div>
          <div class="raw-field"><span>전기실최대온도</span><b>{{ na(typeDetail.condition.elec_room_max_temp, { unit: "℃" }) }}</b></div>
          <div class="raw-field"><span>전기실최고온도 감점</span><b class="neg">{{ na(typeDetail.score_detail.elec_room_max_temp_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>부하율</span><b>{{ na(typeDetail.condition.load, { unit: "%" }) }}</b></div>
          <div class="raw-field"><span>부하율 감점</span><b class="neg">{{ na(typeDetail.score_detail.load_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>모듈간순환전류</span><b>{{ na(typeDetail.condition.mod_cir_curr) }}</b></div>
          <div class="raw-field"><span>모듈간순환전류 감점</span><b class="neg">{{ na(typeDetail.score_detail.mod_cir_curr_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>모듈간출력전압차이</span><b>{{ na(typeDetail.condition.mod_vol_diff) }}</b></div>
          <div class="raw-field"><span>모듈간전압차이 감점</span><b class="neg">{{ na(typeDetail.score_detail.mod_vol_diff_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>소음</span><b>{{ na(typeDetail.condition.noise) }}</b></div>
          <div class="raw-field"><span>소음 감점</span><b class="neg">{{ na(typeDetail.score_detail.noise_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>열화상</span><b>{{ na(typeDetail.condition.thermal_img_chk) }}</b></div>
          <div class="raw-field"><span>열화상점검 감점</span><b class="neg">{{ na(typeDetail.score_detail.thermal_img_chk_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>외함점검</span><b>{{ na(typeDetail.condition.ex_box_chk) }}</b></div>
          <div class="raw-field"><span>외함점검 감점</span><b class="neg">{{ na(typeDetail.score_detail.ex_box_chk_minus, { digits: 1 }) }}</b></div>
        </div>
      </div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">COF 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>정격용량</span><b>{{ na(typeDetail.spec.capa, { locale: true }) }}</b></div>
      <div class="raw-field"><span>부하량</span><b>{{ na(typeDetail.score_detail.capa_times_load, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>사고영향성 감점</span><b class="neg">{{ na(typeDetail.score_detail.capa_times_load_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>설치건물등급</span><b>{{ na(typeDetail.consequence.ins_build_rank) }}</b></div>
      <div class="raw-field"><span>설치건물등급 감점</span><b class="neg">{{ na(typeDetail.score_detail.ins_build_rank_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>화재확산등급</span><b>{{ na(typeDetail.consequence.fire_spread_rank) }}</b></div>
      <div class="raw-field"><span>화재확산등급 감점</span><b class="neg">{{ na(typeDetail.score_detail.fire_spread_rank_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>전력재공급시간등급</span><b>{{ na(typeDetail.consequence.emerge_resp) }}</b></div>
      <div class="raw-field"><span>사고복구시간 감점</span><b class="neg">{{ na(typeDetail.score_detail.emerge_resp_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>정상화기간등급</span><b>{{ na(typeDetail.consequence.rep_time) }}</b></div>
      <div class="raw-field"><span>정상화기간 감점</span><b class="neg">{{ na(typeDetail.score_detail.rep_time_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>사고복구비용등급</span><b>{{ na(typeDetail.consequence.rep_cost) }}</b></div>
      <div class="raw-field"><span>사고복구비용 감점</span><b class="neg">{{ na(typeDetail.score_detail.rep_cost_minus, { digits: 1 }) }}</b></div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">DOF 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>계통신뢰도등급</span><b>{{ na(typeDetail.design.sys_rel) }}</b></div>
      <div class="raw-field"><span>계통신뢰도 감점</span><b class="neg">{{ na(typeDetail.score_detail.sys_rel_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>비상계통전력공급등급</span><b>{{ na(typeDetail.design.emerge_sys) }}</b></div>
      <div class="raw-field"><span>비상계통전력공급 감점</span><b class="neg">{{ na(typeDetail.score_detail.emerge_sys_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>설비신뢰도등급</span><b>{{ na(typeDetail.design.fac_rel) }}</b></div>
      <div class="raw-field"><span>설비신뢰도 감점</span><b class="neg">{{ na(typeDetail.score_detail.fac_rel_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>설비모델단종여부등급</span><b>{{ na(typeDetail.design.part_shortage) }}</b></div>
      <div class="raw-field"><span>설비모델단종여부 감점</span><b class="neg">{{ na(typeDetail.score_detail.part_shortage_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>모델type등급</span><b>{{ na(typeDetail.design.model_type) }}</b></div>
      <div class="raw-field"><span>모델타입 감점</span><b class="neg">{{ na(typeDetail.score_detail.model_type_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>스위칭동작등급</span><b>{{ na(typeDetail.design.switching_type) }}</b></div>
      <div class="raw-field"><span>스위칭타입 감점</span><b class="neg">{{ na(typeDetail.score_detail.switching_type_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>igbt개선등급</span><b>{{ na(typeDetail.design.igbt_rev) }}</b></div>
      <div class="raw-field"><span>IGBT개선 감점</span><b class="neg">{{ na(typeDetail.score_detail.igbt_rev_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>온라인진단등급</span><b>{{ na(typeDetail.design.online_diag) }}</b></div>
      <div class="raw-field"><span>온라인진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.online_diag_minus, { digits: 1 }) }}</b></div>
    </div>
  </div>
</template>
