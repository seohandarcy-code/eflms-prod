"""점수 시뮬레이터 응답 (Stage 19) — 계산만 하고 DB에는 쓰지 않는다."""
from pydantic import BaseModel, Field

from app.schemas.equipment import EquipmentStatus


class SimulatorColumn(BaseModel):
    """데이터 입력 양식(data_admin_service.template)의 한 칸과 같은 모양."""
    name: str
    label: str
    dtype: str
    choices: list[str | int | float] | None = None
    min: float | None = None
    max: float | None = None
    gt: float | None = None
    required: bool | None = None
    allow_blank: bool | None = None  # 빈칸 허용(EF3 포설·종단, Stage 22-8)
    na_allowed: bool


class SimulatorSite(BaseModel):
    factory_code: str
    equipment_count: int


class SimulatorExcludedSite(BaseModel):
    factory_code: str
    reason: str


class SimulatorEquipment(BaseModel):
    equipment_id: int
    factory_code: str
    equipment_name: str


class SimulatorForm(BaseModel):
    ef_code: str
    ef_name: str
    name_field: str
    columns: list[SimulatorColumn]
    header: str
    # 그 유형의 설비가 있고 사업장별 참고표에도 행이 있는 사업장만 — 실제 데이터는 지금 H1
    sites: list[SimulatorSite]
    excluded_sites: list[SimulatorExcludedSite]
    equipment: list[SimulatorEquipment]


class SimulatorRequest(BaseModel):
    # 칸 이름 → 입력 문자열(데이터 입력 붙여넣기와 같은 규칙, "N/A" = 값 없음)
    values: dict[str, str] = Field(default_factory=dict)


class SimulatorFieldError(BaseModel):
    column: str
    raw_value: str
    reason: str


class SimulatorItem(BaseModel):
    field: str
    label: str
    group: str | None = None
    summed: bool = True
    value: float | None = None


class SimulatorResult(BaseModel):
    ok: bool
    errors: list[SimulatorFieldError] = Field(default_factory=list)
    as_of: str | None = None
    pof: float | None = None
    cof: float | None = None
    dof: float | None = None
    total_score: float | None = None
    status: EquipmentStatus | None = None
    breakdown: dict[str, list[SimulatorItem]] = Field(default_factory=dict)


class SimulatorSample(BaseModel):
    values: dict[str, str]
    source: str  # "example" | "equipment"
    equipment_id: int | None = None
    # 시작값 그대로 계산한 결과 — 화면의 "원래 점수"(같은 기준일이라 차이는 바꾼 값 때문만)
    baseline: SimulatorResult
