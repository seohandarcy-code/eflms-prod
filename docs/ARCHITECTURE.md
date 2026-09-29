# 아키텍처

## DB 연결 및 확장

- SQLAlchemy(async) + Alembic 마이그레이션을 처음부터 사용. SQL 문법은 SQLite/PostgreSQL 모두에서 동작하는 표준 범위만 사용(SQLite 전용 함수 지양).
- 연결 문자열은 `DATABASE_URL` env 하나로 결정한다. 개발: `sqlite+aiosqlite:///...`, 운영(추후): `postgresql+asyncpg://...`. DB를 바꿔도 애플리케이션 코드는 변경하지 않는다.
- **(계획, Phase 4)** `DATABASE_URL` 하나뿐 아니라 `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` 조합도 지원하도록 확장 예정 — 사내 유사 프로젝트 `a-ims-prod`의 `_build_database_url()` 패턴 참고: ① `DATABASE_URL`이 있으면 그대로 사용 ② 없고 `DB_HOST`가 있으면 위 5개 값으로 DSN을 조립(PDEP이 ConfigMap=host/port/name, Secret=user/password로 나눠 주입하는 경우에 대응) ③ 둘 다 없으면 SQLite로 폴백. 사람이 완성된 DSN을 직접 관리하는 로컬 개발과, host/port/자격증명이 분리돼 주입되는 실제 배포 환경을 동시에 지원한다.
- Repository/Service 계층으로 라우터와 ORM 세부 구현을 분리한다.

## 데이터 모델

현재는 **스냅샷 구조**(설비 1대당 최신 값 1건)로 시작하고, 각 입력 도메인 테이블에는 처음부터 시점 컬럼(`measured_at` 등)을 넣어둔다 — 나중에 "설비당 유니크" 제약을 풀고 이력(시계열) 구조로 전환할 때 테이블 재설계 없이 제약 완화만으로 끝나도록 하기 위함이다.

**공통 레이어 (모든 설비유형 공통)**
- `equipment_type` — `ef_code`(PK), 설비종류명, 활성 여부
- `equipment` — `equipment_id`(surrogate PK, 자동증가), `factory_code`, `ef_code`(FK), `transformer_name`, `voltage`, `onan_val`, `onaf_val`, `operation_start_time`. `UNIQUE(factory_code, ef_code, transformer_name)` — 동일 설비 중복 등록 방지는 이 자연키 제약이 담당(식별/조회는 항상 `equipment_id`로).
- `score_snapshot` — `equipment_id`(FK, unique), `pof_minus`, `pof`, `cof_minus`, `cof`, `dof_minus`, `dof`, `total_score`, `computed_at`. 설비유형과 무관하게 모든 타입이 이 계약(PoF/CoF/DoF/종합점수)을 공유한다.

**EF1(변압기) 전용 도메인 테이블** — 입력값은 원본 그대로, 계산값은 별도 테이블로 분리해서 관리한다.
- 입력: `dga_reading`, `furan_reading`, `dielectric_test`, `oil_test`, `load_condition`, `periodic_inspection`, `design_attribute` (컬럼 상세는 [DATA_DICTIONARY.md](DATA_DICTIONARY.md) 참고)
- 계산: `transformer_score_detail` — EF1 전용 세부 감점 breakdown 전부(다른 설비유형이 생기면 `ef2_score_detail`처럼 별도 테이블을 추가하고 기존 테이블/코드는 건드리지 않는다)

**설비유형 확장 원칙**: EF2~EF22가 추가될 때는 새 도메인 테이블 + 새 계산기 모듈을 추가할 뿐, `equipment_type`/`equipment`/`score_snapshot` 공통 레이어와 기존 EF1 코드는 변경하지 않는다(개방-폐쇄 원칙).

## 계산 로직 — "설비 타입 계산기 레지스트리"

- `ref_data/schema_eflms.py`의 `INPUT_COLUMNS`/`CALCULATED_COLUMNS` 패턴을 설비 타입별 모듈로 일반화한다: `backend/app/equipment_types/ef1_transformer.py` (추후 `ef2_xxx.py` ...).
- 공통 인터페이스: `calculate(input) -> {pof, cof, dof, total_score, breakdown}`.
- `EF_code → 계산기` 매핑으로 라우팅. 계산은 데이터 적재(시드/임포트) 시점에 수행하고 결과를 `score_snapshot`/`*_score_detail`에 저장한다(매 조회마다 재계산하지 않음 — 성능·감사 추적 목적).

## 인증

