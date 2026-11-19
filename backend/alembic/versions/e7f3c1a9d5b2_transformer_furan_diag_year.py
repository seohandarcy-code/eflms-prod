"""transformer_score_detail.furan_diag_year (2026-11-19)

Furan 연평균을 "Furan 진단 시점 사용년수(진단일 - 가동년월)"로 나누도록 바꾸면서(사용자 결정 — 원본은 오늘까지의
운전년수), 그 사용년수를 계산 결과 테이블에 남긴다. 빈 값 허용(진단일 ≤ 가동년월·진단일 N/A면 평가 불가).
기존 행은 null로 시작한다 — `python -m app.db.recalculate --ef-code EF1`(또는 서버 시작 시 자동 갱신)로 채워진다.

Revision ID: e7f3c1a9d5b2
Revises: d4b9a2c6e8f1
Create Date: 2026-11-19 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f3c1a9d5b2'
down_revision: Union[str, Sequence[str], None] = 'd4b9a2c6e8f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('transformer_score_detail') as batch_op:
        batch_op.add_column(sa.Column('furan_diag_year', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('transformer_score_detail') as batch_op:
        batch_op.drop_column('furan_diag_year')
