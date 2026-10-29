<script setup lang="ts">
// EF4(수배전반) 상세 본문 (Stage 10-4). Ef1~Ef3DetailBody.vue와 같은 틀:
// part="compact": 패널 왼쪽 요약 4줄 / part="raw": "원본 데이터 전체 보기" 펼침 영역.
// 다른 유형처럼 POF·COF·DOF 구성 세 묶음만 두고, 축마다 원본 계산 툴의 소계(PoF 내구성·열적·물리적 /
// CoF 계통·비용·기간 / DoF 계통·비용·복구시간)로 나눠 보여준다. 설치위치는 POF 구성의 첫 소그룹(2026-10-29).
// 스타일은 부모 패널이 :deep()으로 입힌다.
import type { Ef4TypeDetail } from "../../types/equipment";
import { na } from "../../utils/formatValue";

defineProps<{ typeDetail: Ef4TypeDetail; part: "compact" | "raw" }>();
</script>

<template>
  <template v-if="part === 'compact'">
    <div class="compact-row">
      <span class="compact-label">설치위치</span>
      <span class="compact-value mono">{{ na(typeDetail.spec.eqp_building) }} {{ na(typeDetail.spec.eqp_floor) }} · {{ na(typeDetail.spec.eqp_disting) }}</span>
    </div>
    <div class="compact-row">
      <span class="compact-label">온도·부하</span>
      <span class="compact-value mono">CLIP {{ na(typeDetail.condition.max_temp_chk, { unit: "℃" }) }} · 부하율 {{ na(typeDetail.condition.load_chk, { scale: 100, digits: 0, unit: "%" }) }}</span>
    </div>
    <div class="compact-row">
      <span class="compact-label">점검상태</span>
      <span class="compact-value mono">열화 {{ na(typeDetail.condition.part_thermal_chk) }} · 외함 {{ na(typeDetail.condition.ex_box_chk) }} · BOLT {{ na(typeDetail.condition.bolt_chk) }}</span>
    </div>
    <div class="compact-row">
      <span class="compact-label">설계속성</span>
      <span class="compact-value mono">이중화 {{ na(typeDetail.design.reliability) }} · ATO {{ na(typeDetail.design.ato) }}</span>
    </div>
  </template>
  <template v-else>
    <div class="raw-group">
      <div class="raw-title">POF 구성</div>
      <div class="raw-subgrid">
        <div class="raw-subgroup">
          <div class="raw-subtitle">설치위치</div>
          <div class="raw-fields">
            <div class="raw-field"><span>eqp_id_명</span><b>{{ na(typeDetail.spec.eqp_id_name) }}</b></div>
            <div class="raw-field"><span>eqp-설치건물</span><b>{{ na(typeDetail.spec.eqp_building) }}</b></div>
            <div class="raw-field"><span>층</span><b>{{ na(typeDetail.spec.eqp_floor) }}</b></div>
            <div class="raw-field"><span>설비식별</span><b>{{ na(typeDetail.spec.eqp_disting) }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">내구성 (합계 {{ na(typeDetail.score_detail.durability_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>사용년수</span><b>{{ na(typeDetail.score_detail.operation_year, { unit: "년" }) }}</b></div>
            <div class="raw-field"><span>경과년수 감점</span><b class="neg">{{ na(typeDetail.score_detail.age_minus) }}</b></div>
            <div class="raw-field"><span>차단기상태점수</span><b>{{ na(typeDetail.score_detail.cb_stat, { digits: 4 }) }}</b></div>
            <div class="raw-field"><span>차단기고장확률 감점</span><b class="neg">{{ na(typeDetail.score_detail.cb_stat_minus) }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">열적 (합계 {{ na(typeDetail.score_detail.thermal_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>점검결과 반영일</span><b>{{ na(typeDetail.condition.measured_at) }}</b></div>
            <div class="raw-field"><span>각종부품열화여부</span><b>{{ na(typeDetail.condition.part_thermal_chk) }}</b></div>
            <div class="raw-field"><span>각종부품열화여부 감점</span><b class="neg">{{ na(typeDetail.score_detail.part_thermal_chk_minus) }}</b></div>
            <div class="raw-field"><span>전기실평균온도</span><b>{{ na(typeDetail.condition.elec_room_avg_temp, { unit: "℃" }) }}</b></div>
            <div class="raw-field"><span>전기실온도 감점</span><b class="neg">{{ na(typeDetail.score_detail.elec_room_avg_temp_minus) }}</b></div>
            <div class="raw-field"><span>각상별온도편차</span><b>{{ na(typeDetail.condition.temp_diff_chk, { unit: "℃" }) }}</b></div>
            <div class="raw-field"><span>각상별온도편차 감점</span><b class="neg">{{ na(typeDetail.score_detail.temp_diff_chk_minus) }}</b></div>
            <div class="raw-field"><span>차단기CLIP최고온도</span><b>{{ na(typeDetail.condition.max_temp_chk, { unit: "℃" }) }}</b></div>
            <div class="raw-field"><span>차단기CLIP최고온도 감점</span><b class="neg">{{ na(typeDetail.score_detail.max_temp_chk_minus) }}</b></div>
            <div class="raw-field"><span>부하율</span><b>{{ na(typeDetail.condition.load_chk, { scale: 100, digits: 0, unit: "%" }) }}</b></div>
            <div class="raw-field"><span>부하율 감점</span><b class="neg">{{ na(typeDetail.score_detail.load_minus) }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">물리적 (합계 {{ na(typeDetail.score_detail.phy_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>외함정상상태확인</span><b>{{ na(typeDetail.condition.ex_box_chk) }}</b></div>
            <div class="raw-field"><span>외함정상상태확인 감점</span><b class="neg">{{ na(typeDetail.score_detail.ex_box_chk_minus) }}</b></div>
            <div class="raw-field"><span>차단기소음</span><b>{{ na(typeDetail.condition.noise_chk) }}</b></div>
            <div class="raw-field"><span>차단기소음 감점</span><b class="neg">{{ na(typeDetail.score_detail.noise_chk_minus) }}</b></div>
            <div class="raw-field"><span>모선부(접촉부)BOLT풀림</span><b>{{ na(typeDetail.condition.bolt_chk) }}</b></div>
            <div class="raw-field"><span>BOLT풀림 감점</span><b class="neg">{{ na(typeDetail.score_detail.bolt_chk_minus) }}</b></div>
          </div>
        </div>
      </div>
    </div>

    <div class="raw-group">
      <div class="raw-title">COF 구성</div>
      <div class="raw-subgrid">
        <div class="raw-subgroup">
          <div class="raw-subtitle">계통 (합계 {{ na(typeDetail.score_detail.cof_sys_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>피해규모</span><b>{{ na(typeDetail.consequence.scale_dam_chk) }}</b></div>
            <div class="raw-field"><span>피해규모 감점</span><b class="neg">{{ na(typeDetail.score_detail.scale_dam_chk_minus) }}</b></div>
            <div class="raw-field"><span>설치건물</span><b>{{ na(typeDetail.spec.install_building) }}</b></div>
            <div class="raw-field"><span>설치건물 감점</span><b class="neg">{{ na(typeDetail.score_detail.install_building_minus) }}</b></div>
            <div class="raw-field"><span>공급계통</span><b>{{ na(typeDetail.consequence.sup_sys_chk) }}</b></div>
            <div class="raw-field"><span>공급계통 감점</span><b class="neg">{{ na(typeDetail.score_detail.sup_sys_chk_minus) }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">비용 (합계 {{ na(typeDetail.score_detail.cof_cost_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>생산/비생산</span><b>{{ na(typeDetail.consequence.prod_chk) }}</b></div>
            <div class="raw-field"><span>생산/비생산 감점</span><b class="neg">{{ na(typeDetail.score_detail.prod_chk_minus) }}</b></div>
            <div class="raw-field"><span>상시가동여부</span><b>{{ na(typeDetail.consequence.op_chk) }}</b></div>
            <div class="raw-field"><span>상시가동여부 감점</span><b class="neg">{{ na(typeDetail.score_detail.op_chk_minus) }}</b></div>
            <div class="raw-field"><span>교체비용</span><b>{{ na(typeDetail.consequence.replace_chk) }}</b></div>
            <div class="raw-field"><span>교체비용 감점</span><b class="neg">{{ na(typeDetail.score_detail.replace_chk_minus) }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">기간 (합계 {{ na(typeDetail.score_detail.cof_recov_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>복구시부하정상동작시간</span><b>{{ na(typeDetail.consequence.recovery_time_chk) }}</b></div>
            <div class="raw-field"><span>복구시간 감점</span><b class="neg">{{ na(typeDetail.score_detail.recovery_time_chk_minus) }}</b></div>
            <div class="raw-field"><span>설비교체기간</span><b>{{ na(typeDetail.consequence.replace_time_chk) }}</b></div>
            <div class="raw-field"><span>설비교체기간 감점</span><b class="neg">{{ na(typeDetail.score_detail.replace_time_chk_minus) }}</b></div>
          </div>
        </div>
      </div>
    </div>

    <div class="raw-group">
      <div class="raw-title">DOF 구성</div>
      <div class="raw-subgrid">
        <div class="raw-subgroup">
          <div class="raw-subtitle">계통 (합계 {{ na(typeDetail.score_detail.dof_sys_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>공급신뢰도(이중화여부)</span><b>{{ na(typeDetail.design.reliability) }}</b></div>
            <div class="raw-field"><span>공급신뢰도 감점</span><b class="neg">{{ na(typeDetail.score_detail.reliability_minus) }}</b></div>
            <div class="raw-field"><span>ATO구성여부</span><b>{{ na(typeDetail.design.ato) }}</b></div>
            <div class="raw-field"><span>ATO구성여부 감점</span><b class="neg">{{ na(typeDetail.score_detail.ato_minus) }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">비용 (합계 {{ na(typeDetail.score_detail.dof_cost_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>차단기정밀점검</span><b>{{ na(typeDetail.design.cb_inspect) }}</b></div>
            <div class="raw-field"><span>차단기정밀점검 감점</span><b class="neg">{{ na(typeDetail.score_detail.cb_inspect_minus) }}</b></div>
            <div class="raw-field"><span>계전기점검</span><b>{{ na(typeDetail.design.relay_chk) }}</b></div>
            <div class="raw-field"><span>계전기점검 감점</span><b class="neg">{{ na(typeDetail.score_detail.relay_chk_minus) }}</b></div>
            <div class="raw-field"><span>온라인진단</span><b>{{ na(typeDetail.design.online_diag) }}</b></div>
            <div class="raw-field"><span>온라인진단 감점</span><b class="neg">{{ na(typeDetail.score_detail.online_diag_minus) }}</b></div>
          </div>
        </div>

        <div class="raw-subgroup">
          <div class="raw-subtitle">복구시간 (합계 {{ na(typeDetail.score_detail.dof_recov_minus) }})</div>
          <div class="raw-fields">
            <div class="raw-field"><span>부품단종여부</span><b>{{ na(typeDetail.design.part_shortage) }}</b></div>
            <div class="raw-field"><span>부품단종여부 감점</span><b class="neg">{{ na(typeDetail.score_detail.part_shortage_minus) }}</b></div>
            <div class="raw-field"><span>설치년도</span><b>{{ na(typeDetail.score_detail.operation_start_year) }}</b></div>
            <div class="raw-field"><span>관통형CT적용</span><b>{{ na(typeDetail.score_detail.ct_use) }}</b></div>
            <div class="raw-field"><span>관통형CT적용 감점</span><b class="neg">{{ na(typeDetail.score_detail.ct_use_minus) }}</b></div>
            <div class="raw-field"><span>장수명fan적용</span><b>{{ na(typeDetail.score_detail.longlife_fan_use) }}</b></div>
            <div class="raw-field"><span>조명등개선품적용</span><b>{{ na(typeDetail.score_detail.lighting_use) }}</b></div>
            <div class="raw-field"><span>스펙강화 감점</span><b class="neg">{{ na(typeDetail.score_detail.spec_use_minus) }}</b></div>
          </div>
        </div>
      </div>
    </div>
  </template>
</template>
