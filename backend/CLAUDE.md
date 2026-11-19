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

**주의 — 폴더 이동/이름변경 후 `.venv/Scripts/*.exe`가 깨질 수 있음**: Python venv의 `Scripts/uvicorn.exe` 등 실행 파일은 생성 당시 절대경로를 내부에 캐싱하고 있어서, 프로젝트 폴더를 옮기거나 이름을 바꾸면 에러 메시지 없이 즉시 종료될 수 있다. 이 증상이 보이면 `.venv/Scripts/uvicorn.exe app.main:app` 대신 `.venv/Scripts/python.exe -m uvicorn app.main:app`처럼 **`python -m <모듈>` 형태로 우회**하면 즉시 해결됨(재설치 불필요). 완전히 정리하려면 `.venv` 삭제 후 `python -m venv .venv`로 재생성.

## 구조

- `app/core/` — 설정(`config.py`, env 기반) · 인증 추상화(`security.py` — 지금은 안 쓰는 초기 자리, 실제 인증은 `app/auth/` + `app/api/deps.py`)
- `app/db/` — SQLAlchemy `Base`, 세션 팩토리 (`DATABASE_URL` 기반, SQLite↔PostgreSQL 무변경 전환)
- `app/api/routes/` — FastAPI 라우터
- `app/schemas/` — pydantic 요청/응답 모델
- `app/services/` — 비즈니스 로직 (라우터에서 DB 직접 쿼리 금지, 여기 경유)
- `app/equipment_types/` — 설비유형별 계산기 모듈 (`ef1_transformer.py` 등)

## 운영 데이터 임포트 (Phase 2)

사내 입력파일(.dat, 탭구분)을 읽어 DB에 반영하는 CLI. mock 시드(`app/db/seed.py`)와 동일하게 `<설비유형 모듈>.calculate()` → `ingest.ingest_row()` 경로를 그대로 탄다 — 화면·계산 로직·DB 스키마는 전혀 바뀌지 않고, "DB를 채우는 방법"만 하나 늘어나는 구조다. 컬럼 정의와 계산기는 `--ef-code`로 레지스트리(`app/equipment_types/registry.py`)에서 고른다.

```bash
cd backend
.venv/Scripts/python -m app.db.import_data --file sample_data/ef1/sample_valid.dat --ef-code EF1            # 추가/갱신
.venv/Scripts/python -m app.db.import_data --file sample_data/ef1/sample_valid.dat --ef-code EF1 --replace  # EF1만 교체
.venv/Scripts/python -m app.db.import_data --file sample_data/ef1/sample_valid.dat --ef-code EF1 --check    # 검증·계산만(DB 미반영)
```

- 결과는 콘솔 요약 + JSON 로그 한 줄(`app/db/import_data.py`)로 남는다. 종료 코드: 성공 0, 실패 1(`--check`도 동일).
- 처리 순서(`import_service.import_file`): 헤더 매칭 → 행 검증(형식·허용값·칸 수·파일 내 중복) → **전 행 계산**(실패 시 그 행 번호로 행 오류) → `--check`면 여기서 종료 → 저장(한 트랜잭션). 행 번호는 빈 줄을 포함한 실제 파일 줄 번호.
- 받아주는 표기(2026-10-19): UTF-8 BOM(`utf-8-sig`), 값/헤더를 감싼 따옴표, 정수 칸의 `154000.0`(소수면 거부), 날짜 `YYYY-MM-DD`/`YYYY.MM.DD`/`YYYY/MM/DD`/`YYYYMMDD`(`DATE_FORMATS`). float 칸의 `nan`/`inf`는 거부. 빈 숫자/날짜는 "빈 값" 행 오류(원본 계산식이 빈 값을 처리하지 않음).
- 헤더와 칸 수가 다른 행, 같은 설비(`factory_code` + 유형의 `NAME_FIELD`)가 파일에 두 번 나오는 행은 행 오류 — 예전엔 각각 계산 중 `KeyError` rollback, 뒤 행이 앞 행을 조용히 덮어쓰기였다.
- 파일 안에 알려진 컬럼(`ef1_transformer.INPUT_COLUMNS`)에서 값 형식이 틀린 행이 하나라도 있으면 **그 파일은 통째로 반영되지 않는다**(부분 반영 금지) — 오류 목록만 출력됨. 검증 통과 후 반영 도중 실패해도 파일 전체가 rollback된다(파일 1건 = 트랜잭션 1건, `ingest_row`는 commit하지 않음).
- 행의 `EF_code`가 `--ef-code`와 다르거나 등록되지 않은 유형이면 거부.
- 모르는 컬럼(헤더가 `INPUT_COLUMNS`의 `name`에 없음)은 실패시키지 않고 `equipment_extra_attribute` 테이블에 원문 그대로 보관된다.

