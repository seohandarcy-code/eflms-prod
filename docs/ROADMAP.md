# 로드맵

## Phase 1 — 현재: mock 데이터 기반 대시보드 (EF1 한정)

- [x] C-1 스캐폴딩 (backend/frontend, `/healthz`, 각 `CLAUDE.md`)
- [x] C-2 DB 모델 + 초기 Alembic 마이그레이션
- [x] C-3 EF1 계산기 이식(`ef1_transformer.py`) + 공용 적재 매퍼(`ingest.py`) + 시드 스크립트(`seed.py`)
- [x] C-4 최소 API (`/api/equipment`, `/api/equipment/{id}`, `/api/summary`)
- [x] C-5 Vue 대시보드 구현 (Direction A: KPI, PoF·CoF·DoF 3축 분포도, 점검필요 순위/사유, 카드형 목록+인라인 상세확장) — 실제 API 연동, **브라우저 육안 확인은 아직 안 함**(이 세션에 브라우저 도구 없음)
- [x] C-6 스모크 테스트(pytest 5개, vitest 9개, 전부 통과) + 실제 브라우저 확인(Claude in Chrome) — 확인 중 KPI가 사업장 필터를 무시하던 버그 발견 후 수정
- 인증 없음(자리만 확보), env는 최소 세트(`DATABASE_URL` 등)

## Phase 2 — 운영 데이터 연동

- 사내 입력파일(.dat, 탭구분) 정기 임포트 — 알려진 컬럼 검증 + 미등록 컬럼 자동 캡처
- 임포트 이력/오류 리포트 화면

## Phase 3 — 설비유형 확장

- EF2~EF22 순차 추가: 설비유형별 계산기 모듈 + 도메인 테이블 (기존 EF1 코드/테이블 불변)
- 대시보드에 설비유형 필터 실제 활성화

## Phase 4 — 인프라 전환

- PostgreSQL로 전환 (`DATABASE_URL`만 변경)
- 스냅샷 → 이력(시계열) 구조 전환: 각 입력 도메인 테이블의 `equipment_id` UNIQUE 제약 완화 + "최신값" 조회 뷰 추가

## Phase 5 — 인증

- 사내 SSO(OIDC) 연동, `AUTH_MODE=sso` 전환

## 보류 중 (마지막 디자인 고도화 단계에서 재검토)

- **Three.js 기반 3D "설비 전시장" UI**: 사업장/설비를 선택하면 3D 공간에서 해당 설비를 보여주는 연출. 단순 대시보드가 자리잡은 뒤, 별도 디자인 단계에서 다시 논의.
