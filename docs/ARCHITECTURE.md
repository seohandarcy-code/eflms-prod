# 아키텍처

## DB 연결 및 확장

- SQLAlchemy(async) + Alembic 마이그레이션을 처음부터 사용. SQL 문법은 SQLite/PostgreSQL 모두에서 동작하는 표준 범위만 사용(SQLite 전용 함수 지양).
- 연결 문자열은 `DATABASE_URL` env 하나로 결정한다. 개발: `sqlite+aiosqlite:///...`, 운영(추후): `postgresql+asyncpg://...`. DB를 바꿔도 애플리케이션 코드는 변경하지 않는다.
- **(계획, Phase 4)** `DATABASE_URL` 하나뿐 아니라 `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` 조합도 지원하도록 확장 예정 — 사내 유사 프로젝트 `a-ims-prod`의 `_build_database_url()` 패턴 참고: ① `DATABASE_URL`이 있으면 그대로 사용 ② 없고 `DB_HOST`가 있으면 위 5개 값으로 DSN을 조립(PDEP이 ConfigMap=host/port/name, Secret=user/password로 나눠 주입하는 경우에 대응) ③ 둘 다 없으면 SQLite로 폴백. 사람이 완성된 DSN을 직접 관리하는 로컬 개발과, host/port/자격증명이 분리돼 주입되는 실제 배포 환경을 동시에 지원한다.
- Repository/Service 계층으로 라우터와 ORM 세부 구현을 분리한다.

## 데이터 모델

현재는 **스냅샷 구조**(설비 1대당 최신 값 1건)로 시작하고, 각 입력 도메인 테이블에는 처음부터 시점 컬럼(`measured_at` 등)을 넣어둔다 — 나중에 "설비당 유니크" 제약을 풀고 이력(시계열) 구조로 전환할 때 테이블 재설계 없이 제약 완화만으로 끝나도록 하기 위함이다.

**공통 레이어 (모든 설비유형 공통)**
- `equipment_type` — `ef_code`(PK), 설비종류명, 활성 여부
- `equipment` — `equipment_id`(surrogate PK, 자동증가), `factory_code`, `ef_code`(FK), `equipment_name`, `voltage`, `operation_start_time`. `UNIQUE(factory_code, ef_code, equipment_name)` — 동일 설비 중복 등록 방지는 이 자연키 제약이 담당(식별/조회는 항상 `equipment_id`로). 설비유형 전용 속성은 두지 않는다 — Stage 8-1(2026-10-16)에 변압기 전용이던 `transformer_name`/`onan_val`/`onaf_val`을 `equipment_name` + EF1 전용 `transformer_spec`으로 정리했다(공통 레이어 불변 원칙의 1회성 예외, `docs/ROADMAP.md` Phase 3).
- `score_snapshot` — `equipment_id`(FK, unique), `pof_minus`, `pof`, `cof_minus`, `cof`, `dof_minus`, `dof`, `total_score`, `computed_at`. 설비유형과 무관하게 모든 타입이 이 계약(PoF/CoF/DoF/종합점수)을 공유한다.

**EF1(변압기) 전용 도메인 테이블** — 입력값은 원본 그대로, 계산값은 별도 테이블로 분리해서 관리한다.
- 입력: `transformer_spec`(정격용량), `dga_reading`, `furan_reading`, `dielectric_test`, `oil_test`, `load_condition`, `periodic_inspection`, `design_attribute` (컬럼 상세는 [DATA_DICTIONARY.md](DATA_DICTIONARY.md) 참고)
- 계산: `transformer_score_detail` — EF1 전용 세부 감점 breakdown 전부(다른 설비유형이 생기면 `ef2_score_detail`처럼 별도 테이블을 추가하고 기존 테이블/코드는 건드리지 않는다)

**EF2(GIS) 전용 도메인 테이블**(Stage 8-3) — 입력: `gis_operation`, `gis_diagnosis`, `gis_sf6_reading`, `gis_consequence_attribute`, `gis_design_attribute` / 계산: `gis_score_detail`. 계산기 `backend/app/equipment_types/ef2_gis.py`.

**EF3(초고압케이블) 전용 도메인 테이블**(Stage 9) — 입력: `cable_spec`, `cable_condition`, `cable_consequence_attribute`, `cable_design_attribute` / 계산: `cable_score_detail`. 계산기 `backend/app/equipment_types/ef3_cable.py`. 아래 "새 설비유형 추가 절차"를 그대로 따라 공통 레이어·기존 유형 코드 변경 없이 붙였다.