- `AuthProvider` 인터페이스로 추상화. 지금은 무인증(또는 더미 로그인)으로 시작하되, FastAPI 의존성 자리(`get_current_user`류)만 미리 만들어 둔다.
- 토큰 클레임은 OIDC 클레임(`sub`, `email`, `roles`)과 유사하게 맞춰서, 추후 사내 SSO(OIDC) 연동 시 프론트/백엔드 변경을 최소화한다.
- `AUTH_MODE` env로 `none` → `local`(구현 완료, 2026-09-29) → `sso`(계획) 전환. `sso`를 선택하면 아직 `NotImplementedError`가 나는 자리 확보 상태(`backend/app/core/security.py` — 참고로 이 `get_current_user`/`AUTH_MODE` 일반 인증 자리와, 아래 `local` 모드로 실제 구현한 관리자 로그인은 서로 다른 코드 경로다. 일반 대시보드는 여전히 무인증 공개이며, `local`은 오직 `/admin`(DB 테이블 조회 전용 화면)만 게이트한다).
- **`local`(구현 완료)**: 관리자 단일 계정, 메모리 세션(TTL 8시간) + 로그인 시도 5회 실패 시 5분 잠금(`backend/app/auth/state.py`의 `AdminAuthStore`, a-ims-prod 패턴 그대로 채택). JWT 서명 없이 opaque 토큰(`secrets.token_urlsafe`)만 사용. 게이트 대상은 `GET/POST /api/admin/*`(로그인/로그아웃/테이블 목록·조회, `require_admin` 의존성) — 편집 기능 없음, 화이트리스트 11개 테이블 조회 전용.
- **(계획, Phase 5 다음 단계)** `sso`: OIDC(`authlib`). IdP 인증 성공이 곧 접근 허용은 아님 — `allowed_users` DB 테이블에 등록된 계정만 세션이 발급됨(관리자가 화면에서 직접 등록/삭제). `SSO_ADMIN_ALLOWLIST`(env)에 매칭되는 계정은 로그인마다 admin 권한이 자동 복구되는 브레이크글래스 — 전체 락아웃 방지용 안전망.
  - `SSO_ALLOW_LOCAL_LOGIN`: 개발 중 듀얼모드 — 브로커가 client_id를 아직 발급하지 않은 단계에서도 `sso` 모드에서 로컬 비밀번호 로그인을 같이 열어, 관리자가 먼저 들어가 SSO 계정을 등록해둘 수 있게 함(기본값 false).
  - `SSO_BROKER_CONFIGURED = bool(SSO_ISSUER_URL)`: `SSO_CLIENT_ID`/`SSO_CLIENT_SECRET` 없이 issuer URL만 발급하는 사내 브로커 방식에도 대응(authlib이 빈 client_secret/client_id를 이미 지원함을 소스로 확인됨).

## 데이터 적재 파이프라인 (시드 · 임포트 공용)

```
[데이터 소스]                              [공통 파이프라인]                         [저장]
mock 생성기(ref_data 로직 이식)     ─┐
                                       ├─▶ ingest_row(flat dict) 매퍼 ─▶ 도메인 입력 테이블 upsert
사내 입력파일(.dat, 탭구분 텍스트) ─┘        │                            ─▶ 계산기 재실행
                                              └───────────────────────────▶ score_snapshot / *_score_detail 갱신
```

- **공용 매퍼** `ingest_row(row: dict, session)` — mock 시드와 실제 파일 임포트가 동일 함수를 사용.
- **시드 스크립트** `backend/app/db/seed.py` — mock 생성기로 flat dict를 만들어 `ingest_row` 호출 (`--rows`, `--reset`).
- **파일 임포트** `backend/app/services/import_service.py` — 사내 입력 파일(탭 구분 텍스트, `.dat`)을 파싱해 flat dict로 만든 뒤 동일 파이프라인 호출. 실행은 CLI로 웹서버 기동과 분리(`python -m app.db.import_data --file ... --ef-code EF1`).
  - **인코딩**: UTF-8을 우선 시도하고 실패 시 CP949(EUC-KR)로 폴백 — 사내에서 받는 파일이 두 인코딩을 오갈 수 있음을 전제.
  - **컬럼 매칭**: 파일 헤더를 `name`(영문)과 매칭한다(사내 입력파일은 영문 헤더로만 옴을 확인함). `label`(한글)은 각 항목이 무엇인지 설명하는 문서/화면 표시용 메타데이터일 뿐, 매칭에는 쓰지 않는다. 매칭된 컬럼은 정의된 dtype으로 값 검증.
  - **미등록 컬럼**: 실패시키지 않고 `equipment_extra_attribute`(equipment_id, column_name, value, inferred_type, source_file, imported_at)에 자동 저장(타입은 int→float→date→string 순으로 추론) + 임포트 후 "미등록 컬럼 발견" 리포트. 정식 컬럼 승격은 수동(스키마 마이그레이션)으로만 진행.
  - **검증 실패 정책**: 파일 내 일부 행에 오류가 있으면 전체 임포트를 중단하고 문제 행을 상세 리포트로 표시(부분 반영 금지).
  - **임포트 단위**: 파일 1건 = 해당 EF_code 설비들의 전체 입력 스냅샷을 통째로 갱신.

