"""점수 이력과 입력 변경 이력 (2026-11-19, Stage 21-3 / 21-4).

설비는 equipment_id가 아니라 (ef_code, factory_code, equipment_name)으로 묶는다 — 교체 임포트(--replace)는 설비를
지우고 새 equipment_id로 다시 만들기 때문에, id로 묶으면 교체할 때마다 이력이 끊긴다. equipment_id는 기록 당시 값
(참고용, FK 없음)이다.

- score_history: 설비별·점수 기준일별 점수 1행(같은 날 다시 계산하면 마지막 값으로 덮어씀). ingest가 점수를 쓸 때마다 남긴다.
- data_change / data_change_row: 임포트·교체·행 편집·참고표 넣기/리셋·되돌리기 한 번 = data_change 1행,
  바뀐 행마다 바뀌기 전후 값(JSON) = data_change_row. 관리자 "변경 이력"에서 보고 되돌린다(app/services/change_service.py).
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScoreHistory(Base):
    __tablename__ = "score_history"
    __table_args__ = (UniqueConstraint("ef_code", "factory_code", "equipment_name", "as_of", name="uq_score_history_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ef_code: Mapped[str] = mapped_column(String(16), index=True)
    factory_code: Mapped[str] = mapped_column(String(32))
    equipment_name: Mapped[str] = mapped_column(String(128))
    equipment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    as_of: Mapped[date] = mapped_column(Date)
    pof: Mapped[float] = mapped_column(Float)
    cof: Mapped[float] = mapped_column(Float)
    dof: Mapped[float] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    recorded_at: Mapped[datetime] = mapped_column(DateTime)


class DataChange(Base):
    __tablename__ = "data_change"

    change_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    actor: Mapped[str] = mapped_column(String(128))
    # import(추가·갱신) / replace(교체) / row_edit(행 편집) / reference_import / reference_reset / undo(되돌리기)
    kind: Mapped[str] = mapped_column(String(32))
    ef_code: Mapped[str] = mapped_column(String(16))
    target_table: Mapped[str] = mapped_column(String(64), default="")  # "" = 설비 데이터, 아니면 참고표 이름
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)  # 파일 이름 등
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)  # 값이 같아 반영하지 않은 행
    # applied / undone(되돌려짐)
    status: Mapped[str] = mapped_column(String(16), default="applied")
    undone_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    undone_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    undo_of: Mapped[int | None] = mapped_column(Integer, nullable=True)  # kind=undo일 때 되돌린 변경 번호


class DataChangeRow(Base):
    __tablename__ = "data_change_row"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("data_change.change_id"), index=True)
    # 설비: "factory_code|equipment_name", 참고표: 같은 행 판정 키 값들을 "|"로
    row_key: Mapped[str] = mapped_column(String(256))
    action: Mapped[str] = mapped_column(String(16))  # insert / update / delete
    before: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON — 바뀌기 전 입력값(+ _as_of, _extras)
    after: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON — 바뀐 뒤 입력값
