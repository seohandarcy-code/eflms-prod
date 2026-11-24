<script setup lang="ts">
// 안내 페이지 공통 머리글(Stage 17) — "설비 안내"(/guide/facilities), "지표 설명"(/guide), "계산식 상세"(/guide/formulas, Stage 22-11) 탭.
</script>

<template>
  <header class="guide-topbar">
    <div class="brand">
      <div class="brand-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
      </div>
      <div>
        <div class="title">안내</div>
        <div class="subtitle">처음 보는 분을 위한 설비·지표 설명</div>
      </div>
    </div>
    <nav class="tabs" aria-label="안내 페이지">
      <RouterLink to="/guide/facilities" class="tab" exact-active-class="active">설비 안내</RouterLink>
      <RouterLink to="/guide" class="tab" exact-active-class="active">지표 설명 (POF·COF·DOF)</RouterLink>
      <RouterLink to="/guide/formulas" class="tab" active-class="active">계산식 상세</RouterLink>
      <RouterLink to="/" class="back-link">← 대시보드로</RouterLink>
    </nav>
  </header>
</template>

<style scoped>
.guide-topbar {
  background: #fff;
  border-bottom: 1px solid #e2e5ea;
  padding: 24px 32px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.brand-icon {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: #0f8a8a;
  display: flex;
  align-items: center;
  justify-content: center;
}
.title {
  font-size: 24px;
  font-weight: 700;
}
.subtitle {
  font-size: 14px;
  color: #8891a0;
  margin-top: 4px;
}
.tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.tab {
  font-size: 13px;
  font-weight: 600;
  color: #4a5361;
  text-decoration: none;
  border-radius: 6px;
  padding: 7px 14px;
  white-space: nowrap;
}
.tab:hover {
  background: #f4f5f7;
}
.tab.active {
  background: #e6f3f3;
  color: #0b6f6f;
}
.back-link {
  margin-left: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #4a5361;
  text-decoration: none;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 7px 14px;
  white-space: nowrap;
}
.back-link:hover {
  background: #f4f5f7;
}
</style>
