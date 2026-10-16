from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EquipmentType(Base):
    """Common to every equipment type (EF1..EF22)."""

    __tablename__ = "equipment_type"

    ef_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), default=None)


class Equipment(Base):
    """Equipment master. Common across all equipment types.

    설비유형 전용 속성은 여기 두지 않는다 — 각 유형의 이름 컬럼(EF1 transformer_name,
    EF2 gis_name 등)은 equipment_name으로 통일하고, 그 외 전용 값은 유형별 테이블로
    보낸다(예: EF1 정격용량은 transformer_spec). Stage 8-1, docs/DATA_DICTIONARY.md.
    """

    __tablename__ = "equipment"
    __table_args__ = (
        UniqueConstraint("factory_code", "ef_code", "equipment_name", name="uq_equipment_natural_key"),
    )

    equipment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factory_code: Mapped[str] = mapped_column(String(10))
    ef_code: Mapped[str] = mapped_column(ForeignKey("equipment_type.ef_code"))
    equipment_name: Mapped[str] = mapped_column(String(50))
    voltage: Mapped[int] = mapped_column(Integer)
    operation_start_time: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
