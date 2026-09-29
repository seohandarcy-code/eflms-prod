# 로드맵

## Phase 1 — 완료: mock 데이터 기반 대시보드 (EF1 한정)

- [x] C-1 스캐폴딩 (backend/frontend, `/healthz`, 각 `CLAUDE.md`)
- [x] C-2 DB 모델 + 초기 Alembic 마이그레이션
- [x] C-3 EF1 계산기 이식(`ef1_transformer.py`) + 공용 적재 매퍼(`ingest.py`) + 시드 스크립트(`seed.py`)
- [x] C-4 최소 API (`/api/equipment`, `/api/equipment/{id}`, `/api/summary`)
- [x] C-5 Vue 대시보드 구현 (Direction A: KPI, PoF·CoF·DoF 3축 분포도, 점검필요 순위/사유, 카드형 목록+인라인 상세확장) — 실제 API 연동
- [x] C-6 스모크 테스트(pytest 5개, vitest 9개, 전부 통과) + 실제 브라우저 확인(Claude in Chrome) — 확인 중 KPI가 사업장 필터를 무시하던 버그 발견 후 수정
- [x] 디자인 고도화(2026-09 세션): 3D 산점도를 회전 가능한 실제 3D(Plotly)로 교체, 정상범위 와이어프레임 + 커서 추적 호버 카드(문제 축 스포트라이트) + 기준까지 부족한 거리 투영선, 정상/점검필요 설비를 범례에서 독립적으로 켜고 끄는 토글, KPI를 전체/정상/점검필요/최근갱신 4분할, 점검필요 순위를 PoF/CoF/DoF 3열 감점사유로 재구성, 상세 패널에 원본 데이터 전체보기(PoF/CoF/DoF 3열), 선택 시 정상/점검필요 상태색으로 테두리 구분, PoF·CoF·DoF 표기를 POF·COF·DOF 대문자로 통일 등. 과정에서 3D 차트가 멈추는 버그(Plotly 네이티브 호버 렌더링 재진입)를 발견해 근본 원인을 고치고 커스텀 호버 오버레이로 전환.
- [x] 디자인 고도화 2차(2026-09 세션): 정상/점검필요 이진 판정 → **정상/교체검토/즉시교체 3단계 상태 체계**로 교체(COF·DOF가 둘 다 60 초과면 POF 기준 완화, 아니면 더 엄격한 기준 적용 — 계산 로직은 `equipment_service.classify_status`, 안내는 `/guide` 페이지에 문서화). 설비 목록에 검색/정렬/페이지네이션, 카드형/리스트형 뷰 전환, 사업장·설비유형 다중선택 필터(클라이언트 사이드)를 추가. 상세 패널에 신규 차트 2종(POF 분포 히스토그램, 5개년 종합점수 예측선, 순수 SVG 구현) 추가. 상단바 시그니처 컬러(아이콘 배지형) 적용, 사이트 전체 폰트 크기 정리.
- 인증 없음(자리만 확보), env는 최소 세트(`DATABASE_URL` 등)

## Phase 2 — 운영 데이터 연동

- [x] 사내 입력파일(.dat, 탭구분) 임포트 CLI — 알려진 컬럼 검증 + 미등록 컬럼 자동 캡처(`equipment_extra_attribute`) + 인코딩 자동판별(UTF-8/CP949) + 검증 실패 시 부분 반영 금지 (`backend/app/services/import_service.py`, 실행법은 `backend/CLAUDE.md` 참고)
- [ ] 임포트 이력/오류 리포트 화면 (현재는 CLI 콘솔 요약 + JSON 로그 한 줄뿐, 웹 화면 없음)
- [ ] 정기 실행 자동화 — 사내 입력파일이 실제로 들어오기 시작하면 `/schedule`로 주기 실행 전환 (루트 `CLAUDE.md`의 "루프/스케줄 활용 계획" 참고)

## Phase 3 — 보류: 설비유형 확장 (사내 데이터 확보 후 진행)

- EF2~EF22 순차 추가: 설비유형별 계산기 모듈 + 도메인 테이블 (기존 EF1 코드/테이블 불변)
- 대시보드에 설비유형 필터 실제 활성화
- **보류 사유(2026-09-13)**: EF2 이상 설비유형의 실제 입력 데이터가 아직 없어 계산기/스키마를 설계할 근거가 부족함. Phase 2를 먼저 진행하고, 사내에서 해당 데이터를 확보한 뒤 재착수한다.

