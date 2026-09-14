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

## 운영 데이터 임포트 (Phase 2)

사내 입력파일(.dat, 탭구분)을 읽어 DB에 반영하는 CLI. mock 시드(`app/db/seed.py`)와 동일하게 `ef1_transformer.calculate()` → `ingest.ingest_row()` 경로를 그대로 탄다 — 화면·계산 로직·DB 스키마는 전혀 바뀌지 않고, "DB를 채우는 방법"만 하나 늘어나는 구조다.

```bash
cd backend
.venv/Scripts/python -m app.db.import_data --file sample_data/sample_valid.dat --ef-code EF1
```

- 결과는 콘솔 요약 + JSON 로그 한 줄(`app/db/import_data.py`)로 남는다.
- 파일 안에 알려진 컬럼(`ef1_transformer.INPUT_COLUMNS`)에서 값 형식이 틀린 행이 하나라도 있으면 **그 파일은 통째로 반영되지 않는다**(부분 반영 금지) — 오류 목록만 출력됨.
- 모르는 컬럼(헤더가 `INPUT_COLUMNS`의 `name`에 없음)은 실패시키지 않고 `equipment_extra_attribute` 테이블에 원문 그대로 보관된다.

**테스트용 샘플 3종** — `backend/sample_data/`에 있음(실제 회사 파일이 아니라 mock 스키마로 만든 연습용). `python scripts/generate_sample_dat.py`로 재생성 가능.
- `sample_valid.dat` — 정상 케이스
- `sample_with_errors.dat` — 3번째 행 `voltage`(전압)가 숫자가 아닌 값 → 전체 반영 실패 확인용
- `sample_with_extra_columns.dat` — "점검자"/"비고" 같은 미등록 컬럼 포함 → `equipment_extra_attribute` 적재 확인용

**실제 사내 .dat 파일로 바꾸려면 이 3가지만 확인하면 됨:**
1. **컬럼 이름 맞추기** — 실제 파일의 헤더는 `app/equipment_types/ef1_transformer.py`의 `INPUT_COLUMNS`에 있는 `name`(영문)과 정확히 일치해야 매칭된다(사내 입력파일은 영문 헤더로만 오는 것으로 확인됨 — `label`(한글)은 각 항목이 무엇인지 설명하는 문서용 메타데이터일 뿐 매칭에는 쓰이지 않는다). 실제 파일 헤더가 다르면 **`INPUT_COLUMNS`의 `name` 값 자체를 실제 헤더 표기에 맞게 고치는 것**이 방법(새 컬럼을 추가할 필요는 없음). 안 맞는 컬럼은 실패하지 않고 `equipment_extra_attribute`로 빠지니, 처음엔 그냥 돌려보고 "미등록 컬럼" 목록으로 뭐가 안 맞는지 확인한 뒤 `name`을 맞춰가는 방식도 가능.
2. **날짜 형식** — 지금은 `YYYY-MM-DD` 고정(`import_service.py`의 `_cast_value`). 실제 파일이 다른 형식(`YYYY.MM.DD` 등)이면 그 함수의 date 분기만 수정.
3. **실행 시 `--file`을 실제 파일 경로로** — `python -m app.db.import_data --file <실제파일경로> --ef-code EF1`. 인코딩(UTF-8/CP949)은 자동으로 시도하므로 별도 설정 불필요.

## 컨벤션

- 시크릿은 `.env`로만 주입, 코드에 하드코딩 금지
- 새 설비유형 추가 시 기존 설비유형 코드/공통 테이블 변경 금지
