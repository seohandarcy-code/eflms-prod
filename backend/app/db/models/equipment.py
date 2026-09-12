from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EquipmentType(Base):
    """Common to every equipment type (EF1..EF22)."""

    __tablename__ = "equipment_type"

    ef_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), default=None)


class Equipment(Base):
    """Equipment master. Common across all equipment types."""

    __tablename__ = "equipment"
    __table_args__ = (
        UniqueConstraint("factory_code", "ef_code", "transformer_name", name="uq_equipment_natural_key"),
    )

    equipment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factory_code: Mapped[str] = mapped_column(String(10))
    ef_code: Mapped[str] = mapped_column(ForeignKey("equipment_type.ef_code"))
    transformer_name: Mapped[str] = mapped_column(String(50))
    voltage: Mapped[int] = mapped_column(Integer)
    onan_val: Mapped[int] = mapped_column(Integer)
    onaf_val: Mapped[float] = mapped_column(Float)
    operation_start_time: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