## Phase 4 — 인프라 전환

> 사내 유사 프로젝트 `a-ims-prod`(SQLite→PostgreSQL 전환 + Nginx/K8s 배포를 이미 검증한 레포)의 구동 방식을 참고해 아래 순서로 진행. 단계별 실행 계획은 2026-09-29 세션에서 Stage 0~7로 합의됨(각 Stage 종료 시 검증 후 다음 단계 진행).

- [x] **DB 접속 설정 우선순위 로직 도입** (`backend/app/core/config.py`): `DATABASE_URL` 있으면 그대로 사용 → 없고 `DB_HOST` 있으면 `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` 조합으로 DSN 자동 조립(PDEP의 ConfigMap=host/port, Secret=user/password 분리 관리에 대응) → 둘 다 없으면 SQLite 폴백(fresh clone 기본 동작 유지)
- [x] (선택, opt-in) `AUTO_SEED_IF_EMPTY=true`일 때만 기동 시 DB가 비어있으면 mock 시드 자동 실행 — 기본값 false, 운영/공유 환경 동작에 영향 없음
- [x] PostgreSQL로 로컬 실전환 검증(2026-09-29, PostgreSQL 14로 진행 — role/db 분리 생성, `alembic upgrade head` 대상 확인, 기존 pytest 스위트 9개를 Postgres 대상으로 재실행해 통과 확인, 앱 기동까지 확인) — 검증 후에도 기본 개발 흐름은 SQLite 유지. 재현 절차는 `backend/CLAUDE.md` "PostgreSQL로 전환해서 개발하기" 참고. 실제 PDEP 목표 버전(17)으로의 재확인은 남아있음
- [x] Nginx 로컬 구성(2026-09-29): `nginx/nginx.conf.template` 신설 — 정적 파일 서빙(vite dev server 프록시) + `/api`·`/healthz` 내부 리버스 프록시만 담당(TLS 종료·외부 라우팅은 사내 PDEP Ingress가 처리 예정). `scripts/start-dev.ps1`/`stop-dev.ps1`로 backend+frontend+nginx 동시 기동/종료 정의(미뤄뒀던 "`run` 스킬"의 실체). 검증 중 두 가지 실제 버그를 고쳤다: ① 이 시스템의 vite가 `localhost`를 IPv6(`::1`)로 바인드해 nginx의 IPv4 프록시가 502를 내던 문제 → `vite.config.ts`에 `server.host: '127.0.0.1'` 고정, ② 프론트가 `VITE_API_BASE_URL`로 백엔드 절대 URL(`http://localhost:8000`)을 직접 호출해 nginx `/api` 프록시를 우회하던 문제 → 상대경로(`VITE_API_BASE_URL` 비움) + vite dev proxy(`/api`, `/healthz` → 8000)로 전환, nginx·vite 직접 접속 두 경로 모두 동일 코드로 동작하게 됨. 브라우저로 `:8080`(nginx 경유) 대시보드 정상 렌더링 확인, pytest 9개/vitest 10개 전부 통과
- [x] 포트 커스터마이즈(2026-09-29): 처음엔 `start-dev.ps1`이 포트를 하드코딩하고 `stop-dev.ps1`만 환경변수를 지원해 서로 어긋나는 문제가 있었음(실제로 재현해서 확인) → `backend/.env`의 `BACKEND_PORT`, `frontend/.env`의 `VITE_PORT`, `nginx/.env`의 `NGINX_PORT`를 유일한 원본으로 삼도록 통일. `scripts/_ports.ps1`(start/stop 공용 파싱 로직)이 세 파일을 읽고, `nginx.conf`는 `nginx.conf.template`에서 매 실행 시 값을 채워 생성(런타임 산출물, git 미포함), `vite.config.ts`는 `frontend/.env`(자기 포트)와 `backend/.env`(프록시 타겟)를 직접 읽음. 9001/9002/9003 커스텀 조합으로 start→브라우저 확인→stop→포트 해제, 기본값(8000/5173/8080) 회귀까지 전부 재현 검증
- [ ] 스냅샷 → 이력(시계열) 구조 전환: 각 입력 도메인 테이블의 `equipment_id` UNIQUE 제약 완화 + "최신값" 조회 뷰 추가
- [ ] PostgreSQL 전환 후 Alembic 마이그레이션이 여러 backend replica에서 동시 실행되지 않도록 하는 절차 확정
- [ ] PDEP 실연동 준비 체크리스트 문서화(접속정보·Secret 관리 방식은 사내 담당자 확인 필요, K8s 매니페스트 초안) — 실제 접속정보/시크릿 값은 `.env`/사내 Secret 관리로만 주입

