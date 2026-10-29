# EFLMS — 전기설비수명관리시스템

변압기(EF1)를 시작으로 전기설비의 자산 건전성을 PoF(고장확률)·CoF(고장영향)·DoF(설계/방어수준) 3축으로 평가하고, 웹 대시보드로 보여주는 사내 시스템. FastAPI 백엔드 + Vue 3 프론트엔드 + SQLite(개발)/PostgreSQL(운영 예정) 구조입니다.

현재 단계: Phase 1(mock 데이터 대시보드) 완료, Phase 2(운영 데이터 임포트 파이프라인) 완료, Phase 3(EF2 GIS·EF3 초고압케이블·EF4 수배전반 추가 — 설비유형별 계산·조회·화면) 완료, Phase 4(PostgreSQL/Nginx 인프라) 로컬 검증 완료, Phase 5(관리자 로그인/SSO) 로컬 검증 완료. 등록된 설비유형: EF1 변압기, EF2 GIS, EF3 초고압케이블, EF4 수배전반. 자세한 진행 상황은 [docs/ROADMAP.md](docs/ROADMAP.md) 참고.

## 요구 사항

- **Python 3.11**
- **Node.js 22 LTS** — `frontend/.nvmrc`에 버전이 고정되어 있음. `nvm` 사용 시 `frontend/`에서 `nvm install && nvm use`로 맞출 수 있음(다른 버전의 Node가 시스템에 이미 깔려 있어도 무관 — 이 프로젝트에서만 22를 쓰면 됨).
- **(선택) Nginx** — 아래 "빠른 시작"으로 backend+frontend+nginx를 한 번에 띄우고 싶을 때만 필요. nginx 없이 backend/frontend를 각각 직접 띄우는 것도 가능(운영과 동일한 프록시 구조를 로컬에서 재현하고 싶을 때만 nginx 사용).

## 클론

```bash
git clone https://github.com/seohandarcy-code/eflms-prod.git
cd eflms-prod
```

## 다른 PC에서 실데이터로 시작하기 (Windows)

준비물: Python 3.11, Node.js 22, (선택) nginx

**1) 백엔드 설치** — mock 시드는 실행하지 않는다
```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python -m alembic upgrade head
```
- `py -3.11`로 버전을 지정한다 — 그냥 `python`은 PC에 따라 3.12 등 다른 버전일 수 있다.

