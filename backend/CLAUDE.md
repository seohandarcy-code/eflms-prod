# backend

FastAPI + SQLAlchemy(async) + Alembic. 상위 저장소 규칙(계획 승인 필수 등)은 루트 `CLAUDE.md`를 따른다.

## 실행

```bash
cd backend
.venv/Scripts/pip install -r requirements.txt   # 최초 1회
cp .env.example .env                             # 최초 1회, 값은 로컬에 맞게 조정
.venv/Scripts/uvicorn app.main:app --reload
```

`GET /healthz` 로 기동 확인.

**주의 — 폴더 이동/이름변경 후 `.venv/Scripts/*.exe`가 깨질 수 있음**: Python venv의 `Scripts/uvicorn.exe` 등 실행 파일은 생성 당시 절대경로를 내부에 캐싱하고 있어서, 프로젝트 폴더를 옮기거나 이름을 바꾸면 에러 메시지 없이 즉시 종료될 수 있다. 이 증상이 보이면 `.venv/Scripts/uvicorn.exe app.main:app` 대신 `.venv/Scripts/python.exe -m uvicorn app.main:app`처럼 **`python -m <모듈>` 형태로 우회**하면 즉시 해결됨(재설치 불필요). 완전히 정리하려면 `.venv` 삭제 후 `python -m venv .venv`로 재생성.

## 구조

- `app/core/` — 설정(`config.py`, env 기반) · 인증 추상화(`security.py`)
- `app/db/` — SQLAlchemy `Base`, 세션 팩토리 (`DATABASE_URL` 기반, SQLite↔PostgreSQL 무변경 전환)
- `app/api/routes/` — FastAPI 라우터
- `app/schemas/` — pydantic 요청/응답 모델
- `app/services/` — 비즈니스 로직 (라우터에서 DB 직접 쿼리 금지, 여기 경유)
- `app/equipment_types/` — 설비유형별 계산기 모듈 (`ef1_transformer.py` 등)

## 운영 데이터 임포트 (Phase 2)

사내 입력파일(.dat, 탭구분)을 읽어 DB에 반영하는 CLI. mock 시드(`app/db/seed.py`)와 동일하게 `<설비유형 모듈>.calculate()` → `ingest.ingest_row()` 경로를 그대로 탄다 — 화면·계산 로직·DB 스키마는 전혀 바뀌지 않고, "DB를 채우는 방법"만 하나 늘어나는 구조다. 컬럼 정의와 계산기는 `--ef-code`로 레지스트리(`app/equipment_types/registry.py`)에서 고른다.

```bash
cd backend
.venv/Scripts/python -m app.db.import_data --file sample_data/ef1/sample_valid.dat --ef-code EF1            # 추가/갱신
.venv/Scripts/python -m app.db.import_data --file sample_data/ef1/sample_valid.dat --ef-code EF1 --replace  # EF1만 교체
```

- 결과는 콘솔 요약 + JSON 로그 한 줄(`app/db/import_data.py`)로 남는다.
- 파일 안에 알려진 컬럼(`ef1_transformer.INPUT_COLUMNS`)에서 값 형식이 틀린 행이 하나라도 있으면 **그 파일은 통째로 반영되지 않는다**(부분 반영 금지) — 오류 목록만 출력됨. 검증 통과 후 반영 도중 실패해도 파일 전체가 rollback된다(파일 1건 = 트랜잭션 1건, `ingest_row`는 commit하지 않음).
- 행의 `EF_code`가 `--ef-code`와 다르거나 등록되지 않은 유형이면 거부.
- 모르는 컬럼(헤더가 `INPUT_COLUMNS`의 `name`에 없음)은 실패시키지 않고 `equipment_extra_attribute` 테이블에 원문 그대로 보관된다.

