from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EquipmentExtraAttribute(Base):
    """사내 입력파일에서 알려진 컬럼(schema)과 매칭되지 않는 헤더를 자동 보관하는 곳.

    임포트를 실패시키지 않기 위한 안전망 — 정식 컬럼 승격은 수동 마이그레이션으로.
    """

    __tablename__ = "equipment_extra_attribute"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"))
    column_name: Mapped[str] = mapped_column(String(100))
    value: Mapped[str | None] = mapped_column(String(255), default=None)
    inferred_type: Mapped[str] = mapped_column(String(20))
    source_file: Mapped[str] = mapped_column(String(255))
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