**테스트용 샘플 3종** — `backend/sample_data/<유형 소문자>/`(예: `ef1/`)에 있음(실제 회사 파일이 아니라 mock 스키마로 만든 연습용). `python scripts/generate_sample_dat.py --ef-code EF1`로 재생성 가능(`all`이면 등록된 전 유형).
- `sample_valid.dat` — 정상 케이스
- `sample_with_errors.dat` — 3번째 행 `voltage`(전압)가 숫자가 아닌 값 → 전체 반영 실패 확인용
- `sample_with_extra_columns.dat` — "점검자"/"비고" 같은 미등록 컬럼 포함 → `equipment_extra_attribute` 적재 확인용

**실제 사내 .dat 파일로 바꾸려면 이 3가지만 확인하면 됨:**
1. **컬럼 이름 맞추기** — 실제 파일의 헤더는 `app/equipment_types/ef1_transformer.py`의 `INPUT_COLUMNS`에 있는 `name`(영문)과 정확히 일치해야 매칭된다(사내 입력파일은 영문 헤더로만 오는 것으로 확인됨 — `label`(한글)은 각 항목이 무엇인지 설명하는 문서용 메타데이터일 뿐 매칭에는 쓰이지 않는다). 실제 파일 헤더가 다르면 **`INPUT_COLUMNS`의 `name` 값 자체를 실제 헤더 표기에 맞게 고치는 것**이 방법(새 컬럼을 추가할 필요는 없음). 안 맞는 컬럼은 실패하지 않고 `equipment_extra_attribute`로 빠지니, 처음엔 그냥 돌려보고 "미등록 컬럼" 목록으로 뭐가 안 맞는지 확인한 뒤 `name`을 맞춰가는 방식도 가능.
2. **날짜 형식** — `YYYY-MM-DD`, `YYYY.MM.DD`, `YYYY/MM/DD`, `YYYYMMDD`를 받는다(`import_service.py`의 `DATE_FORMATS`/`_parse_date`). 그 외 형식이면 거기에 추가.
3. **실행 시 `--file`을 실제 파일 경로로** — `python -m app.db.import_data --file <실제파일경로> --ef-code EF1 --replace`(mock을 걷어내고 실데이터로 교체). 인코딩(UTF-8/CP949)은 자동으로 시도하므로 별도 설정 불필요.

## 등록된 설비유형

| EF_code | 모듈 | 전용 테이블 | 샘플 |
|---|---|---|---|
| EF1 변압기 | `app/equipment_types/ef1_transformer.py` | `transformer_spec`, `dga_reading` 외 7개, `transformer_score_detail` | `sample_data/ef1/` |
| EF2 GIS | `app/equipment_types/ef2_gis.py` | `gis_operation`, `gis_diagnosis`, `gis_sf6_reading`, `gis_consequence_attribute`, `gis_design_attribute`, `gis_score_detail` | `sample_data/ef2/` |
| EF3 초고압케이블 | `app/equipment_types/ef3_cable.py` | `cable_spec`, `cable_condition`, `cable_consequence_attribute`, `cable_design_attribute`, `cable_score_detail` | `sample_data/ef3/` |
| EF4 수배전반 | `app/equipment_types/ef4_switchgear.py` | `switchgear_spec`, `switchgear_condition`, `switchgear_consequence_attribute`, `switchgear_design_attribute`, `switchgear_score_detail` | `sample_data/ef4/` |
| EF5 UPS | `app/equipment_types/ef5_ups.py` | `ups_spec`, `ups_condition`, `ups_consequence_attribute`, `ups_design_attribute`, `ups_score_detail` | `sample_data/ef5/` |
| EF6 VDP | `app/equipment_types/ef6_vdp.py` | `vdp_spec`, `vdp_condition`, `vdp_consequence_attribute`, `vdp_design_attribute`, `vdp_score_detail` | `sample_data/ef6/` |
| EF7 배터리 | `app/equipment_types/ef7_battery.py` | `battery_spec`, `battery_condition`, `battery_consequence_attribute`, `battery_design_attribute`, `battery_score_detail` + 참고표 `battery_discharge_history`, `battery_temp_decay_coef` | `sample_data/ef7/`(설비 3종 + `reference_*.dat`) |