**2) 실파일 두기** — 저장소 루트의 `real_data\` 폴더(git 제외 대상이라 실수로 커밋되지 않음)나 저장소 밖에 둔다.
설비별 파일 하나씩(변압기 → EF1, GIS → EF2, 초고압케이블 → EF3, 수배전반 → EF4). 헤더는 `ref_data/schema_eflms.py`·`schema_eflms_gis.py`·`schema_eflms_cable.py`·`schema_eflms_subaejeon.py`의 컬럼명 그대로면 된다(순서 무관, 탭 구분). 수배전반 파일에는 전압 컬럼이 없다(정상).

**3) 점검 → 반영** (backend 폴더에서, 경로에 한글·공백이 있으면 따옴표)
```powershell
.venv\Scripts\python -m app.db.import_data --file "..\real_data\변압기.dat" --ef-code EF1 --check
.venv\Scripts\python -m app.db.import_data --file "..\real_data\변압기.dat" --ef-code EF1 --replace
.venv\Scripts\python -m app.db.import_data --file "..\real_data\GIS.dat" --ef-code EF2 --check
.venv\Scripts\python -m app.db.import_data --file "..\real_data\GIS.dat" --ef-code EF2 --replace
.venv\Scripts\python -m app.db.import_data --file "..\real_data\케이블.dat" --ef-code EF3 --check
.venv\Scripts\python -m app.db.import_data --file "..\real_data\케이블.dat" --ef-code EF3 --replace
.venv\Scripts\python -m app.db.import_data --file "..\real_data\수배전반.dat" --ef-code EF4 --check
.venv\Scripts\python -m app.db.import_data --file "..\real_data\수배전반.dat" --ef-code EF4 --replace
```
- `--check`가 실패하면 줄 번호·컬럼·사유가 나온다 — 파일을 고친 뒤 다시 점검. 실패한 파일은 한 건도 반영되지 않는다.
- GIS 파일의 `cb_op_char_over`는 쓰지 않는 컬럼이라 "사용 안 하는 컬럼(무시)"으로 표시되고 저장되지 않는다(정상).
- 위 목록에 없는 컬럼은 "미등록 컬럼"으로 표시되고 `equipment_extra_attribute`에 원문 보관된다(점수에는 영향 없음).
- 받아주는 표기·거부하는 값은 아래 "데이터 리셋 & 사내 입력파일(.dat) 로드" 참고.

**4) 프론트 설치와 기동**
```powershell
cd ..\frontend
npm install
copy .env.example .env
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
```
- 접속: http://127.0.0.1:8080 — nginx가 없으면 경고 후 8080만 안 뜨고, http://127.0.0.1:5173 으로 접속한다.
- 종료: `powershell -ExecutionPolicy Bypass -File .\scripts\stop-dev.ps1`
- `-ExecutionPolicy Bypass`는 새 PC에서 PowerShell 스크립트 실행이 막혀 있을 때를 대비한 것이다(시스템 설정은 바꾸지 않음).

**5) 데이터를 갱신할 때** — 새 파일로 3)을 다시(`--check` → `--replace`). 그 유형만 교체되고 다른 유형은 그대로이며, 서버를 다시 띄울 필요는 없다.

`backend\.env`의 `AUTO_SEED_IF_EMPTY`는 false(기본값)로 둔다 — true면 비어 있는 유형에 mock이 섞인다.

## 빠른 시작 (Windows, backend+frontend+nginx 동시 기동)

최초 1회 아래 "백엔드 실행"/"프론트엔드 실행" 섹션의 설치 단계(`pip install`, `alembic upgrade head`, `npm install` 등)를 먼저 끝낸 뒤:

```powershell
.\scripts\start-dev.ps1
```

- backend(uvicorn), frontend(vite), nginx를 한 번에 백그라운드로 띄운다.
- 접속: **http://127.0.0.1:8080** (nginx 경유 — 정적서빙+`/api` 프록시만 담당, 운영 배포와 동일한 구조를 로컬에서 재현). 직접 접속도 가능: 프론트 `http://127.0.0.1:5173`, 백엔드 `http://127.0.0.1:8000`.
- 종료: `.\scripts\stop-dev.ps1`
- PowerShell 전용 스크립트다(macOS/Linux는 아래 "백엔드 실행"/"프론트엔드 실행"을 각각 터미널 두 개로 띄우면 됨).
- 포트를 바꾸고 싶으면 아래 "환경변수 설정"의 `BACKEND_PORT`/`VITE_PORT`/`NGINX_PORT` 참고.

## 백엔드 실행 (수동으로 하나씩 띄우고 싶을 때, 또는 macOS/Linux)

```bash
cd backend
py -3.11 -m venv .venv          # macOS/Linux: python3.11 -m venv .venv

# Windows
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m app.db.seed --rows 30      # 화면 확인용 mock — 실데이터를 넣을 거면 생략
.venv\Scripts\python -m uvicorn app.main:app --reload

# macOS / Linux
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed --rows 30
.venv/bin/uvicorn app.main:app --reload
```

- `.env`는 값을 로컬에 맞게 조정(기본값으로도 로컬 실행은 가능) — 자세한 항목은 아래 "환경변수 설정" 참고.
- `alembic upgrade head`가 DB 스키마(`backend/eflms.db`, SQLite)를 만듦.
- `app.db.seed --rows 30`은 화면을 바로 확인할 수 있도록 등록된 설비유형마다 **mock(가짜) 데이터**를 30건씩 채워 넣음 — 실제 운영 데이터는 아래 "데이터 리셋 & 사내 입력파일(.dat) 로드" 참고.
- 기동 확인: `http://localhost:8000/healthz`
- **주의(폴더 이동/이름변경 후)**: `.venv/Scripts/uvicorn.exe`처럼 실행 파일을 직접 실행하면 생성 당시 경로가 캐싱돼 있어 조용히 실패할 수 있음 — 항상 `python -m uvicorn ...`처럼 `python -m <모듈>` 형태로 실행할 것. 자세한 내용은 [backend/CLAUDE.md](backend/CLAUDE.md) 참고.

