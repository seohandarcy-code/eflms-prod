# 환경변수 / 시크릿 관리

`.env.example`은 레포에 커밋(값 없이 키만), 실제 값이 든 `.env`/`.env.local`은 `.gitignore`에 포함되어 절대 커밋되지 않는다. pydantic-settings로 타입 안전하게 로드한다.

## 일반 설정 (지금 확정)

| 변수 | 기본값(개발) | 설명 |
|---|---|---|
| `APP_ENV` | `development` | 실행 환경 구분 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./eflms.db` | 운영 전환 시 `postgresql+asyncpg://...`로 값만 교체 |
| `CORS_ORIGINS` | `http://localhost:5173` | 프론트 개발 서버. 콤마(`,`)로 여러 오리진 구분 가능. 배포 시에는 실제 사내 도메인 목록으로 값만 교체(코드 변경 없음) |
| `AUTH_MODE` | `none` | `none` → `local` → `sso` 순으로 전환 예정 |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | *(비어있음)* | **(계획, Phase 4)** `DATABASE_URL`이 없을 때 이 값들로 PostgreSQL DSN을 자동 조립(`docs/ARCHITECTURE.md` "DB 연결 및 확장" 참고). 셋 다 없으면 SQLite로 폴백. PDEP ConfigMap으로 주입 예정 |
| `SSO_ALLOW_LOCAL_LOGIN` | `false` | **(계획, Phase 5)** `AUTH_MODE=sso`에서도 로컬 비밀번호 로그인을 함께 열어두는 개발용 듀얼모드 스위치. 공유 서버에서 켤 경우 `ADMIN_BOOTSTRAP_PASSWORD`를 기본값에서 반드시 변경할 것 |
| `SESSION_COOKIE_SECURE` | `false` | **(계획, Phase 5)** OAuth state/nonce 세션 쿠키에 Secure 플래그 부여 여부. 실제 HTTPS 배포에서 `true` |
| `FRONTEND_BASE_URL` | *(비어있음)* | **(계획, Phase 5)** PDEP이 프론트/백엔드 도메인을 분리하는 경우에만 필요(SSO 콜백 리다이렉트 대상 지정). 같은 origin이면 비워둠 |

## 시크릿 (이름만 예약, 값은 아직 없음 — 발급/생성은 추후 단계)

| 변수 | 용도 | 비고 |
|---|---|---|
| `JWT_SECRET_KEY` | (미사용으로 확정) | `AUTH_MODE=local` 구현 시 `a-ims-prod` 패턴대로 JWT 서명 없이 프로세스 메모리 전용 opaque 토큰(`secrets.token_urlsafe`, `app/auth/state.py`)을 채택함 — 이 변수는 필요 없어짐. SSO(Phase 5 다음 단계) 착수 시 재검토 |
| `DB_USER` / `DB_PASSWORD` | PostgreSQL 접속 자격증명 | **(계획, Phase 4)** `DB_HOST`와 함께 DSN 조립에 사용. PDEP Secret으로 주입 예정, URL-safe 인코딩 필요 |
| `ADMIN_BOOTSTRAP_PASSWORD` | 관리자 초기 비밀번호(`AUTH_MODE=local` 로그인용) | **(구현 완료, 2026-09-29)** 서버 재기동 시 항상 이 값(비어있으면 기본값 `0000`)으로 리셋됨 — 여러 서버가 같은 잘 알려진 기본값을 공유하지 않도록 서버별로 다르게 주입. `backend/app/auth/state.py` |
| `SSO_CLIENT_ID` | 사내 SSO(OIDC) 클라이언트 ID | `AUTH_MODE=sso` 전환 시 필요. 단, issuer URL만 발급하고 client_id를 안 주는 사내 브로커 방식이면 비워둘 수 있음(`SSO_BROKER_CONFIGURED = bool(SSO_ISSUER_URL)`) |
| `SSO_CLIENT_SECRET` | 사내 SSO(OIDC) 클라이언트 시크릿 | 사내 보안팀/SSO 관리자 발급 필요, 위와 동일 이유로 비어있을 수 있음 |
| `SSO_ISSUER_URL` | 사내 SSO Issuer URL | |
| `SSO_ADMIN_ALLOWLIST` | SSO 로그인 시 admin 권한이 자동 복구되는 브레이크글래스 계정 목록(콤마 구분) | **(계획, Phase 5)** 최초 배포 시 반드시 한 명 이상 채워야 함 — 안 그러면 접근 허용 목록(`allowed_users`)이 비어있는 상태에서 아무도 로그인 못 하는 락아웃 발생 |
| `SSO_USER_ID_CLAIM` | 접근 허용 목록과 대조할 OIDC 클레임 이름 | **(계획, Phase 5)** 표준 클레임이 아니라 IdP(사내 SSO)마다 다름 — 실제 연동 전 사번/이메일 등 안정적 식별자로 확인 필요 |
| `SESSION_SECRET_KEY` | OAuth state/nonce 서명용 세션 키 | **(계획, Phase 5)** 로컬 개발은 비워두면 매 기동마다 임의 생성해도 무방. 여러 replica 운영 시 안정적인 값 고정 필요 |

시크릿 값이 실제로 필요해지는 시점(로컬 로그인/SSO 연동 단계)에 생성 방법과 발급 절차를 이 문서에 추가한다. 지금은 이름과 용도만 예약해 둔다. 위 "계획" 표시 항목은 사내 유사 프로젝트 `a-ims-prod`의 실전 검증 패턴을 참고한 것이며, 실제 eflms 구현 착수(Stage 1 이후) 시점에 값이 아닌 이름/용도만 먼저 반영한 상태다.
