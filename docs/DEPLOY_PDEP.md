# PDEP 배포 체크리스트

eflms를 사내 DevOps 플랫폼(PDEP, Jenkins → 사내 레지스트리 → Helm/K8s)에 올리기 위한 준비 목록.
사내 유사 프로젝트 `a-ims-prod`의 PDEP 문서(`docs/vue_fastapi_nginx_github_pdep_guide.md` §15,
`pdep-vue-template-guide.md`)를 eflms 코드와 대조해 작성했다(2026-10-17).

- 표기: `[x]` 이미 충족 / `[ ]` 할 일 / `[?]` 사내 담당자 확인 필요
- 실제 접속정보·시크릿 값은 이 문서에 적지 않는다 — `.env`(로컬) / K8s Secret(PDEP)으로만 주입한다(`docs/SECURITY_ENV.md`).
- 이 문서의 매니페스트·Dockerfile은 **초안(예시)** 이다. 1절 답이 나온 뒤 별도 단계(계획 승인)로 실제 파일을 만든다.

---

## 1. 사내 담당자에게 먼저 확인할 것

아래 답에 따라 Dockerfile·Jenkinsfile·K8s YAML의 최종 형태가 정해진다.

| # | 질문 | eflms에 미치는 영향 |
|---|---|---|
| 1 | **프로덕트 단위** — frontend/backend를 별도 레포·별도 프로덕트로 등록해야 하나? | a-ims-prod는 분리함(`git filter-repo`로 히스토리 보존). 분리 시 `frontend/`·`backend/`가 각각 레포 루트가 됨 |
| 2 | **라우팅** — 단일 도메인 + 경로 분기(`/api` → backend)인가, 도메인 분리(`app.` / `api-app.`)인가? 프로젝트별 nginx를 쓰나, Ingress가 대신하나? | 단일 도메인이면 지금 코드 그대로(상대경로 `/api`). 분리면 `VITE_API_BASE_URL`(빌드 시점 고정)·`CORS_ORIGINS`·`FRONTEND_BASE_URL` 설정 필요 |
| 3 | **DB** — PostgreSQL 17 제공 방식, 접속정보를 ConfigMap(host/port/name)·Secret(user/password)로 나눠 주나? | `DB_HOST` 계열 DSN 조립은 이미 구현됨 — 값만 주입 |
| 4 | **이미지 빌드** — Dockerfile을 레포에 직접 두나, PDEP CI가 내장 빌드하나? 사내 레지스트리 주소·인증, 허용 베이스 이미지, npm/PyPI 사내 미러 | Dockerfile·Jenkinsfile 작성 여부와 내용 |
| 5 | **운영 데이터 투입 경로** — 사내 입력파일(DAT/CSV)을 파드에 어떻게 넣나? | `import_data --replace` 실행 방식(K8s Job / `kubectl exec` / 볼륨) |
| 6 | **SSO** — ADFS에 eflms client 등록, redirect URI(운영 도메인 확정 후), 사용자 식별 클레임, 사내 CA 인증서 | `SSO_*` 값, CA를 Secret으로 마운트 → `SSO_CA_BUNDLE_PATH`(`backend/certs/README.md`) |

---

## 2. eflms 고유 배포 위험

코드 확인으로 찾은 것. 체크리스트(3절)에도 반영했다.

