"""data_change and data_change_row (Stage 21-4, 2026-11-19)

입력 변경 이력 — 임포트·교체·행 편집·참고표 넣기/리셋·되돌리기 한 번 = data_change 1행, 바뀐 행마다 바뀌기 전후
입력값(JSON) = data_change_row. 관리자 "변경 이력"에서 보고 되돌린다(app/services/change_service.py).
이 마이그레이션 전의 변경은 기록이 없다(되돌릴 수 없음).

Revision ID: d4b9a2c6e8f1
Revises: c8e1f5a3b7d2
Create Date: 2026-11-19 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4b9a2c6e8f1'
down_revision: Union[str, Sequence[str], None] = 'c8e1f5a3b7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_change',
        sa.Column('change_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('actor', sa.String(length=128), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('ef_code', sa.String(length=16), nullable=False),
        sa.Column('target_table', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=256), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('unchanged_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('undone_at', sa.DateTime(), nullable=True),
        sa.Column('undone_by', sa.String(length=128), nullable=True),
        sa.Column('undo_of', sa.Integer(), nullable=True),
    )
    op.create_table(
        'data_change_row',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('change_id', sa.Integer(), sa.ForeignKey('data_change.change_id'), nullable=False),
        sa.Column('row_key', sa.String(length=256), nullable=False),
        sa.Column('action', sa.String(length=16), nullable=False),
        sa.Column('before', sa.Text(), nullable=True),
        sa.Column('after', sa.Text(), nullable=True),
    )
    op.create_index('ix_data_change_row_change_id', 'data_change_row', ['change_id'])


def downgrade() -> None:
    op.drop_index('ix_data_change_row_change_id', table_name='data_change_row')
    op.drop_table('data_change_row')
    op.drop_table('data_change')
