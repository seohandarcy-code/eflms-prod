"""EF1(변압기) 전용 입력 도메인 테이블.

스냅샷 구조(설비당 1행)로 시작하되, 이력 전환을 대비해 각 테이블에
시점 컬럼(measured_at/updated_at)을 둔다. 이력 구조로 갈 때는
equipment_id를 PK에서 일반 FK+색인으로 바꾸기만 하면 된다.
"""
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DgaReading(Base):
    __tablename__ = "dga_reading"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    diag_time: Mapped[date] = mapped_column(Date)
    dga_h2: Mapped[int] = mapped_column(Integer)
    dga_c2h2: Mapped[float] = mapped_column(Float)
    dga_c2h4: Mapped[int] = mapped_column(Integer)
    dga_c2h6: Mapped[int] = mapped_column(Integer)
    dga_ch4: Mapped[int] = mapped_column(Integer)
    dga_c3h8: Mapped[int] = mapped_column(Integer)
    dga_co: Mapped[int] = mapped_column(Integer)
    dga_co2: Mapped[int] = mapped_column(Integer)
    dga_o2: Mapped[int] = mapped_column(Integer)
    dga_n2: Mapped[int] = mapped_column(Integer)
    dga_fluc: Mapped[int] = mapped_column(Integer)


class FuranReading(Base):
    __tablename__ = "furan_reading"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    diag_time: Mapped[date] = mapped_column(Date)
    furan_5h2f: Mapped[int] = mapped_column(Integer)
    furan_2fol: Mapped[float] = mapped_column(Float)
    furan_2fal: Mapped[int] = mapped_column(Integer)
    furan_2acf: Mapped[int] = mapped_column(Integer)
    furan_5m2f: Mapped[int] = mapped_column(Integer)


class DielectricTest(Base):
    __tablename__ = "dielectric_test"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    dielec_str_te_1: Mapped[float] = mapped_column(Float)
    dielec_str_te_2: Mapped[float] = mapped_column(Float)
    dielec_str_te_3: Mapped[float] = mapped_column(Float)
    dielec_str_te_4: Mapped[float] = mapped_column(Float)
    dielec_str_te_5: Mapped[float] = mapped_column(Float)
    dielec_str_te_6: Mapped[float] = mapped_column(Float)


class OilTest(Base):
    __tablename__ = "oil_test"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    acid_measure_val: Mapped[float] = mapped_column(Float)
    moisture_rslt: Mapped[float] = mapped_column(Float)


class LoadCondition(Base):
    __tablename__ = "load_condition"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    load_percent: Mapped[float] = mapped_column(Float)
    coil_max_temp: Mapped[int] = mapped_column(Integer)


class PeriodicInspection(Base):
    __tablename__ = "periodic_inspection"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    part_discharge_diag: Mapped[str] = mapped_column(String(20))
    oltc_96t_diag: Mapped[str] = mapped_column(String(20))
    oltc_rslt: Mapped[int] = mapped_column(Integer)
    oltc_type: Mapped[str] = mapped_column(String(20))
    thermal_img_temp: Mapped[str] = mapped_column(String(20))
    noise_diag: Mapped[str] = mapped_column(String(20))


class DesignAttribute(Base):
    __tablename__ = "design_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    fire_vul_type: Mapped[str] = mapped_column(String(20))
    fire_spread_loc: Mapped[str] = mapped_column(String(20))
    emerge_response_1s: Mapped[str] = mapped_column(String(20))
    redundancy: Mapped[str] = mapped_column(String(20))
    ato: Mapped[str] = mapped_column(String(20))
    online_og_chk: Mapped[str] = mapped_column(String(20))
    offline_safety_chk: Mapped[str] = mapped_column(String(20))
    sec_num: Mapped[int] = mapped_column(Integer)
    alarm_num: Mapped[int] = mapped_column(Integer)
    insul_1st_lvup: Mapped[str] = mapped_column(String(20))
    high_insul_adt: Mapped[str] = mapped_column(String(20))
    double_insul: Mapped[str] = mapped_column(String(20))
    install_55k: Mapped[str] = mapped_column(String(20))
    sfra_test: Mapped[str] = mapped_column(String(20))
    rip_install: Mapped[str] = mapped_column(String(20))
    vacuum_set: Mapped[str] = mapped_column(String(20))
