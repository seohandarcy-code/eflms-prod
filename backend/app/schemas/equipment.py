from datetime import date, datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ef1 import Ef1Detail
from app.schemas.ef2 import Ef2Detail
from app.schemas.ef3 import Ef3Detail
from app.schemas.ef4 import Ef4Detail
from app.schemas.ef5 import Ef5Detail
from app.schemas.ef6 import Ef6Detail
from app.schemas.ef7 import Ef7Detail

EquipmentStatus = Literal["normal", "review", "replace"]


class EquipmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: int
    factory_code: str
    ef_code: str
    equipment_name: str
    voltage: int
    operation_start_time: date
    pof: float
    cof: float
    dof: float
    total_score: float
    status: EquipmentStatus
    last_diag_date: date | None = None


class ScoreSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pof_minus: float
    pof: float
    cof_minus: float
    cof: float
    dof_minus: float
    dof: float
    total_score: float
    computed_at: datetime


class ScoreHistoryPoint(BaseModel):
    """점수 이력 한 점 — 설비(유형·사업장·이름)·점수 기준일별(Stage 21-3)."""

    as_of: date
    pof: float
    cof: float
    dof: float
    total_score: float
    status: str


class ProjectionChange(BaseModel):
    """예측 한 해에서 값이 바뀐 POF 감점 항목 — 직전 해 대비(Stage 21-2)."""

    field: str
    label: str
    value: float
    delta: float  # 직전 해보다 얼마나 바뀌었나(음수 = 더 깎임, 양수 = 감점이 줄어 POF 상승)


class ProjectionPoint(BaseModel):
    """N년 뒤 점수 — 저장된 입력값으로 설비유형 공식을 기준일만 바꿔 재계산한 값(0년 = 저장된 점수).

    화면의 "5개년 POF 예측"이 이 값을 쓴다(2026-11-19 Stage 21-2, 사용자 결정 — 현재 로직 그대로 + 이유 표시).
    진단·점검값은 지금 그대로라고 가정하고 날짜에 따라 바뀌는 감점(경과연수·와이블 노화·EF1 Furan 연평균·
    EF7 SOH)만 반영한다. 그래서 POF가 오히려 오르는 해가 있을 수 있다 — EF1 Furan(총량 ÷ 사용년수가
    5 아래로 내려가 -24 해제), EF5·EF6 차단기(7.5년에 1회 교체 가정으로 수명이 다시 시작). 이전 결정
    (2026-10-17 "화면에서는 쓰지 않음")을 대신한다. 바뀐 항목은 pof_changes로 함께 준다.
    """

    years_ahead: int
    as_of: date
    pof: float
    cof: float
    dof: float
    total_score: float
    status: str = "normal"  # 그 해 판정(normal/review/replace)
    pof_changes: list[ProjectionChange] = []


# 설비유형별 상세는 ef_code로 구분되는 union — 새 유형은 여기에 스키마 하나를 추가한다.
TypeDetail = Annotated[Union[Ef1Detail, Ef2Detail, Ef3Detail, Ef4Detail, Ef5Detail, Ef6Detail, Ef7Detail], Field(discriminator="ef_code")]


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
    last_updated: datetime | None = None  # 호환용(점수 행을 처음 만든 시각) — 화면은 아래 두 날짜를 쓴다
    # 점수 기준일(계산 결과 테이블 today) — 설비마다 다를 수 있어 가장 이른 날과 가장 늦은 날(Stage 21-1)
    score_as_of: date | None = None
    score_as_of_latest: date | None = None
    # 진단 데이터 반영일 — 설비별 '최근 진단일' 중 가장 최근(점수 갱신으로는 바뀌지 않는다)
    data_updated_on: date | None = None
    # 마지막 점수 갱신(성공·일부 실패) 종료 시각(한국 시간)과 구분 — startup/daily/schedule = 자동, admin/cli = 수동(Stage 21-1c)
    score_refreshed_at: datetime | None = None
    score_refresh_trigger: str | None = None
    score_refresh_auto: bool = False  # 서버 자동 갱신(SCORE_REFRESH_AUTO) 켜짐 여부
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


class FormulaAxisOut(BaseModel):
    axis: str
    label: str
    # 항목 형태(steps/map/worse/expr)마다 칸이 달라 dict로 둔다 — 형식은 app/equipment_types/formula_docs.py
    items: list[dict[str, Any]]


class FormulaDocsOut(BaseModel):
    """지표설명 상세 페이지의 유형별 계산식(Stage 22-11). documented=False면 아직 설명을 채우지 않은 유형."""

    ef_code: str
    ef_name: str
    documented: bool
    total_tex: str
    axes: list[FormulaAxisOut]
    common_rules: list[str]