- EF2~EF7은 임포트 허용값(`choices`/`min`/`max`/`required`)을 선언해 둬서 오류값(예: EF2 소문자 `c`·154k/345k 외 전압·순도 100 초과, EF3 원본 판정에 없는 포설방법·회선별용량 0, EF4 `양호`/`불량` 외 점검결과·목록에 없는 설치건물)을 행 오류로 거부한다. EF4~EF7은 원본에 전압이 없어 `calculate()`가 `voltage=0`을 채운다(공통 `equipment.voltage` 필수). 목록은 `docs/DATA_DICTIONARY.md` 각 유형 절.
- 값 없음: 입력파일의 `N/A`·`n/a`·`#N/A`는 null로 저장되고 계산에서 그 감점은 0이다(`app/equipment_types/na.py`의 `evaluate()` — 네 유형의 `calculate()`가 공통 사용, Stage 11). 사업장·`EF_code`·설비명·가동년월·전압은 N/A 불가(`import_service.NOT_NULLABLE_COLUMNS` + `NAME_FIELD`). 새 유형도 `calculate()`에서 `evaluate()`를 쓰고 입력 컬럼을 null 허용으로 둔다.
- 점수 지표(POF·COF·DOF 감점/점수, 종합점수)와 모든 감점 항목(`_minus`)은 `na.evaluate()`가 float·소수 첫째 자리로 반올림한다(엑셀 ROUND식 5에서 올림, `app/equipment_types/rounding.py`, Stage 13-0 / Stage 20). 감점은 정수 반올림 없이 소수로 계산한다(2026-11-19 — 경과연수 = -운전년수 등, 원본과의 의도적 차이 목록은 `docs/DATA_DICTIONARY.md` "감점 소수 계산"). 새 유형도 감점 공식에 `round()`/`int()`/`floor()`를 쓰지 않는다. 원본 대조 테스트는 `tests/reference_rules.py`(원본 공식 + 바꾼 공식 + 같은 반올림). 감점·점수 컬럼은 모두 FLOAT.
- 점수 재계산·갱신(Stage 20 / 21-1): `python -m app.db.recalculate --ef-code all|EF2 [--as-of today|YYYY-MM-DD] [--trigger cli|schedule]` — 저장된 입력값으로 다시 계산해 **점수 테이블만** 덮어쓴다(`ingest.save_scores` → 모듈 `ingest_scores` + `score_snapshot`, 입력 테이블·최근 진단일은 그대로). `--as-of` 생략 = 저장된 기준일(계산 규칙이 바뀐 뒤), `today` = 한국 시간 오늘(`app/core/clock.today_kst`). **매일 정기 실행**은 `--as-of today --trigger schedule`(PDEP CronJob, Stage 21-5에서 매니페스트). 서비스 `app/services/score_refresh_service.py`(유형마다 한 트랜잭션, 실패한 유형만 이전 점수 유지 → `partial`), 실행 기록 `score_refresh_run`. 관리자 API `GET/POST /api/admin/score-refresh`(admin, 진행 중이면 409).
- 데이터 작업 잠금(`app/services/job_lock.py`, 테이블 `data_job_lock`, 30분 만료): 점수 갱신·실제 반영 임포트(웹·명령·행 편집)·참고표 넣기/리셋이 잡는다. 잡혀 있으면 임포트는 파일 오류 "다른 데이터 작업(…)이 진행 중", 갱신 명령은 종료 코드 1. 검증만(`--check`)과 개발용 seed/reset은 잠그지 않는다. 새로 DB에 쓰는 관리 작업을 만들면 이 잠금을 잡는다.
- 원본엔 있지만 쓰지 않는 컬럼은 모듈의 `IGNORED_COLUMNS`(선택 속성)에 넣는다 — 임포트가 저장하지 않고 건너뛰고 결과에 "사용 안 하는 컬럼"으로 표시(미등록 컬럼처럼 `equipment_extra_attribute`에 쌓이지 않음). 현재 EF2 `cb_op_char_over`(2026-10-19 미사용 결정).
- 조회 API는 설비유형별로 동작한다(Stage 8-4, `docs/ARCHITECTURE.md` "조회 API"). 상세는 `type_detail`(EF1~EF7 union), 유형별 스키마는 `app/schemas/ef1.py`~`ef7.py`. EF6(VDP)은 지금 EF5(UPS)와 거의 같지만 앞으로 달라질 수 있어 코드를 공유하지 않는다. 화면은 8-5 전까지 `ef_code=EF1`만 요청한다.
- 설비유형 모듈의 조회용 인터페이스: `BREAKDOWN`(감점 라벨 메타), `calculate(row, as_of=)`(계산 기준일), `load_inputs`(저장값 → 계산 입력 복원 — 재계산하면 저장 점수와 같아야 함, `tests/test_type_queries.py`), `last_diag_dates`, `load_detail`.

