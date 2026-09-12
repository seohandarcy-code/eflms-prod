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

## 구조

- `app/core/` — 설정(`config.py`, env 기반) · 인증 추상화(`security.py`)
- `app/db/` — SQLAlchemy `Base`, 세션 팩토리 (`DATABASE_URL` 기반, SQLite↔PostgreSQL 무변경 전환)
- `app/api/routes/` — FastAPI 라우터
- `app/schemas/` — pydantic 요청/응답 모델
- `app/services/` — 비즈니스 로직 (라우터에서 DB 직접 쿼리 금지, 여기 경유)
- `app/equipment_types/` — 설비유형별 계산기 모듈 (`ef1_transformer.py` 등)

## 컨벤션

- 시크릿은 `.env`로만 주입, 코드에 하드코딩 금지
- 새 설비유형 추가 시 기존 설비유형 코드/공통 테이블 변경 금지
