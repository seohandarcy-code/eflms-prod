# 환경변수 / 시크릿 관리

`.env.example`은 레포에 커밋(값 없이 키만), 실제 값이 든 `.env`/`.env.local`은 `.gitignore`에 포함되어 절대 커밋되지 않는다. pydantic-settings로 타입 안전하게 로드한다.

## 일반 설정 (지금 확정)

| 변수 | 기본값(개발) | 설명 |
|---|---|---|
| `APP_ENV` | `development` | 실행 환경 구분 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./eflms.db` | 운영 전환 시 `postgresql+asyncpg://...`로 값만 교체 |
| `CORS_ORIGINS` | `http://localhost:5173` | 프론트 개발 서버. 콤마(`,`)로 여러 오리진 구분 가능. 배포 시에는 실제 사내 도메인 목록으로 값만 교체(코드 변경 없음) |
| `AUTH_MODE` | `none` | `none` → `local`(구현 완료) → `sso`(로컬 Keycloak 전체 생애주기 검증 완료). 대소문자·공백 무시, 그 외 값이나 빈 값이면 기동 실패(Stage 6-8) |
| `SSO_FLOW_MODE` | `auth_code` | **(구현 완료, 2026-10-06, Stage 6-7 / 기본값 `auth_code`로 변경, 2026-10-16, Stage 6-8)** `AUTH_MODE=sso`일 때만 의미 있음. 대소문자·공백 무시, 그 외 값이나 빈 값이면 기동 실패. 선택 기준은 "로컬이냐 운영이냐"가 아니라 **"IdP가 OIDC discovery를 지원하느냐"**다 — 모드별 상세는 `backend/app/auth/SSO_MODES.md`. `implicit_form_post`(이제 기본값 아님 — 브로커 경유가 필요하면 반드시 명시)는 discovery 미지원 자체 브로커 경유(`{SSO_ISSUER_URL}/oidc/form-authorize`+`/oidc/jwks`를 직접 호출, `backend/app/auth/oidc.py`의 `build_broker_authorize_url()`/`verify_broker_id_token()`), `auth_code`(기본값)는 discovery 지원 IdP 직접 연결(authlib, authorization code flow) — 브로커 없이 ADFS에 직접 붙는 경우(`a-ims-prod`가 실서버 연동 성공) **또는** 로컬 Keycloak 검증 둘 다 해당(ADFS는 Microsoft 표준 OIDC 구현이라 discovery를 지원함). 클레임을 받은 이후(allowed_users 대조, role 판정, 세션 발급) 로직은 두 모드가 공유 |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | *(비어있음)* | **(구현 완료, Phase 4)** `DATABASE_URL`이 없을 때 이 값들로 PostgreSQL DSN을 자동 조립(`docs/ARCHITECTURE.md` "DB 연결 및 확장" 참고). 셋 다 없으면 SQLite로 폴백. PDEP ConfigMap으로 주입 예정 |
| `SSO_ALLOW_LOCAL_LOGIN` | `false` | **(구현 완료, 2026-09-29)** `AUTH_MODE=sso`에서도 로컬 비밀번호 로그인을 함께 열어두는 개발용 듀얼모드 스위치. 공유 서버에서 켤 경우 `ADMIN_BOOTSTRAP_PASSWORD`를 기본값에서 반드시 변경할 것 |
| `SESSION_COOKIE_SECURE` | `false` | **(구현 완료, 2026-09-29)** OAuth state/nonce 세션 쿠키에 Secure 플래그 부여 여부(`backend/app/main.py`의 `SessionMiddleware`). 실제 HTTPS 배포에서 `true` |
| `FRONTEND_BASE_URL` | *(비어있음)* | **(구현 완료, 2026-09-29)** PDEP이 프론트/백엔드 도메인을 분리하는 경우에만 필요(SSO 콜백 리다이렉트 대상 지정, `backend/app/api/routes/admin.py`). 같은 origin이면 비워둠 |
| `SSO_CA_BUNDLE_PATH` | *(비어있음)* | **(구현 완료, 2026-10-01, Stage 6-6)** 사내 CA가 발급한 인증서를 쓰는 SSO 브로커(ADFS 등)에 연결할 때 필요 — Python(`httpx`)이 Windows와 달리 사내 CA를 기본적으로 신뢰하지 않아 `SSL: CERTIFICATE_VERIFY_FAILED`로 실패하는 걸 막음(`a-ims-prod`가 실제 ADFS 연동 중 겪은 문제). 상대경로면 `backend/` 기준으로 해석(`backend/app/core/config.py`의 `sso_ca_bundle_resolved_path`). PEM이 아닌 것 같으면 기동 시 경고 로그. 로컬은 `backend/certs/`(gitignore 대상)에 두고, 실 배포는 K8s Secret을 Volume mount로 연결 |

## 시크릿 (이름만 예약, 값은 아직 없음 — 발급/생성은 추후 단계)