**테스트용 샘플 3종** — `backend/sample_data/<유형 소문자>/`(예: `ef1/`)에 있음(실제 회사 파일이 아니라 mock 스키마로 만든 연습용). `python scripts/generate_sample_dat.py --ef-code EF1`로 재생성 가능(`all`이면 등록된 전 유형).
- `sample_valid.dat` — 정상 케이스
- `sample_with_errors.dat` — 3번째 행 `voltage`(전압)가 숫자가 아닌 값 → 전체 반영 실패 확인용
- `sample_with_extra_columns.dat` — "점검자"/"비고" 같은 미등록 컬럼 포함 → `equipment_extra_attribute` 적재 확인용

**실제 사내 .dat 파일로 바꾸려면 이 3가지만 확인하면 됨:**
1. **컬럼 이름 맞추기** — 실제 파일의 헤더는 `app/equipment_types/ef1_transformer.py`의 `INPUT_COLUMNS`에 있는 `name`(영문)과 정확히 일치해야 매칭된다(사내 입력파일은 영문 헤더로만 오는 것으로 확인됨 — `label`(한글)은 각 항목이 무엇인지 설명하는 문서용 메타데이터일 뿐 매칭에는 쓰이지 않는다). 실제 파일 헤더가 다르면 **`INPUT_COLUMNS`의 `name` 값 자체를 실제 헤더 표기에 맞게 고치는 것**이 방법(새 컬럼을 추가할 필요는 없음). 안 맞는 컬럼은 실패하지 않고 `equipment_extra_attribute`로 빠지니, 처음엔 그냥 돌려보고 "미등록 컬럼" 목록으로 뭐가 안 맞는지 확인한 뒤 `name`을 맞춰가는 방식도 가능.
2. **날짜 형식** — 지금은 `YYYY-MM-DD` 고정(`import_service.py`의 `_cast_value`). 실제 파일이 다른 형식(`YYYY.MM.DD` 등)이면 그 함수의 date 분기만 수정.
3. **실행 시 `--file`을 실제 파일 경로로** — `python -m app.db.import_data --file <실제파일경로> --ef-code EF1 --replace`(mock을 걷어내고 실데이터로 교체). 인코딩(UTF-8/CP949)은 자동으로 시도하므로 별도 설정 불필요.

## 등록된 설비유형

| EF_code | 모듈 | 전용 테이블 | 샘플 |
|---|---|---|---|
| EF1 변압기 | `app/equipment_types/ef1_transformer.py` | `transformer_spec`, `dga_reading` 외 7개, `transformer_score_detail` | `sample_data/ef1/` |
| EF2 GIS | `app/equipment_types/ef2_gis.py` | `gis_operation`, `gis_diagnosis`, `gis_sf6_reading`, `gis_consequence_attribute`, `gis_design_attribute`, `gis_score_detail` | `sample_data/ef2/` |

- EF2는 임포트 허용값(`choices`/`min`/`max`/`required`)을 선언해 둬서 오류값(예: 소문자 `c`, 154k/345k 외 전압, 순도 100 초과)을 행 오류로 거부한다. 목록은 `docs/DATA_DICTIONARY.md` EF2 절.
- 조회 API는 설비유형별로 동작한다(Stage 8-4, `docs/ARCHITECTURE.md` "조회 API"). 상세는 `type_detail`(EF1/EF2 union), 유형별 스키마는 `app/schemas/ef1.py`·`ef2.py`. 화면은 8-5 전까지 `ef_code=EF1`만 요청한다.
- 설비유형 모듈의 조회용 인터페이스: `BREAKDOWN`(감점 라벨 메타), `calculate(row, as_of=)`(계산 기준일), `load_inputs`(저장값 → 계산 입력 복원 — 재계산하면 저장 점수와 같아야 함, `tests/test_type_queries.py`), `last_diag_dates`, `load_detail`.

## 설비유형별 데이터 운영 (Stage 8-2)

