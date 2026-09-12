# 환경변수 / 시크릿 관리

`.env.example`은 레포에 커밋(값 없이 키만), 실제 값이 든 `.env`/`.env.local`은 `.gitignore`에 포함되어 절대 커밋되지 않는다. pydantic-settings로 타입 안전하게 로드한다.

## 일반 설정 (지금 확정)

| 변수 | 기본값(개발) | 설명 |
|---|---|---|
| `APP_ENV` | `development` | 실행 환경 구분 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./eflms.db` | 운영 전환 시 `postgresql+asyncpg://...`로 값만 교체 |
| `CORS_ORIGINS` | `http://localhost:5173` | 프론트 개발 서버 |
| `AUTH_MODE` | `none` | `none` → `local` → `sso` 순으로 전환 예정 |

## 시크릿 (이름만 예약, 값은 아직 없음 — 발급/생성은 추후 단계)

| 변수 | 용도 | 비고 |
|---|---|---|
| `JWT_SECRET_KEY` | 자체 로그인 토큰 서명 | `AUTH_MODE=local` 전환 시 필요, 랜덤 생성 필요 |
| `SSO_CLIENT_ID` | 사내 SSO(OIDC) 클라이언트 ID | `AUTH_MODE=sso` 전환 시 필요 |
| `SSO_CLIENT_SECRET` | 사내 SSO(OIDC) 클라이언트 시크릿 | 사내 보안팀/SSO 관리자 발급 필요 |
| `SSO_ISSUER_URL` | 사내 SSO Issuer URL | |

시크릿 값이 실제로 필요해지는 시점(로컬 로그인/SSO 연동 단계)에 생성 방법과 발급 절차를 이 문서에 추가한다. 지금은 이름과 용도만 예약해 둔다.