## 프론트엔드 실행 (수동으로 하나씩 띄우고 싶을 때, 또는 macOS/Linux)

```bash
cd frontend
npm install
cp .env.example .env   # Windows는 copy .env.example .env
npm run dev
```

브라우저에서 `http://localhost:5173` 접속. API 호출은 상대경로(`/api/...`)를 쓰며 `vite.config.ts`의 dev proxy가 백엔드로 연결해준다(백엔드가 먼저 떠 있어야 함). 프론트/백엔드 origin이 완전히 분리되는 배포 환경에서만 `VITE_API_BASE_URL`에 절대 URL을 채운다.

## 환경변수 설정

세 컴포넌트가 각자 `.env.example`을 갖고 있고, 실제 값은 `.env`로 복사해서 조정한다(`.env`는 git에 커밋되지 않음).

| 파일 | 주요 항목 |
|---|---|
| `backend/.env.example` | `DATABASE_URL`(SQLite 기본값, PostgreSQL 전환은 `postgresql+asyncpg://...`로 값만 교체 — 또는 `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` 조합도 지원), `CORS_ORIGINS`, `AUTH_MODE`(`none`/`local`/`sso`, 아래 "관리자 로그인" 참고), `BACKEND_PORT`, `AUTO_SEED_IF_EMPTY`(아래 "데이터 리셋" 참고) |
| `frontend/.env.example` | `VITE_API_BASE_URL`(보통 비워둠 — 상대경로 사용), `VITE_PORT` |
| `nginx/.env.example` | `NGINX_PORT` |

**포트 커스터마이즈**: `BACKEND_PORT`/`VITE_PORT`/`NGINX_PORT`가 유일한 원본이다. `scripts/start-dev.ps1`/`stop-dev.ps1`이 이 세 파일을 직접 읽어 항상 같은 포트를 보고 기동/종료하며(`scripts/_ports.ps1`), `frontend/vite.config.ts`도 `backend/.env`를 직접 읽어 dev proxy 타겟을 맞춘다 — 한 곳만 바꾸면 나머지가 자동으로 맞물린다.

DB/인증 구조에 대한 자세한 설명은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), 전체 env/시크릿 목록은 [docs/SECURITY_ENV.md](docs/SECURITY_ENV.md) 참고.

## Secret 설정

`.env.example`은 키 이름만 커밋되고 값은 비어있다. 로컬 개발에서 최소한 신경 쓸 것:

- **관리자 로그인을 쓸 계획이면** `ADMIN_BOOTSTRAP_PASSWORD` — 비워두면 기본값(`0000`)으로 동작(로컬 개발용, 공유 서버에서는 반드시 변경).
- **SSO(`AUTH_MODE=sso`)를 검증/연동할 계획이면** `SSO_ISSUER_URL`/`SSO_CLIENT_ID`/`SSO_CLIENT_SECRET`/`SSO_ADMIN_ALLOWLIST` 등 — 로컬 Keycloak으로 재현하는 절차는 [backend/CLAUDE.md](backend/CLAUDE.md) "로컬 Keycloak으로 SSO 검증하기", 실제 연동 시 참고할 패턴/트러블슈팅은 [docs/SSO_INTEGRATION_NOTES.md](docs/SSO_INTEGRATION_NOTES.md) 참고.
- 전체 목록(값의 용도, 기본값, 발급 필요 여부)은 [docs/SECURITY_ENV.md](docs/SECURITY_ENV.md)에 정리되어 있다.
- 시크릿 값은 **항상 `.env`로만 주입**하고 코드에 하드코딩하지 않는다. `.env`/`.env.local`은 `.gitignore`에 포함되어 있어 실수로 커밋되지 않는다.

## 관리자 로그인 / DB 테이블 조회 화면

대시보드 왼쪽 사이드바 하단에 항상 보이는 "관리자" 버튼(클릭 전까지 데이터 비노출) → `/admin`에서 로그인하면, 시스템이 쓰는 DB 테이블(총 19개)을 조회 전용으로 볼 수 있다(편집 기능 없음).