| 위험 | 현재 상태 | 대응 |
|---|---|---|
| 관리자 로그인 세션이 메모리 | `app/auth/state.py` `AdminAuthStore._sessions` — 파드마다 따로, 재시작 시 소멸 | 당분간 backend **replicas: 1** 고정. 여러 개가 필요해지면 세션을 DB/Redis로 이전(코드 변경, 별도 계획) |
| `SESSION_SECRET_KEY` 비면 기동마다 임의 생성 | SSO state/nonce 쿠키 서명 키가 파드 재시작·다중 파드마다 달라져 로그인 왕복 중 실패 | 운영은 Secret으로 **필수** 주입 + `SESSION_COOKIE_SECURE=true` |
| 시간대 | ~~계산 기준일이 `date.today()` — 컨테이너 기본은 UTC~~ → 2026-11-19(Stage 21-1)부터 기본 계산 기준일은 `app/core/clock.today_kst()`(UTC+9 고정) | 코드로 해결 — `TZ` 설정·`tzdata` 없이도 KST 기준. (로그 시각만 UTC로 찍힐 수 있음) |
| 점수 매일 갱신 | 점수가 마지막 임포트일에 멈추지 않도록 **서버가 자동 갱신**(Stage 21-1b — 시작 직후·날짜가 바뀌면, `SCORE_REFRESH_AUTO=true` 기본) | 별도 CronJob 불필요(선택). replicas를 늘려도 데이터 작업 잠금(`data_job_lock`)으로 한 대만 갱신. 배포 직후 migrate Job이 먼저 끝나야 함 — DB가 최신이 아니면 갱신하지 않고 로그 `EFLMS score refresh: DB 업그레이드 필요` |
| 마이그레이션 실행 절차 없음 | 앱 기동 시 `alembic upgrade`를 하지 않음(`create_all`도 없음) | 배포마다 **migrate Job(또는 initContainer) 1회** 실행 → 그 뒤 Deployment 롤아웃. 여러 replica가 동시에 돌리지 않게(ROADMAP Phase 4 미결 항목) |
| `AUTO_SEED_IF_EMPTY` | true면 빈 설비유형에 mock 30건 자동 투입 | 운영은 **반드시 false**(기본값 false — ConfigMap에서 명시) |
| SQLite 기본값 | `DATABASE_URL` 없고 `DB_HOST`도 없으면 `./eflms.db`로 폴백 | 컨테이너 파일은 재시작 시 사라짐 → 운영은 PostgreSQL만. 기동 로그로 DB 대상 확인 |
| nginx 설정이 개발용 | `nginx/nginx.conf.template`은 `/`를 vite dev server로 프록시 | 운영용 별도 설정: 정적 서빙 + `try_files $uri $uri/ /index.html`(라우터가 `createWebHistory` — 없으면 새로고침 시 404) + (단일 도메인이면) `/api` → backend Service 프록시 |
| DB 이관(다른 PostgreSQL로 통째로) | 관리자 화면 데이터 입력 탭 → **전체 DB 내려받기(.sql)**(Stage 16-8) — 원본이 SQLite여도 PostgreSQL 문법 | 새 서버에서 빈 DB 생성 → `psql -v ON_ERROR_STOP=1 -d <DB> -f <파일>`(한 트랜잭션, alembic 버전 포함) → `alembic current`가 head인지 확인 → 앱의 `DATABASE_URL`/`DB_*`를 새 DB로. 파일에 접근 권한 명단이 있으니 Secret처럼 다룰 것 |
| 관리자 SQL 조회의 테이블 제한(Stage 16-5) | SQLite는 코드가 허용 목록 테이블만 읽게 막지만, PostgreSQL은 읽기 전용 트랜잭션·5초 제한만 코드로 건다 | 운영 전 **읽기 전용 DB 계정**(허용 목록 테이블에만 SELECT 권한, `allowed_users`·`alembic_version` 제외)을 만들어 SQL 조회 전용 연결로 쓰도록 별도 작업(코드 변경, 별도 계획) — 그 전까지는 admin만 쓰는 기능이라는 점을 감안 |
| `/healthz`가 DB를 안 봄 | `{"status":"ok"}`만 반환 | liveness로는 충분. readiness에 DB 확인이 필요하면 별도 엔드포인트 추가(코드 변경, 선택) |
| 베이스 이미지 버전 | a-ims-prod 예시는 `node:20`/`python:3.12` | eflms 기준 **Node 22 / Python 3.11** (루트 `CLAUDE.md` 기술스택) |
| 실데이터 투입 | CLI `python -m app.db.import_data --file ... --ef-code ... --replace`만 있음 | 1절 #5 답에 맞춰 실행 방법 확정 — 유형별 독립 교체(한 유형만 `--replace`해도 다른 유형 불변) |

