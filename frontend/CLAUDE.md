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

## 컨벤션

- `design/Main.dc.html`은 최초 승인 방향(Direction A)을 담은 2026-09-14 시점 목업이며, 그 이후 화면은 목업 갱신 없이 코드에서 직접 반복 개선해왔다(이력은 `docs/ROADMAP.md` 참고). 현재 화면의 정본은 실제 구현 코드(`src/views/`, `src/components/`)다.
- 시크릿/환경별 값은 `.env`로만 주입한다.
