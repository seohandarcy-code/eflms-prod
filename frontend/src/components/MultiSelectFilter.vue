<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

const props = defineProps<{
  label: string;
  options: { value: string; label: string }[];
  modelValue: string[];
  allLabel?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [values: string[]] }>();

const open = ref(false);
const rootEl = ref<HTMLDivElement | null>(null);

const summary = computed(() => {
  if (props.modelValue.length === 0) return props.allLabel ?? `전체 ${props.label}`;
  if (props.modelValue.length <= 2) {
    return props.options
      .filter((o) => props.modelValue.includes(o.value))
      .map((o) => o.label)
      .join(", ");
  }
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
    <div class="msf-title">{{ label }}</div>
    <button type="button" class="msf-trigger" :class="{ open }" @click="open = !open">
      <span class="msf-summary">{{ summary }}</span>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :style="{ transform: open ? 'rotate(180deg)' : 'none' }">
        <path d="M6 9 L12 15 L18 9" />
      </svg>
    </button>
    <div v-if="open" class="msf-panel">
      <label v-for="opt in options" :key="opt.value" class="msf-option">
        <input type="checkbox" :checked="modelValue.includes(opt.value)" @change="toggle(opt.value)" />
        {{ opt.label }}
      </label>
      <button v-if="modelValue.length > 0" type="button" class="msf-clear" @click="clearAll">전체 해제</button>
    </div>
  </div>
</template>

<style scoped>
.msf {
  position: relative;
}
.msf-title {
  font: 600 13px "IBM Plex Sans", sans-serif;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
  margin-bottom: 8px;
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
