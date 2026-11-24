<script setup lang="ts">
import { computed } from "vue";
import katex from "katex";
import "katex/dist/katex.min.css";

// LaTeX 수식 한 줄(지표설명 상세 페이지, Stage 22-11). KaTeX 글꼴은 빌드에 같이 묶여 사내망에서도 외부 접속이 없다.
// 수식 문자열은 백엔드 FORMULA_DOCS(코드에 적힌 고정 문구)에서만 온다. 한글은 \text{} 안에 쓴다.
const props = withDefaults(defineProps<{ tex: string; display?: boolean }>(), { display: true });

const html = computed(() =>
  katex.renderToString(props.tex, {
    displayMode: props.display,
    throwOnError: false, // 잘못된 식은 빨간 원문으로 보여주고 페이지는 계속 그린다
    strict: "ignore", // \text{} 안 한글 경고 끔
    trust: false,
  }),
);
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- KaTeX 출력(trust: false, 입력은 서버 고정 문구) -->
  <span class="math-tex" :class="{ block: display }" v-html="html"></span>
</template>

<style scoped>
.math-tex.block {
  display: block;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 0;
}
.math-tex :deep(.katex-display) {
  margin: 0;
  text-align: left;
}
.math-tex :deep(.katex) {
  font-size: 1.08em;
}
</style>