- **`AUTH_MODE=local`(기본 추천, 개발용)**: 비밀번호 로그인(`ADMIN_BOOTSTRAP_PASSWORD`, 기본값 `0000`)만으로 활성화됨. `AUTH_MODE=none`(기본값)이면 이 기능 자체가 비활성화된다.
- **`AUTH_MODE=sso`**: 사내 SSO(OIDC) 로그인으로 전환, "접근 권한 관리" 탭에서 계정별 접근 허용/관리자 권한을 관리할 수 있음 — 자세한 내용은 위 "Secret 설정"의 SSO 링크 참고.
- 세션은 브라우저 메모리에만 있어 새로고침하면 로그아웃된다(서버도 재기동 시 세션이 초기화됨).

## 데이터 리셋 & 사내 입력파일(.dat) 로드

모든 명령은 **설비유형(`--ef-code`) 단위**로 동작한다 — 한 유형을 지우거나 교체해도 다른 유형의 데이터는 그대로 남는다(예: EF1 실데이터는 두고 EF2 mock만 다시 만들기). `all`은 등록된 모든 유형을 각각 처리한다.

**Mock 데이터 재시딩(초기화 후 다시 채우기)**
```bash
cd backend
.venv/Scripts/python -m app.db.seed --rows 30 --reset                # 전체 유형(기본값 all)
.venv/Scripts/python -m app.db.seed --ef-code EF1 --rows 30 --reset  # EF1만
```
`--reset`을 빼면 기존 데이터에 추가로 쌓인다. macOS/Linux는 `.venv/bin/python`.

**유형 단위 삭제**
```bash
.venv/Scripts/python -m app.db.reset --ef-code EF1   # EF1 설비와 딸린 데이터만 삭제 (all도 가능)
```
`equipment_type`(마스터)과 `allowed_users`(접근 권한)는 지우지 않는다.

**기동 시 자동 시딩(로컬 개발 편의용)**: `backend/.env`에 `AUTO_SEED_IF_EMPTY=true`를 설정하면, 기동할 때 **비어 있는 설비유형만** mock 30건으로 채운다(기본값 false — 데이터가 있는 유형은 건드리지 않음, `alembic upgrade head`는 여전히 미리 실행돼 있어야 함).

**DB 완전 초기화**: SQLite 사용 중이면 `backend/eflms.db` 파일을 삭제하고 `alembic upgrade head`를 다시 실행하면 빈 스키마부터 새로 시작한다.

**실제 사내 입력파일(.dat, 탭구분) 반영**:
```bash
cd backend
.venv/Scripts/python -m app.db.import_data --file <파일경로> --ef-code EF1 --check     # 먼저 점검(DB 미반영)
.venv/Scripts/python -m app.db.import_data --file <파일경로> --ef-code EF1 --replace   # 반영
```
- `--check`: 검증과 점수 계산까지만 하고 DB에는 쓰지 않는다. 오류가 있으면 줄 번호·컬럼·사유를 출력하고 종료 코드 1.
- `--replace`: 해당 유형의 기존 데이터(mock 포함)를 지우고 파일 내용으로 **교체**한다. 빼면 추가/갱신(upsert)만 한다.
- 파일 하나가 트랜잭션 하나다 — 값 오류가 한 행이라도 있거나 반영 도중 실패하면 아무것도 바뀌지 않는다(`--replace`로 지운 것도 되돌아감).
- 헤더는 `ref_data/schema_eflms.py`(EF1)·`schema_eflms_gis.py`(EF2)·`schema_eflms_cable.py`(EF3)·`schema_eflms_subaejeon.py`(EF4)의 `INPUT_COLUMNS` 컬럼명과 같아야 한다(순서 무관). 파일 안 `EF_code` 값이 `--ef-code`와 다르거나 등록되지 않은 유형이면 거부한다.
- GIS의 `cb_op_char_over`는 쓰지 않는 컬럼이라 있어도 건너뛴다(저장 안 함, "사용 안 하는 컬럼"으로 표시). 그 밖에 목록에 없는 컬럼은 "미등록 컬럼"으로 표시되고 `equipment_extra_attribute`에 원문 보관된다.
- 받아주는 표기: UTF-8(BOM 있어도 됨)·CP949, LF/CRLF, 값을 감싼 따옴표, 정수 칸의 `154000.0`, 날짜 `YYYY-MM-DD`·`YYYY.MM.DD`·`YYYY/MM/DD`·`YYYYMMDD`.
- 거부하는 것(행 오류): 헤더와 칸 수가 다른 행, 같은 설비(`factory_code` + 설비명)가 파일에 두 번, 빈 숫자/날짜, 소수인 정수, `nan`/`inf`, EF2~EF4 허용값 밖 값(예: EF3 포설방법 `지중`, 종단접속함 `DEBG,EBA`처럼 공백 빠진 표기, EF4 점검결과 `양호`/`불량` 외 표기·목록에 없는 설치건물), EF4 온도의 소수(원본 양식대로 정수).