## 프론트엔드

- Vue 3 + Vite + Pinia(상태관리) + Element Plus(UI 컴포넌트).
- [design/Main.dc.html](../design/Main.dc.html)은 최초 승인된 방향(Direction A: 관제실형 테이블 + PoF/CoF/DoF 3축 분포도 + 카드형 설비 목록)을 담은 2026-09-14 시점 목업으로, **그 이후 실제 화면 구현은 목업을 갱신하지 않고 코드에서 직접 반복 개선**해왔다(3단계 정상/교체검토/즉시교체 상태 체계, 검색·정렬·페이지네이션·리스트뷰, 다중선택 필터, 상세 패널 신규 차트 2종, `/guide` 안내 페이지 등 — 자세한 이력은 [ROADMAP.md](ROADMAP.md) Phase 1 참고). 즉 `design/*.dc.html`은 초기 승인 근거를 남긴 기록이고, **현재 화면의 정본은 `frontend/src/views/DashboardView.vue` 등 실제 구현 코드**다.

## API 문서화

- FastAPI가 자동 생성하는 OpenAPI 스펙을 프론트-백엔드 계약으로 사용한다. 별도의 API 문서를 손으로 관리하지 않는다.
- 필요 시 `openapi-typescript`로 Vue 쪽 요청/응답 타입을 OpenAPI 스펙에서 자동 생성하는 방안을 Stage C 착수 시점에 결정한다(도입 여부만 미정, 스펙 자체는 항상 존재).

## CORS 정책

- 지금(로컬 개발)은 `CORS_ORIGINS`에 `http://localhost:5173`(Vite dev server)만 허용한다.
- 사내 devops 플랫폼에 배포될 때는 실제 도메인으로 `CORS_ORIGINS` 값만 교체한다(콤마로 여러 오리진 구분 가능) — 코드 변경 없이 env만으로 대응.
- **(계획, Phase 4)** Nginx가 프론트/백엔드를 동일 origin에서 서빙하게 되면(아래 "배포" 참고) `CORS_ORIGINS` 자체가 불필요해질 수 있음 — 실제 배포 구조 확정 후 재검토.

## 배포 (Nginx/K8s) — 계획, Phase 4

- 사내 유사 프로젝트 `a-ims-prod`(PDEP/K8s 배포까지 설계·로컬 검증한 레포)의 구조를 참고.
- **Nginx 역할은 정적 파일 서빙 + `/api` 내부 리버스 프록시로 한정**한다. TLS 종료·외부 라우팅은 Nginx가 아니라 사내 **PDEP Ingress**가 담당(이미 사내 devops 플랫폼 사용을 전제하고 있음, 위 CORS 정책 참고).
- Dockerfile은 멀티스테이지로 구성 예정: 프론트 빌드 → Nginx 이미지, 백엔드 빌드 → Python 슬림 이미지.
- 로컬 개발에서도 운영과 동일하게 Nginx를 거치는 구조를 재현하기 위해, backend(uvicorn)+frontend(vite)+nginx를 한 번에 띄우는 스크립트를 마련한다(미뤄뒀던 "`run` 스킬"을 이 시점에 이 형태로 정의).
- PostgreSQL(실제 DB) 사용을 전제로 하므로, `a-ims-prod`가 SQLite 파일 동시쓰기 문제로 뒀던 "백엔드 Replica=1 고정" 제약은 eflms엔 해당 없음 — 대신 Alembic 마이그레이션이 여러 replica에서 동시 실행되지 않도록 하는 절차가 별도로 필요하다.

## 로깅 & 헬스체크

- `/healthz` 엔드포인트를 스캐폴딩 단계부터 만들어 둔다 — 사내 devops 플랫폼이 배포 상태를 점검할 때 보통 요구하는 최소 요건이다.
- 로그는 구조화(JSON) 형식으로 남겨서, 나중에 사내 로그 수집 시스템과 연동하기 쉽게 한다.

## 테스트 전략

- 백엔드: pytest. 프론트: vitest.
- 1단계(Stage C 초기)는 최소한의 스모크 테스트로 시작한다 — 주요 API가 200을 응답하는지, 시드 스크립트가 에러 없이 끝나는지 정도. 기능이 늘어나면 점진적으로 확대한다.
