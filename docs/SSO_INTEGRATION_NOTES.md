# SSO(OIDC) 연동 작업 회고 — 다른 프로젝트 참고용

> 이 문서는 eflms-prod 저장소에서 진행한 SSO 연동 작업(2026-09-29~30)을 다른 작업 폴더/프로젝트에서도
> 참고할 수 있도록 정리한 것이다. 코드 자체는 이 저장소(`backend/app/auth/`, `backend/app/api/routes/admin.py`,
> `frontend/src/views/AdminView.vue` 등)에 있고, 여기서는 **패턴과 실제로 겪은 문제들**을 정리한다.

## 1. 배경

- 참고한 레포: `a-ims-prod`(사내 유사 프로젝트, 투자관리시스템) — SQLite→PostgreSQL 전환과 SSO 연동을
  이미 로컬 Keycloak으로 검증까지 마친 상태였음.
- eflms 쪽 목표: 관리자 전용 화면(이 프로젝트에서는 "DB 테이블 조회" 화면) 로그인 수단을
  단일 공유 비밀번호(`AUTH_MODE=local`) → 사내 SSO(`AUTH_MODE=sso`)로 확장.
- **중요한 범위 차이**: a-ims-prod는 `AUTH_MODE=sso`일 때 애플리케이션 전체를 로그인 게이트 뒤에 둔다.
  eflms는 대시보드 전체는 계속 무인증 공개로 두고, **관리자 전용 화면 하나만** SSO로 게이트했다.
  다른 프로젝트에 이 패턴을 가져올 때는 "전체 앱을 게이트할지, 특정 화면만 게이트할지"부터 먼저 정해야 한다.

## 2. 적용한 패턴 (다른 프로젝트에도 그대로 이식 가능)

### 2.1 세션 저장소 — 로그인 수단과 무관하게 공유

`AdminAuthStore`(메모리 전용, 서버 재기동 시 초기화):
- opaque random token(`secrets.token_urlsafe`) 기반 — JWT 서명 불필요
- 세션마다 `is_admin` 플래그를 함께 저장해서, **로그인 수단(비밀번호 vs SSO)과 무관하게 세션 검증/권한 판단 로직 하나를 공유**한다.
- 로그인 시도 5회 실패 시 5분 잠금(`AccountLockedError`), TTL 8시간.
- `login(password)`: 비밀번호 검증 후 세션 발급, 항상 `is_admin=True`(단일 관리자 개념).
- `issue_session(is_admin)`: 비밀번호 없이(SSO 콜백처럼 이미 검증된 상황에서) 세션만 발급.

### 2.2 접근 허용 목록 — "IdP 인증 성공 ≠ 접근 허용"

사내 SSO는 직접 관리하지 않는 시스템이므로, "IdP 인증에 성공하면 곧 우리 서비스 접근도 허용"이라고
가정하면 위험하다(회사 SSO 계정이 있는 누구나 조회 가능해짐). 그래서 별도 DB 테이블로 화이트리스트를 둔다:

- `allowed_users(sso_id PK, name, team, is_admin, created_at)`
- 로그인 콜백에서 IdP가 돌려준 사용자 식별 클레임(`SSO_USER_ID_CLAIM`, 기본값 `email` — **표준 클레임이 아니라 IdP마다 다르므로 실제 연동 전 확인 필수**)을 이 테이블의 `sso_id`와 대조.
- 등록 안 된 계정이면 IdP 인증 자체는 성공해도 세션 발급을 거부(403).
- CRUD는 관리자 화면 안에서 직접(등록/수정/삭제).
- **마지막 admin 삭제/강등 방지**(`LastAdminError`) — 전체 락아웃 방지용 안전장치. 실제로 UI에서 재현 확인함.

### 2.3 브레이크글래스 계정

`SSO_ADMIN_ALLOWLIST`(env, 콤마 구분) — 여기 매칭되는 sso_id는 로그인할 때마다 `allowed_users`에
admin 권한이 자동으로 보장(`upsert_bootstrap_admin`, 이미 있으면 admin=True만 보장하고 이름/팀은
건드리지 않음). **최초 배포 시 반드시 한 명 이상 채워야 한다** — 안 그러면 `allowed_users`가
비어있는 상태에서 아무도 로그인 못 해 관리자 화면 자체에 못 들어가는 락아웃이 생긴다.

### 2.4 개발용 듀얼모드

`SSO_ALLOW_LOCAL_LOGIN=true` — 사내 SSO 브로커가 아직 client_id를 발급하지 않은 개발 단계에서도,
`AUTH_MODE=sso` 상태 그대로 기존 비밀번호 로그인을 같이 열어둔다. 관리자가 먼저 비밀번호로 들어가
"접근 권한 관리"에 SSO 계정들을 미리 등록해둘 수 있다. 새 인증 경로를 만들지 않고 이미 검증된
로컬 로그인을 재사용하는 게 핵심(우회 경로를 늘리지 않기 위함).

