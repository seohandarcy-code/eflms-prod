<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

const props = defineProps<{
  label: string;
  // sub: 이름 뒤에 작게 붙일 글자(예: 설비유형 코드 "EF1")
  options: { value: string; label: string; sub?: string }[];
  modelValue: string[];
  allLabel?: string;
  // 선택지가 하나도 없을 때 목록에 흐리게 보여 줄 문구(예: 사업장 필터 — 받아 둔 설비가 없을 때).
  emptyText?: string;
  // 제목 옆 "?" 안내 링크(Stage 17 — 설비유형 필터 → 설비 안내 페이지). 없으면 표시하지 않는다.
  helpTo?: string;
  helpTitle?: string;
  helpCaption?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [values: string[]] }>();

const open = ref(false);
const rootEl = ref<HTMLDivElement | null>(null);

// 1~2개 골랐으면 고른 항목을 그대로(작은 글자 포함), 그 외에는 문구 하나.
const summaryItems = computed(() =>
  props.modelValue.length >= 1 && props.modelValue.length <= 2 ? props.options.filter((o) => props.modelValue.includes(o.value)) : [],
);
const summary = computed(() => {
  if (props.modelValue.length === 0) return props.allLabel ?? `전체 ${props.label}`;
  return `${props.modelValue.length}개 선택`;
});

function toggle(value: string) {
  const set = new Set(props.modelValue);
  if (set.has(value)) set.delete(value);
  else set.add(value);
  emit("update:modelValue", Array.from(set));
}

function clearAll() {
  emit("update:modelValue", []);
}

function onDocMouseDown(event: MouseEvent) {
  if (rootEl.value && !rootEl.value.contains(event.target as Node)) open.value = false;
}

onMounted(() => document.addEventListener("mousedown", onDocMouseDown));
onUnmounted(() => document.removeEventListener("mousedown", onDocMouseDown));
</script>

<template>
  <div ref="rootEl" class="msf">
    <div class="msf-title">
      {{ label }}
      <span v-if="helpTo" class="msf-help-wrap">
        <RouterLink :to="helpTo" class="msf-help" :aria-label="helpTitle ?? `${label} 안내 보기`">?</RouterLink>
        <span class="msf-tooltip" role="tooltip">
          <span class="msf-tooltip-title">{{ helpTitle ?? `${label} 안내 보기` }}</span>
          <span v-if="helpCaption" class="msf-tooltip-caption">{{ helpCaption }}</span>
        </span>
      </span>
    </div>
    <button type="button" class="msf-trigger" :class="{ open }" @click="open = !open">
      <span class="msf-summary">
        <template v-if="summaryItems.length">
          <template v-for="(o, i) in summaryItems" :key="o.value">{{ i > 0 ? ", " : "" }}{{ o.label }}<small v-if="o.sub" class="msf-sub">{{ o.sub }}</small></template>
        </template>
        <template v-else>{{ summary }}</template>
      </span>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :style="{ transform: open ? 'rotate(180deg)' : 'none' }">
        <path d="M6 9 L12 15 L18 9" />
      </svg>
    </button>
    <div v-if="open" class="msf-panel">
      <div v-if="options.length === 0 && emptyText" class="msf-empty">{{ emptyText }}</div>
      <label v-for="opt in options" :key="opt.value" class="msf-option">
        <input type="checkbox" :checked="modelValue.includes(opt.value)" @change="toggle(opt.value)" />
        {{ opt.label }}<small v-if="opt.sub" class="msf-sub">{{ opt.sub }}</small>
      </label>
      <button v-if="modelValue.length > 0" type="button" class="msf-clear" @click="clearAll">전체 해제</button>
    </div>
  </div>
</template>

<style scoped>
.msf {
  position: relative;
}
.msf-empty {
  padding: 6px 4px;
  font-size: 13px;
  color: #9aa2b1;
}
.msf-title {
  font: 600 13px "IBM Plex Sans", sans-serif;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
  margin-bottom: 8px;
}
.msf-help-wrap {
  position: relative;
  display: inline-block;
  vertical-align: middle;
}
.msf-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: 4px;
  border-radius: 50%;
  border: 1px solid #1b8a5a;
  color: #1b8a5a;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  text-decoration: none;
  background: #fff;
}
.msf-help:hover,
.msf-help:focus-visible {
  background: #1b8a5a;
  color: #fff;
}
.msf-tooltip {
  position: absolute;
  z-index: 7;
  top: calc(100% + 8px);
  left: -60px;
  width: 210px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #fff;
  border: 1px solid #1b8a5a;
  border-radius: 9px;
  padding: 10px 12px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
  text-transform: none;
  letter-spacing: 0;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.12s ease;
  pointer-events: none;
}
.msf-help-wrap:hover .msf-tooltip,
.msf-help-wrap:focus-within .msf-tooltip {
  opacity: 1;
  visibility: visible;
}
.msf-tooltip-title {
  font-size: 12px;
  font-weight: 700;
  color: #1a2230;
}
.msf-tooltip-caption {
  font-size: 11px;
  font-weight: 500;
  color: #8891a0;
  line-height: 1.5;
}
.msf-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  background: #fff;
  padding: 7px 10px;
  font: 500 13px "IBM Plex Sans", sans-serif;
  color: #1a2230;
  cursor: pointer;
}
.msf-trigger.open {
  border-color: #0f8a8a;
}
.msf-trigger svg {
  flex: 0 0 auto;
  color: #8891a0;
  transition: transform 0.15s ease;
}
.msf-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}
.msf-panel {
  position: absolute;
  z-index: 6;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.msf-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px;
  border-radius: 5px;
  font-size: 13px;
  color: #1a2230;
  cursor: pointer;
}
.msf-sub {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #8891a0;
}
.msf-option:hover {
  background: #f4f5f7;
}
.msf-option input {
  accent-color: #1a2230;
}
.msf-clear {
  margin-top: 4px;
  border: none;
  background: none;
  color: #8891a0;
  font-size: 12px;
  text-align: left;
  padding: 4px 6px;
  cursor: pointer;
}
.msf-clear:hover {
  color: #c4392b;
}
</style>