**EF4(수배전반) 전용 도메인 테이블**(Stage 10) — 입력: `switchgear_spec`, `switchgear_condition`, `switchgear_consequence_attribute`, `switchgear_design_attribute` / 계산: `switchgear_score_detail`. 계산기 `backend/app/equipment_types/ef4_switchgear.py`. 원본에 전압이 없어 공통 `equipment.voltage`에는 0을 넣는다(계산기가 채움 — 공통 적재 코드 불변). 같은 Stage에서 공통 화면의 전압 표시를 가동년월로 바꿨다(10-0, 목록 API에 `operation_start_time` 추가 — 테이블 변경 없음).

**EF5(UPS) 전용 도메인 테이블**(Stage 13) — 입력: `ups_spec`, `ups_condition`, `ups_consequence_attribute`, `ups_design_attribute` / 계산: `ups_score_detail`. 계산기 `backend/app/equipment_types/ef5_ups.py`. 전압은 EF4처럼 0. 같은 Stage에서 점수 지표를 모든 유형 공통으로 소수 첫째 자리로 바꿨다(13-0, `score_snapshot` 점수 컬럼 FLOAT — 사용자 승인 공통 테이블 변경, `docs/DATA_DICTIONARY.md` "점수 지표 소수 첫째 자리"). 2026-11-19(Stage 20)에 감점도 정수 반올림 없이 소수로 계산하게 바꾸고 EF1~EF4 계산 결과 테이블 감점 컬럼을 FLOAT로(공통 테이블은 그대로, "감점 소수 계산").

**EF6(VDP) 전용 도메인 테이블**(Stage 14) — 입력: `vdp_spec`, `vdp_condition`, `vdp_consequence_attribute`, `vdp_design_attribute` / 계산: `vdp_score_detail`. 계산기 `backend/app/equipment_types/ef6_vdp.py`. 지금은 EF5(UPS)와 구조·공식이 거의 같지만(모델type만 다름) 앞으로 달라질 수 있어 모듈·테이블·화면을 공유하지 않고 독립으로 붙였다.

**EF7(배터리) 전용 도메인 테이블 + 참고표**(Stage 15) — 입력: `battery_spec`, `battery_condition`, `battery_consequence_attribute`, `battery_design_attribute` / 계산: `battery_score_detail` / 참고표: `battery_discharge_history`(방전이력), `battery_temp_decay_coef`(온도감소계수). 계산기 `backend/app/equipment_types/ef7_battery.py`. 배터리는 계산에 설비 밖의 표가 필요해 **참고표 구조**(Stage 15-0)를 추가했다 — 아래 "참고표" 절.

**설비유형 확장 원칙**: 공통 레이어는 EF2 도입 때 한 번 일반화했다(Stage 8-1 `equipment` 정리, 8-2 레지스트리·플러그인화 — 승인된 1회성 예외). 이후 새 설비유형(EF3~)은 **새 계산기 모듈 + 새 도메인 테이블 + 레지스트리 등록만** 추가하고, `equipment_type`/`equipment`/`score_snapshot` 공통 레이어와 기존 유형 코드는 변경하지 않는다(개방-폐쇄 원칙). 절차는 아래 "새 설비유형 추가 절차".

## 계산 로직 — "설비 타입 계산기 레지스트리"

- `ref_data/`의 `INPUT_COLUMNS`/`CALCULATED_COLUMNS` 패턴을 설비 타입별 모듈로 일반화한다: `backend/app/equipment_types/ef1_transformer.py`, `ef2_gis.py` (추후 `ef3_xxx.py` ...).
- 공통 인터페이스(2026-11-19에 `ingest_scores`·`SCORE_DETAIL_MODEL` 추가 — 사용자 승인 공통 레이어 변경): `backend/app/equipment_types/base.py`의 `EquipmentTypeModule` — `calculate(input_row, as_of=None)`(입력 + 전체 계산 컬럼 flat dict), `generate_input_row`, `ingest_domain`, `ingest_scores`(계산 결과 테이블만 — 점수 갱신용, Stage 21-1), `load_inputs`/`last_diag_dates`/`load_detail`, 메타데이터 `EF_CODE`/`EF_NAME`/`NAME_FIELD`/`INPUT_COLUMNS`/`DOMAIN_TABLES`/`SCORE_DETAIL_MODEL`/`BREAKDOWN`. 레지스트리는 `registry.py`.
- `EF_code → 계산기` 매핑으로 라우팅. 계산은 데이터 적재(시드/임포트) 시점에 수행하고 결과를 `score_snapshot`/`*_score_detail`에 저장한다(매 조회마다 재계산하지 않음 — 성능·감사 추적 목적).

