# EFLMS — 전기설비수명관리시스템

변압기(EF1)를 시작으로 전기설비의 자산 건전성을 PoF(설비상태)·CoF(고장영향성)·DoF(고장예방력) 3축으로 평가하고, 웹 대시보드로 보여주는 사내 시스템. FastAPI 백엔드 + Vue 3 프론트엔드 + SQLite(개발)/PostgreSQL(운영 예정) 구조입니다.

현재 단계: Phase 1(mock 데이터 대시보드) 완료, Phase 2(운영 데이터 임포트 파이프라인) 완료, Phase 3(EF2 GIS·EF3 초고압케이블·EF4 수배전반·EF5 UPS·EF6 VDP·EF7 배터리 추가 — 설비유형별 계산·조회·화면) 완료, Phase 4(PostgreSQL/Nginx 인프라) 로컬 검증 완료, Phase 5(관리자 로그인/SSO) 로컬 검증 완료. 등록된 설비유형: EF1 변압기, EF2 GIS, EF3 초고압케이블, EF4 수배전반, EF5 UPS, EF6 VDP, EF7 배터리. 점수(POF·COF·DOF·종합)는 소수 첫째 자리로 표시한다. 자세한 진행 상황은 [docs/ROADMAP.md](docs/ROADMAP.md) 참고.

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
설비별 파일 하나씩(변압기 → EF1, GIS → EF2, 초고압케이블 → EF3, 수배전반 → EF4, UPS → EF5, VDP → EF6, 배터리 → EF7). 배터리는 설비 파일 말고 **참고표 2개**(방전이력·온도감소계수)도 따로 넣는다 — 아래 3)의 마지막 블록. 헤더는 `ref_data/schema_eflms.py`·`schema_eflms_gis.py`·`schema_eflms_cable.py`·`schema_eflms_subaejeon.py`·`schema_eflms_ups.py`·`schema_eflms_vdp.py`·`schema_eflms_battery.py`의 컬럼명 그대로면 된다(순서 무관, 탭 구분). 수배전반·UPS·VDP·배터리 파일에는 전압 컬럼이 없다(정상).

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
.venv\Scripts\python -m app.db.import_data --file "..\real_data\UPS.dat" --ef-code EF5 --check
.venv\Scripts\python -m app.db.import_data --file "..\real_data\UPS.dat" --ef-code EF5 --replace
.venv\Scripts\python -m app.db.import_data --file "..\real_data\VDP.dat" --ef-code EF6 --check
.venv\Scripts\python -m app.db.import_data --file "..\real_data\VDP.dat" --ef-code EF6 --replace
# 배터리: 참고표를 먼저(교체), 그다음 설비 파일
.venv\Scripts\python -m app.db.import_reference --ef-code EF7 --table discharge_history --file "..\real_data\방전이력.dat" --replace
.venv\Scripts\python -m app.db.import_reference --ef-code EF7 --table temp_decay_coef --file "..\real_data\온도감소계수.dat" --replace
.venv\Scripts\python -m app.db.import_data --file "..\real_data\배터리.dat" --ef-code EF7 --check
.venv\Scripts\python -m app.db.import_data --file "..\real_data\배터리.dat" --ef-code EF7 --replace
```
- 배터리 참고표(Stage 15): 헤더는 방전이력 `disch_date factory_code volt_change disch_index`(전압변동은 % 숫자, 11.6% → `11.6`), 온도감소계수 `year gamma_y`. `--replace` 없이 넣으면 같은 행(방전이력은 사업장+일자, 온도감소계수는 year)은 갱신·새 행은 추가, `--check`는 검증만. 참고표를 넣거나 바꾸면 배터리 점수가 자동으로 다시 계산된다. 비우려면 `python -m app.db.reset_reference --ef-code EF7 --table discharge_history|temp_decay_coef|all`(빈 표는 0으로 계산 — 경고 표시). 설비 리셋은 참고표를 지우지 않는다.
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

## 다른 PC로 옮겨서 기존 DB 이어 쓰기 (SQLite, Windows)

실파일을 다시 넣지 않고 지금 PC의 데이터를 그대로 새 PC에서 쓰고 싶을 때. 데이터는 전부 **`backend\eflms.db` 파일 하나**에 들어 있으므로 이 파일만 옮기면 된다.

**옮길 것 / 옮기지 않을 것** (모두 git 제외 대상이라 클론으로는 따라오지 않는다)

| 대상 | 옮기나 | 설명 |
|---|---|---|
| `backend\eflms.db` | **옮긴다** | 설비·입력값·점수·이력·접근 권한 전부. **복사 전에 원래 PC 서버를 끈다**(`scripts\stop-dev.ps1`) — 켜 둔 채 복사하면 쓰던 내용이 빠질 수 있다 |
| `backend\.env`, `frontend\.env`, `nginx\.env` | 바꿔 쓴 값이 있으면 옮긴다 | 포트·`AUTH_MODE`·관리자 비밀번호 등을 기본값에서 바꿨다면 그대로 가져간다. 아니면 새 PC에서 `.env.example`을 복사해도 된다 |
| `real_data\` | 필요할 때만 | 새 PC에서 입력파일을 다시 넣을 계획이 있을 때만 |
| `backend\eflms.before-*.db` | 옮기지 않는다 | 단계별 작업 전 백업본 |
| `backend\.venv`, `frontend\node_modules` | **옮기지 않는다** | 만든 PC·폴더 경로에 묶여 있어 옮기면 깨진다 — 새 PC에서 새로 설치 |

**새 PC에서 할 일**
```powershell
git clone https://github.com/seohandarcy-code/eflms-prod.git
cd eflms-prod\backend
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # alembic도 여기서 같이 설치됨
# 여기서 원래 PC의 eflms.db를 backend\ 폴더에, .env 파일들을 각 폴더에 복사
.venv\Scripts\python -m alembic current        # DB 버전 확인 — "(head)"가 붙어 있으면 최신
.venv\Scripts\python -m alembic upgrade head   # 최신이면 아무것도 안 바뀜, 예전 DB면 최신 구조로 올림
cd ..\frontend
npm install
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
```
- 파일 이름은 `eflms.db` 그대로 둔다 — `backend\.env`의 `DATABASE_URL=sqlite+aiosqlite:///./eflms.db`가 이 이름을 가리킨다.
- **mock 시드(`app.db.seed`)는 실행하지 않는다** — 옮겨 온 실데이터에 가짜 데이터가 섞인다. `AUTO_SEED_IF_EMPTY`도 false로 둔다.
- 서버가 시작되면 점수 기준일이 오늘보다 이전인 설비의 점수를 자동으로 다시 계산한다(입력값은 그대로).
- 나중에 코드를 업데이트(`git pull`)했을 때도 서버를 켜기 전에 `alembic upgrade head`를 한 번 실행한다. DB 버전이 코드보다 낮으면 서버는 점수 갱신·임포트를 멈추고 "DB 업그레이드 필요"를 띄운다.
- `alembic`이 무엇이고 어떻게 동작하는지는 아래 "DB 구조 버전 관리(Alembic)" 참고.

