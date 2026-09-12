# 로드맵

## Phase 1 — 현재: mock 데이터 기반 대시보드 (EF1 한정)

- SQLite에 `ref_data` 목업 로직으로 만든 EF1(변압기) 데이터만 시드
- FastAPI 조회 API (설비 목록/상세/집계)
- Vue 대시보드: [design/Main.dc.html](../design/Main.dc.html)에 확정된 화면
  - KPI(전체 설비 / 최근 데이터 갱신)
  - PoF·CoF·DoF 3축 분포도 + 점검필요 판정(각 축 중 하나라도 기준 미달: PoF<20 또는 CoF<30 또는 DoF<20) + 점검필요 순위/사유 리스트
  - 설비 목록 카드 + 클릭 시 인라인 상세 확장
- 인증 없음(자리만 확보), env는 최소 세트(`DATABASE_URL` 등)
- 체크리스트(C-1 완료분): `backend/CLAUDE.md` ✅, `frontend/CLAUDE.md` ✅, `/healthz` ✅ — 스모크 테스트(pytest/vitest)는 C-6에서 작성

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
