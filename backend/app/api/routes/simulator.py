"""점수 시뮬레이터 API (Stage 19) — 대시보드와 같은 권한(`require_viewer`), 계산만 하고 DB에 쓰지 않는다.

- `GET  /api/simulator/{ef_code}/form`   — 입력 양식 + 고를 수 있는 사업장·설비(+ 제외된 사업장과 이유)
- `GET  /api/simulator/{ef_code}/sample` — 시작값(?equipment_id= 기존 설비, 없으면 예시값) + 그 값의 결과
- `POST /api/simulator/{ef_code}/calculate` {values} — 칸별 오류 또는 POF·COF·DOF·종합점수·판정·감점 항목
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_viewer
from app.db.session import get_session
from app.schemas.simulator import SimulatorForm, SimulatorRequest, SimulatorResult, SimulatorSample
from app.services import simulator_service
from app.services.simulator_service import SimulatorError

router = APIRouter(prefix="/api/simulator", tags=["simulator"], dependencies=[Depends(require_viewer)])


@router.get("/{ef_code}/form", response_model=SimulatorForm)
async def get_form(ef_code: str, session: AsyncSession = Depends(get_session)) -> SimulatorForm:
    try:
        return await simulator_service.form(session, ef_code)
    except SimulatorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{ef_code}/sample", response_model=SimulatorSample)
async def get_sample(
    ef_code: str, equipment_id: int | None = None, session: AsyncSession = Depends(get_session)
) -> SimulatorSample:
    try:
        return await simulator_service.sample(session, ef_code, equipment_id)
    except SimulatorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{ef_code}/calculate", response_model=SimulatorResult)
async def post_calculate(
    ef_code: str, body: SimulatorRequest, session: AsyncSession = Depends(get_session)
) -> SimulatorResult:
    try:
        return await simulator_service.calculate(session, ef_code, body.values)
    except SimulatorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
