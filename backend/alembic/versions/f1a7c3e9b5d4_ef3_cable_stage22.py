"""EF3 케이블 횡전개 개정 (Stage 22, 2026-11-20)

`ref_data_revised/schema_eflms_cable.py`(사용자 횡전개 수정본) 기준으로 EF3 입력·계산 컬럼을 바꾼다.
- cable_spec: +tl_apply, tl_num, laying_type2, end_joint2 / -cable_length(사고복구비용을 길이로 계산하지 않음)
- cable_condition: +recent_diag_date, 진단결과(온도·열화상·PD·시스순환전류·SVL·피뢰기), PD신호 3종, 시스순환전류 이론치,
  기본파·3고조파 누설전류(DB 이름 third_har_leak_curr) / -failure_rate(이제 계산값)
- cable_consequence_attribute: +rep_cost(등급)
- cable_design_attribute: reliability 정수(회선수) → 문자(N+0/N+1/N+N)
- cable_score_detail: +failure_rate(계산값), la_leak_curr_minus, tl_minus / -rep_cost(옛 길이 기반 계산값)

기존 EF3 행은 값의 형식이 바뀌어 옮길 수 없다(새 입력은 null, 공급신뢰도는 숫자가 글자로 남음) — 업그레이드 뒤
`python -m app.db.seed --ef-code EF3 --rows 30 --reset`(목업) 또는 새 양식 파일로 교체 임포트한다. 새 감점 칸은 0으로
시작하고 다음 점수 갱신 때 다시 계산된다. 되돌리면(downgrade) 새 칸의 값은 버려진다.

Revision ID: f1a7c3e9b5d4
Revises: e7f3c1a9d5b2
Create Date: 2026-11-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a7c3e9b5d4'
down_revision: Union[str, Sequence[str], None] = 'e7f3c1a9d5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cable_spec') as batch_op:
        batch_op.add_column(sa.Column('tl_apply', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('tl_num', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('laying_type2', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('end_joint2', sa.String(length=20), nullable=True))
        batch_op.drop_column('cable_length')

    with op.batch_alter_table('cable_condition') as batch_op:
        batch_op.add_column(sa.Column('recent_diag_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('max_temp_diag', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('diff_temp_diag', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('pd_signal_3Mhz', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pd_signal_6Mhz', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pd_signal_10Mhz', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pd_diag_rslt', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('sys_cycle_theo_curr', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('sys_cycle_curr_diag', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('svl_leak_curr_diag', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('basic_leak_curr', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('third_har_leak_curr', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('la_leak_curr_diag', sa.String(length=10), nullable=True))
        batch_op.drop_column('failure_rate')

    with op.batch_alter_table('cable_consequence_attribute') as batch_op:
        batch_op.add_column(sa.Column('rep_cost', sa.String(length=10), nullable=True))

    with op.batch_alter_table('cable_design_attribute') as batch_op:
        batch_op.alter_column('reliability', existing_type=sa.Integer(), type_=sa.String(length=10),
                              postgresql_using='reliability::varchar')

    with op.batch_alter_table('cable_score_detail') as batch_op:
        batch_op.add_column(sa.Column('failure_rate', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('la_leak_curr_minus', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('tl_minus', sa.Float(), nullable=False, server_default='0'))
        batch_op.drop_column('rep_cost')


def downgrade() -> None:
    with op.batch_alter_table('cable_score_detail') as batch_op:
        batch_op.add_column(sa.Column('rep_cost', sa.Float(), nullable=True))
        batch_op.drop_column('tl_minus')
        batch_op.drop_column('la_leak_curr_minus')
        batch_op.drop_column('failure_rate')

    # 숫자가 아닌 값(N+N 등)은 정수로 바꿀 수 없어 비운다
    if op.get_bind().dialect.name == 'sqlite':
        op.execute("UPDATE cable_design_attribute SET reliability = NULL "
                   "WHERE reliability IS NOT NULL AND reliability GLOB '*[^0-9]*'")
    else:
        op.execute("UPDATE cable_design_attribute SET reliability = NULL "
                   "WHERE reliability IS NOT NULL AND reliability !~ '^[0-9]+$'")
    with op.batch_alter_table('cable_design_attribute') as batch_op:
        batch_op.alter_column('reliability', existing_type=sa.String(length=10), type_=sa.Integer(),
                              postgresql_using='reliability::integer')

    with op.batch_alter_table('cable_consequence_attribute') as batch_op:
        batch_op.drop_column('rep_cost')

    with op.batch_alter_table('cable_condition') as batch_op:
        batch_op.add_column(sa.Column('failure_rate', sa.Float(), nullable=True))
        for name in ('la_leak_curr_diag', 'third_har_leak_curr', 'basic_leak_curr', 'svl_leak_curr_diag',
                     'sys_cycle_curr_diag', 'sys_cycle_theo_curr', 'pd_diag_rslt', 'pd_signal_10Mhz',
                     'pd_signal_6Mhz', 'pd_signal_3Mhz', 'diff_temp_diag', 'max_temp_diag', 'recent_diag_date'):
            batch_op.drop_column(name)

    with op.batch_alter_table('cable_spec') as batch_op:
        batch_op.add_column(sa.Column('cable_length', sa.Integer(), nullable=True))
        batch_op.drop_column('end_joint2')
        batch_op.drop_column('laying_type2')
        batch_op.drop_column('tl_num')
        batch_op.drop_column('tl_apply')
