"""설비유형 모듈이 갖춰야 할 인터페이스 (Stage 8-2).

각 설비유형(EF1 변압기, EF2 GIS, ...)은 이 프로토콜을 만족하는 **파이썬 모듈** 하나로
구현하고 `registry.py`에 등록한다. 공통 파이프라인(적재·시드·리셋·임포트)은 EF_code로
모듈을 찾아 아래 항목만 사용하므로, 새 유형을 추가할 때 공통 코드나 다른 유형 코드를
고칠 필요가 없다.
"""
from typing import Any, Protocol

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

    def generate_input_row(self) -> dict: ...

    def calculate(self, input_row: dict) -> dict: ...

    async def ingest_domain(self, row: dict, equipment_id: int, session: AsyncSession) -> None:
        """calculate()가 만든 flat dict에서 이 유형 전용 테이블들에 upsert한다. commit하지 않는다."""
        ...
