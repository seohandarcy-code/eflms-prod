<script setup lang="ts">
// EF7(배터리) 상세 본문 (Stage 15-2). Ef1~Ef6DetailBody.vue와 같은 틀.
// 패널의 "원본 데이터 전체 보기" 펼침 영역 — POF·COF·DOF 구성 세 묶음.
// 원본 계산 툴에 소계가 없어 COF·DOF는 축별로 나열한다(EF3과 같음). POF는 설비정보(라인·제작사·모델명, 계산에는
// 안 쓰임)를 첫 소그룹으로 두고, SOH·BMS(참고표로 낸 방전인덱스합·온도감소계수 포함)와 셀·배터리실 상태로 나눈다.
// 부하율은 CoF(부하량)에만 쓰여 COF 구성에 둔다. 스타일은 부모 패널이 :deep()으로 입힌다.
import type { Ef7TypeDetail } from "../../types/equipment";
import { na } from "../../utils/formatValue";

defineProps<{ typeDetail: Ef7TypeDetail }>();
</script>

<template>
  <div class="raw-group">
    <div class="raw-title">POF(설비상태) 구성</div>
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
        <div class="raw-subtitle">SOH·BMS</div>
        <div class="raw-fields">
          <div class="raw-field"><span>사용년수</span><b>{{ na(typeDetail.score_detail.operation_year, { unit: "년" }) }}</b></div>
          <div class="raw-field"><span>경과년수 감점</span><b class="neg">{{ na(typeDetail.score_detail.age_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>방전인덱스합계</span><b>{{ na(typeDetail.score_detail.disch_index, { digits: 3 }) }}</b></div>
          <div class="raw-field"><span>방전감소계수</span><b>{{ na(typeDetail.score_detail.disch_dec_coef, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>온도감소계수</span><b>{{ na(typeDetail.score_detail.temp_dec_coef, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>SOH 감점</span><b class="neg">{{ na(typeDetail.score_detail.soh_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>BMS사용수명</span><b>{{ na(typeDetail.score_detail.bms_life, { digits: 1, unit: "년" }) }}</b></div>
          <div class="raw-field"><span>BMS고장확률상태점수</span><b>{{ na(typeDetail.score_detail.bms_stat, { digits: 4 }) }}</b></div>
          <div class="raw-field"><span>BMS고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.bms_minus, { digits: 1 }) }}</b></div>
        </div>
      </div>

      <div class="raw-subgroup">
        <div class="raw-subtitle">셀·배터리실</div>
        <div class="raw-fields">
          <div class="raw-field"><span>점검결과 반영일</span><b>{{ na(typeDetail.condition.measured_at) }}</b></div>
          <div class="raw-field"><span>셀간전압편차</span><b>{{ na(typeDetail.condition.vol_diff) }}</b></div>
          <div class="raw-field"><span>셀간전압편차 감점</span><b class="neg">{{ na(typeDetail.score_detail.vol_diff_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>셀간온도편차</span><b>{{ na(typeDetail.condition.temp_diff) }}</b></div>
          <div class="raw-field"><span>셀간온도편차 감점</span><b class="neg">{{ na(typeDetail.score_detail.temp_diff_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>셀온도범위초과이력</span><b>{{ na(typeDetail.condition.temp_range_over) }}</b></div>
          <div class="raw-field"><span>셀온도범위초과이력 감점</span><b class="neg">{{ na(typeDetail.score_detail.temp_range_over_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>배터리실온도</span><b>{{ na(typeDetail.condition.bat_room_temp, { unit: "℃" }) }}</b></div>
          <div class="raw-field"><span>배터리실온도 감점</span><b class="neg">{{ na(typeDetail.score_detail.bat_room_temp_minus, { digits: 1 }) }}</b></div>
          <div class="raw-field"><span>배터리실습도</span><b>{{ na(typeDetail.condition.bat_room_humid, { unit: "%" }) }}</b></div>
          <div class="raw-field"><span>배터리실습도 감점</span><b class="neg">{{ na(typeDetail.score_detail.bat_room_humid_minus, { digits: 1 }) }}</b></div>
        </div>
      </div>
    </div>
  </div>

  <div class="raw-group">
    <div class="raw-title">COF(고장영향성) 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>정격용량</span><b>{{ na(typeDetail.spec.capa, { locale: true }) }}</b></div>
      <div class="raw-field"><span>부하율</span><b>{{ na(typeDetail.condition.load, { unit: "%" }) }}</b></div>
      <div class="raw-field"><span>부하량</span><b>{{ na(typeDetail.score_detail.capa_times_load, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>사고영향성 감점</span><b class="neg">{{ na(typeDetail.score_detail.capa_times_load_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>연결설비</span><b>{{ na(typeDetail.consequence.con_rank) }}</b></div>
      <div class="raw-field"><span>연결설비 감점</span><b class="neg">{{ na(typeDetail.score_detail.con_rank_minus, { digits: 1 }) }}</b></div>
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
    <div class="raw-title">DOF(고장예방력) 구성</div>
    <div class="raw-fields">
      <div class="raw-field"><span>모델세대</span><b>{{ na(typeDetail.design.model_gen) }}</b></div>
      <div class="raw-field"><span>모델세대 감점</span><b class="neg">{{ na(typeDetail.score_detail.model_gen_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>화재방지</span><b>{{ na(typeDetail.design.fire_resist) }}</b></div>
      <div class="raw-field"><span>화재방지 감점</span><b class="neg">{{ na(typeDetail.score_detail.fire_resist_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>UL인증</span><b>{{ na(typeDetail.design.ul_auth) }}</b></div>
      <div class="raw-field"><span>UL인증 감점</span><b class="neg">{{ na(typeDetail.score_detail.ul_auth_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>설비신뢰도등급</span><b>{{ na(typeDetail.design.fac_rel) }}</b></div>
      <div class="raw-field"><span>설비신뢰도 감점</span><b class="neg">{{ na(typeDetail.score_detail.fac_rel_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>부품상태진단(온라인)</span><b>{{ na(typeDetail.design.part_stat_diag) }}</b></div>
      <div class="raw-field"><span>부품상태진단(온라인) 감점</span><b class="neg">{{ na(typeDetail.score_detail.part_stat_diag_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>배터리서버</span><b>{{ na(typeDetail.design.bat_server) }}</b></div>
      <div class="raw-field"><span>배터리서버 감점</span><b class="neg">{{ na(typeDetail.score_detail.bat_server_minus, { digits: 1 }) }}</b></div>
      <div class="raw-field"><span>배터리실소화설비</span><b>{{ na(typeDetail.design.bat_room_fire_resist) }}</b></div>
      <div class="raw-field"><span>배터리실소화설비 감점</span><b class="neg">{{ na(typeDetail.score_detail.bat_room_fire_resist_minus, { digits: 1 }) }}</b></div>
    </div>
  </div>
</template>
