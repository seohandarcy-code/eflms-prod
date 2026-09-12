# frontend

Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus. 상위 저장소 규칙(계획 승인 필수 등)은 루트 `CLAUDE.md`를 따른다.

## 실행

로컬/운영 Node 버전을 22 LTS로 통일하기로 했으므로(`.nvmrc` 참고), 시스템에 다른 Node가 깔려 있어도 이 프로젝트는 아래 로컬 바이너리를 사용한다:

```bash
cd frontend
export PATH="C:\system_work\eflms_dev\.tools\node-v22.23.2-win-x64:$PATH"
npm install       # 최초 1회
cp .env.example .env
npm run dev
```

## 구조

- `src/router/` — vue-router
- `src/stores/` — Pinia 스토어
- `src/views/` — 화면 단위 컴포넌트 (`DashboardView.vue`는 Stage C-5에서 채움)
- `src/api/client.ts` — axios 인스턴스, `VITE_API_BASE_URL` 사용

## 컨벤션

- 화면 구성은 `design/Main.dc.html`에 확정된 Direction A를 따른다.
- 시크릿/환경별 값은 `.env`로만 주입한다.