### 참고표 — 계산에 쓰는 설비 밖의 표 (Stage 15-0, 2026-11-16 사용자 결정)

- 대부분의 유형은 입력 한 행만으로 계산하지만, EF7(배터리)은 사업장별 방전이력과 년차별 온도감소계수 표를 함께 읽는다. 이런 유형은 모듈에 선택 항목 `REFERENCE_TABLES`(표 이름 → 모델·컬럼·검증·같은 행 판정 열쇠·목업 행)를 선언하고, `calculate(row, as_of=None, reference=None)`로 표 내용을 받는다. 참고표 테이블은 `equipment_id`가 없는 독립 테이블이다.
- 계산기를 부르는 곳(임포트 `import_service`, 시드 `seed.seed_type`, 예측 그래프 `equipment_service._projection`, 참고표 재계산)은 `app/services/reference_data.calc_options(session, module)`를 펼쳐 넘긴다 — 참고표가 없는 유형은 빈 dict라 EF1~EF6 동작은 그대로다(공통 코드 예외 — 사용자 승인). 참고표가 필요한 유형은 `reference`를 빠뜨리면 조용히 0으로 계산하지 않고 오류를 낸다.
- 운영(`app/services/reference_service.py`, CLI `app.db.import_reference` / `app.db.reset_reference`): 설비 파일과 같은 규칙으로 넣기(같은 행 갱신·새 행 추가) / `--replace` / `--check` / 리셋. 참고표가 바뀌면 같은 트랜잭션에서 그 유형 설비를 `load_inputs` → `calculate(as_of=저장 기준일)` → `save_scores`(점수만, Stage 21-1)로 다시 계산한다. 빈 표는 원본 수식대로 0이고 경고만 낸다.
- 시드는 비어 있는 참고표에만 목업을 넣는다(`ensure_mock_reference`). 유형 리셋(`dataset_service.reset_type`)은 `DOMAIN_TABLES`만 지우므로 참고표는 남는다.
- **사업장별 참고표(Stage 19, 2026-11-18 사용자 결정)**: 참고표 정의에 `"scope": "factory_code"`를 달면 사업장마다 따로 관리하는 표가 된다(지금 EF7 방전이력 — 실제 데이터는 H1만). 원본 합계식은 그 사업장 행이 없으면 조용히 0이 되므로 `reference_data`가 판단한다: 시뮬레이터는 행이 없는 사업장을 선택지에서 빼고 계산을 거부(`calculable_sites`), 설비 입력·참고표 재계산은 막지 않고 사업장별 경고(`scope_warnings` — "참고표 '방전이력'에 H2 사업장 행이 없음 — 설비 N대는 0으로 계산됨"). 관리자가 그 사업장 행을 넣으면 코드 변경 없이 바로 계산 대상이 된다. 다른 유형에 사업장별 표가 생겨도 `scope`만 달면 같은 규칙이 적용된다.
- **점수 시뮬레이터(Stage 19)**: `/api/simulator/{ef}/form|sample|calculate`(대시보드와 같은 `require_viewer`, DB 쓰기 없음, `app/services/simulator_service.py`). 입력 양식은 데이터 입력 양식(`data_admin_service.template`), 값 검사는 데이터 입력과 같은 함수(`import_service`의 형식 변환·허용값·N/A)라 붙여넣기로 들어갈 값이면 계산된다. 사업장은 DB에 그 유형 설비가 있는 곳만(+ 사업장별 참고표), 계산 기준일은 오늘, 시작값 결과(baseline)도 같은 기준일로 계산해 차이는 바꾼 값 때문만 나온다.

## 인증

