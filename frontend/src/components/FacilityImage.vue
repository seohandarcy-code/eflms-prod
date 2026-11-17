<script setup lang="ts">
import type { FacilityInfo } from "../utils/facilityInfo";

// 설비 사진 한 장. animated면 움직이는 사진을 브라우저 상황에 맞게 고른다:
// 움직임 줄이기 설정 → 정지 PNG, 그 외 → 움직이는 WebP, WebP를 못 쓰는 브라우저 → GIF.
// 움직이는 사진을 받는 동안 빈칸이 보이지 않게 정지 PNG를 배경으로 깔아 둔다.
// 크기·테두리는 부모가 이 컴포넌트에 준 class로 정한다(사진은 그 안을 contain으로 채움).
defineProps<{
  info: FacilityInfo;
  alt: string;
  animated?: boolean;
  lazy?: boolean;
}>();
</script>

<template>
  <picture class="fi">
    <template v-if="animated">
      <source :srcset="info.image" media="(prefers-reduced-motion: reduce)" />
      <source :srcset="info.animatedWebp" type="image/webp" />
    </template>
    <img
      class="fi-img"
      :src="animated ? info.animated : info.image"
      :alt="alt"
      :loading="lazy ? 'lazy' : undefined"
      :style="animated ? { backgroundImage: `url(${info.image})` } : undefined"
    />
  </picture>
</template>

<style scoped>
.fi {
  display: block;
  overflow: hidden;
}
.fi-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background-position: center;
  background-size: contain;
  background-repeat: no-repeat;
}
</style>
