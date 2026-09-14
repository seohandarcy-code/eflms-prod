# EFLMS — 전기설비수명관리시스템

변압기(EF1)를 시작으로 전기설비의 자산 건전성을 PoF(고장확률)·CoF(고장영향)·DoF(설계/방어수준) 3축으로 평가하고, 웹 대시보드로 보여주는 사내 시스템. FastAPI 백엔드 + Vue 3 프론트엔드 + SQLite(개발)/PostgreSQL(운영 예정) 구조입니다.

현재 단계: Phase 1(mock 데이터 대시보드) 완료, Phase 2(운영 데이터 임포트 파이프라인) 진행 중. 자세한 진행 상황은 [docs/ROADMAP.md](docs/ROADMAP.md) 참고.

## 요구 사항

- **Python 3.11**
- **Node.js 22 LTS** — `frontend/.nvmrc`에 버전이 고정되어 있음. `nvm` 사용 시 `frontend/`에서 `nvm install && nvm use`로 맞출 수 있음(다른 버전의 Node가 시스템에 이미 깔려 있어도 무관 — 이 프로젝트에서만 22를 쓰면 됨).

## 클론

```bash
git clone https://github.com/seohandarcy-code/eflms_dev.git
cd eflms_dev
```

## 백엔드 실행

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.db.seed --rows 30
.venv\Scripts\uvicorn app.main:app --reload

# macOS / Linux
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed --rows 30
.venv/bin/uvicorn app.main:app --reload
```

- `.env`는 값을 로컬에 맞게 조정(기본값으로도 로컬 실행은 가능).
- `alembic upgrade head`가 DB 스키마(`backend/eflms.db`, SQLite)를 만듦.
- `app.db.seed --rows 30`은 화면을 바로 확인할 수 있도록 **mock(가짜) 데이터**를 30건 채워 넣음 — 실제 운영 데이터는 아래 "운영 데이터로 바꾸기" 참고.
- 기동 확인: `http://localhost:8000/healthz`

## 프론트엔드 실행

```bash
cd frontend
npm install
cp .env.example .env   # Windows는 copy .env.example .env
npm run dev
```

브라우저에서 `http://localhost:5173` 접속. `VITE_API_BASE_URL`(기본 `http://localhost:8000`)로 위 백엔드를 호출하므로, 백엔드가 먼저 떠 있어야 함.

## 운영 데이터로 바꾸기

지금은 mock 데이터로 시드되어 있음. 실제 사내 입력파일(.dat, 탭구분)을 반영하려면:

```bash
cd backend
.venv/Scripts/python -m app.db.import_data --file <파일경로> --ef-code EF1
```

먼저 아래처럼 샘플 파일로 바로 실행해볼 수 있음(mock 스키마 기준으로 만든 100행짜리 연습용 파일, 실제 회사 파일 아님):

```bash
.venv/Scripts/python -m app.db.import_data --file sample_data/sample_valid.dat --ef-code EF1
```

`backend/sample_data/`에는 이 정상 케이스 외에 오류/미등록컬럼 케이스 파일도 있고(`sample_with_errors.dat`, `sample_with_extra_columns.dat`), `python scripts/generate_sample_dat.py`로 재생성 가능. 컬럼명이 실제 파일과 다르거나 날짜 형식이 다를 때 무엇을 고쳐야 하는지는 [backend/CLAUDE.md](backend/CLAUDE.md)의 "운영 데이터 임포트" 섹션에 정리되어 있음.

## 테스트

```bash
# 백엔드
cd backend && .venv/Scripts/pytest        # Windows
cd backend && .venv/bin/pytest            # macOS/Linux

# 프론트엔드
cd frontend && npm run test -- --run
```

## 저장소 구조

| 경로 | 내용 |
|---|---|
| `backend/` | FastAPI + SQLAlchemy(async) + Alembic. 세부 컨벤션·명령어는 [backend/CLAUDE.md](backend/CLAUDE.md) |
| `frontend/` | Vue 3 + Vite + Pinia + Element Plus. 세부 컨벤션은 [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| `docs/` | 아키텍처([ARCHITECTURE.md](docs/ARCHITECTURE.md)) · 데이터 사전([DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) · 로드맵([ROADMAP.md](docs/ROADMAP.md)) · 보안/env([SECURITY_ENV.md](docs/SECURITY_ENV.md)) |
| `ref_data/` | 엑셀 기반 원본 계산 로직 참고자료 — **읽기 전용**, 수정하지 않음 |
| `design/` | 확정된 대시보드 디자인(Direction A) 목업 작업 파일 |

## 작업 방식

이 저장소의 모든 실제 작업(코드/설정 변경, DB 조작, git 조작 등)은 "구체적인 계획 제시 → 승인" 절차를 거쳐 진행합니다. 자세한 내용은 루트 [CLAUDE.md](CLAUDE.md) 참고.
