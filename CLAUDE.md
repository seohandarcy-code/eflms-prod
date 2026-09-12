# EFLMS (전기설비수명관리시스템)

변압기를 시작으로 전기설비의 자산 건전성을 PoF(고장확률)·CoF(고장영향)·DoF(설계/방어수준) 세 축으로 평가하고, 그 결과를 웹 대시보드로 보여주는 사내 시스템. 설비유형은 EF1(변압기)부터 시작해 향후 EF2~EF22까지 확장 예정 — 설비유형마다 입력 항목과 계산 로직이 달라질 수 있음을 전제로 설계한다.

## 기술 스택 (확정)

| 영역 | 선택 | 비고 |
|---|---|---|
| 언어 | Python 3.11 | |
| 백엔드 | FastAPI + SQLAlchemy(async) + Alembic | `DATABASE_URL` env로 DB 교체 |
| DB (개발) | SQLite | |
| DB (운영, 추후) | PostgreSQL 17 | 최신 메이저(18)보다 한 버전 이전, 사내망 안정 운영 목적 |
| 패키지 매니저(백엔드) | pip + requirements.txt | 사내 devops 파이프라인 호환성 우선 |
| 프론트 | Vue 3 + Vite + Pinia + Element Plus | |
| Node | 22 LTS (Maintenance) | 사내망 안정 운영 목적, 최신(24) 대신 선택 |
| 패키지 매니저(프론트) | npm | |
| 인증 | 자체 추상화(`AuthProvider`), 지금은 무인증 | 추후 사내 SSO(OIDC) 연동 대비 |

## 저장소 구조

- `ref_data/` — 엑셀 기반 원본 인풋/계산 로직 참고자료 (`schema_eflms.py`, `main.py`, `output/`). **수정 금지, 참고용으로만 사용.**
- `design/` — 승인된 대시보드 화면(Direction A) 목업 작업파일(`*.dc.html`, `canvas.json`). 캔버스 산출물(`eflms-dashboard-directions.html`)은 재생성 가능하므로 git에는 올리지 않음.
- `docs/` — 설계 문서:
  - [ARCHITECTURE.md](docs/ARCHITECTURE.md) — DB/인증/데이터모델/계산기 확장 구조
  - [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) — 입력/계산 컬럼 정의 및 테이블 매핑
  - [ROADMAP.md](docs/ROADMAP.md) — 단계별 계획
  - [SECURITY_ENV.md](docs/SECURITY_ENV.md) — env 변수 목록 (일반/시크릿 구분)
- (추후) `backend/`, `frontend/` — Stage C에서 생성 예정

## 작업 방식

- **실제 코드/설정 변경(파일 생성·수정, git 조작 등)은 항상 먼저 계획을 제시하고 승인받은 뒤 진행한다.** 사용자가 이 대화에서 명시적으로 요청한 규칙이며, 매 작업마다 다시 확인한다.
- `ref_data/`는 읽기 전용 참고자료로 취급하고, 새 기능은 `docs/ARCHITECTURE.md`에 정의된 구조(공통 레이어 + 설비타입별 도메인 테이블/계산기)를 따른다.

## 에이전트 / 스킬 활용 방침

- 커스텀 서브에이전트는 아직 불필요. 화면/UI 작업은 `design` 스킬, 차트·시각화는 `dataviz` 스킬을 사용한다.
- 반복적인 다단계 작업(예: 시드 재실행 + 검증)이 Stage C 구현 중 실제로 생기면, 그때 전용 스킬이나 `/loop` 활용을 다시 검토한다.
- 코드 변경 후에는 `/code-review`로 점검하는 것을 기본으로 한다.