## DB 구조 버전 관리(Alembic)

Alembic은 **DB 구조(테이블·컬럼) 변경 이력을 코드로 관리하는 도구**다. 코드가 바뀌어 새 테이블이나 컬럼이 필요할 때, 데이터는 그대로 두고 구조만 순서대로 고쳐 준다.

- 변경 하나하나가 `backend\alembic\versions\` 안의 파이썬 파일 하나다(예: `a3d9e5f7c1b8_ef3_max_load_float.py` — EF3 최대부하를 정수→실수로). 각 파일은 자기 앞 버전을 가리켜 한 줄로 이어진다.
- DB 안의 `alembic_version` 테이블에 "이 DB가 어디까지 적용됐는지"가 한 줄 기록된다.
- `alembic upgrade head`는 그 기록 다음부터 최신(head)까지 남은 변경만 차례로 적용한다. 이미 최신이면 아무것도 하지 않으므로 여러 번 실행해도 안전하다.
- 접속 대상은 앱과 같은 `backend\.env`의 `DATABASE_URL`(또는 `DB_*`)을 그대로 쓴다 — SQLite든 PostgreSQL이든 같은 명령.
- 앱은 기동할 때 `alembic upgrade`를 스스로 하지 않는다. **설치 직후·코드 업데이트 후에는 직접 한 번 실행**한다(운영은 배포마다 migrate Job 1회 — [docs/DEPLOY_PDEP.md](docs/DEPLOY_PDEP.md)).

| 명령 (backend 폴더에서) | 하는 일 |
|---|---|
| `.venv\Scripts\python -m alembic current` | 이 DB의 현재 버전 표시(`(head)`가 붙으면 최신) |
| `.venv\Scripts\python -m alembic upgrade head` | 최신까지 남은 변경 적용 |
| `.venv\Scripts\python -m alembic history` | 전체 변경 목록 |
| `.venv\Scripts\python -m alembic downgrade -1` | 한 단계 되돌리기 — 데이터가 줄어들 수 있으니 **먼저 DB 백업** |

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

## 관리자 로그인 / DB 테이블 조회 · 데이터 입력 화면

대시보드 왼쪽 사이드바 하단에 항상 보이는 "관리자" 버튼(클릭 전까지 데이터 비노출) → `/admin`에서 로그인하면, 시스템이 쓰는 DB 테이블(총 19개)을 조회 전용으로 볼 수 있다(편집 기능 없음).

- **`AUTH_MODE=local`(기본 추천, 개발용)**: 비밀번호 로그인(`ADMIN_BOOTSTRAP_PASSWORD`, 기본값 `0000`)만으로 활성화됨. `AUTH_MODE=none`(기본값)이면 이 기능 자체가 비활성화된다.
- **`AUTH_MODE=sso`**: 사내 SSO(OIDC) 로그인으로 전환, "접근 권한 관리" 탭에서 계정별 접근 허용/관리자 권한을 관리할 수 있음 — 자세한 내용은 위 "Secret 설정"의 SSO 링크 참고.
- **`AUTH_MODE=sso`면 대시보드·지표설명도 로그인해야 보인다**(Stage 16-1). 첫 화면에 "회사 계정으로 로그인"이 뜨고, 로그인 뒤 원래 보던 화면으로 돌아온다. `allowed_users`에 없는 사람도 회사 인증만 되면 **대시보드 조회 전용**으로 들어온다(관리자 화면은 막힘) — 예전처럼 거부하려면 `SSO_DENY_UNREGISTERED_USERS=true`. `none`/`local` 모드의 대시보드는 지금처럼 공개.
- 역할: 관리자(admin, 모든 탭) / 등록 사용자(user, 테이블 조회) / 미등록 사용자(general, 대시보드만).
- **데이터 입력 탭(관리자만, Stage 16-2/16-3/16-6)**: 대상(설비 데이터·참고표)과 방식(추가·갱신/교체)을 고르고, 엑셀에서 **헤더 포함 범위를 복사해 붙여넣은 뒤 검증 → 입력값 미리보기(행별 추가/갱신, 오류 칸 빨간색) → 확정 반영**한다. [양식 복사]로 헤더 한 줄을 받아 엑셀 첫 행에 쓰고, [양식 보기]로 컬럼 설명·허용값을 본다. 파일이 있으면 [파일에서 불러오기]로 붙여넣기 칸을 채울 수 있다. 지금 DB 내용은 같은 형식의 dat로 **내려받는다**(백업·서버 이관용 — 그대로 다시 넣을 수 있음). 검증·계산 규칙은 아래 명령줄과 같다(같은 서비스 사용). 리셋(전체 비우기)은 명령줄로만 한다. 내용 최대 5MB.
- **전체 DB 내려받기(.sql, PostgreSQL용 — Stage 16-8)**: 데이터 입력 탭의 내려받기 카드 맨 위. 모든 테이블의 구조 + 데이터 + 마이그레이션 버전을 psql로 복원하는 파일 하나로 받는다(원본이 SQLite여도 PostgreSQL 문법). 다른 PostgreSQL로 통째로 옮길 때 **빈 DB**에 `createdb eflms_new` → `psql -v ON_ERROR_STOP=1 -d eflms_new -f eflms_full_YYYYMMDD_HHMM.sql`. 한 트랜잭션이라 실패하면 아무것도 남지 않고, 복원 뒤 `alembic upgrade head`를 그대로 이어 쓸 수 있다. 접근 권한 명단도 들어 있으니 파일 보관에 주의.
- **SQL 조회(관리자만, Stage 16-5)**: 테이블 조회 탭 오른쪽 위 SQL 입력창에서 조회문을 실행하고 아래 그리드로 본다(테이블을 누르면 `SELECT * … LIMIT 100`이 채워져 실행, `Ctrl+Enter`, 선택한 부분만 실행, 최근 실행 10개, CSV 내려받기). **조회(SELECT/WITH)만, 목록의 테이블만, 최대 1,000행·5초** — DB 쪽에서 강제한다(SQLite 읽기 전용 연결 + 권한 검사). 등록 사용자는 지금처럼 테이블을 눌러 보는 조회만.
- 세션은 브라우저 탭에 보관된다(새로고침해도 유지, 탭을 닫으면 로그아웃). 서버가 재기동되면 세션이 없어져 다시 로그인해야 한다.

## 데이터 리셋 & 사내 입력파일(.dat) 로드

> 운영 서버(PDEP)에서는 관리자 화면의 **데이터 입력** 탭으로 같은 작업(넣기·교체·검증·내려받기)을 할 수 있다 — 아래 명령은 로컬·서버 셸에서 쓰는 방법이고, 리셋은 명령줄로만 한다.

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
- 헤더는 `ref_data/schema_eflms.py`(EF1)·`schema_eflms_gis.py`(EF2)·`schema_eflms_cable.py`(EF3)·`schema_eflms_subaejeon.py`(EF4)·`schema_eflms_ups.py`(EF5)·`schema_eflms_vdp.py`(EF6)·`schema_eflms_battery.py`(EF7)의 `INPUT_COLUMNS` 컬럼명과 같아야 한다(순서 무관). 파일 안 `EF_code` 값이 `--ef-code`와 다르거나 등록되지 않은 유형이면 거부한다.
- GIS의 `cb_op_char_over`는 쓰지 않는 컬럼이라 있어도 건너뛴다(저장 안 함, "사용 안 하는 컬럼"으로 표시). 그 밖에 목록에 없는 컬럼은 "미등록 컬럼"으로 표시되고 `equipment_extra_attribute`에 원문 보관된다.
- 받아주는 표기: UTF-8(BOM 있어도 됨)·CP949, LF/CRLF, 값을 감싼 따옴표, 정수 칸의 `154000.0`, 날짜 `YYYY-MM-DD`·`YYYY.MM.DD`·`YYYY/MM/DD`·`YYYYMMDD`.
- 값 없음: `N/A`·`n/a`·`#N/A`는 null로 저장되고 그 항목은 감점 0(평가 안 함, 화면에 "N/A"). 단 사업장·설비명·가동년월·전압은 N/A 불가. 빈 칸은 N/A가 아니라 오류다 — `docs/DATA_DICTIONARY.md` "값 없음(N/A) 처리".
- 거부하는 것(행 오류): 헤더와 칸 수가 다른 행, 같은 설비(`factory_code` + 설비명)가 파일에 두 번, 빈 숫자/날짜, 소수인 정수, `nan`/`inf`, EF2~EF7 허용값 밖 값(예: EF3 포설방법 `지중`, 종단접속함 `DEBG,EBA`처럼 공백 빠진 표기, EF4 점검결과 `양호`/`불량` 외 표기·목록에 없는 설치건물), EF4 온도의 소수(원본 양식대로 정수).

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