## Phase 5 — 인증

> 마찬가지로 `a-ims-prod`가 이미 로컬 Keycloak으로 전체 생애주기까지 검증한 패턴을 참고. eflms는 현재 `AUTH_MODE=none`만 실제로 동작하고, `local`/`sso`는 자리만 있고 실제로 선택하면 `NotImplementedError`가 남(`backend/app/core/security.py`) — 아래는 이걸 실제로 채우는 순서.

- [x] **`AUTH_MODE=local` 실제 구현(2026-09-29)**: 관리자 단일 계정 로그인(`app/auth/state.py`의 `AdminAuthStore` — 메모리 세션, 시도 5회 실패 시 잠금, TTL). 게이트 대상은 "DB 테이블 조회 관리자 페이지"로 결정(`GET /api/admin/tables`, `/api/admin/tables/{table_name}` — 11개 테이블 화이트리스트, 조회 전용·편집 기능 없음). 프론트: 왼쪽 사이드바 하단에 항상 보이는 "관리자" 버튼 → `/admin` 라우트에서 비밀번호 입력(틀리면 데이터 비노출) → 테이블 목록/페이지네이션 조회(`AdminView.vue`). pytest 3개(로그인 성공/실패/잠금, 화이트리스트 밖 테이블 404, `AUTH_MODE=none`일 때 503) + 브라우저 전체 흐름(로그인 실패→성공→조회→로그아웃) 확인. SSO/사용자 구분(admin/viewer)은 다음 항목(Phase 5 SSO)에서 별도 진행
- [x] **`AUTH_MODE=sso` 코드 구현(Stage 6-1, 6-2, 2026-09-29)**: `allowed_users` DB 테이블(`sso_id`/`name`/`team`/`is_admin`, 마이그레이션 `3d49abc45e95`) + `app/auth/access_store.py`(CRUD, 마지막 admin 삭제/강등 방지 `LastAdminError`) + `app/auth/oidc.py`(`authlib`, `SSO_BROKER_CONFIGURED = bool(SSO_ISSUER_URL)`) + `GET /api/admin/sso/login`·`/sso/callback`(IdP 인증 성공 ≠ 접근 허용 — `allowed_users`에 등록된 `sso_id`만 세션 발급) + 브레이크글래스(`SSO_ADMIN_ALLOWLIST` → `upsert_bootstrap_admin`) + `require_session`(등록된 사람이면 테이블 조회 가능) / `require_admin`(is_admin 세션만 접근권한 관리 가능) 권한 분리 + `/api/admin/access-users` CRUD. pytest 4개 추가(SSO 미설정 시 503, 세션 권한 분리, CRUD) — 전체 22개 통과. **아직 안 된 것**: `SSO_ALLOW_LOCAL_LOGIN` 듀얼모드, 프론트 "접근 권한 관리" 화면, 로컬 Keycloak 실제 연동 검증
- [ ] `SSO_ALLOW_LOCAL_LOGIN` — 개발 중 듀얼모드: 브로커가 client_id를 아직 발급하지 않은 단계에서도 `AUTH_MODE=sso`에서 로컬 비밀번호 로그인을 같이 열어 관리자가 먼저 접근권한을 등록해둘 수 있게 함(기본값 false)
- [ ] 프론트 "접근 권한 관리" 화면 — `/admin`에 탭 추가(`AUTH_MODE=sso`일 때만 노출), `allowed_users` 등록/수정/삭제
- [ ] 로컬 Keycloak으로 전체 생애주기 검증(등록→로그인 가능→삭제→로그인 불가→재등록), 이후 PDEP 실제 SSO 브로커 연동

## 보류 중 (마지막 디자인 고도화 단계에서 재검토)

- **Three.js 기반 3D "설비 전시장" UI**: 사업장/설비를 선택하면 3D 공간에서 해당 설비를 보여주는 연출. 단순 대시보드가 자리잡은 뒤, 별도 디자인 단계에서 다시 논의.