**다른 PC에서 클론해 실데이터로 띄우기**: 위 "다른 PC에서 실데이터로 시작하기" 절의 단계를 그대로 따른다.

먼저 아래처럼 샘플 파일로 바로 실행해볼 수 있음(mock 스키마 기준으로 만든 100행짜리 연습용 파일, 실제 회사 파일 아님):

```bash
.venv/Scripts/python -m app.db.import_data --file sample_data/ef1/sample_valid.dat --ef-code EF1
```

`backend/sample_data/<유형>/`(예: `ef1/`)에는 이 정상 케이스 외에 오류/미등록컬럼 케이스 파일도 있고(`sample_with_errors.dat`, `sample_with_extra_columns.dat`), `python scripts/generate_sample_dat.py --ef-code EF1`로 재생성 가능. 컬럼명이 실제 파일과 다르거나 날짜 형식이 다를 때 무엇을 고쳐야 하는지는 [backend/CLAUDE.md](backend/CLAUDE.md)의 "운영 데이터 임포트" 섹션에 정리되어 있음.

## 테스트

```bash
# 백엔드
cd backend && .venv/Scripts/python -m pytest   # Windows
cd backend && .venv/bin/python -m pytest        # macOS/Linux

# 프론트엔드
cd frontend && npm run test -- --run
```

## 저장소 구조

| 경로 | 내용 |
|---|---|
| `backend/` | FastAPI + SQLAlchemy(async) + Alembic. 세부 컨벤션·명령어는 [backend/CLAUDE.md](backend/CLAUDE.md) |
| `frontend/` | Vue 3 + Vite + Pinia + Element Plus. 세부 컨벤션은 [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| `nginx/` | 로컬 개발용 nginx 설정(`nginx.conf.template` — 정적서빙 + `/api` 프록시). 실제 `nginx.conf`는 `scripts/start-dev.ps1`이 매 실행 시 생성하는 산출물(git 미포함) |
| `scripts/` | `start-dev.ps1`/`stop-dev.ps1`(backend+frontend+nginx 동시 기동/종료), `_ports.ps1`(포트 설정 공유 로직) |
| `docs/` | 아키텍처([ARCHITECTURE.md](docs/ARCHITECTURE.md)) · 데이터 사전([DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) · 로드맵([ROADMAP.md](docs/ROADMAP.md)) · 보안/env([SECURITY_ENV.md](docs/SECURITY_ENV.md)) · SSO 연동 노트([SSO_INTEGRATION_NOTES.md](docs/SSO_INTEGRATION_NOTES.md)) |
| `ref_data/` | 엑셀 기반 원본 계산 로직 참고자료 — **읽기 전용**, 수정하지 않음 |
| `design/` | 최초 승인된 디자인(Direction A) 목업 — 2026-09-14 시점 기록, 이후 화면은 코드에서 직접 반복 개선(현재 화면의 정본은 실제 구현 코드) |

## 작업 방식

이 저장소의 모든 실제 작업(코드/설정 변경, DB 조작, git 조작 등)은 "구체적인 계획 제시 → 승인" 절차를 거쳐 진행합니다. 자세한 내용은 루트 [CLAUDE.md](CLAUDE.md) 참고.