## 참고표 (Stage 15-0 — EF7 배터리)

계산에 설비 밖의 표가 필요한 유형은 모듈에 `REFERENCE_TABLES`를 선언하고 `calculate(row, reference=...)`로 받는다. 계산기를 부르는 쪽은 `app/services/reference_data.calc_options()`를 펼쳐 넘긴다(참고표 없는 유형은 빈 dict). 형식·규칙은 `docs/ARCHITECTURE.md` "참고표", `docs/DATA_DICTIONARY.md` "EF7(배터리)".

```bash
cd backend
.venv/Scripts/python -m app.db.import_reference --ef-code EF7 --table discharge_history --file sample_data/ef7/reference_discharge_history.dat            # 넣기(같은 행 갱신·새 행 추가)
.venv/Scripts/python -m app.db.import_reference --ef-code EF7 --table temp_decay_coef --file sample_data/ef7/reference_temp_decay_coef.dat --replace    # 교체
.venv/Scripts/python -m app.db.import_reference --ef-code EF7 --table discharge_history --file <파일> --check                                            # 검증만
.venv/Scripts/python -m app.db.reset_reference --ef-code EF7 --table discharge_history|temp_decay_coef|all                                            # 비우기
.venv/Scripts/python -m app.db.seed --ef-code EF7 --rows 0                                                                                             # 빈 참고표에만 목업 다시 넣기
```
- 참고표가 바뀌면 같은 트랜잭션에서 그 유형 설비 점수를 전부 재계산한다(계산 기준일 유지). 오류가 한 행이라도 있으면 파일 전체 미반영, 종료 코드 1.
- 빈 표는 원본 수식대로 0으로 계산되고 경고만 나온다(설비 임포트 결과에도 표시). 설비 리셋은 참고표를 지우지 않는다.
- 테스트에서 DB 없이 계산할 때는 `reference_data.mock_reference(module)`.
- 사업장별 참고표(Stage 19): 참고표 정의에 `"scope": "factory_code"`(EF7 방전이력). 그 사업장 행이 없으면 시뮬레이터는 계산 거부, 설비 입력·참고표 재계산은 사업장별 경고만(`reference_data.calculable_sites` / `scope_warnings`).

## 점수 시뮬레이터 (Stage 19)

`/api/simulator/{ef}/form|sample|calculate` — `require_viewer`(대시보드와 같은 권한), `app/services/simulator_service.py`, DB 쓰기 없음. 양식은 `data_admin_service.template`, 값 검사는 `import_service`와 같은 함수(형식·허용값·N/A·필수 칸). 사업장은 DB에 그 유형 설비가 있고 사업장별 참고표에 행이 있는 곳만. 계산 기준일은 오늘. 테스트 `tests/test_simulator.py`.

## 관리자 웹 데이터 입력·내보내기 (Stage 16-2/16-3, 16-6 붙여넣기)

