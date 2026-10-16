"""EF_code → 설비유형 모듈 레지스트리 (Stage 8-2).

새 설비유형은 모듈을 만들고 아래 _REGISTRY에 한 줄 추가하는 것으로 등록한다.
"""
from app.equipment_types import ef1_transformer, ef2_gis
from app.equipment_types.base import EquipmentTypeModule

_REGISTRY: dict[str, EquipmentTypeModule] = {
    ef1_transformer.EF_CODE: ef1_transformer,
    ef2_gis.EF_CODE: ef2_gis,
}


class UnknownEquipmentTypeError(KeyError):
    def __init__(self, ef_code: str):
        super().__init__(ef_code)
        self.ef_code = ef_code

    def __str__(self) -> str:
        return f"등록되지 않은 설비유형: {self.ef_code} (등록됨: {', '.join(registered_codes())})"


def get_module(ef_code: str) -> EquipmentTypeModule:
    try:
        return _REGISTRY[ef_code]
    except KeyError:
        raise UnknownEquipmentTypeError(ef_code) from None


def registered_codes() -> list[str]:
    return list(_REGISTRY)


def all_modules() -> list[EquipmentTypeModule]:
    return list(_REGISTRY.values())


def resolve_codes(ef_code: str) -> list[str]:
    """CLI용 — "all"이면 등록된 전체, 아니면 해당 코드 하나(검증 포함)."""
    if ef_code.lower() == "all":
        return registered_codes()
    get_module(ef_code)
    return [ef_code]
