# frontend

Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus. 상위 저장소 규칙(계획 승인 필수 등)은 루트 `CLAUDE.md`를 따른다.

## 실행

로컬/운영 Node 버전을 22 LTS로 통일하기로 했음(`.nvmrc` 참고). 시스템에 다른 Node 버전이 이미 깔려 있어도 이 프로젝트에서는 22를 써야 함 — `nvm`(nvm-windows 등)으로 버전을 맞추는 걸 권장:

```bash
cd frontend
nvm install 22   # 최초 1회 (버전 관리자에 22가 없을 때만)
nvm use 22
npm install       # 최초 1회
cp .env.example .env
npm run dev
```

`nvm-windows` 사용 시 `nvm use`가 심볼릭 링크 생성을 위해 관리자 승인(UAC)을 요구할 수 있음 — Windows 개발자 모드를 켜두면 매번 승인 없이 동작함(설정 > 개인정보 및 보안 > 개발자용).

## 구조

- `src/router/` — vue-router
- `src/stores/` — Pinia 스토어
- `src/views/` — 화면 단위 컴포넌트 (`DashboardView.vue` 메인 대시보드, `GuideView.vue` — POF/COF/DOF 지표·판정기준 안내 `/guide`)
- `src/api/client.ts` — axios 인스턴스, `VITE_API_BASE_URL` 사용
- `src/components/detail/` — 설비유형별 상세 본문(`Ef1DetailBody.vue` ~ `Ef4DetailBody.vue`). `EquipmentDetailPanel.vue`는 공통 헤더·점수·차트만 갖고, `type_detail.ef_code`로 본문을 고른다. 본문 클래스(`compact-row`, `raw-*`) 스타일은 패널이 `:deep()`으로 입힌다.

## 설비유형 (Stage 8-5)

- 유형 목록과 감점 항목 라벨은 `/api/equipment-types`(스토어 `equipmentTypes`, `breakdownFor(ef_code)`)에서 온다 — `utils/scoreBreakdown.ts`에 라벨을 하드코딩하지 않는다. 근거 툴팁 문구만 유형별 맵(`EF1_EVIDENCE` ~ `EF4_EVIDENCE`)으로 둔다.
- 공통 표시(점검필요 순위, 상세 패널 헤더, 설비목록 카드·리스트)는 모든 유형에 있는 값만 쓴다 — 전압 대신 가동년월(`utils/formatDate.ts`의 `formatMonth`, 2026-10-29 Stage 10-0). 유형별 값(예: EF1 1차전압)은 각 `EfNDetailBody.vue`에 둔다.
- 새 설비유형을 붙일 때: `types/equipment.ts`에 `EfNTypeDetail` 추가(→ `TypeDetail` union), `components/detail/EfNDetailBody.vue`, `scoreBreakdown.ts`의 근거 맵, 패널 헤더 부제(`typeSubtitle`), 가이드의 계산 방법 설명(`utils/typeGuide.ts`의 `TYPE_GUIDES` — 없으면 가이드에 항목 목록만 나옴). 필터·KPI·분포도·가이드 항목 목록은 메타데이터로 자동 반영된다.
- 화면 라벨은 원본(`ref_data`) 라벨 표현을 따른다 — 원본에 없는 용어(예: 계산식 이름)를 라벨에 덧붙이지 않는다. 계산식 설명은 가이드(`typeGuide.ts`)에 둔다(2026-10-19, GIS 라벨의 "(와이블)" 제거).
- 점수는 원본 공식대로 음수가 될 수 있다 — 막대·분포도는 표시만 0~100으로 자른다.

## 컨벤션

- `design/Main.dc.html`은 최초 승인 방향(Direction A)을 담은 2026-09-14 시점 목업이며, 그 이후 화면은 목업 갱신 없이 코드에서 직접 반복 개선해왔다(이력은 `docs/ROADMAP.md` 참고). 현재 화면의 정본은 실제 구현 코드(`src/views/`, `src/components/`)다.
- 시크릿/환경별 값은 `.env`로만 주입한다.