- `AuthProvider` 인터페이스로 추상화. 지금은 무인증(또는 더미 로그인)으로 시작하되, FastAPI 의존성 자리(`get_current_user`류)만 미리 만들어 둔다.
- 토큰 클레임은 OIDC 클레임(`sub`, `email`, `roles`)과 유사하게 맞춰서, 추후 사내 SSO(OIDC) 연동 시 프론트/백엔드 변경을 최소화한다.
- `AUTH_MODE` env로 `none` → `local`(구현 완료, 2026-09-29) → `sso`(계획) 전환. `sso`를 선택하면 아직 `NotImplementedError`가 나는 자리 확보 상태(`backend/app/core/security.py` — 참고로 이 `get_current_user`/`AUTH_MODE` 일반 인증 자리와, 아래 `local` 모드로 실제 구현한 관리자 로그인은 서로 다른 코드 경로다. `none`/`local`에서 일반 대시보드는 무인증 공개이며 `/admin`만 게이트한다 — `sso`의 대시보드 게이트는 아래 Stage 16-1).
- **`local`(구현 완료)**: 관리자 단일 계정, 메모리 세션(TTL 8시간) + 로그인 시도 5회 실패 시 5분 잠금(`backend/app/auth/state.py`의 `AdminAuthStore`, a-ims-prod 패턴 그대로 채택). JWT 서명 없이 opaque 토큰(`secrets.token_urlsafe`)만 사용. 게이트 대상은 `GET/POST /api/admin/*`(로그인/로그아웃/테이블 목록·조회, `require_admin` 의존성) — 편집 기능 없음, 화이트리스트 19개 테이블 조회 전용(Stage 8-1에 `transformer_spec`, 8-3에 `gis_*` 6개 추가).
- **`sso`(구현 완료, Stage 6 — 로컬 Keycloak 검증)**: OIDC(`authlib`). IdP 인증 성공이 곧 접근 허용은 아님 — `allowed_users` DB 테이블에 등록된 계정만 세션이 발급됨(관리자가 화면에서 직접 등록/삭제). `SSO_ADMIN_ALLOWLIST`(env)에 매칭되는 계정은 로그인마다 admin 권한이 자동 복구되는 브레이크글래스 — 전체 락아웃 방지용 안전망.
  - `SSO_ALLOW_LOCAL_LOGIN`: 개발 중 듀얼모드 — 브로커가 client_id를 아직 발급하지 않은 단계에서도 `sso` 모드에서 로컬 비밀번호 로그인을 같이 열어, 관리자가 먼저 들어가 SSO 계정을 등록해둘 수 있게 함(기본값 false).
  - `SSO_BROKER_CONFIGURED = bool(SSO_ISSUER_URL)`: `SSO_CLIENT_ID`/`SSO_CLIENT_SECRET` 없이 issuer URL만 발급하는 사내 브로커 방식에도 대응(authlib이 빈 client_secret/client_id를 이미 지원함을 소스로 확인됨).
- **역할 3단계와 대시보드 게이트(Stage 16-1, 2026-11-17, a-ims-prod 정책 참고 — 사용자 결정 권장안)**: 세션 역할 `admin`/`user`/`general`(SSO 인증만 된 미등록 사용자 — 대시보드 조회 전용, `SSO_DENY_UNREGISTERED_USERS=true`면 대신 거부). `AUTH_MODE=sso`면 조회 API(`/api/equipment*`, `/api/summary`, `/api/equipment-types`)에 `require_viewer`가 걸려 로그인이 필요하다(none/local은 공개 그대로). 프론트는 `auth-config.dashboard_login_required`로 로그인 화면(`LoginGate.vue`)을 띄우고, SSO 로그인은 `next`로 시작한 화면에 돌아온다(같은 사이트 경로만 허용). 토큰은 탭 단위 `sessionStorage`, 401이면 지움. 세션 저장소는 여전히 서버 메모리라 replicas 1 전제는 그대로(`docs/DEPLOY_PDEP.md`).
- **관리자 웹 데이터 입력·내보내기(Stage 16-2/16-3)**: `/api/admin/data/*`(admin만). CLI와 같은 임포트·참고표 서비스를 그대로 써서 검증·계산·전체 rollback·참고표 재계산 규칙이 같다. 내보내기는 입력파일과 같은 dat(다시 넣으면 점수 동일). 행 단위 웹 편집은 Stage 18에서 추가(사용자 결정, 처음엔 넣지 않았음) — `GET /api/admin/data/rows`가 내려받기와 같은 칸 값을 표(JSON)로 주고, 화면(`DataRowEditor.vue`)이 고친·추가한 행만 탭 구분 텍스트로 만들어 같은 `/import`(추가·갱신)로 보낸다 — 저장 경로가 따로 없어 검증·계산·rollback 규칙이 붙여넣기와 같다. 같은 행 판정 칸은 기존 행에서 잠그고(바꾸면 새 행 추가가 됨), 행 삭제는 없다. 웹에서 고치면 원본 입력파일과 DB가 어긋날 수 있으므로 원본을 맞추려면 내려받기(dat)를 쓴다. 리셋은 명령줄로만. 입력은 엑셀 범위 붙여넣기(탭 구분 텍스트) → 검증 → 입력값 미리보기(행별 추가/갱신·오류 칸) → 확정(Stage 16-6, 사용자 결정 — 계산 점수 미리보기는 하지 않음).
- **관리자 SQL 조회(Stage 16-5)**: `POST /api/admin/sql`(admin만). 조회 한 문장·허용 목록 테이블·1,000행·5초를 DB 쪽에서 강제(SQLite 읽기 전용 별도 연결 + authorizer + EXPLAIN 테이블 검사, PostgreSQL 읽기 전용 트랜잭션). 운영 PostgreSQL에서 테이블 제한은 읽기 전용 DB 계정 분리로.

