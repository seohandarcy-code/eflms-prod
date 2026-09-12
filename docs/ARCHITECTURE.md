# 아키텍처

## DB 연결 및 확장

- SQLAlchemy(async) + Alembic 마이그레이션을 처음부터 사용. SQL 문법은 SQLite/PostgreSQL 모두에서 동작하는 표준 범위만 사용(SQLite 전용 함수 지양).
- 연결 문자열은 `DATABASE_URL` env 하나로 결정한다. 개발: `sqlite+aiosqlite:///...`, 운영(추후): `postgresql+asyncpg://...`. DB를 바꿔도 애플리케이션 코드는 변경하지 않는다.
- Repository/Service 계층으로 라우터와 ORM 세부 구현을 분리한다.

## 데이터 모델

현재는 **스냅샷 구조**(설비 1대당 최신 값 1건)로 시작하고, 각 입력 도메인 테이블에는 처음부터 시점 컬럼(`measured_at` 등)을 넣어둔다 — 나중에 "설비당 유니크" 제약을 풀고 이력(시계열) 구조로 전환할 때 테이블 재설계 없이 제약 완화만으로 끝나도록 하기 위함이다.

**공통 레이어 (모든 설비유형 공통)**
- `equipment_type` — `ef_code`(PK), 설비종류명, 활성 여부
- `equipment` — `equipment_id`(surrogate PK, 자동증가), `factory_code`, `ef_code`(FK), `transformer_name`, `voltage`, `onan_val`, `onaf_val`, `operation_start_time`. `UNIQUE(factory_code, ef_code, transformer_name)` — 동일 설비 중복 등록 방지는 이 자연키 제약이 담당(식별/조회는 항상 `equipment_id`로).
- `score_snapshot` — `equipment_id`(FK, unique), `pof_minus`, `pof`, `cof_minus`, `cof`, `dof_minus`, `dof`, `total_score`, `computed_at`. 설비유형과 무관하게 모든 타입이 이 계약(PoF/CoF/DoF/종합점수)을 공유한다.

**EF1(변압기) 전용 도메인 테이블** — 입력값은 원본 그대로, 계산값은 별도 테이블로 분리해서 관리한다.
- 입력: `dga_reading`, `furan_reading`, `dielectric_test`, `oil_test`, `load_condition`, `periodic_inspection`, `design_attribute` (컬럼 상세는 [DATA_DICTIONARY.md](DATA_DICTIONARY.md) 참고)
- 계산: `transformer_score_detail` — EF1 전용 세부 감점 breakdown 전부(다른 설비유형이 생기면 `ef2_score_detail`처럼 별도 테이블을 추가하고 기존 테이블/코드는 건드리지 않는다)

**설비유형 확장 원칙**: EF2~EF22가 추가될 때는 새 도메인 테이블 + 새 계산기 모듈을 추가할 뿐, `equipment_type`/`equipment`/`score_snapshot` 공통 레이어와 기존 EF1 코드는 변경하지 않는다(개방-폐쇄 원칙).

## 계산 로직 — "설비 타입 계산기 레지스트리"

- `ref_data/schema_eflms.py`의 `INPUT_COLUMNS`/`CALCULATED_COLUMNS` 패턴을 설비 타입별 모듈로 일반화한다: `backend/app/equipment_types/ef1_transformer.py` (추후 `ef2_xxx.py` ...).
- 공통 인터페이스: `calculate(input) -> {pof, cof, dof, total_score, breakdown}`.
- `EF_code → 계산기` 매핑으로 라우팅. 계산은 데이터 적재(시드/임포트) 시점에 수행하고 결과를 `score_snapshot`/`*_score_detail`에 저장한다(매 조회마다 재계산하지 않음 — 성능·감사 추적 목적).

## 인증

- `AuthProvider` 인터페이스로 추상화. 지금은 무인증(또는 더미 로그인)으로 시작하되, FastAPI 의존성 자리(`get_current_user`류)만 미리 만들어 둔다.
- 토큰 클레임은 OIDC 클레임(`sub`, `email`, `roles`)과 유사하게 맞춰서, 추후 사내 SSO(OIDC) 연동 시 프론트/백엔드 변경을 최소화한다.
- `AUTH_MODE` env로 `none`(지금) → `local` → `sso` 전환.

## 데이터 적재 파이프라인 (시드 · 임포트 공용)

```
[데이터 소스]                              [공통 파이프라인]                         [저장]
mock 생성기(ref_data 로직 이식)     ─┐
                                       ├─▶ ingest_row(flat dict) 매퍼 ─▶ 도메인 입력 테이블 upsert
사내 입력파일(.dat, 탭구분 텍스트) ─┘        │                            ─▶ 계산기 재실행
                                              └───────────────────────────▶ score_snapshot / *_score_detail 갱신
```

- **공용 매퍼** `ingest_row(row: dict, session)` — mock 시드와 실제 파일 임포트가 동일 함수를 사용.
- **시드 스크립트** `backend/app/db/seed.py` — mock 생성기로 flat dict를 만들어 `ingest_row` 호출 (`--rows`, `--reset`).
- **파일 임포트** `backend/app/services/import_service.py` — 사내 입력 파일(탭 구분 텍스트, `.dat`)을 파싱해 flat dict로 만든 뒤 동일 파이프라인 호출. 실행은 CLI로 웹서버 기동과 분리(`python -m app.db.import_data --file ... --ef-code EF1`).
  - **인코딩**: UTF-8을 우선 시도하고 실패 시 CP949(EUC-KR)로 폴백 — 사내에서 받는 파일이 두 인코딩을 오갈 수 있음을 전제.
  - **컬럼 매칭**: 파일 헤더를 `schema_eflms.py`의 `name`(영문) 또는 `label`(한글) 중 하나와 매칭. 매칭된 컬럼은 정의된 dtype으로 값 검증.
  - **미등록 컬럼**: 실패시키지 않고 `equipment_extra_attribute`(equipment_id, column_name, value, inferred_type, source_file, imported_at)에 자동 저장(타입은 int→float→date→string 순으로 추론) + 임포트 후 "미등록 컬럼 발견" 리포트. 정식 컬럼 승격은 수동(스키마 마이그레이션)으로만 진행.
  - **검증 실패 정책**: 파일 내 일부 행에 오류가 있으면 전체 임포트를 중단하고 문제 행을 상세 리포트로 표시(부분 반영 금지).
  - **임포트 단위**: 파일 1건 = 해당 EF_code 설비들의 전체 입력 스냅샷을 통째로 갱신.

## 프론트엔드

- Vue 3 + Vite + Pinia(상태관리) + Element Plus(UI 컴포넌트).
- 화면 구성은 [design/Main.dc.html](../design/Main.dc.html)에 확정된 Direction A(관제실형 테이블 + PoF/CoF/DoF 3축 분포도 + 카드형 설비 목록)를 기준으로 한다.
