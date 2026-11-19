"""score_refresh_run and data_job_lock (Stage 21-1, 2026-11-19)

점수 갱신 실행 기록(score_refresh_run)과 데이터 작업 잠금(data_job_lock) 테이블을 만든다.
기존 테이블은 바꾸지 않는다 — 날짜 분리는 갱신이 입력 테이블을 다시 쓰지 않게 해서 이룬다
(입력 테이블 measured_at/updated_at = 진단 데이터 반영일, 계산 결과 테이블 today = 점수 기준일).

Revision ID: a6c2e9f4d1b8
Revises: f3b8d1e6a9c4
Create Date: 2026-11-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6c2e9f4d1b8'
down_revision: Union[str, Sequence[str], None] = 'f3b8d1e6a9c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'score_refresh_run',
        sa.Column('run_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('trigger', sa.String(length=16), nullable=False),
        sa.Column('requested_by', sa.String(length=128), nullable=True),
        sa.Column('as_of', sa.Date(), nullable=True),
        sa.Column('equipment_count', sa.Integer(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
    )
    op.create_table(
        'data_job_lock',
        sa.Column('name', sa.String(length=32), primary_key=True),
        sa.Column('holder', sa.String(length=128), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('acquired_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('data_job_lock')
    op.drop_table('score_refresh_run')