## 데이터 적재 파이프라인 (시드 · 임포트 공용)

> **점수 갱신(Stage 21-1, 2026-11-19)** — 저장된 입력으로 기준일만 바꿔 다시 계산하고 **점수 테이블만** 다시 쓰는 경로가 따로 있다: `ingest.save_scores(row, equipment_id)` = 모듈 `ingest_scores()`(계산 결과 테이블) + `score_snapshot`. 입력 테이블의 `measured_at`/`updated_at` = **진단 데이터 반영일**(임포트·행 편집 때만 바뀜), 계산 결과 테이블의 `today` = **점수 기준일**(갱신마다 바뀜). 서비스 `app/services/score_refresh_service.py`(유형마다 한 트랜잭션, 실패한 유형만 이전 점수 유지, 실행 기록 `score_refresh_run`), **서버 자동 갱신**(Stage 21-1b, `app/services/score_scheduler.py`): lifespan이 백그라운드 작업을 띄워 시작 직후와 날짜가 바뀐 뒤 점수 기준일이 오늘보다 이전이면 갱신(이미 오늘이면 아무것도 안 함, DB가 최신이 아니면 `schema_check`로 막고 로그 안내, 실패 시 1시간 뒤 재시도, `SCORE_REFRESH_AUTO`). 수동은 명령 `python -m app.db.recalculate --as-of today`와 관리자 `POST /api/admin/score-refresh`. 점수 갱신·실제 반영 임포트·참고표 넣기/리셋은 데이터 작업 잠금(`data_job_lock`, `app/services/job_lock.py`, 30분 만료)을 잡고 돌아 서로 겹치지 않는다(검증만은 잠그지 않음). 기본 계산 기준일은 한국 시간 오늘(`app/core/clock.today_kst`, 컨테이너 UTC 대비).

```
[데이터 소스]                              [공통 파이프라인]                         [저장]
mock 생성기(ref_data 로직 이식)     ─┐
                                       ├─▶ ingest_row(flat dict) 매퍼 ─▶ 도메인 입력 테이블 upsert
사내 입력파일(.dat, 탭구분 텍스트) ─┘        │                            ─▶ 계산기 재실행
                                              └───────────────────────────▶ score_snapshot / *_score_detail 갱신
```

