from datetime import date, datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ef1 import Ef1Detail
from app.schemas.ef2 import Ef2Detail

EquipmentStatus = Literal["normal", "review", "replace"]


class EquipmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: int
    factory_code: str
    ef_code: str
    equipment_name: str
    voltage: int
    pof: int
    cof: int
    dof: int
    total_score: float
    status: EquipmentStatus
    last_diag_date: date | None = None


class ScoreSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pof_minus: int
    pof: int
    cof_minus: int
    cof: int
    dof_minus: int
    dof: int
    total_score: float
    computed_at: datetime


class ProjectionPoint(BaseModel):
    """N년 뒤 점수 — 저장된 입력값으로 설비유형 공식을 기준일만 바꿔 재계산한 값(0년 = 저장된 점수).

    **화면에서는 쓰지 않는다(2026-10-17 결정)**: 측정값을 고정한 채 기준일만 늦추므로, 시간에 따라
    쌓이는 값을 연수로 나눠 판정하는 항목이 있으면 점수가 오히려 좋아진다 — EF1 Furan(총량÷사용년수)
    때문에 실제로 2년 뒤 PoF가 21→44로 역전되는 설비가 있었다. 화면의 5개년 예측은 기존대로 "연 -1점
    단순 가정"(frontend ScoreProjectionChart). 예측 모델(누적값 증가율 가정 등)이 정해지면 이 값을 보정해 쓴다.
    """

    years_ahead: int
    as_of: date
    pof: int
    cof: int
    dof: int
    total_score: float


# 설비유형별 상세는 ef_code로 구분되는 union — 새 유형은 여기에 스키마 하나를 추가한다.
TypeDetail = Annotated[Union[Ef1Detail, Ef2Detail], Field(discriminator="ef_code")]


class EquipmentDetail(BaseModel):
    equipment_id: int
    factory_code: str
    ef_code: str
    ef_name: str
    equipment_name: str
    voltage: int
    operation_start_time: date
    status: EquipmentStatus
    score: ScoreSnapshotOut
    type_detail: TypeDetail
    projection: list[ProjectionPoint]


class TypeKPI(BaseModel):
    ef_code: str
    ef_name: str
    total_equipment: int
    review_count: int
    replace_count: int


class SummaryKPI(BaseModel):
    total_equipment: int
    review_count: int
    replace_count: int
    last_updated: datetime | None = None
    by_type: list[TypeKPI] = []


class BreakdownItem(BaseModel):
    field: str
    label: str
    group: str | None = None
    # False면 계산 결과에는 나오지만 축 점수(pof 등) 합산에는 들어가지 않는 항목(원본 공식대로).
    summed: bool = True


class EquipmentTypeOut(BaseModel):
    ef_code: str
    ef_name: str
    equipment_count: int
    breakdown: dict[str, list[BreakdownItem]]