관리자 화면 "데이터 입력" 탭이 부르는 API(`app/api/routes/admin_data.py`, `require_admin`) — 명령줄과 **같은 서비스**(`import_service.import_file`, `reference_service.import_reference_file`)를 `app/services/data_admin_service.py`가 감싼다(붙여넣은 텍스트를 임시 파일로 넘기고 지움).
- `GET /api/admin/data/targets` — 유형별 설비 수·참고표 행 수
- `GET /api/admin/data/template?ef_code=&table=` — 붙여넣기 양식(헤더 순서·컬럼 설명·형식·허용값·N/A 가능 여부, 같은 행 판정 키)
- `POST /api/admin/data/import` (JSON: `ef_code`, `table`(빈 값 = 설비), `replace`, `check`, `text`=탭 구분 텍스트) — `check=true`(기본)면 검증·계산만. 결과는 CLI JSON 로그와 같은 필드 + `kind`·`ok`, 검증 통과 시 `row_actions`(행별 추가/갱신 — 교체면 전부 추가). 최대 5MB(413)
- `GET /api/admin/data/export?ef_code=&table=` — 지금 DB를 입력파일과 같은 dat로(UTF-8 BOM, null은 `N/A`, 날짜 `YYYY-MM-DD`, 임포트 때 보관한 미등록 컬럼 포함). 내보낸 파일을 교체로 다시 넣으면 점수가 같다(모든 유형 왕복 테스트 — `tests/test_admin_data.py`)
- `GET /api/admin/data/export-sql` — 전체 DB를 psql용 PostgreSQL .sql로(Stage 16-8, `app/services/db_dump_service.py`). 모델(`Base.metadata`)을 PostgreSQL 문법으로 컴파일한 CREATE TABLE·인덱스(의존 순서) + 테이블별 `COPY … FROM stdin`(null `\N`, 탭·줄바꿈·역슬래시 이스케이프, 불리언 t/f) + `alembic_version` + SERIAL 시퀀스 `setval`, 전체 `BEGIN … COMMIT`, DROP 없음(빈 DB 전제). 원본이 PostgreSQL이면 REPEATABLE READ READ ONLY로 한 시점 기준. 새 모델 테이블은 자동 포함. 메모리에서 만든 뒤 보낸다(지금 데이터 규모 기준)
- 리셋은 웹에 없다(명령줄로만). 새 설비유형도 `INPUT_COLUMNS`·`load_inputs()`만 있으면 자동으로 입력·내보내기 대상이 된다.

## 관리자 SQL 조회 (Stage 16-5)

`POST /api/admin/sql` {`sql`} — admin만, `app/services/sql_query_service.py`. 조회(SELECT/WITH) 한 문장, 허용 목록 테이블(`admin_service.ALLOWED_TABLES`)만, 최대 1,000행·5초. **안전장치는 DB 쪽**: SQLite는 같은 파일을 `mode=ro`로 새로 연 별도 연결 + `set_authorizer`(SELECT·허용 테이블 읽기·함수만) + 실행 전 EXPLAIN으로 여는 테이블의 루트 페이지 검사(컬럼을 안 읽는 `SELECT 1 FROM t`·`count(*)`는 authorizer에 안 잡힘) + `set_progress_handler` 시간 제한. PostgreSQL은 `SET TRANSACTION READ ONLY` + `statement_timeout` 후 rollback — 테이블 제한은 읽기 전용 DB 계정으로(`docs/DEPLOY_PDEP.md`).

## 설비유형별 데이터 운영 (Stage 8-2)

- 레지스트리: `app/equipment_types/registry.py`(EF_code → 모듈), 인터페이스: `app/equipment_types/base.py`(`NAME_FIELD`, `INPUT_COLUMNS`, `DOMAIN_TABLES`, `generate_input_row`, `calculate`, `ingest_domain`).
- 시드: `python -m app.db.seed --ef-code EF1|all --rows 30 [--reset]` — `--reset`은 지정 유형만 지움.
- 리셋: `python -m app.db.reset --ef-code EF1|all` — 유형 전용 테이블 → `score_snapshot`/`equipment_extra_attribute` → `equipment` 순(`app/services/dataset_service.py`). `equipment_type`/`allowed_users`는 그대로.
- `AUTO_SEED_IF_EMPTY=true`: 비어 있는 유형만 기동 시 mock 30건.
- 새 유형 추가 시 공통 코드(`ingest.py`/`dataset_service.py`/CLI)는 고치지 않는다 — 모듈 + 테이블 + 레지스트리 한 줄.