- **공용 매퍼** `ingest_row(row: dict, session)` — mock 시드와 실제 파일 임포트가 동일 함수를 사용. 공통 테이블(`equipment_type`/`equipment`/`score_snapshot`)만 직접 다루고, 유형 전용 테이블은 `row["EF_code"]`로 찾은 설비유형 모듈의 `ingest_domain()`에 맡긴다(Stage 8-2, `app/equipment_types/registry.py`). **commit하지 않는다** — 호출자가 파일/배치 단위로 한 번 commit.
- **설비유형 단위 운영**(Stage 8-2): 시드·리셋·임포트 모두 `--ef-code`(또는 `all`) 단위. 유형 리셋은 그 유형 설비와 딸린 행만 지운다(`app/services/dataset_service.py`) — 한 유형을 mock으로 다시 만들거나 실데이터로 교체해도 다른 유형은 그대로다.
- **시드 스크립트** `backend/app/db/seed.py` — mock 생성기로 flat dict를 만들어 `ingest_row` 호출 (`--ef-code`, `--rows`, `--reset`). 유형 삭제만 할 때는 `app/db/reset.py`.
- **파일 임포트** `backend/app/services/import_service.py` — 사내 입력 파일(탭 구분 텍스트, `.dat`)을 파싱해 flat dict로 만든 뒤 동일 파이프라인 호출. 실행은 CLI로 웹서버 기동과 분리(`python -m app.db.import_data --file ... --ef-code EF1`).
  - **인코딩**: UTF-8을 우선 시도하고 실패 시 CP949(EUC-KR)로 폴백 — 사내에서 받는 파일이 두 인코딩을 오갈 수 있음을 전제.
  - **컬럼 매칭**: 파일 헤더를 `name`(영문)과 매칭한다(사내 입력파일은 영문 헤더로만 옴을 확인함). `label`(한글)은 각 항목이 무엇인지 설명하는 문서/화면 표시용 메타데이터일 뿐, 매칭에는 쓰지 않는다. 매칭된 컬럼은 정의된 dtype으로 값 검증.
  - **미등록 컬럼**: 실패시키지 않고 `equipment_extra_attribute`(equipment_id, column_name, value, inferred_type, source_file, imported_at)에 자동 저장(타입은 int→float→date→string 순으로 추론) + 임포트 후 "미등록 컬럼 발견" 리포트. 정식 컬럼 승격은 수동(스키마 마이그레이션)으로만 진행.
  - **검증 실패 정책**: 파일 내 일부 행에 오류가 있으면 전체 임포트를 중단하고 문제 행을 상세 리포트로 표시(부분 반영 금지). 검증 통과 후 반영 도중 실패해도 파일 전체 rollback(파일 1건 = 트랜잭션 1건). 행의 `EF_code`가 `--ef-code`와 다르면 거부.
  - **임포트 단위**: 파일 1건 = 해당 EF_code 설비들의 입력 스냅샷. `--replace`면 같은 트랜잭션에서 그 유형 기존 데이터를 지우고 파일 내용으로 교체(원래 의도한 "통째로 갱신"), 빼면 upsert(추가·갱신)만 — Stage 8-2 이전 코드는 문서와 달리 upsert만 했었다.

## 프론트엔드

- Vue 3 + Vite + Pinia(상태관리) + Element Plus(UI 컴포넌트).
- [design/Main.dc.html](../design/Main.dc.html)은 최초 승인된 방향(Direction A: 관제실형 테이블 + PoF/CoF/DoF 3축 분포도 + 카드형 설비 목록)을 담은 2026-09-14 시점 목업으로, **그 이후 실제 화면 구현은 목업을 갱신하지 않고 코드에서 직접 반복 개선**해왔다(3단계 정상/교체검토/즉시교체 상태 체계, 검색·정렬·페이지네이션·리스트뷰, 다중선택 필터, 상세 패널 신규 차트 2종, `/guide` 안내 페이지 등 — 자세한 이력은 [ROADMAP.md](ROADMAP.md) Phase 1 참고). 즉 `design/*.dc.html`은 초기 승인 근거를 남긴 기록이고, **현재 화면의 정본은 `frontend/src/views/DashboardView.vue` 등 실제 구현 코드**다.

## 조회 API — 설비유형별 (Stage 8-4)

| 엔드포인트 | 내용 |
|---|---|
| `GET /api/equipment-types` | 등록된 유형, 유형별 설비 수, 감점 항목 메타데이터(`breakdown` — 축별 `field`/`label`/`group`/`summed`) |
| `GET /api/equipment?ef_code=&factory_code=` | 공통 요약 목록. `ef_code`를 빼면 전체 유형. 최근 진단일은 유형별 기준(EF1 DGA, EF2 SF6, EF3 상태값 측정일, EF4~EF7 점검결과 반영일). 항목마다 `operation_start_time`(가동년월, Stage 10-0) 포함 |
| `GET /api/equipment/{id}` | 공통 헤더 + `score` + `type_detail`(`ef_code`로 구분되는 union: EF1~EF7 전용 상세) + `projection` |
| `GET /api/summary?ef_code=` | KPI + `by_type`(유형별 합계·교체검토·즉시교체) |