- 레지스트리: `app/equipment_types/registry.py`(EF_code → 모듈), 인터페이스: `app/equipment_types/base.py`(`NAME_FIELD`, `INPUT_COLUMNS`, `DOMAIN_TABLES`, `generate_input_row`, `calculate`, `ingest_domain`).
- 시드: `python -m app.db.seed --ef-code EF1|all --rows 30 [--reset]` — `--reset`은 지정 유형만 지움.
- 리셋: `python -m app.db.reset --ef-code EF1|all` — 유형 전용 테이블 → `score_snapshot`/`equipment_extra_attribute` → `equipment` 순(`app/services/dataset_service.py`). `equipment_type`/`allowed_users`는 그대로.
- `AUTO_SEED_IF_EMPTY=true`: 비어 있는 유형만 기동 시 mock 30건.
- 새 유형 추가 시 공통 코드(`ingest.py`/`dataset_service.py`/CLI)는 고치지 않는다 — 모듈 + 테이블 + 레지스트리 한 줄.

## PostgreSQL로 전환해서 개발하기 (로컬 검증 완료, 2026-09-29)

기본 개발 흐름은 계속 SQLite다 — 아래는 로컬에서 PostgreSQL 전환을 검증/재현하고 싶을 때만 필요.

- Windows에 PostgreSQL 14 네이티브 설치(`winget install --id PostgreSQL.PostgreSQL.14`), 이 프로젝트 전용 role/db(`eflms_dev`/`eflms_dev`, 테스트용 `eflms_dev_test`)를 별도로 생성 — `postgres` 슈퍼유저를 앱 접속에 그대로 쓰지 않는다.
- `app/core/config.py`가 이미 `DATABASE_URL` 우선 → `DB_HOST` 조합 → SQLite 폴백 순서를 지원하므로, 코드 변경 없이 `.env`의 `DATABASE_URL`만 `postgresql+asyncpg://...`로 바꾸면 전환된다.
- `alembic upgrade head`를 PostgreSQL 대상으로 실행 → 코드 변경 없이 테이블 정상 생성 확인.
- `backend/tests/conftest.py`가 `DATABASE_URL`이 이미 설정돼 있으면 그 값을 존중하도록 되어 있음(테스트마다 스키마를 새로 만들어 SQLite 임시 파일 방식과 동일한 격리 수준 유지) — `DATABASE_URL=postgresql+asyncpg://eflms_dev:<비밀번호>@127.0.0.1:5432/eflms_dev_test .venv/Scripts/python -m pytest` 로 기존 스위트 9개를 그대로 PostgreSQL 대상으로 실행해 통과 확인(평소 `pytest`는 여전히 SQLite 임시 파일을 자동으로 씀 — 기본 경험 변화 없음).
- 앱을 `DATABASE_URL`로 PostgreSQL을 가리키게 기동(`AUTO_SEED_IF_EMPTY=true`와 함께 쓰면 편함) → `/healthz`·`/api/summary`·`/api/equipment`까지 SQLite 때와 동일하게 동작 확인.
- 실제 PDEP 배포 시 버전은 PostgreSQL 17을 목표로 함(`CLAUDE.md` 기술스택 표 참고) — 이번 로컬 검증은 14로 진행했으나, `DATABASE_URL`/SQLAlchemy Core 수준에서 버전 차이로 인한 문제는 없을 것으로 예상(실제 17 전환 시 재확인 권장).

## 로컬 Keycloak으로 SSO 검증하기 (로컬 검증 완료, 2026-09-29)

기본 개발 흐름은 계속 `AUTH_MODE=local`(비밀번호 로그인)이다 — 아래는 `AUTH_MODE=sso`를 로컬에서 검증/재현하고 싶을 때만 필요. Docker 없이(이 컴퓨터엔 미설치, PostgreSQL 때와 같은 네이티브 우선 원칙) JDK 17 + Keycloak 독립 서버로 진행한다.

**설치**
```powershell
winget install --id EclipseAdoptium.Temurin.17.JDK --accept-package-agreements --accept-source-agreements
# https://github.com/keycloak/keycloak/releases 에서 keycloak-26.x.x.zip 다운로드 후 C:\tools\keycloak-26.x.x 에 압축 해제
```

