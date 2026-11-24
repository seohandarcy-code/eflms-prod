"""EF3 최대부하 소수 허용 (Stage 22-8, 2026-11-23)

cable_condition.max_load를 정수에서 실수로 바꾼다(실데이터 최대부하가 소수로 들어옴). 기존 값은 그대로 옮겨진다.
되돌리면(downgrade) 정수로 반올림된다.

포설방법·종단접속함 빈칸 허용(같은 단계)은 입력 검증만 바뀌어 스키마 변경이 없다(문자 칸에 빈 문자열로 저장).

Revision ID: a3d9e5f7c1b8
Revises: f1a7c3e9b5d4
Create Date: 2026-11-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d9e5f7c1b8'
down_revision: Union[str, Sequence[str], None] = 'f1a7c3e9b5d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cable_condition') as batch_op:
        batch_op.alter_column(
            'max_load', existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=True,
            postgresql_using='max_load::double precision',
        )


def downgrade() -> None:
    # 소수 값은 반올림해서 정수 칸에 넣는다(SQLite는 batch 복사 때 정수로 바뀌지 않으므로 먼저 반올림).
    op.execute('UPDATE cable_condition SET max_load = ROUND(max_load) WHERE max_load IS NOT NULL')
    with op.batch_alter_table('cable_condition') as batch_op:
        batch_op.alter_column(
            'max_load', existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=True,
            postgresql_using='ROUND(max_load)::integer',
        )