- 서비스(`equipment_service`)는 공통 테이블만 직접 읽고, 유형별 정보는 설비유형 모듈의 `last_diag_dates`/`load_detail`/`load_inputs`에 맡긴다 — 새 유형은 모듈과 `app/schemas/<유형>.py` 상세 스키마, `TypeDetail` union 한 줄만 추가한다.
- `projection`(0~5년, 저장된 입력을 기준일만 바꿔 재계산)은 **화면에서 쓰지 않는다** — 측정값 고정 재계산이라 EF1 Furan(총량÷사용년수 판정)처럼 시간이 지나면 점수가 오히려 좋아지는 항목이 있다(2026-10-17 확인·결정). 화면 예측 차트는 기존 "연 -1점 단순 가정"을 유지.
- 화면(Stage 8-5)은 전체 유형을 받아 사이드바 "설비유형" 다중 선택 필터(비우면 전체, URL `?type=EF1,EF2`)로 클라이언트에서 거른다. 감점 사유 라벨·가이드 구성 항목은 `/api/equipment-types`의 `breakdown`이 단일 원본이다(프론트에 라벨 하드코딩 없음).

## 새 설비유형 추가 절차 (EF3~ 체크리스트)

EF2(GIS)를 붙이며 실제로 거친 순서다(Stage 8-0~8-5, `docs/ROADMAP.md` Phase 3). 각 단계는 루트 `CLAUDE.md` 규칙대로 계획 승인 후 진행한다.

1. **원본 분석·확정** — `ref_data/`의 계산 툴을 실제로 돌려본다(캐시를 남기지 않게 `python -I -B`). 실행 불가 오류, 컬럼 이름 불일치, 비정상 점수 범위를 찾아 원본 작성자에게 확인한다. 원본과 다르게 해석할 곳이 없도록 하고, "원본 그대로 유지하는 판단"과 입력 허용값을 `docs/DATA_DICTIONARY.md`에 절로 남긴다. `ref_data/` 파일은 수정하지 않는다(참고자료로 커밋).
2. **DB** — `backend/app/db/models/<유형>.py`에 입력 도메인 테이블(설비당 1행 + 시점 컬럼)과 `<유형>_score_detail`, `models/__init__.py` 등록, Alembic 마이그레이션(새 테이블 생성만 — 공통·기존 테이블 변경 금지). 관리자 화이트리스트(`admin_service.ALLOWED_TABLES`)에 추가.
3. **계산기 모듈** — `backend/app/equipment_types/ef<N>_<이름>.py`에 `base.py` 인터페이스 전부: 원본 공식을 그대로 옮긴 `CALCULATED_COLUMNS`(날짜는 `row["_as_of"]`/`row["today"]` 사용), 허용값(`choices`/`min`/`max`/`required`)을 붙인 `INPUT_COLUMNS`, `NAME_FIELD`, `DOMAIN_TABLES`, `SCORE_DETAIL_MODEL`(계산 결과 테이블), `ingest_domain`(입력 테이블 저장 후 `ingest_scores` 호출), `ingest_scores`(계산 결과 테이블만 — 점수 갱신이 이것만 부른다), `load_inputs`, `last_diag_dates`, `load_detail`, `BREAKDOWN`(축별 감점 라벨 — PoF 합산에 안 들어가는 항목은 넣지 않거나 `summed: False`). `registry.py`에 한 줄 등록. `calculate()`는 공통 `na.evaluate()`로 공식을 돌린다(N/A(null) 입력 → 그 감점 0, Stage 11). 입력 테이블의 입력 컬럼은 null 허용으로 만든다.
4. **응답 스키마** — `backend/app/schemas/ef<N>.py`에 `Ef<N>Detail`(`ef_code: Literal[...]`)과 하위 스키마, `schemas/equipment.py`의 `TypeDetail` union에 추가.
5. **샘플·테스트** — `python scripts/generate_sample_dat.py --ef-code EF<N>`(`sample_data/ef<n>/`). 테스트: 원본 파일과 전 계산 컬럼 일치, 감점 분기별 정답값(mock에서 안 나오는 분기 포함), mock 생성값의 허용값 통과·허용값 밖 거부, `load_inputs` 왕복(재계산 = 저장 점수, `tests/test_type_queries.py`에 파라미터 추가), "새 유형만 `--replace`해도 기존 유형 불변", 마이그레이션 왕복. 참고 예시: `tests/test_ef2_gis.py`.
6. **프론트** — `types/equipment.ts`에 `Ef<N>TypeDetail`(→ `TypeDetail` union), `components/detail/Ef<N>DetailBody.vue`("원본 데이터 전체 보기" 본문), `utils/scoreBreakdown.ts`에 근거 문구 맵, `EquipmentDetailPanel.vue`의 헤더 부제(`typeSubtitle`), 가이드 계산 방법 설명(`utils/typeGuide.ts`), (선택) 설비 안내 문구·사진(`utils/facilityInfo.ts`의 `FACILITY_INFO` + `assets/facilities/ef<N>.png`·`.gif` — 없으면 대시보드 카드는 아이콘, 안내 페이지는 이름·항목만 표시. 계통도에 넣으려면 `FacilityFlowDiagram.vue`의 배치도 추가). 필터·KPI·분포도 마커·감점 사유 라벨·가이드는 `/api/equipment-types` 메타데이터로 자동 반영된다.
7. **운영 데이터** — 개발 DB는 복사본에서 먼저 마이그레이션·시드를 검증한 뒤 적용(백업). 실데이터는 `python -m app.db.import_data --file <파일> --ef-code EF<N> --replace`로 그 유형만 교체.
8. **문서** — `DATA_DICTIONARY.md`(구현 반영), `backend/CLAUDE.md` "등록된 설비유형" 표, `ROADMAP.md`.