## PostgreSQL로 전환해서 개발하기 (로컬 검증 완료, 2026-09-29)

기본 개발 흐름은 계속 SQLite다 — 아래는 로컬에서 PostgreSQL 전환을 검증/재현하고 싶을 때만 필요.

- Windows에 PostgreSQL 14 네이티브 설치(`winget install --id PostgreSQL.PostgreSQL.14`), 이 프로젝트 전용 role/db(`eflms_dev`/`eflms_dev`, 테스트용 `eflms_dev_test`)를 별도로 생성 — `postgres` 슈퍼유저를 앱 접속에 그대로 쓰지 않는다.
- `app/core/config.py`가 이미 `DATABASE_URL` 우선 → `DB_HOST` 조합 → SQLite 폴백 순서를 지원하므로, 코드 변경 없이 `.env`의 `DATABASE_URL`만 `postgresql+asyncpg://...`로 바꾸면 전환된다.
- `alembic upgrade head`를 PostgreSQL 대상으로 실행 → 코드 변경 없이 테이블 정상 생성 확인.
- `backend/tests/conftest.py`가 `DATABASE_URL`이 이미 설정돼 있으면 그 값을 존중하도록 되어 있음(테스트마다 스키마를 새로 만들어 SQLite 임시 파일 방식과 동일한 격리 수준 유지) — `DATABASE_URL=postgresql+asyncpg://eflms_dev:<비밀번호>@127.0.0.1:5432/eflms_dev_test .venv/Scripts/python -m pytest` 로 기존 스위트 9개를 그대로 PostgreSQL 대상으로 실행해 통과 확인(평소 `pytest`는 여전히 SQLite 임시 파일을 자동으로 씀 — 기본 경험 변화 없음).
- 앱을 `DATABASE_URL`로 PostgreSQL을 가리키게 기동(`AUTO_SEED_IF_EMPTY=true`와 함께 쓰면 편함) → `/healthz`·`/api/summary`·`/api/equipment`까지 SQLite 때와 동일하게 동작 확인.
- 실제 PDEP 배포 시 버전은 PostgreSQL 17을 목표로 함(`CLAUDE.md` 기술스택 표 참고) — 이번 로컬 검증은 14로 진행했으나, `DATABASE_URL`/SQLAlchemy Core 수준에서 버전 차이로 인한 문제는 없을 것으로 예상(실제 17 전환 시 재확인 권장).

## 로컬 Keycloak으로 SSO 검증하기 (로컬 검증 완료, 2026-09-29)

기본 개발 흐름은 계속 `AUTH_MODE=local`(비밀번호 로그인)이다 — 아래는 `AUTH_MODE=sso`를 로컬에서 검증/재현하고 싶을 때만 필요. Docker 없이(이 컴퓨터엔 미설치, PostgreSQL 때와 같은 네이티브 우선 원칙) JDK 17 + Keycloak 독립 서버로 진행한다.

**설치**
```powershell
winget install --id EclipseAdoptium.Temurin.17.JDK --accept-package-agreements --accept-source-agreements
# https://github.com/keycloak/keycloak/releases 에서 keycloak-26.x.x.zip 다운로드 후 C:\tools\keycloak-26.x.x 에 압축 해제
```

**기동**
```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.x.x-hotspot"
$env:KEYCLOAK_ADMIN = "admin"; $env:KEYCLOAK_ADMIN_PASSWORD = "admin"
cd C:\tools\keycloak-26.x.x
bin\kc.bat start-dev --http-port=8180
```

**realm/client/테스트 계정 생성** — Admin REST API(`http://127.0.0.1:8180/admin/realms/...`)로 realm `eflms`, confidential 클라이언트 `eflms-backend`(redirect URI에 `nginx`/`backend` 양쪽 콜백 주소 모두 등록: `http://127.0.0.1:8080/api/admin/sso/callback`, `http://127.0.0.1:8000/api/admin/sso/callback`), 브레이크글래스 계정(`eflms.admin@...`) + 테스트 계정(`eflms.test1~4@...`)을 생성한다. 클라이언트 시크릿은 `/admin/realms/eflms/clients/{uuid}/client-secret`로 조회.

