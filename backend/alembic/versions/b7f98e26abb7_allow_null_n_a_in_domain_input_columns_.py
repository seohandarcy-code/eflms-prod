"""allow null (N/A) in domain input columns (Stage 11)

사내 입력파일의 N/A(`N/A`·`n/a`·`#N/A`)를 null로 저장하기 위해 EF1~EF4 유형별 테이블의 입력 컬럼
전부(계산 기준일로 채우는 updated_at/measured_at 제외)와, null 입력 때문에 null이 될 수 있는 파생값
(EF1 TCG·판정값 등 11개, EF3 부하율·사고영향성용량·사고복구비용)을 null 허용으로 바꾼다.
감점(_minus) 컬럼과 공통 테이블(equipment/score_snapshot)은 그대로다. 규칙은 app/equipment_types/na.py,
docs/DATA_DICTIONARY.md "값 없음(N/A) 처리".

SQLite는 컬럼 제약을 바꿀 수 없어 batch(테이블 재생성)로 처리한다.
되돌리기는 null 값이 하나도 없을 때만 가능하다 — 있으면 어느 테이블·컬럼인지 알려주고 멈춘다.

Revision ID: b7f98e26abb7
Revises: 6e6b51952ee7
Create Date: 2026-10-29 11:29:21.785277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f98e26abb7'
down_revision: Union[str, Sequence[str], None] = '6e6b51952ee7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 테이블 → [(컬럼, 기존 타입)]
NULLABLE_COLUMNS = {
    'cable_condition': [
        ('max_load', sa.INTEGER()),
        ('max_temp', sa.FLOAT()),
        ('diff_temp', sa.FLOAT()),
        ('failure_rate', sa.FLOAT()),
        ('pd_num', sa.INTEGER()),
        ('sys_cycle_curr', sa.FLOAT()),
        ('svl_leak_curr', sa.FLOAT()),
        ('joint_ex_damage', sa.VARCHAR(length=10)),
        ('cable_move', sa.FLOAT()),
    ],
    'cable_consequence_attribute': [
        ('emerge_resp', sa.VARCHAR(length=20)),
        ('rep_time', sa.VARCHAR(length=20)),
    ],
    'cable_design_attribute': [
        ('reliability', sa.INTEGER()),
        ('temp_diag', sa.VARCHAR(length=10)),
        ('pd_diag', sa.VARCHAR(length=10)),
        ('live_line_diag', sa.VARCHAR(length=10)),
        ('cable_move_diag', sa.VARCHAR(length=10)),
        ('offline_diag', sa.VARCHAR(length=20)),
        ('longlife_insul', sa.VARCHAR(length=10)),
    ],
    'cable_score_detail': [
        ('load_percent', sa.FLOAT()),
        ('risk_mva', sa.INTEGER()),
        ('rep_cost', sa.FLOAT()),
    ],
    'cable_spec': [
        ('cable_sq', sa.INTEGER()),
        ('cable_per_phase', sa.INTEGER()),
        ('cable_mva', sa.INTEGER()),
        ('cable_length', sa.INTEGER()),
        ('laying_type', sa.VARCHAR(length=20)),
        ('mid_joint', sa.INTEGER()),
        ('end_joint', sa.VARCHAR(length=20)),
    ],
    'design_attribute': [
        ('fire_vul_type', sa.VARCHAR(length=20)),
        ('fire_spread_loc', sa.VARCHAR(length=20)),
        ('emerge_response_1s', sa.VARCHAR(length=20)),
        ('redundancy', sa.VARCHAR(length=20)),
        ('ato', sa.VARCHAR(length=20)),
        ('online_og_chk', sa.VARCHAR(length=20)),
        ('offline_safety_chk', sa.VARCHAR(length=20)),
        ('sec_num', sa.INTEGER()),
        ('alarm_num', sa.INTEGER()),
        ('insul_1st_lvup', sa.VARCHAR(length=20)),
        ('high_insul_adt', sa.VARCHAR(length=20)),
        ('double_insul', sa.VARCHAR(length=20)),
        ('install_55k', sa.VARCHAR(length=20)),
        ('sfra_test', sa.VARCHAR(length=20)),
        ('rip_install', sa.VARCHAR(length=20)),
        ('vacuum_set', sa.VARCHAR(length=20)),
    ],
    'dga_reading': [
        ('diag_time', sa.DATE()),
        ('dga_h2', sa.INTEGER()),
        ('dga_c2h2', sa.FLOAT()),
        ('dga_c2h4', sa.INTEGER()),
        ('dga_c2h6', sa.INTEGER()),
        ('dga_ch4', sa.INTEGER()),
        ('dga_c3h8', sa.INTEGER()),
        ('dga_co', sa.INTEGER()),
        ('dga_co2', sa.INTEGER()),
        ('dga_o2', sa.INTEGER()),
        ('dga_n2', sa.INTEGER()),
        ('dga_fluc', sa.INTEGER()),
    ],
    'dielectric_test': [
        ('dielec_str_te_1', sa.FLOAT()),
        ('dielec_str_te_2', sa.FLOAT()),
        ('dielec_str_te_3', sa.FLOAT()),
        ('dielec_str_te_4', sa.FLOAT()),
        ('dielec_str_te_5', sa.FLOAT()),
        ('dielec_str_te_6', sa.FLOAT()),
    ],
    'furan_reading': [
        ('diag_time', sa.DATE()),
        ('furan_5h2f', sa.INTEGER()),
        ('furan_2fol', sa.FLOAT()),
        ('furan_2fal', sa.INTEGER()),
        ('furan_2acf', sa.INTEGER()),
        ('furan_5m2f', sa.INTEGER()),
    ],
    'gis_consequence_attribute': [
        ('in_vol', sa.VARCHAR(length=10)),
        ('capa_times_load', sa.VARCHAR(length=10)),
        ('fire_spread', sa.VARCHAR(length=10)),
        ('env_loc', sa.VARCHAR(length=10)),
        ('emerge_resp_pat', sa.VARCHAR(length=10)),
        ('rep_cost', sa.VARCHAR(length=10)),
        ('rep_time', sa.VARCHAR(length=10)),
    ],
    'gis_design_attribute': [
        ('in_line_num', sa.VARCHAR(length=10)),
        ('ato', sa.VARCHAR(length=10)),
        ('reliability', sa.VARCHAR(length=10)),
        ('online_diag', sa.VARCHAR(length=10)),
        ('offline_diag', sa.VARCHAR(length=10)),
        ('tbm', sa.VARCHAR(length=10)),
        ('conn_rev', sa.VARCHAR(length=10)),
        ('leak_str', sa.VARCHAR(length=10)),
        ('insul_str', sa.VARCHAR(length=10)),
        ('vt_la_str', sa.VARCHAR(length=10)),
    ],
    'gis_diagnosis': [
        ('part_dischar_pat', sa.VARCHAR(length=10)),
        ('elec_room_max_temp', sa.INTEGER()),
    ],
    'gis_operation': [
        ('op_type', sa.VARCHAR(length=20)),
        ('cb_op_num', sa.INTEGER()),
        ('rated_trip_count', sa.INTEGER()),
        ('cum_trip_current', sa.FLOAT()),
        ('load_percent', sa.FLOAT()),
        ('leakage_curr', sa.FLOAT()),
    ],
    'gis_sf6_reading': [
        ('diag_time', sa.DATE()),
        ('sf6_so2', sa.FLOAT()),
        ('sf6_leak', sa.VARCHAR(length=10)),
        ('sf6_h2o', sa.FLOAT()),
        ('sf6_purity', sa.FLOAT()),
    ],
    'load_condition': [
        ('load_percent', sa.FLOAT()),
        ('coil_max_temp', sa.INTEGER()),
    ],
    'oil_test': [
        ('acid_measure_val', sa.FLOAT()),
        ('moisture_rslt', sa.FLOAT()),
    ],
    'periodic_inspection': [
        ('part_discharge_diag', sa.VARCHAR(length=20)),
        ('oltc_96t_diag', sa.VARCHAR(length=20)),
        ('oltc_rslt', sa.INTEGER()),
        ('oltc_type', sa.VARCHAR(length=20)),
        ('thermal_img_temp', sa.VARCHAR(length=20)),
        ('noise_diag', sa.VARCHAR(length=20)),
    ],
    'switchgear_condition': [
        ('part_thermal_chk', sa.VARCHAR(length=10)),
        ('elec_room_avg_temp', sa.INTEGER()),
        ('temp_diff_chk', sa.INTEGER()),
        ('max_temp_chk', sa.INTEGER()),
        ('load_chk', sa.FLOAT()),
        ('ex_box_chk', sa.VARCHAR(length=10)),
        ('noise_chk', sa.VARCHAR(length=10)),
        ('bolt_chk', sa.VARCHAR(length=10)),
    ],
    'switchgear_consequence_attribute': [
        ('scale_dam_chk', sa.FLOAT()),
        ('sup_sys_chk', sa.VARCHAR(length=10)),
        ('prod_chk', sa.VARCHAR(length=10)),
        ('op_chk', sa.VARCHAR(length=10)),
        ('replace_chk', sa.FLOAT()),
        ('recovery_time_chk', sa.FLOAT()),
        ('replace_time_chk', sa.INTEGER()),
    ],
    'switchgear_design_attribute': [
        ('reliability', sa.VARCHAR(length=10)),
        ('ato', sa.VARCHAR(length=10)),
        ('cb_inspect', sa.VARCHAR(length=10)),
        ('relay_chk', sa.VARCHAR(length=10)),
        ('online_diag', sa.VARCHAR(length=10)),
        ('part_shortage', sa.VARCHAR(length=10)),
    ],
    'switchgear_spec': [
        ('eqp_id_name', sa.VARCHAR(length=50)),
        ('eqp_building', sa.VARCHAR(length=50)),
        ('eqp_disting', sa.VARCHAR(length=20)),
        ('eqp_floor', sa.VARCHAR(length=20)),
        ('install_building', sa.VARCHAR(length=20)),
    ],
    'transformer_score_detail': [
        ('dga_tcg', sa.FLOAT()),
        ('dga_diag', sa.VARCHAR(length=20)),
        ('dielec_str_te_avg', sa.FLOAT()),
        ('dielec_str_te_diag', sa.VARCHAR(length=20)),
        ('acid_measure_desc', sa.VARCHAR(length=20)),
        ('moisture_desc', sa.VARCHAR(length=20)),
        ('furan_total', sa.FLOAT()),
        ('furan_total_per_year', sa.FLOAT()),
        ('furan_desc', sa.VARCHAR(length=20)),
        ('oltc_diag', sa.VARCHAR(length=20)),
        ('capa_times_load', sa.FLOAT()),
    ],
    'transformer_spec': [
        ('onan_val', sa.INTEGER()),
        ('onaf_val', sa.FLOAT()),
    ],
}


def _set_nullable(nullable: bool) -> None:
    for table, columns in NULLABLE_COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for column, existing_type in columns:
                batch_op.alter_column(column, existing_type=existing_type, nullable=nullable)


def upgrade() -> None:
    """Upgrade schema."""
    _set_nullable(True)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    found = []
    for table, columns in NULLABLE_COLUMNS.items():
        for column, _ in columns:
            count = conn.execute(sa.text(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NULL')).scalar()
            if count:
                found.append(f"{table}.{column}({count}건)")
    if found:
        raise RuntimeError(
            "N/A(null) 값이 남아 있어 되돌릴 수 없습니다: " + ", ".join(found[:10])
            + (" 외" if len(found) > 10 else "")
            + " — 해당 유형을 N/A 없는 파일로 다시 --replace 임포트한 뒤 되돌리세요."
        )
    _set_nullable(False)