## API 문서화

- FastAPI가 자동 생성하는 OpenAPI 스펙을 프론트-백엔드 계약으로 사용한다. 별도의 API 문서를 손으로 관리하지 않는다.
- 필요 시 `openapi-typescript`로 Vue 쪽 요청/응답 타입을 OpenAPI 스펙에서 자동 생성하는 방안을 Stage C 착수 시점에 결정한다(도입 여부만 미정, 스펙 자체는 항상 존재).

## CORS 정책

- 지금(로컬 개발)은 `CORS_ORIGINS`에 `http://localhost:5173`(Vite dev server)만 허용한다.
- 사내 devops 플랫폼에 배포될 때는 실제 도메인으로 `CORS_ORIGINS` 값만 교체한다(콤마로 여러 오리진 구분 가능) — 코드 변경 없이 env만으로 대응.
- **(계획, Phase 4)** Nginx가 프론트/백엔드를 동일 origin에서 서빙하게 되면(아래 "배포" 참고) `CORS_ORIGINS` 자체가 불필요해질 수 있음 — 실제 배포 구조 확정 후 재검토.

## 배포 (Nginx/K8s) — 계획, Phase 4

- 사내 유사 프로젝트 `a-ims-prod`(PDEP/K8s 배포까지 설계·로컬 검증한 레포)의 구조를 참고.
- **Nginx 역할은 정적 파일 서빙 + `/api` 내부 리버스 프록시로 한정**한다. TLS 종료·외부 라우팅은 Nginx가 아니라 사내 **PDEP Ingress**가 담당(이미 사내 devops 플랫폼 사용을 전제하고 있음, 위 CORS 정책 참고).
- Dockerfile은 멀티스테이지로 구성 예정: 프론트 빌드 → Nginx 이미지, 백엔드 빌드 → Python 슬림 이미지.
- 로컬 개발에서도 운영과 동일하게 Nginx를 거치는 구조를 재현하기 위해, backend(uvicorn)+frontend(vite)+nginx를 한 번에 띄우는 스크립트를 마련한다(미뤄뒀던 "`run` 스킬"을 이 시점에 이 형태로 정의).
- PostgreSQL(실제 DB) 사용을 전제로 하므로, `a-ims-prod`가 SQLite 파일 동시쓰기 문제로 뒀던 "백엔드 Replica=1 고정" 제약은 eflms엔 해당 없음 — 대신 Alembic 마이그레이션이 여러 replica에서 동시 실행되지 않도록 하는 절차가 별도로 필요하다.

## 로깅 & 헬스체크

- `/healthz` 엔드포인트를 스캐폴딩 단계부터 만들어 둔다 — 사내 devops 플랫폼이 배포 상태를 점검할 때 보통 요구하는 최소 요건이다.
- 로그는 구조화(JSON) 형식으로 남겨서, 나중에 사내 로그 수집 시스템과 연동하기 쉽게 한다.

## 테스트 전략

- 백엔드: pytest. 프론트: vitest.
- 1단계(Stage C 초기)는 최소한의 스모크 테스트로 시작한다 — 주요 API가 200을 응답하는지, 시드 스크립트가 에러 없이 끝나는지 정도. 기능이 늘어나면 점진적으로 확대한다.