### 2.5 client_id/secret 없이 issuer URL만 주는 브로커 대응

```python
SSO_BROKER_CONFIGURED = bool(settings.sso_issuer_url)  # client_id/secret 유무와 무관
```

일부 사내 SSO 브로커는 "서비스 URL을 등록하면 그 서비스 전용 고유 issuer 주소가 발급되고,
client_id/secret은 따로 안 준다"는 모델을 쓴다(로컬 Keycloak 같은 범용 멀티테넌트 IdP와는 다름).
`authlib`은 `client_secret`이 비면 `token_endpoint_auth_method`를 자동으로 `"none"`으로 바꾸고,
`client_id`가 비면 ID 토큰의 `aud` 클레임 검증 자체를 건너뛰므로 코드 변경 없이 대응 가능
(라이브러리 소스로 확인함). 실제 연동 전 사내 브로커가 어느 모델인지 확인 필요.

## 3. 로컬 검증 방법 (Docker 없이, 네이티브 설치 우선)

```powershell
# JDK
winget install --id EclipseAdoptium.Temurin.17.JDK --accept-package-agreements --accept-source-agreements

# Keycloak (zip 다운로드 후 압축 해제)
# https://github.com/keycloak/keycloak/releases/download/<버전>/keycloak-<버전>.zip

$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-<버전>-hotspot"
$env:KEYCLOAK_ADMIN = "admin"; $env:KEYCLOAK_ADMIN_PASSWORD = "admin"
cd C:\tools\keycloak-<버전>
bin\kc.bat start-dev --http-port=8180
```

Admin REST API(`POST /admin/realms/master/protocol/openid-connect/token`으로 토큰 발급 후
`/admin/realms`, `/admin/realms/{realm}/clients`, `/admin/realms/{realm}/users` 호출)로
realm, confidential client(redirect URI 등록), 브레이크글래스 계정 + 테스트 계정 여러 개를 만든다.

**검증 시나리오 체크리스트**(전부 실제 브라우저로 재현 권장, 단위테스트만으로는 불충분):
1. 브레이크글래스 계정 로그인 → `allowed_users`에 자동 admin 등록되는지
2. 관리자가 일반 계정을 등록 → 그 계정으로 로그인 → 관리자 전용 기능은 안 보이고 일반 기능만 되는지
3. 미등록 계정으로 로그인 시도 → 거부되는지 (IdP 인증 자체는 성공하지만 세션은 안 나옴)
4. 관리자가 계정을 삭제 → 그 계정으로 재로그인 시 거부로 바뀌는지
5. 마지막 admin을 강등/삭제하려는 시도가 막히는지

## 4. 실제로 겪은 버그 (다른 프로젝트에서도 재발 가능성 높음)

### 4.1 nginx가 리버스 프록시할 때 `Host` 헤더에서 포트가 빠지는 문제 ⚠️ 가장 흔할 버그

```nginx
proxy_set_header Host $host;        # 틀림 — 포트가 빠짐 (예: "127.0.0.1")
proxy_set_header Host $http_host;   # 맞음 — 포트 포함 (예: "127.0.0.1:8080")
```

백엔드가 `request.url_for(...)`처럼 현재 요청의 Host 헤더를 바탕으로 콜백 URL을 스스로 생성하는
구조라면, nginx 뒤에 있을 때 `$host`를 쓰면 포트 없는 URL이 만들어진다(`http://127.0.0.1/api/...`).
이게 SSO redirect_uri로 쓰이면 IdP가 "등록된 redirect_uri와 다르다"며 거부한다(`Invalid parameter: redirect_uri`).
**nginx 리버스 프록시 뒤에서 OAuth/SSO 콜백을 쓰는 프로젝트라면 반드시 `$http_host`를 써야 한다.**

### 4.2 SSO 콜백 실패 시 raw JSON 에러가 브라우저에 그대로 노출

콜백 엔드포인트는 브라우저가 리다이렉트되어 도착하는 곳이라, `HTTPException`을 그대로 raise하면
FastAPI가 JSON 에러 바디를 응답하고 브라우저는 그 raw JSON을 화면에 그대로 보여준다
(`{"detail": "등록되지 않은 계정입니다"}` 같은 게 API 문서처럼 보임 — 일반 사용자 입장에서 나쁜 경험).

**해결**: 실패 시에도 항상 프론트 URL로 리다이렉트하되, 에러 코드를 URL 프래그먼트에 실어 보낸다
(`/admin#error=not_registered`). 프론트는 이 코드를 읽어서 사람이 읽을 수 있는 메시지로 보여준다.
쿼리스트링이 아니라 프래그먼트를 쓰는 이유는 성공 시 토큰도 같은 방식으로 전달하기 때문 —
프래그먼트는 서버 로그/리퍼러 헤더에 안 남는다.

### 4.3 테스트가 로컬 `.env` 내용에 오염됨 (모듈 import 시점에 고정되는 상수)

