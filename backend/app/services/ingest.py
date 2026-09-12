"""공용 데이터 적재 매퍼.

mock 시드(app/db/seed.py)와 향후 사내 입력파일 임포트가 동일하게 사용하는 함수.
`row`는 EF1 계산기(ef1_transformer.calculate)가 만든 "입력+계산 전체" flat dict.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DesignAttribute,
    DgaReading,
    DielectricTest,
    Equipment,
    EquipmentType,
    FuranReading,
    LoadCondition,
    OilTest,
    PeriodicInspection,
    ScoreSnapshot,
    TransformerScoreDetail,
)
from app.equipment_types.ef1_transformer import EF_CODE, EF_NAME


async def _get_or_create_equipment(row: dict, session: AsyncSession) -> Equipment:
    stmt = select(Equipment).where(
        Equipment.factory_code == row["factory_code"],
        Equipment.ef_code == row["EF_code"],
        Equipment.transformer_name == row["transformer_name"],
    )
    equipment = (await session.execute(stmt)).scalar_one_or_none()

    if equipment is None:
        equipment = Equipment(
            factory_code=row["factory_code"],
            ef_code=row["EF_code"],
            transformer_name=row["transformer_name"],
            voltage=row["voltage"],
            onan_val=row["ONAN_val"],
            onaf_val=row["ONAF_val"],
            operation_start_time=row["operation_start_time"],
        )
        session.add(equipment)
    else:
        equipment.voltage = row["voltage"]
        equipment.onan_val = row["ONAN_val"]
        equipment.onaf_val = row["ONAF_val"]
        equipment.operation_start_time = row["operation_start_time"]

    await session.flush()  # equipment_id 확보
    return equipment


async def ingest_row(row: dict, session: AsyncSession) -> int:
    """EF1 flat dict 한 건을 도메인 테이블들에 upsert 한다. equipment_id를 반환."""

    if await session.get(EquipmentType, EF_CODE) is None:
        session.add(EquipmentType(ef_code=EF_CODE, name=EF_NAME))
        await session.flush()

    equipment = await _get_or_create_equipment(row, session)
    eq_id = equipment.equipment_id

    await session.merge(
        DgaReading(
            equipment_id=eq_id,
            diag_time=row["dga_diag_time"],
            dga_h2=row["dga_h2"],
            dga_c2h2=row["dga_c2h2"],
            dga_c2h4=row["dga_c2h4"],
            dga_c2h6=row["dga_c2h6"],
            dga_ch4=row["dga_ch4"],
            dga_c3h8=row["dga_c3h8"],
            dga_co=row["dga_co"],
            dga_co2=row["dga_co2"],
            dga_o2=row["dga_o2"],
            dga_n2=row["dga_n2"],
            dga_fluc=row["dga_fluc"],
        )
    )

    await session.merge(
        FuranReading(
            equipment_id=eq_id,
            diag_time=row["furan_diag_time"],
            furan_5h2f=row["furan_5H2F"],
            furan_2fol=row["furan_2FOL"],
            furan_2fal=row["furan_2FAL"],
            furan_2acf=row["furan_2ACF"],
            furan_5m2f=row["furan_5M2F"],
        )
    )

    await session.merge(
        DielectricTest(
            equipment_id=eq_id,
            measured_at=row["today"],
            dielec_str_te_1=row["dielec_str_te_1"],
            dielec_str_te_2=row["dielec_str_te_2"],
            dielec_str_te_3=row["dielec_str_te_3"],
            dielec_str_te_4=row["dielec_str_te_4"],
            dielec_str_te_5=row["dielec_str_te_5"],
            dielec_str_te_6=row["dielec_str_te_6"],
        )
    )

    await session.merge(
        OilTest(
            equipment_id=eq_id,
            measured_at=row["today"],
            acid_measure_val=row["acid_measure_val"],
            moisture_rslt=row["moisture_rslt"],
        )
    )

    await session.merge(
        LoadCondition(
            equipment_id=eq_id,
            measured_at=row["today"],
            load_percent=row["load_percent"],
            coil_max_temp=row["coil_max_temp"],
        )
    )

    await session.merge(
        PeriodicInspection(
            equipment_id=eq_id,
            measured_at=row["today"],
            part_discharge_diag=row["part_discharge_diag"],
            oltc_96t_diag=row["oltc_96T_diag"],
            oltc_rslt=row["oltc_rslt"],
            oltc_type=row["oltc_type"],
            thermal_img_temp=row["thermal_img_temp"],
            noise_diag=row["noise_diag"],
        )
    )

    await session.merge(
        DesignAttribute(
            equipment_id=eq_id,
            updated_at=row["today"],
            fire_vul_type=row["fire_vul_type"],
            fire_spread_loc=row["fire_spread_loc"],
            emerge_response_1s=row["emerge_response_1s"],
            redundancy=row["redundancy"],
            ato=row["ato"],
            online_og_chk=row["online_og_chk"],
            offline_safety_chk=row["offline_safety_chk"],
            sec_num=row["sec_num"],
            alarm_num=row["alarm_num"],
            insul_1st_lvup=row["insul_1st_lvup"],
            high_insul_adt=row["high_insul_adt"],
            double_insul=row["double_insul"],
            install_55k=row["55k_install"],
            sfra_test=row["sfra_test"],
            rip_install=row["rip_install"],
            vacuum_set=row["vacuum_set"],
        )
    )

    await session.merge(
        ScoreSnapshot(
            equipment_id=eq_id,
            pof_minus=row["pof_minus"],
            pof=row["pof"],
            cof_minus=row["cof_minus"],
            cof=row["cof"],
            dof_minus=row["dof_minus"],
            dof=row["dof"],
            total_score=row["total_score"],
        )
    )

    await session.merge(
        TransformerScoreDetail(
            equipment_id=eq_id,
            today=row["today"],
            operation_year=row["operation_year"],
            age_minus=row["age_minus"],
            dga_tcg=row["dga_tcg"],
            dga_diag=row["dga_diag"],
            dga_minus=row["dga_minus"],
            load_minus=row["load_minus"],
            temp_minus=row["temp_minus"],
            dielec_str_te_avg=row["dielec_str_te_avg"],
            dielec_str_te_diag=row["dielec_str_te_diag"],
            dielec_str_te_minus=row["dielec_str_te_minus"],
            acid_measure_desc=row["acid_measure_desc"],
            acid_measure_minus=row["acid_measure_minus"],
            moisture_desc=row["moisture_desc"],
            moisture_minus=row["moisture_minus"],
            furan_total=row["furan_total"],
            furan_total_per_year=row["furan_total_per_year"],
            furan_desc=row["furan_desc"],
            furan_minus=row["furan_minus"],
            part_discharge_minus=row["part_discharge_minus"],
            oltc_96t_minus=row["oltc_96T_minus"],
            oltc_diag=row["oltc_diag"],
            oltc_minus=row["oltc_minus"],
            thermal_img_minus=row["thermal_img_minus"],
            noise_minus=row["noise_minus"],
            first_voltage=row["1st_voltage"],
            first_voltage_minus=row["1st_voltage_minus"],
            capa_times_load=row["capa_times_load"],
            productivity_minus=row["productivity_minus"],
            fire_minus=row["fire_minus"],
            fire_spread_minus=row["fire_spread_minus"],
            emerge_response_minus=row["emerge_response_minus"],
            rep_cost=row["rep_cost"],
            rep_cost_minus=row["rep_cost_minus"],
            rep_time=row["rep_time"],
            rep_time_minus=row["rep_time_minus"],
            redundancy_minus=row["redundancy_minus"],
            ato_minus=row["ato_minus"],
            online_og_minus=row["online_og_minus"],
            offline_safety_minus=row["offline_safety_minus"],
            sec_minus=row["sec_minus"],
            alarm_minus=row["alarm_minus"],
            winding_minus=row["winding_minus"],
            prod_life_minus=row["prod_life_minus"],
            connect_part_minus=row["connect_part_minus"],
            temp_inc_limit_minus=row["temp_inc_limit_minus"],
            test_reliability_minus=row["test_reliability_minus"],
            bushing_minus=row["bushing_minus"],
            oltc2_minus=row["oltc2_minus"],
        )
    )

    await session.commit()
    return eq_id
