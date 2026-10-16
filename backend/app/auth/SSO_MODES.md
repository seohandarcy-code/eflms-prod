# SSO 모드 설정 가이드 (`AUTH_MODE` / `SSO_FLOW_MODE`)

이 폴더(`app/auth/`)의 인증 코드가 어떤 설정값으로 어떤 경로를 타는지 정리한 문서.
작업 경위·회고는 [`docs/SSO_INTEGRATION_NOTES.md`](../../../docs/SSO_INTEGRATION_NOTES.md),
env 전체 목록은 [`docs/SECURITY_ENV.md`](../../../docs/SECURITY_ENV.md) 참고.

## 1. 두 단계 스위치

| 변수 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| `AUTH_MODE` | `none` / `local` / `sso` | `none` | `/admin` 로그인 **수단**. `none`=게이트 없음(관리자 API 503), `local`=비밀번호(`ADMIN_BOOTSTRAP_PASSWORD`), `sso`=OIDC |
| `SSO_FLOW_MODE` | `auth_code` / `implicit_form_post` | **`auth_code`** | `AUTH_MODE=sso`일 때만 의미. IdP와 **어떤 프로토콜 흐름**으로 붙을지 |

- 두 값 모두 대소문자·앞뒤 공백은 무시한다(`" SSO "` → `sso`).
- **허용값 외의 값이나 빈 값이면 서버가 기동 시점에 `ValidationError`로 멈춘다** (`app/core/config.py`).
  예전엔 오타(`auth-code`)나 빈 값이 경고 없이 `auth_code` 분기로 떨어졌다 — 잘못된 모드로 조용히
  도는 것보다 아예 안 뜨는 편이 원인 찾기가 빠르다(Stage 6-8, 2026-10-16).
- 대시보드 자체는 어느 모드든 항상 공개다. 게이트 대상은 `/admin`(DB 테이블 조회·접근권한 관리)뿐이다.

## 2. `SSO_FLOW_MODE` 선택 기준 — "IdP가 OIDC discovery를 지원하느냐"

로컬이냐 운영이냐로 고르지 않는다. 확인 방법:
`{SSO_ISSUER_URL}/.well-known/openid-configuration`이 200 + JSON(`authorization_endpoint`,
`token_endpoint`, `jwks_uri`)을 주는지 본다.

| | `auth_code` (기본값) | `implicit_form_post` |
|---|---|---|
| 대상 | discovery 지원 IdP — **ADFS 직접 연결**, 로컬 Keycloak | discovery 미지원 사내 자체 브로커 |
| 검증 상태 | a-ims-prod가 **실서버 ADFS 연동 성공**, eflms는 로컬 Keycloak 전체 생애주기 검증 | 합성 RSA 키쌍 테스트만(실 브로커 미검증) |
| 인가 요청 | authlib이 discovery로 알아낸 `authorization_endpoint` (ADFS: `/adfs/oauth2/authorize`) | `{SSO_ISSUER_URL}/oidc/form-authorize?client_id=...` (코드에서 조립) |
| 콜백 | `GET /api/admin/sso/callback?code=...` → 백엔드가 token 엔드포인트로 교환 | `POST /api/admin/sso/callback` (form body에 `id_token`) |
| 서명 검증 | authlib (discovery의 `jwks_uri`) | PyJWT로 `{SSO_ISSUER_URL}/oidc/jwks` 직접 조회 |
| `SSO_ISSUER_URL` | ADFS: `https://<ADFS 도메인>/adfs` · Keycloak: `http://127.0.0.1:8180/realms/<realm>` | 브로커 **도메인만** (서비스 경로 없이) |
| `SSO_CLIENT_ID` | IdP에 등록한 client_id (issuer URL만 주는 브로커면 비울 수 있음) | 브로커가 발급한 서비스 식별자 |
| `SSO_CLIENT_SECRET` | IdP 발급값 | **안 씀** (토큰 교환 단계가 없음) |
| 코드 위치 | `oidc.py`의 `oauth.register(...)` | `oidc.py`의 `build_broker_authorize_url()` / `verify_broker_id_token()` |

클레임을 받은 **이후**(`SSO_USER_ID_CLAIM`으로 `allowed_users` 대조 → role 판정 → 세션 발급,
실패 시 `/admin#error=...` 배너)는 두 모드가 완전히 같은 코드를 쓴다(`app/api/routes/admin.py`의 `sso_callback`).

