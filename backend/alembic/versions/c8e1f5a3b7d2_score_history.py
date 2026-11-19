"""score_history (Stage 21-3, 2026-11-19)

설비별·점수 기준일별 점수 이력. 설비는 (ef_code, factory_code, equipment_name)으로 묶는다(교체 임포트로
equipment_id가 바뀌어도 이어지게). 지금 저장된 점수를 첫 이력으로 채운다(점수 기준일 = 각 유형 계산 결과
테이블의 today). 판정 기준은 app/services/equipment_service.classify_status와 같다(여기 따로 둔다 —
마이그레이션은 앱 코드가 바뀌어도 그대로 돌아야 한다).

Revision ID: c8e1f5a3b7d2
Revises: a6c2e9f4d1b8
Create Date: 2026-11-19 20:00:00.000000

"""
from datetime import date, datetime, timedelta, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e1f5a3b7d2'
down_revision: Union[str, Sequence[str], None] = 'a6c2e9f4d1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCORE_DETAIL_TABLES = [
    'transformer_score_detail', 'gis_score_detail', 'cable_score_detail', 'switchgear_score_detail',
    'ups_score_detail', 'vdp_score_detail', 'battery_score_detail',
]


def _status(pof: float, cof: float, dof: float) -> str:
    normal_bar, replace_bar = (50, 30) if cof > 60 and dof > 60 else (60, 40)
    if pof > normal_bar:
        return 'normal'
    if pof >= replace_bar:
        return 'review'
    return 'replace'


def upgrade() -> None:
    history = op.create_table(
        'score_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ef_code', sa.String(length=16), nullable=False),
        sa.Column('factory_code', sa.String(length=32), nullable=False),
        sa.Column('equipment_name', sa.String(length=128), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=True),
        sa.Column('as_of', sa.Date(), nullable=False),
        sa.Column('pof', sa.Float(), nullable=False),
        sa.Column('cof', sa.Float(), nullable=False),
        sa.Column('dof', sa.Float(), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('ef_code', 'factory_code', 'equipment_name', 'as_of', name='uq_score_history_day'),
    )
    op.create_index('ix_score_history_ef_code', 'score_history', ['ef_code'])

    conn = op.get_bind()
    now = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
    rows = []
    existing = set(sa.inspect(conn).get_table_names())
    for table in SCORE_DETAIL_TABLES:
        if table not in existing:
            continue
        result = conn.execute(sa.text(
            'SELECT e.ef_code, e.factory_code, e.equipment_name, e.equipment_id, d.today, '
            's.pof, s.cof, s.dof, s.total_score '
            f'FROM equipment e JOIN score_snapshot s ON s.equipment_id = e.equipment_id '
            f'JOIN {table} d ON d.equipment_id = e.equipment_id'
        ))
        for ef, factory, name, eq_id, today, pof, cof, dof, total in result:
            rows.append(dict(
                ef_code=ef, factory_code=factory, equipment_name=name, equipment_id=eq_id,
                as_of=date.fromisoformat(today) if isinstance(today, str) else today,
                pof=pof, cof=cof, dof=dof, total_score=total, status=_status(pof, cof, dof), recorded_at=now,
            ))
    if rows:
        op.bulk_insert(history, rows)


def downgrade() -> None:
    op.drop_index('ix_score_history_ef_code', table_name='score_history')
    op.drop_table('score_history')
