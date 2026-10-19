"""설비유형 모듈이 갖춰야 할 인터페이스 (Stage 8-2).

각 설비유형(EF1 변압기, EF2 GIS, ...)은 이 프로토콜을 만족하는 **파이썬 모듈** 하나로
구현하고 `registry.py`에 등록한다. 공통 파이프라인(적재·시드·리셋·임포트)은 EF_code로
모듈을 찾아 아래 항목만 사용하므로, 새 유형을 추가할 때 공통 코드나 다른 유형 코드를
고칠 필요가 없다.
"""
from datetime import date
from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


class EquipmentTypeModule(Protocol):
    EF_CODE: str
    EF_NAME: str
    # 입력 행에서 공통 equipment.equipment_name으로 들어갈 컬럼 이름(EF1 transformer_name 등)
    NAME_FIELD: str
    # 임포트 컬럼 매칭/검증과 mock 생성에 쓰는 입력 컬럼 정의(name/label/dtype/generator)
    INPUT_COLUMNS: list[dict[str, Any]]
    # 이 유형 전용 테이블(모두 equipment_id FK). 유형 단위 리셋 시 이 순서대로 지운다.
    DOMAIN_TABLES: list[type]
    # 축별 감점 항목 메타데이터 {"pof"|"cof"|"dof": [{field, label, group?, summed?}]} — 화면 표시용(Stage 8-4)
    BREAKDOWN: dict[str, list[dict[str, Any]]]
    # (선택) 원본 파일에 있지만 쓰지 않는 컬럼 이름 튜플 — 임포트가 저장하지 않고 건너뛴다.
    # 선언하지 않으면 빈 튜플로 취급한다(import_service가 getattr로 읽음). 예: EF2 cb_op_char_over.

    def generate_input_row(self) -> dict: ...

    def calculate(self, input_row: dict, as_of: date | None = None) -> dict:
        """as_of = 계산 기준일(기본 오늘). N년 뒤 점수 예측은 기준일만 바꿔 같은 공식으로 재계산한다."""
        ...

    async def ingest_domain(self, row: dict, equipment_id: int, session: AsyncSession) -> None:
        """calculate()가 만든 flat dict에서 이 유형 전용 테이블들에 upsert한다. commit하지 않는다."""
        ...

    # --- 조회 (Stage 8-4) ---
    async def load_inputs(self, session: AsyncSession, equipment_id: int) -> tuple[dict, date] | None:
        """저장된 값으로 calculate() 입력 행을 복원하고, 저장된 점수를 계산했던 기준일과 함께 돌려준다."""
        ...

    async def last_diag_dates(self, session: AsyncSession, equipment_ids: list[int]) -> dict[int, date]:
        """설비별 '최근 진단일'(유형마다 기준 측정이 다르다 — EF1 DGA, EF2 SF6)."""
        ...

    async def load_detail(self, session: AsyncSession, equipment_id: int) -> BaseModel | None:
        """유형 전용 상세(EquipmentDetail.type_detail). ef_code 필드로 union이 구분된다."""
        ...