**`backend/.env` 설정** — 로컬 Keycloak은 discovery 지원 IdP라 `SSO_FLOW_MODE=auth_code`
경로를 탄다. 2026-10-16(Stage 6-8)부터 `auth_code`가 기본값이라 생략해도 되지만 명시해두면
헷갈리지 않는다. 모드별 설정은 `app/auth/SSO_MODES.md` 참고:
```
AUTH_MODE=sso
SSO_FLOW_MODE=auth_code
SSO_ISSUER_URL=http://127.0.0.1:8180/realms/eflms
SSO_CLIENT_ID=eflms-backend
SSO_CLIENT_SECRET=<위에서 조회한 값>
SSO_ADMIN_ALLOWLIST=eflms.admin@company.local
SSO_ALLOW_LOCAL_LOGIN=true
```

**검증 시나리오(전부 확인됨)**: 브레이크글래스 계정 로그인 → `allowed_users`에 자동 admin 등록 확인 → "접근 권한 관리" 탭에서 테스트 계정을 일반 사용자로 등록 → 그 계정으로 로그인(테이블 조회는 되고 "접근 권한 관리" 탭은 안 보임) → 미등록 계정으로 로그인 시도("등록되지 않은 계정입니다" 확인) → 마지막 admin은 강등/삭제 불가 확인. Keycloak 자체 로그인 세션은 브라우저에 남아있어 재테스트 시 다른 계정으로 확인하려면 `http://127.0.0.1:8180/realms/eflms/protocol/openid-connect/logout`으로 먼저 로그아웃해야 함(우리 앱 로그아웃과는 별개).

**실제로 겪은 버그**: `nginx/nginx.conf.template`이 `proxy_set_header Host $host;`를 쓰고 있었는데, nginx의 `$host`는 포트를 뺀 호스트명만 담는다(`$http_host`가 포트 포함). 이 때문에 백엔드가 `request.url_for()`로 만드는 SSO redirect_uri에서 포트가 통째로 빠져(`http://127.0.0.1/...`) Keycloak이 "Invalid parameter: redirect_uri"로 거부했다 — `$http_host`로 교체해 해결.

## 인증 모드 설정 (`AUTH_MODE` / `SSO_FLOW_MODE`)

**역할과 게이트(Stage 16-1)** — 세션마다 역할 하나(`app/auth/state.py`): `admin`(local 로그인 또는 `is_admin`) / `user`(`allowed_users` 등록) / `general`(SSO 인증만 된 미등록 사용자, `SSO_DENY_UNREGISTERED_USERS=true`면 대신 거부). 의존성(`app/api/deps.py`): `require_viewer`(대시보드 API — `AUTH_MODE=sso`일 때만 세션 필요, 역할 무관), `require_session`(테이블 조회 — admin/user), `require_admin`(접근 권한·데이터 입력). SSO 로그인은 `/api/admin/sso/login?next=<경로>`로 시작한 화면으로 돌아간다(같은 사이트 경로만 — `_safe_next`). implicit_form_post는 세션 쿠키가 안 올 수 있어 `/`로 돌아간다.

모드별 의미·설정 예시·반영 확인법은 [`app/auth/SSO_MODES.md`](app/auth/SSO_MODES.md)에 정리. 요점만:
- `AUTH_MODE`(`none`/`local`/`sso`), `SSO_FLOW_MODE`(`auth_code` 기본 / `implicit_form_post`)는 허용값 외·빈 값이면 **기동 실패**.
- 실제 적용값은 `uvicorn.log`의 `EFLMS auth config:` 한 줄로 확인. `.env`를 고쳐도 반영이 안 되면 셸에 같은 이름의 빈 환경변수가 남아있는지(`Test-Path Env:SSO_FLOW_MODE`) 먼저 본다.

## 컨벤션

- 시크릿은 `.env`로만 주입, 코드에 하드코딩 금지
- 새 설비유형 추가 시 기존 설비유형 코드/공통 테이블 변경 금지 — 모듈·테이블·레지스트리 등록만(`docs/ARCHITECTURE.md` "새 설비유형 추가 절차")
