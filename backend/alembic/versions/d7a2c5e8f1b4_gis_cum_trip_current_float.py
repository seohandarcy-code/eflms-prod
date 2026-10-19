"""GIS cum_trip_current to float

EF2 입력 `cum_trip_current`(누적 차단 전류)에 소수값이 있어(2026-10-19, 실데이터 확인)
`gis_operation.cum_trip_current`를 Integer에서 Float로 바꾼다. EF2 전용 테이블만 바꾼다.

SQLite는 타입 변경을 batch_alter_table(테이블 재생성)로 한다 — PostgreSQL에서는 일반 ALTER.
downgrade는 소수값을 반올림한 정수로 되돌린다.

Revision ID: d7a2c5e8f1b4
Revises: c4e9a1d7b2f3
Create Date: 2026-10-19 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a2c5e8f1b4'
down_revision: Union[str, Sequence[str], None] = 'c4e9a1d7b2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('gis_operation') as batch_op:
        batch_op.alter_column('cum_trip_current', existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)


def downgrade() -> None:
    op.execute("UPDATE gis_operation SET cum_trip_current = ROUND(cum_trip_current)")
    with op.batch_alter_table('gis_operation') as batch_op:
        batch_op.alter_column(
            'cum_trip_current', existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False,
            postgresql_using='cum_trip_current::integer',
        )
