"""score detail deductions to float (2026-11-19)

감점은 소수를 포함해 계산하고 소수 첫째 자리로 저장한다(2026-11-19 사용자 결정 — 경과연수·부품 상태 등에서
원본의 정수 반올림을 뺐다, app/equipment_types/rounding.py). EF1~EF4 계산 결과 테이블의 감점 컬럼이 정수라
소수 감점이 잘리므로 INTEGER → FLOAT로 바꾼다(EF5~EF7 테이블과 score_snapshot은 이미 FLOAT).
기존 값은 정수 그대로 옮겨진다 — 새 규칙의 점수는 `python -m app.db.recalculate`로 다시 계산해야 반영된다.

SQLite는 컬럼 타입을 바꿀 수 없어 batch(테이블 재생성)로 처리한다(PostgreSQL에서는 일반 ALTER).
되돌리기는 감점 컬럼에 소수 값이 하나도 없을 때만 가능하다 — 있으면 컬럼을 알려주고 멈춘다.

Revision ID: f3b8d1e6a9c4
Revises: 9df1f3504cfe
Create Date: 2026-11-19 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b8d1e6a9c4'
down_revision: Union[str, Sequence[str], None] = '9df1f3504cfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEDUCTION_COLUMNS: dict[str, list[str]] = {
    'transformer_score_detail': [
        'age_minus', 'dga_minus', 'load_minus', 'temp_minus', 'dielec_str_te_minus', 'acid_measure_minus',
        'moisture_minus', 'furan_minus', 'part_discharge_minus', 'oltc_96t_minus', 'oltc_minus',
        'thermal_img_minus', 'noise_minus', 'first_voltage_minus', 'productivity_minus', 'fire_minus',
        'fire_spread_minus', 'emerge_response_minus', 'rep_cost_minus', 'rep_time_minus', 'redundancy_minus',
        'ato_minus', 'online_og_minus', 'offline_safety_minus', 'sec_minus', 'alarm_minus', 'winding_minus',
        'prod_life_minus', 'connect_part_minus', 'temp_inc_limit_minus', 'test_reliability_minus',
        'bushing_minus', 'oltc2_minus',
    ],
    'gis_score_detail': [
        'age_minus', 'cb_op_num_minus', 'cb_stat_minus', 'insul_stat_minus', 'gis_mech_minus',
        'rated_trip_count_minus', 'cum_trip_current_minus', 'load_minus', 'leakage_curr_minus', 'gis_elec_minus',
        'part_dischar_minus', 'sf6_minus', 'elec_room_minus', 'gis_chem_minus', 'in_vol_minus',
        'productivity_minus', 'fire_spread_minus', 'env_minus', 'emerge_resp_minus', 'rep_cost_minus',
        'rep_time_minus', 'in_line_minus', 'ato_minus', 'reliability_minus', 'online_diag_minus',
        'offline_diag_minus', 'tbm_minus', 'conn_rev_minus', 'leak_str_minus', 'insul_str_minus', 'vt_la_minus',
    ],
    'cable_score_detail': [
        'age_minus', 'load_minus', 'temp_minus', 'diff_temp_minus', 'failure_rate_minus', 'pd_minus',
        'sys_cycle_curr_minus', 'svl_leak_curr_minus', 'joint_ex_damage_minus', 'cable_move_minus',
        'risk_mva_minus', 'laying_type_minus', 'mid_joint_minus', 'end_joint_minus', 'emerge_resp_minus',
        'rep_cost_minus', 'rep_time_minus', 'reliability_minus', 'temp_diag_minus', 'pd_diag_minus',
        'live_line_diag_minus', 'cable_move_diag_minus', 'offline_diag_minus', 'longlife_insul_minus',
    ],
    'switchgear_score_detail': [
        'age_minus', 'cb_stat_minus', 'durability_minus', 'part_thermal_chk_minus', 'elec_room_avg_temp_minus',
        'temp_diff_chk_minus', 'max_temp_chk_minus', 'load_minus', 'thermal_minus', 'ex_box_chk_minus',
        'noise_chk_minus', 'bolt_chk_minus', 'phy_minus', 'scale_dam_chk_minus', 'install_building_minus',
        'sup_sys_chk_minus', 'cof_sys_minus', 'prod_chk_minus', 'op_chk_minus', 'replace_chk_minus',
        'cof_cost_minus', 'recovery_time_chk_minus', 'replace_time_chk_minus', 'cof_recov_minus',
        'reliability_minus', 'ato_minus', 'dof_sys_minus', 'cb_inspect_minus', 'relay_chk_minus',
        'online_diag_minus', 'dof_cost_minus', 'part_shortage_minus', 'ct_use_minus', 'spec_use_minus',
        'dof_recov_minus',
    ],
}


def upgrade() -> None:
    for table, columns in DEDUCTION_COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for name in columns:
                batch_op.alter_column(name, existing_type=sa.INTEGER(), type_=sa.Float(), existing_nullable=False)


def downgrade() -> None:
    conn = op.get_bind()
    fractional = [
        f'{table}.{name}'
        for table, columns in DEDUCTION_COLUMNS.items()
        for name in columns
        if conn.execute(sa.text(f'SELECT COUNT(*) FROM {table} WHERE {name} <> CAST({name} AS INTEGER)')).scalar()
    ]
    if fractional:
        raise RuntimeError(
            '소수 감점이 남아 있어 정수 컬럼으로 되돌릴 수 없습니다: ' + ', '.join(fractional)
            + ' — 해당 설비유형 데이터를 지운 뒤(python -m app.db.reset --ef-code <유형>) 다시 시도하세요.'
        )
    for table, columns in DEDUCTION_COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for name in columns:
                batch_op.alter_column(name, existing_type=sa.Float(), type_=sa.INTEGER(), existing_nullable=False)