```python
# app/auth/oidc.py
SSO_BROKER_CONFIGURED = bool(settings.sso_issuer_url)  # 모듈이 처음 import될 때 딱 한 번 계산됨
```

이 상수는 **요청마다 다시 계산되는 게 아니라 모듈이 처음 로드될 때(pytest가 앱을 처음 import할 때)
그 시점의 `.env` 내용으로 고정**된다. 로컬 개발자가 Keycloak 검증을 위해 `backend/.env`에 실제
`SSO_ISSUER_URL`을 넣어두면, 이후 `pytest`를 돌릴 때 "SSO 미설정 시 503" 같은 테스트가
`monkeypatch.setenv(...)`를 아무리 해도 실패한다 — 이미 import 시점에 `True`로 고정됐기 때문.

또한 `from app.auth.oidc import SSO_BROKER_CONFIGURED`처럼 **다른 모듈이 `from ... import`로
값을 복사해가면, 원본 모듈의 값을 나중에 patch해도 복사해간 쪽은 안 바뀐다**(Python의
이름 바인딩 특성). 실제로 이 프로젝트에서 `admin.py`가 `oidc.py`에서 값을 import해갔기 때문에,
`monkeypatch.setattr(oidc, "SSO_BROKER_CONFIGURED", False)`가 아니라
`monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", False)`처럼
**값을 실제로 참조하는 모듈(여기서는 라우터 모듈) 쪽을 직접 patch**해야 테스트가 로컬 `.env`와
무관하게 결정적으로 동작했다.

### 4.4 (버그는 아니지만 트러블슈팅 포인트) Keycloak 자체 세션이 브라우저에 남아있음

우리 앱을 로그아웃해도 Keycloak(IdP) 자체의 브라우저 세션은 살아있다. 그래서 로그아웃 직후
"회사 계정으로 로그인"을 다시 누르면, 로그인 폼 없이 조용히 방금 그 계정으로 재로그인된다
(정상 SSO 동작 — 사내 게이트형 도구에서 흔함). **다른 계정으로 테스트하려면 우리 앱
로그아웃이 아니라 Keycloak 자체 로그아웃**(`http://<keycloak>/realms/<realm>/protocol/openid-connect/logout`,
확인 화면에서 Logout 클릭)이 필요하다.

### 4.5 (Keycloak 자체 특성) 신규 사용자는 프로필 완성을 요구함

Admin REST API로 만든 계정이 `firstName`/`lastName`을 다 채우지 않으면, 최초 로그인 시
Keycloak이 "Update Account Information"(`VERIFY_PROFILE`) 화면을 끼워 넣는다. 자동화된
검증 스크립트를 짤 계획이라면 계정 생성 시 `firstName`/`lastName`을 미리 채워서 이 단계를
건너뛰게 하는 게 편하다.

## 5. 이 프로젝트에서의 최종 상태 / 아직 안 한 것

- ✅ `AUTH_MODE=local`(비밀번호) / `AUTH_MODE=sso`(OIDC) 둘 다 실제 동작, 로컬 Keycloak으로 전체 생애주기 검증 완료
- ✅ 관리자 화면(조회 전용 DB 테이블 뷰어) 로그인 게이트 + 접근 권한 관리 CRUD
- ⬜ **실제 사내 SSO 브로커 연동** — 로컬 Keycloak과 실제 브로커가 issuer URL만 주는 모델인지, client_id/secret도 주는 범용 모델인지부터 사내 SSO 담당자 확인 필요
- ⬜ 완전한 로그아웃(OIDC RP-Initiated Logout, `end_session_endpoint` 호출) — 지금은 우리 앱 로그아웃이 IdP 세션까지 끊지 않음(4.4 참고). 필요해지면 추가
- ⬜ 이 관리자 화면 외의 일반 대시보드까지 SSO로 게이트하는 것 — 현재 의도적으로 범위 밖(§1 참고)

## 6. 관련 파일 (이 저장소 기준)

| 역할 | 파일 |
|---|---|
| 세션 저장소 | `backend/app/auth/state.py` |
| 접근 허용 목록 CRUD | `backend/app/auth/access_store.py` |
| OIDC 클라이언트 등록 | `backend/app/auth/oidc.py` |
| 라우터(로그인/콜백/접근관리) | `backend/app/api/routes/admin.py` |
| 세션 검증 의존성 | `backend/app/api/deps.py` (`require_session` / `require_admin`) |
| DB 모델 | `backend/app/db/models/auth.py` |
| 프론트 로그인/탭 UI | `frontend/src/views/AdminView.vue`, `frontend/src/components/AccessUsersPanel.vue` |
| 프론트 인증 상태 | `frontend/src/stores/auth.ts` |
| env 카탈로그 | `docs/SECURITY_ENV.md` |
| 재현 절차(로컬 Keycloak) | `backend/CLAUDE.md` "로컬 Keycloak으로 SSO 검증하기" |
| 작업 이력(커밋 단위) | `docs/ROADMAP.md` Phase 5 |
