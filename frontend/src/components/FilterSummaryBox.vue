<script setup lang="ts">
import { computed } from "vue";
import { summarizeRow } from "../utils/filterSummary";
import { typeLabel } from "../utils/formatValue";

// 메인 화면 위 오른쪽 — 사업장·설비유형 선택을 각각 한 행으로(2026-11-19 시안 D, 로그인 카드 왼쪽).
// 행마다 한 줄 고정: 사업장은 4곳, 설비유형은 3개까지 보이고 나머지는 "외 N"(마우스를 올리면 전체 목록).
const props = defineProps<{
  factories: string[];
  types: string[];
  typeNames: Record<string, string>;
}>();

const factoryRow = computed(() => summarizeRow(props.factories, 4));
const typeRow = computed(() => summarizeRow(props.types.map((code) => ({ code, name: props.typeNames[code] ?? "" })), 3));
const factoryTitle = computed(() => (props.factories.length ? props.factories.join(", ") : "전체 사업장"));
const typeTitle = computed(() =>
  props.types.length ? props.types.map((c) => typeLabel(props.typeNames[c], c)).join(", ") : "전체 설비유형",
);
</script>

<template>
  <dl class="fsb" aria-label="현재 선택한 사업장과 설비유형">
    <dt>사업장</dt>
    <dd :title="factoryTitle">
      <span v-if="factoryRow.all" class="fsb-all">전체</span>
      <template v-else>
        <span class="fsb-list">{{ factoryRow.shown.join(", ") }}</span>
        <span v-if="factoryRow.rest" class="fsb-rest">외 {{ factoryRow.rest }}</span>
      </template>
    </dd>
    <dt>설비유형</dt>
    <dd :title="typeTitle">
      <span v-if="typeRow.all" class="fsb-all">전체</span>
      <template v-else>
        <span class="fsb-list">
          <template v-for="(t, i) in typeRow.shown" :key="t.code">{{ i > 0 ? ", " : "" }}{{ t.name || t.code }}<small v-if="t.name" class="fsb-code">{{ t.code }}</small></template>
        </span>
        <span v-if="typeRow.rest" class="fsb-rest">외 {{ typeRow.rest }}</span>
      </template>
    </dd>
  </dl>
</template>

<style scoped>
.fsb {
  margin: 0;
  width: 360px;
  min-width: 220px;
  flex: 0 1 360px;
  box-sizing: border-box;
  height: 56px;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 6px 12px;
  display: grid;
  grid-template-columns: 60px minmax(0, 1fr);
  align-content: center;
  row-gap: 2px;
  font-size: 12px;
  line-height: 1.6;
}
dt {
  font-weight: 600;
  color: #6b7480;
}
dd {
  margin: 0;
  display: flex;
  gap: 4px;
  min-width: 0;
  font-weight: 600;
  color: #1a2230;
  white-space: nowrap;
}
.fsb-list {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.fsb-all {
  color: #4a5361;
}
.fsb-code {
  margin-left: 3px;
  font-size: 11px;
  color: #6b7480;
}
.fsb-rest {
  flex: 0 0 auto;
  color: #0b7474;
}
</style>