**기동**
```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.x.x-hotspot"
$env:KEYCLOAK_ADMIN = "admin"; $env:KEYCLOAK_ADMIN_PASSWORD = "admin"
cd C:\tools\keycloak-26.x.x
bin\kc.bat start-dev --http-port=8180
```

**realm/client/테스트 계정 생성** — Admin REST API(`http://127.0.0.1:8180/admin/realms/...`)로 realm `eflms`, confidential 클라이언트 `eflms-backend`(redirect URI에 `nginx`/`backend` 양쪽 콜백 주소 모두 등록: `http://127.0.0.1:8080/api/admin/sso/callback`, `http://127.0.0.1:8000/api/admin/sso/callback`), 브레이크글래스 계정(`eflms.admin@...`) + 테스트 계정(`eflms.test1~4@...`)을 생성한다. 클라이언트 시크릿은 `/admin/realms/eflms/clients/{uuid}/client-secret`로 조회.

**`backend/.env` 설정** — 로컬 Keycloak은 discovery 지원 IdP라 `SSO_FLOW_MODE=auth_code`
경로를 탄다. 2026-10-16(Stage 6-8)부터 `auth_code`가 기본값이라 생략해도 되지만 명시해두면
헷갈리지 않는다. 모드별 설정은 `app/auth/SSO_MODES.md` 참고:
```
AUTH_MODE=sso
SSO_FLOW_MODE=auth_code
SSO_ISSUER_URL=http://127.0.0.1:8180/realms/eflms
SSO_CLIENT_ID=eflms-backend
SSO_CLIENT_SECRET=<위에서 조회한 값>
SSO_ADMIN_ALLOWLIST=eflms.admin@company.local
SSO_ALLOW_LOCAL_LOGIN=true
```

**검증 시나리오(전부 확인됨)**: 브레이크글래스 계정 로그인 → `allowed_users`에 자동 admin 등록 확인 → "접근 권한 관리" 탭에서 테스트 계정을 일반 사용자로 등록 → 그 계정으로 로그인(테이블 조회는 되고 "접근 권한 관리" 탭은 안 보임) → 미등록 계정으로 로그인 시도("등록되지 않은 계정입니다" 확인) → 마지막 admin은 강등/삭제 불가 확인. Keycloak 자체 로그인 세션은 브라우저에 남아있어 재테스트 시 다른 계정으로 확인하려면 `http://127.0.0.1:8180/realms/eflms/protocol/openid-connect/logout`으로 먼저 로그아웃해야 함(우리 앱 로그아웃과는 별개).

**실제로 겪은 버그**: `nginx/nginx.conf.template`이 `proxy_set_header Host $host;`를 쓰고 있었는데, nginx의 `$host`는 포트를 뺀 호스트명만 담는다(`$http_host`가 포트 포함). 이 때문에 백엔드가 `request.url_for()`로 만드는 SSO redirect_uri에서 포트가 통째로 빠져(`http://127.0.0.1/...`) Keycloak이 "Invalid parameter: redirect_uri"로 거부했다 — `$http_host`로 교체해 해결.

## 인증 모드 설정 (`AUTH_MODE` / `SSO_FLOW_MODE`)

모드별 의미·설정 예시·반영 확인법은 [`app/auth/SSO_MODES.md`](app/auth/SSO_MODES.md)에 정리. 요점만:
- `AUTH_MODE`(`none`/`local`/`sso`), `SSO_FLOW_MODE`(`auth_code` 기본 / `implicit_form_post`)는 허용값 외·빈 값이면 **기동 실패**.
- 실제 적용값은 `uvicorn.log`의 `EFLMS auth config:` 한 줄로 확인. `.env`를 고쳐도 반영이 안 되면 셸에 같은 이름의 빈 환경변수가 남아있는지(`Test-Path Env:SSO_FLOW_MODE`) 먼저 본다.

## 컨벤션

- 시크릿은 `.env`로만 주입, 코드에 하드코딩 금지
- 새 설비유형 추가 시 기존 설비유형 코드/공통 테이블 변경 금지
