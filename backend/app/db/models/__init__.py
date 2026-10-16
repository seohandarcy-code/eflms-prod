from app.db.models.auth import AllowedUser
from app.db.models.equipment import Equipment, EquipmentType
from app.db.models.extra import EquipmentExtraAttribute
from app.db.models.gis import (
    GisConsequenceAttribute,
    GisDesignAttribute,
    GisDiagnosis,
    GisOperation,
    GisScoreDetail,
    GisSf6Reading,
)
from app.db.models.readings import (
    DesignAttribute,
    DielectricTest,
    DgaReading,
    FuranReading,
    LoadCondition,
    OilTest,
    PeriodicInspection,
    TransformerSpec,
)
from app.db.models.scoring import ScoreSnapshot, TransformerScoreDetail

__all__ = [
    "AllowedUser",
    "Equipment",
    "EquipmentType",
    "EquipmentExtraAttribute",
    "DgaReading",
    "FuranReading",
    "DielectricTest",
    "OilTest",
    "LoadCondition",
    "PeriodicInspection",
    "DesignAttribute",
    "TransformerSpec",
    "ScoreSnapshot",
    "TransformerScoreDetail",
    "GisOperation",
    "GisDiagnosis",
    "GisSf6Reading",
    "GisConsequenceAttribute",
    "GisDesignAttribute",
    "GisScoreDetail",
]