| 변수 | 용도 | 비고 |
|---|---|---|
| `JWT_SECRET_KEY` | (미사용으로 확정) | `AUTH_MODE=local` 구현 시 `a-ims-prod` 패턴대로 JWT 서명 없이 프로세스 메모리 전용 opaque 토큰(`secrets.token_urlsafe`, `app/auth/state.py`)을 채택함 — 이 변수는 필요 없어짐. SSO(Phase 5 다음 단계) 착수 시 재검토 |
| `DB_USER` / `DB_PASSWORD` | PostgreSQL 접속 자격증명 | **(계획, Phase 4)** `DB_HOST`와 함께 DSN 조립에 사용. PDEP Secret으로 주입 예정, URL-safe 인코딩 필요 |
| `ADMIN_BOOTSTRAP_PASSWORD` | 관리자 초기 비밀번호(`AUTH_MODE=local` 로그인용) | **(구현 완료, 2026-09-29)** 서버 재기동 시 항상 이 값(비어있으면 기본값 `0000`)으로 리셋됨 — 여러 서버가 같은 잘 알려진 기본값을 공유하지 않도록 서버별로 다르게 주입. `backend/app/auth/state.py` |
| `SSO_CLIENT_ID` | 사내 SSO(OIDC) 클라이언트 ID | **(구현 완료)** `AUTH_MODE=sso` 전환 시 필요. `SSO_FLOW_MODE=implicit_form_post`면 브로커가 발급한 서비스 식별자(`/oidc/form-authorize?client_id=...` 쿼리 파라미터로 쓰임). `auth_code`면 issuer URL만으로 연동되는 브로커는 비워둘 수 있음(`SSO_BROKER_CONFIGURED = bool(SSO_ISSUER_URL)`, `backend/app/auth/oidc.py`), 로컬 Keycloak 같은 범용 멀티테넌트 IdP는 채워야 함 |
| `SSO_CLIENT_SECRET` | 사내 SSO(OIDC) 클라이언트 시크릿 | **(구현 완료)** `implicit_form_post`에서는 아예 쓰이지 않음(토큰 교환 단계 자체가 없음). `auth_code`에서는 사내 보안팀/SSO 관리자 발급 필요, 위와 동일 이유로 비어있을 수 있음 |
| `SSO_ISSUER_URL` | 사내 SSO Issuer URL | **(구현 완료)** 비어있으면 `/api/admin/sso/*`가 503을 반환(SSO 비활성). `implicit_form_post`면 **서비스 경로 없는 브로커 도메인만**(`{값}/oidc/form-authorize`, `{값}/oidc/jwks`로 쓰임). `auth_code`면 `{값}/.well-known/openid-configuration`을 자동 조회(로컬 Keycloak은 `{값}/realms/<realm>`, ADFS 직접 연결은 `{값}/adfs` 형태) |
| `SSO_ADMIN_ALLOWLIST` | SSO 로그인 시 admin 권한이 자동 복구되는 브레이크글래스 계정 목록(콤마 구분) | **(구현 완료, 2026-09-29)** 최초 배포 시 반드시 한 명 이상 채워야 함 — 안 그러면 접근 허용 목록(`allowed_users`)이 비어있는 상태에서 아무도 로그인 못 하는 락아웃 발생. `backend/app/auth/access_store.py`의 `upsert_bootstrap_admin` |
| `SSO_USER_ID_CLAIM` | 접근 허용 목록과 대조할 OIDC 클레임 이름 | **(구현 완료, 기본값 `email`)** 표준 클레임이 아니라 IdP(사내 SSO)마다 다름 — 실제 연동 전 사번/이메일 등 안정적 식별자로 확인 필요 |
| `SESSION_SECRET_KEY` | OAuth state/nonce 서명용 세션 키 | **(구현 완료, 2026-09-29)** 로컬 개발은 비워두면 매 기동마다 임의 생성해도 무방. 여러 replica 운영 시 안정적인 값 고정 필요. `backend/app/main.py`의 `SessionMiddleware` |

> **주의(Stage 6-8)**: pydantic-settings는 OS 프로세스 환경변수를 `backend/.env`보다 우선하고 빈 문자열도 값으로 취급한다. 셸이나 ConfigMap에 빈 변수가 남아 있으면 `.env` 값이 무시된다 — `AUTH_MODE`/`SSO_FLOW_MODE`/`SSO_USER_ID_CLAIM`/`ADMIN_BOOTSTRAP_PASSWORD`는 빈 값으로 존재하면 기동 시 경고를 남긴다. 실제 적용된 인증 설정은 기동 로그의 `EFLMS auth config:` 한 줄로 확인(`backend/app/auth/SSO_MODES.md` §4).

시크릿 값이 실제로 필요해지는 시점(실제 SSO 브로커 연동 단계)에 생성 방법과 발급 절차를 이 문서에 추가한다. 지금은 이름과 용도만 예약해 둔다. `allowed_users` DB 테이블/`AllowedUser` 모델(`backend/app/db/models/auth.py`)도 Stage 6-1에서 추가됨(마이그레이션 `3d49abc45e95`).