## 3. 설정 예시 (`backend/.env` 또는 ConfigMap/Secret)

**ADFS 직접 연결 (운영 목표, 기본 경로)**
```
AUTH_MODE=sso
# SSO_FLOW_MODE=auth_code   ← 기본값이라 생략 가능
SSO_ISSUER_URL=https://<ADFS 도메인>/adfs
SSO_CLIENT_ID=<ADFS에 등록된 client_id>
SSO_CLIENT_SECRET=<Secret으로 주입>
SSO_REDIRECT_URI=https://<서비스 도메인>/api/admin/sso/callback
SSO_USER_ID_CLAIM=<IdP 담당자 확인 — upn/email 등>
SSO_ADMIN_ALLOWLIST=<브레이크글래스 계정, 최초 배포 시 필수>
SSO_CA_BUNDLE_PATH=<사내 CA PEM 경로 — ADFS가 사내 CA 인증서를 쓰면 필요>
```

**사내 자체 브로커 경유 (필요할 때만 — 반드시 명시)**
```
AUTH_MODE=sso
SSO_FLOW_MODE=implicit_form_post
SSO_ISSUER_URL=https://<브로커 도메인>
SSO_CLIENT_ID=<브로커 발급 서비스 식별자>
```

**로컬 Keycloak 검증** — 절차는 `backend/CLAUDE.md` "로컬 Keycloak으로 SSO 검증하기".
`auth_code`가 기본값이라 `SSO_FLOW_MODE`는 따로 안 적어도 된다.

## 4. 설정이 실제로 반영됐는지 확인하기

**기동 로그 한 줄**을 먼저 본다 (`backend/uvicorn.log`, PDEP에선 파드 로그):
```
INFO:     EFLMS auth config: auth_mode=sso sso_flow_mode=auth_code issuer=https://.../adfs client_id=설정됨 user_id_claim=email allow_local_login=False
```
시크릿(client_secret, 비밀번호)과 client_id 값 자체는 찍지 않는다.

### 주의 — 빈 OS 환경변수가 `.env`를 덮어쓴다

pydantic-settings는 **OS 프로세스 환경변수 > `backend/.env`** 순으로 읽고, 빈 문자열도 "값이 있음"으로
취급한다. PowerShell 세션이나 ConfigMap에 `SSO_FLOW_MODE=`처럼 빈 변수가 남아 있으면 `.env`를 아무리
고쳐도 반영되지 않는다 — a-ims-prod가 PDEP와 로컬 양쪽에서 실제로 겪은 문제(2026-10-15).

- `AUTH_MODE`, `SSO_FLOW_MODE`, `SSO_USER_ID_CLAIM`, `ADMIN_BOOTSTRAP_PASSWORD`가 빈 문자열로 존재하면
  기동 시 `WARNING ... 환경변수가 프로세스에 빈 문자열로 존재합니다` 로그가 남는다
  (`app/core/config.py`의 `_warn_blank_process_env`). 앞의 두 개는 빈 값이면 아예 기동 실패한다.
- 로컬 확인/정리:
  ```powershell
  Test-Path Env:SSO_FLOW_MODE      # True면 셸에 남아 있는 것
  Remove-Item Env:SSO_FLOW_MODE    # 지운 뒤 재기동
  ```
- PDEP: `kubectl exec <pod> -- env | grep -E "AUTH_MODE|SSO_"`로 파드 안의 실제 값을 본다.

## 5. 관련 파일

| 역할 | 파일 |
|---|---|
| 설정 로드·모드 검증·빈 env 경고·기동 요약 | `app/core/config.py` (`Settings`, `_warn_blank_process_env`, `auth_summary`) |
| 기동 로그 출력 | `app/main.py` (`lifespan`) |
| OIDC 클라이언트 등록 / 브로커 URL 조립·id_token 검증 / CA 번들 | `app/auth/oidc.py` |
| 로그인·콜백 라우터(모드 분기) | `app/api/routes/admin.py` (`sso_login`, `sso_callback`) |
| 세션 저장소 / 접근 허용 목록 | `app/auth/state.py` / `app/auth/access_store.py` |
| 테스트 | `tests/test_settings_modes.py`(모드 검증), `tests/test_sso_implicit_form_post.py`, `tests/test_sso_and_access_admin.py` |
