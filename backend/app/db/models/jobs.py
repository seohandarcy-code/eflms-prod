"""점수 갱신 실행 기록과 데이터 작업 잠금 (2026-11-19, Stage 21-1).

- score_refresh_run: 점수 갱신(저장된 입력으로 기준일만 바꿔 점수 테이블만 다시 쓰기) 한 번 = 한 행.
  유형별 건수·오류는 summary(JSON 문자열). app/services/score_refresh_service.py.
- data_job_lock: 점수 갱신·실제 반영 임포트·참고표 변경이 동시에 돌지 않게 하는 잠금(이름당 한 행).
  비정상 종료로 남아도 expires_at이 지나면 다음 작업이 지우고 잡는다. app/services/job_lock.py.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScoreRefreshRun(Base):
    __tablename__ = "score_refresh_run"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # running / success / partial(일부 유형 실패) / failed(전부 실패)
    status: Mapped[str] = mapped_column(String(16))
    # schedule(정기 실행) / cli(명령) / admin(관리자 화면)
    trigger: Mapped[str] = mapped_column(String(16))
    requested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 계산 기준일 — null이면 설비마다 저장된 기준일 그대로 다시 계산(규칙 변경 후 재계산)
    as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    equipment_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataJobLock(Base):
    __tablename__ = "data_job_lock"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    holder: Mapped[str] = mapped_column(String(128))
    token: Mapped[str] = mapped_column(String(64))
    acquired_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
