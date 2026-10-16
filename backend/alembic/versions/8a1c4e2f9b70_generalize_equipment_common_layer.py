"""generalize equipment common layer (Stage 8-1)

equipment에서 변압기 전용 요소를 걷어낸다 — transformer_name -> equipment_name,
onan_val/onaf_val -> EF1 전용 transformer_spec 테이블로 값 이관. EF2(GIS)부터는
공통 레이어를 건드리지 않고 유형별 테이블만 추가하기 위한 1회성 정리
(docs/ROADMAP.md Phase 3, docs/DATA_DICTIONARY.md).

SQLite는 ALTER로 제약조건/컬럼 삭제를 못 하므로 batch_alter_table(테이블 재생성)을
쓴다 — PostgreSQL에서는 같은 코드가 일반 ALTER 문으로 실행된다.

Revision ID: 8a1c4e2f9b70
Revises: 3d49abc45e95
Create Date: 2026-10-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a1c4e2f9b70'
down_revision: Union[str, Sequence[str], None] = '3d49abc45e95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transformer_spec',
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.Date(), nullable=False),
        sa.Column('onan_val', sa.Integer(), nullable=False),
        sa.Column('onaf_val', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.equipment_id'], ),
        sa.PrimaryKeyConstraint('equipment_id'),
    )
    # 지금까지 equipment에 있던 설비는 전부 EF1이지만, 의도를 분명히 하려고 EF1만 옮긴다.
    op.execute(
        "INSERT INTO transformer_spec (equipment_id, updated_at, onan_val, onaf_val) "
        "SELECT equipment_id, CURRENT_DATE, onan_val, onaf_val FROM equipment WHERE ef_code = 'EF1'"
    )

    with op.batch_alter_table('equipment') as batch_op:
        batch_op.drop_constraint('uq_equipment_natural_key', type_='unique')
        batch_op.alter_column(
            'transformer_name',
            new_column_name='equipment_name',
            existing_type=sa.String(length=50),
            existing_nullable=False,
        )
        batch_op.drop_column('onan_val')
        batch_op.drop_column('onaf_val')
    # 같은 batch 안에서 같은 이름의 제약을 drop 후 create하면 SQLite 재생성 테이블에서 create가
    # 빠진다(실제로 확인함 — 자연키 없이 테이블이 만들어짐). 그래서 별도 batch로 다시 건다.
    with op.batch_alter_table('equipment') as batch_op:
        batch_op.create_unique_constraint(
            'uq_equipment_natural_key', ['factory_code', 'ef_code', 'equipment_name']
        )


def downgrade() -> None:
    with op.batch_alter_table('equipment') as batch_op:
        batch_op.drop_constraint('uq_equipment_natural_key', type_='unique')
        batch_op.alter_column(
            'equipment_name',
            new_column_name='transformer_name',
            existing_type=sa.String(length=50),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column('onan_val', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('onaf_val', sa.Float(), nullable=True))

    # 이전 스키마는 NOT NULL이었다 — transformer_spec이 없는 설비(EF1 외 유형)는 0으로 채운다.
    # 그런 설비가 있는 상태에서의 downgrade는 원래 표현할 수 없는 상태라 손실이 생긴다.
    op.execute(
        "UPDATE equipment SET "
        "onan_val = COALESCE((SELECT onan_val FROM transformer_spec t WHERE t.equipment_id = equipment.equipment_id), 0), "
        "onaf_val = COALESCE((SELECT onaf_val FROM transformer_spec t WHERE t.equipment_id = equipment.equipment_id), 0)"
    )
    with op.batch_alter_table('equipment') as batch_op:
        batch_op.alter_column('onan_val', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('onaf_val', existing_type=sa.Float(), nullable=False)
        batch_op.create_unique_constraint(
            'uq_equipment_natural_key', ['factory_code', 'ef_code', 'transformer_name']
        )

    op.drop_table('transformer_spec')
