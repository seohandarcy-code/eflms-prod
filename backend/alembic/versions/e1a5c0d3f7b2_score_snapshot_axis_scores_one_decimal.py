"""score_snapshot axis scores to one decimal (Stage 13-0)

POF·COF·DOF와 각 감점을 소수 첫째 자리로 저장하기 위해 score_snapshot의 6개 컬럼을 INTEGER → FLOAT로
바꾼다(2026-11-06 사용자 결정 — (가) 방식, 모든 설비유형 공통). 기존 값은 정수 그대로 옮겨진다.
종합점수(total_score, 원래 FLOAT)는 계산이 소수 첫째 자리로 반올림하게 됐으므로 저장값도 맞춰 둔다.
규칙은 app/equipment_types/rounding.py, docs/DATA_DICTIONARY.md "점수 지표 소수 첫째 자리".

SQLite는 컬럼 타입을 바꿀 수 없어 batch(테이블 재생성)로 처리한다.
되돌리기는 6개 컬럼에 소수 값이 하나도 없을 때만 가능하다 — 있으면 컬럼을 알려주고 멈춘다.

Revision ID: e1a5c0d3f7b2
Revises: b7f98e26abb7
Create Date: 2026-11-06 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a5c0d3f7b2'
down_revision: Union[str, Sequence[str], None] = 'b7f98e26abb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AXIS_COLUMNS = ['pof_minus', 'pof', 'cof_minus', 'cof', 'dof_minus', 'dof']


def upgrade() -> None:
    with op.batch_alter_table('score_snapshot') as batch_op:
        for name in AXIS_COLUMNS:
            batch_op.alter_column(name, existing_type=sa.INTEGER(), type_=sa.Float(), existing_nullable=False)
    # ROUND(NUMERIC, 1)은 SQLite·PostgreSQL 모두 0에서 먼 쪽으로 반올림 — rounding.round1과 같다.
    op.execute('UPDATE score_snapshot SET total_score = ROUND(CAST(total_score AS NUMERIC), 1)')


def downgrade() -> None:
    conn = op.get_bind()
    fractional = [
        name for name in AXIS_COLUMNS
        if conn.execute(sa.text(f'SELECT COUNT(*) FROM score_snapshot WHERE {name} <> CAST({name} AS INTEGER)')).scalar()
    ]
    if fractional:
        raise RuntimeError(
            '소수 점수가 남아 있어 정수 컬럼으로 되돌릴 수 없습니다: '
            + ', '.join(f'score_snapshot.{name}' for name in fractional)
            + ' — 해당 설비유형 데이터를 지운 뒤(python -m app.db.reset --ef-code <유형>) 다시 시도하세요.'
        )
    with op.batch_alter_table('score_snapshot') as batch_op:
        for name in AXIS_COLUMNS:
            batch_op.alter_column(name, existing_type=sa.Float(), type_=sa.INTEGER(), existing_nullable=False)