---

## 3. 체크리스트

### 3.1 소스코드

- [x] 시크릿 하드코딩 없음 — 전부 env(`docs/SECURITY_ENV.md`)
- [x] `.env` git 제외, `backend/.env.example`·`frontend/.env.example` 존재
- [x] `requirements.txt` 전 패키지 버전 고정, `package-lock.json` 커밋됨
- [x] Health Check — `GET /healthz`
- [x] API prefix `/api`로 통일, 프론트는 상대경로 호출(`VITE_API_BASE_URL` 비움)
- [x] CORS는 `CORS_ORIGINS` env로 주입
- [x] 외부 CDN·웹폰트 의존 없음(사내망 단독 동작)
- [x] DB 접속: `DATABASE_URL` → `DB_HOST` 조합 → SQLite 폴백 (`app/core/config.py`)
- [x] 인증 모드 설정 오타·빈 값이면 기동 실패 + 기동 로그 `EFLMS auth config: ...` 한 줄
- [ ] `TZ=Asia/Seoul` 적용 확인(Dockerfile 또는 Deployment env)
- [ ] 운영 nginx 설정 파일 작성(2절)
- [ ] (선택) readiness용 DB 확인 엔드포인트
- [?] 프론트/백엔드 도메인 분리 여부(1절 #2) → `VITE_API_BASE_URL`·`CORS_ORIGINS`·`FRONTEND_BASE_URL` 값

### 3.2 Docker

- [?] Dockerfile을 직접 둘지 PDEP 내장 빌드인지(1절 #4)
- [ ] backend Dockerfile — `python:3.11-slim`, non-root, `tzdata`, `.dockerignore`(`.venv`, `*.db`, `.env`, `__pycache__`, `*.log`)
- [ ] frontend Dockerfile — multi-stage(`node:22` 빌드 → nginx 정적 서빙), `npm ci`, `.dockerignore`(`node_modules`, `dist`, `.env`)
- [?] 베이스 이미지 사내 허용 목록
- [ ] 로컬 `docker build` 성공, 컨테이너 재시작 후 정상, `/healthz` 응답
- [ ] 런타임 env 반영 확인(기동 로그 auth 요약 + DB 대상)

### 3.3 GitHub

- [?] 레포 분리 여부(1절 #1) — 분리 시 `git filter-repo --path backend/ --path-rename backend/:` 방식으로 히스토리 보존
- [ ] 브랜치 전략·보호 규칙, Jenkins webhook·접근 권한
- [ ] 푸시 전 민감정보 검사(`.env`, `*.db`, `backend/certs/*.pem` 미포함 확인)
- [ ] README에 배포·롤백·로그 확인 방법 추가

### 3.4 Jenkins

- [?] PDEP 표준 Jenkinsfile 템플릿 문법, agent의 Node 22 / Python 3.11 존재 여부
- [?] npm·PyPI 사내 미러, 레지스트리 자격증명
- [ ] 테스트 단계 — backend `pytest`, frontend `npm run test` + `npm run build`(`vue-tsc -b` 포함). 실패 시 배포 중단
- [ ] 이미지 태그 규칙 — `latest` 금지, git SHA 또는 날짜+SHA
- [ ] dev/prod 배포 조건 분리, prod 승인 방식, 알림

### 3.5 PDEP / Kubernetes

- [?] Namespace(dev/prod), Ingress 방식(1절 #2), imagePullSecret
- [ ] ConfigMap — `APP_ENV`, `DB_HOST`/`DB_PORT`/`DB_NAME`, `CORS_ORIGINS`, `AUTH_MODE`, `SSO_FLOW_MODE`, `SSO_ISSUER_URL`, `SSO_REDIRECT_URI`, `SSO_USER_ID_CLAIM`, `SSO_CA_BUNDLE_PATH`, `FRONTEND_BASE_URL`, `AUTO_SEED_IF_EMPTY=false`, `SESSION_COOKIE_SECURE=true`, `TZ=Asia/Seoul`
- [ ] Secret — `DB_USER`/`DB_PASSWORD`, `SSO_CLIENT_ID`/`SSO_CLIENT_SECRET`, `SESSION_SECRET_KEY`, `ADMIN_BOOTSTRAP_PASSWORD`, 사내 CA 인증서(볼륨 마운트)
- [ ] ConfigMap에 **빈 값으로 키만 두지 않기** — OS 환경의 빈 문자열이 기본값보다 우선한다(`backend/app/auth/SSO_MODES.md`, a-ims-prod가 실제로 겪음)
- [ ] backend Deployment `replicas: 1`(2절 세션 문제), requests/limits, readiness·liveness probe(`/healthz`)
- [ ] migrate Job — 롤아웃 전 `alembic upgrade head` 1회
- [ ] frontend Deployment + Service
- [ ] 로그(파드 로그), 모니터링(Prometheus/Grafana 기본 제공 여부), 롤백 방법 확인

### 3.6 SSO

- [x] `auth_code`(ADFS 직접 연결) 기본값, discovery 미지원 브로커용 `implicit_form_post`도 지원
- [x] 사내 CA 번들 경로 설정 지원(`SSO_CA_BUNDLE_PATH`)
- [?] ADFS client 등록, 운영 redirect URI(`https://<운영도메인>/api/admin/sso/callback`), 사용자 식별 클레임
- [ ] 최초 관리자 — `SSO_ADMIN_ALLOWLIST`로 브레이크글래스 등록 후 화면에서 사용자 추가
- [ ] 배포 후 파드 안 실제 값 확인: `kubectl exec <pod> -- env | grep -E "AUTH_MODE|SSO_"`

### 3.7 데이터

- [ ] 빈 PostgreSQL에 `alembic upgrade head`(migrate Job)
- [?] 실데이터 파일 투입 경로(1절 #5)
- [ ] 유형별 투입 — `python -m app.db.import_data --file <파일> --ef-code EF1 --replace`, EF2 동일. EF2는 사내 파일 헤더가 `ef2_gis.INPUT_COLUMNS`와 맞는지 먼저 확인
- [ ] 투입 전 DB 백업(`pg_dump`) 절차

---

## 4. 배포 완료 판정 기준

1. `GET /healthz` → `{"status":"ok","app_env":"production"}`(값은 ConfigMap의 `APP_ENV`)
2. backend 파드 로그에 `EFLMS auth config: auth_mode=sso ...` — 의도한 모드·플로우인지
3. 대시보드 접속 → 설비유형별 설비 수 표시, 상세 패널 열림, 새로고침(딥링크) 시 404 없음
4. SSO 로그인 → 등록 사용자 세션 발급, 미등록 사용자 거부
5. migrate Job 성공, mock 데이터 미투입(`AUTO_SEED_IF_EMPTY=false`)

## 5. 롤백

- **앱**: 이전 이미지 태그로 Deployment 되돌림(PDEP/Helm 롤백). 태그를 SHA로 관리해야 가능
- **DB**: 롤백 전 `pg_dump` 백업. 새 마이그레이션이 포함된 배포였다면 `alembic downgrade <이전 revision>` 가능 여부를 먼저 판단 — 데이터 손실 가능 마이그레이션은 백업 복원이 우선
- **데이터 투입 실수**: 먼저 관리자 화면 **"변경 이력" → 되돌리기**(Stage 21-4 — 그 변경 전 값·반영일로 복원, 점수는 오늘 기준 재계산). 이력이 없는 오래된 변경이면 해당 유형만 이전 파일로 `--replace` 재투입(유형 간 독립). 자세한 순서는 7절

---

## 6. 매니페스트 초안 (예시 — 1절 답 이후 확정)

### backend Dockerfile

```dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 TZ=Asia/Seoul
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* && useradd -m -u 10001 app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

### frontend Dockerfile + 운영 nginx 설정

```dockerfile
FROM node:22 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# 도메인 분리 시에만 값 주입(Vite env는 빌드 시점에 번들에 고정됨). 단일 도메인이면 비움.
ARG VITE_API_BASE_URL=
RUN echo "VITE_API_BASE_URL=${VITE_API_BASE_URL}" > .env.production && npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;

    # 단일 도메인 + 프로젝트 nginx가 프록시하는 경우에만. Ingress가 /api를 나누면 제거.
    location /api/ {
        proxy_pass http://eflms-backend:8000/api/;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;   # Vue Router history 모드
    }
}
```

### migrate Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: eflms-migrate-<태그>
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: <레지스트리>/eflms-backend:<태그>
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef: { name: eflms-backend-config }
            - secretRef: { name: eflms-backend-secret }
```

### backend Deployment + Service

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eflms-backend
spec:
  replicas: 1                     # 관리자 세션이 메모리 저장 — 늘리기 전에 세션 저장소 이전
  selector: { matchLabels: { app: eflms-backend } }
  template:
    metadata: { labels: { app: eflms-backend } }
    spec:
      imagePullSecrets: [{ name: <pull-secret> }]
      containers:
        - name: backend
          image: <레지스트리>/eflms-backend:<태그>
          ports: [{ containerPort: 8000 }]
          envFrom:
            - configMapRef: { name: eflms-backend-config }
            - secretRef: { name: eflms-backend-secret }
          readinessProbe: { httpGet: { path: /healthz, port: 8000 }, periodSeconds: 10 }
          livenessProbe:  { httpGet: { path: /healthz, port: 8000 }, initialDelaySeconds: 15, periodSeconds: 20 }
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits:   { cpu: 500m, memory: 512Mi }
          volumeMounts:
            - { name: corp-ca, mountPath: /etc/eflms/certs, readOnly: true }   # SSO_CA_BUNDLE_PATH=/etc/eflms/certs/ca.pem
      volumes:
        - name: corp-ca
          secret: { secretName: eflms-corp-ca }
---
apiVersion: v1
kind: Service
metadata:
  name: eflms-backend
spec:
  selector: { app: eflms-backend }
  ports: [{ port: 8000, targetPort: 8000 }]
```

frontend Deployment/Service는 같은 형태(포트 80, probe `/`)로 둔다. Ingress는 1절 #2 답에 따라 PDEP 표준 Chart 값으로 작성한다.

### (선택) 점수 갱신 CronJob

서버가 시작될 때와 날짜가 바뀐 뒤 스스로 점수를 갱신하므로(Stage 21-1b, `SCORE_REFRESH_AUTO=true` 기본) **필수가 아니다**. 서버 자동 갱신을 끄는 환경(`SCORE_REFRESH_AUTO=false`)이거나, 백엔드와 별도로 갱신 기록을 남기고 싶을 때만 둔다. 서버와 동시에 돌아도 데이터 작업 잠금(`data_job_lock`) 때문에 한쪽만 갱신하고, 이미 오늘 기준이면 다시 계산해도 결과가 같다.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: eflms-score-refresh
spec:
  schedule: "30 0 * * *"          # 매일 00:30
  timeZone: "Asia/Seoul"           # k8s 1.27+. 없으면 UTC 기준 "30 15 * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 1
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: refresh
              image: <레지스트리>/eflms-backend:<태그>
              command: ["python", "-m", "app.db.recalculate", "--ef-code", "all", "--as-of", "today", "--trigger", "schedule"]
              envFrom:
                - configMapRef: { name: eflms-backend-config }
                - secretRef: { name: eflms-backend-secret }
```

종료 코드: 성공 0, 일부·전부 실패 또는 다른 작업 진행 중·DB 업그레이드 필요 1(실행 기록은 관리자 "데이터 입력" 탭 맨 위 "점수 갱신" 카드).

---

## 7. 데이터 백업·복구 (Stage 21-5, 2026-11-19)

### 7.1 무엇이 어디에 남나

| 무엇 | 어디 | 보관 | 되살리는 방법 |
|---|---|---|---|
| 지금 입력값·점수 | 설비유형 테이블, `score_snapshot`, `*_score_detail` | 최신 1행 | — |
| 점수 이력 | `score_history`(설비 유형·사업장·이름 + 점수 기준일별 1행) | 계속 쌓임(305대 × 365일 ≈ 11만 행/년) | 조회 전용(`/api/equipment/{id}/history`) |
| 입력 변경 이력 | `data_change` / `data_change_row`(바뀌기 전후 입력값 JSON) | 계속 쌓임 | 관리자 "변경 이력" → 되돌리기 |
| 점수 갱신 기록 | `score_refresh_run` | 계속 쌓임 | 점수는 `python -m app.db.recalculate`로 언제든 다시 계산 가능 |
| DB 전체 | PostgreSQL | **운영팀 백업(아래)** | `pg_restore` / `psql` |

이력 테이블은 지우지 않는다(용량이 커지면 별도 계획으로 기간 정리). 21-4 이전의 변경과 개발용 명령(`app.db.seed`/`app.db.reset`)은 기록되지 않는다.

### 7.2 사내 운영팀에 요청할 백업(1절 질문에 추가)

- [ ] PostgreSQL **매일 백업**(`pg_dump -Fc`, 보관 기간 예: 30일) — PDEP 관리형 DB면 제공 기능 확인, 아니면 아래 CronJob 초안
- [ ] 배포(특히 마이그레이션 포함) 직전 수동 백업 절차
- [ ] 복원 연습 1회(복원 DB에서 `/healthz`·대시보드·관리자 "변경 이력" 확인)

```yaml
# (예시) 백업 CronJob — 저장 위치(PVC/오브젝트 스토리지)는 운영팀 표준에 맞춘다
apiVersion: batch/v1
kind: CronJob
metadata:
  name: eflms-db-backup
spec:
  schedule: "0 2 * * *"
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: backup
              image: postgres:17
              command: ["sh", "-c", "pg_dump -Fc \"$DATABASE_DSN\" > /backup/eflms-$(date +%Y%m%d).dump"]
              envFrom:
                - secretRef: { name: eflms-backup-secret }   # DATABASE_DSN(postgresql://… — asyncpg 접두어 없이)
              volumeMounts:
                - { name: backup, mountPath: /backup }
          volumes:
            - name: backup
              persistentVolumeClaim: { claimName: eflms-backup }
```

관리자 화면의 "전체 DB .sql 내려받기"(Stage 16-8)는 수동 보관용 보조 수단이다 — 정기 백업을 대신하지 않는다.

### 7.3 문제가 생겼을 때 순서

1. **잘못 넣은 데이터(최근)** — 관리자 **"변경 이력"**에서 해당 변경을 골라 되돌리기. 그 뒤에 같은 데이터를 바꾼 변경이 있으면 최근 것부터. 되돌리면 이전 값·이전 진단 데이터 반영일로 돌아가고 점수는 오늘 기준으로 다시 계산된다. 되돌리기 자체도 기록된다(다시 되돌리지는 않는다 — 필요하면 데이터를 다시 입력).
2. **점수만 이상(계산 규칙 변경·참고표 실수 뒤)** — 참고표는 1과 같이 되돌리고, 점수는 `python -m app.db.recalculate --ef-code all --as-of today`(또는 관리자 "지금 갱신").
3. **이력이 없는 오래된 변경·대량 손상** — 해당 유형만 보관한 원본 파일로 `python -m app.db.import_data --file <파일> --ef-code EF<N> --replace`(이것도 변경 이력에 남는다).
4. **DB 전체 손상·마이그레이션 실패** — 앱을 내리고(replicas 0) 운영팀 백업으로 복원 → 이미지가 기대하는 리비전인지 확인(`alembic current`, 아니면 `alembic upgrade head`) → 앱 기동. 서버가 시작되면 점수 기준일이 오늘보다 이전인 설비를 자동으로 다시 계산한다.

DB 버전이 코드보다 낮으면 서버는 갱신·임포트를 하지 않고 "DB 업그레이드 필요"를 로그·관리자 화면에 띄운다(Stage 21-1b) — 먼저 `alembic upgrade head`.

