"""drop GIS cb_op_char_over (unused input)

EF2 입력 `cb_op_char_over`(CB 동작특성 기준치 초과)를 쓰지 않기로 해서(2026-10-19, 사용자 결정)
`gis_operation.cb_op_char_over`와 그 감점 `gis_score_detail.cb_op_char_over_minus`를 지운다.
EF2 전용 테이블만 바꾸고 공통·EF1 테이블은 건드리지 않는다.

SQLite는 컬럼 삭제를 batch_alter_table(테이블 재생성)로 한다 — PostgreSQL에서는 일반 ALTER.
downgrade는 NOT NULL 컬럼을 기존 행에 채울 값(감점 없음: 'N', 0)과 함께 되살린다.

Revision ID: c4e9a1d7b2f3
Revises: b3f7d2a8c615
Create Date: 2026-10-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e9a1d7b2f3'
down_revision: Union[str, Sequence[str], None] = 'b3f7d2a8c615'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('gis_operation') as batch_op:
        batch_op.drop_column('cb_op_char_over')
    with op.batch_alter_table('gis_score_detail') as batch_op:
        batch_op.drop_column('cb_op_char_over_minus')


def downgrade() -> None:
    with op.batch_alter_table('gis_score_detail') as batch_op:
        batch_op.add_column(sa.Column('cb_op_char_over_minus', sa.Integer(), nullable=False, server_default='0'))
    with op.batch_alter_table('gis_operation') as batch_op:
        batch_op.add_column(sa.Column('cb_op_char_over', sa.String(length=10), nullable=False, server_default='N'))
