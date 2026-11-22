"""입력 변경 이력과 되돌리기 (2026-11-19, Stage 21-4).

임포트(추가·갱신)·교체·행 편집·참고표 넣기/리셋 한 번 = data_change 1행, 실제로 바뀐 행마다 바뀌기 전후 입력값을
data_change_row(JSON)로 남긴다. 값이 하나도 바뀌지 않은 설비 행은 반영하지 않는다(진단 데이터 반영일도 그대로 —
오타 하나 없이 같은 행을 다시 넣었는데 "새로 진단한 것처럼" 보이던 문제, 2026-11-19 확인).

되돌리기(undo_change): 바뀌기 전 값으로 되돌린다 — 추가된 설비·행은 지우고, 갱신·삭제된 것은 이전 값(이전 반영일
포함)으로 다시 넣은 뒤 점수를 오늘 기준으로 다시 계산한다. 같은 설비·행을 그 뒤에 바꾼 변경이 아직 살아 있으면
막는다(최근 변경부터 되돌린다). 되돌리기 자체도 kind=undo로 기록되고, 되돌리기를 다시 되돌리지는 않는다.

이 모듈의 함수는 commit하지 않는다 — 부르는 쪽(import_service·reference_service·undo API)이 한 트랜잭션으로 묶는다.
설비는 (factory_code, 설비명)으로 묶어 교체로 equipment_id가 바뀌어도 이력이 이어진다(app/db/models/history.py).
"""
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now_kst_naive, today_kst
from app.db.models import DataChange, DataChangeRow, Equipment, EquipmentExtraAttribute, ScoreSnapshot
from app.equipment_types.registry import get_module
from app.services.reference_data import calc_options, reference_specs

KIND_LABEL = {
    "import": "추가·갱신",
    "replace": "교체",
    "row_edit": "행 편집",
    "reference_import": "참고표 넣기",
    "reference_reset": "참고표 리셋",
    "undo": "되돌리기",
}


# ------------------------------------------------------------------ 직렬화
def _jsonable(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value


def _dump(data: dict | None) -> str | None:
    if data is None:
        return None
    return json.dumps({k: _jsonable(v) for k, v in data.items()}, ensure_ascii=False)


def _typed(value: Any, dtype: str | None) -> Any:
    if value is None:
        return None
    if dtype == "date" and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _load_inputs_json(module, text: str | None) -> dict | None:
    if text is None:
        return None
    raw = json.loads(text)
    dtypes = {c["name"]: c.get("dtype") for c in module.INPUT_COLUMNS}
    out = {name: _typed(raw.get(name), dtypes.get(name)) for name in dtypes if name in raw}
    out["_as_of"] = date.fromisoformat(raw["_as_of"]) if raw.get("_as_of") else None
    out["_dates"] = raw.get("_dates") or {}
    out["_extras"] = raw.get("_extras") or {}
    return out


def equipment_key(factory_code: str, name: str) -> str:
    return f"{factory_code}|{name}"


# ------------------------------------------------------------------ 설비 비교·캡처
def input_values(module, row: dict) -> dict:
    return {c["name"]: row.get(c["name"]) for c in module.INPUT_COLUMNS}


def inputs_equal(module, a: dict, b: dict) -> bool:
    """입력 컬럼 값이 모두 같은지 — 숫자는 1.0 == 1, None은 None끼리만."""
    for c in module.INPUT_COLUMNS:
        x, y = a.get(c["name"]), b.get(c["name"])
        if x is None or y is None:
            if x is not y:
                return False
        elif x != y:
            return False
    return True


async def equipment_extras(session: AsyncSession, equipment_id: int) -> dict[str, str]:
    """설비의 미등록 컬럼 — 같은 이름이 여러 번 쌓였으면 마지막 값."""
    stmt = select(EquipmentExtraAttribute).where(EquipmentExtraAttribute.equipment_id == equipment_id).order_by(
        EquipmentExtraAttribute.id
    )
    return {a.column_name: a.value for a in (await session.execute(stmt)).scalars()}


async def find_equipment(session: AsyncSession, ef_code: str, factory_code: str, name: str) -> Equipment | None:
    stmt = select(Equipment).where(
        Equipment.ef_code == ef_code, Equipment.factory_code == factory_code, Equipment.equipment_name == name
    )
    return (await session.execute(stmt)).scalar_one_or_none()


TIME_COLUMNS = ("measured_at", "updated_at")  # 입력 테이블의 반영일 칸(진단 데이터 반영일)


def _input_models(module) -> list:
    score_model = getattr(module, "SCORE_DETAIL_MODEL", None)
    return [m for m in getattr(module, "DOMAIN_TABLES", []) if m is not score_model]


async def _input_dates(session: AsyncSession, module, equipment_id: int) -> dict[str, dict[str, str]]:
    """입력 테이블별 반영일 칸 값 {테이블: {칸: 날짜}} — 점수 기준일과 달라질 수 있어(매일 점수 갱신) 따로 남긴다."""
    out: dict[str, dict[str, str]] = {}
    for model in _input_models(module):
        cols = [c for c in TIME_COLUMNS if hasattr(model, c)]
        if not cols:
            continue
        row = (await session.execute(
            select(*(getattr(model, c) for c in cols)).where(model.equipment_id == equipment_id)
        )).first()
        if row is not None:
            out[model.__tablename__] = {c: _jsonable(v) for c, v in zip(cols, row) if v is not None}
    return out


async def capture_equipment(session: AsyncSession, module, equipment_id: int) -> dict | None:
    """되돌리기에 필요한 지금 값 — 입력 컬럼 + 점수 기준일(_as_of) + 입력 테이블 반영일(_dates) + 미등록 컬럼(_extras)."""
    load_inputs = getattr(module, "load_inputs", None)  # 최소 모듈(테스트 대역)은 없을 수 있다
    loaded = await load_inputs(session, equipment_id) if load_inputs else None
    if loaded is None:
        return None
    row, as_of = loaded
    return input_values(module, row) | {
        "_as_of": as_of,
        "_dates": await _input_dates(session, module, equipment_id),
        "_extras": await equipment_extras(session, equipment_id),
    }


# ------------------------------------------------------------------ 기록
@dataclass
class ChangeDraft:
    kind: str
    ef_code: str
    actor: str
    target_table: str = ""
    source: str | None = None
    rows: list[tuple[str, str, dict | None, dict | None]] = field(default_factory=list)  # key, action, before, after
    unchanged: int = 0

    def add(self, key: str, action: str, before: dict | None, after: dict | None) -> None:
        self.rows.append((key, action, before, after))


async def save_draft(session: AsyncSession, draft: ChangeDraft, undo_of: int | None = None) -> int | None:
    """바뀐 행이 있으면 기록하고 change_id를 돌려준다(없으면 기록하지 않음). commit하지 않는다."""
    if not draft.rows:
        return None
    change = DataChange(
        created_at=now_kst_naive(),
        actor=draft.actor,
        kind=draft.kind,
        ef_code=draft.ef_code,
        target_table=draft.target_table,
        source=draft.source,
        row_count=len(draft.rows),
        unchanged_count=draft.unchanged,
        status="applied",
        undo_of=undo_of,
    )
    session.add(change)
    await session.flush()
    for key, action, before, after in draft.rows:
        session.add(DataChangeRow(change_id=change.change_id, row_key=key, action=action, before=_dump(before), after=_dump(after)))
    await session.flush()
    return change.change_id


# ------------------------------------------------------------------ 조회
def _change_dict(c: DataChange) -> dict:
    return {
        "change_id": c.change_id,
        "created_at": c.created_at,
        "actor": c.actor,
        "kind": c.kind,
        "kind_label": KIND_LABEL.get(c.kind, c.kind),
        "ef_code": c.ef_code,
        "target_table": c.target_table,
        "source": c.source,
        "row_count": c.row_count,
        "unchanged_count": c.unchanged_count,
        "status": c.status,
        "undone_at": c.undone_at,
        "undone_by": c.undone_by,
        "undo_of": c.undo_of,
    }


async def list_changes(session: AsyncSession, limit: int = 100) -> list[dict]:
    stmt = select(DataChange).order_by(DataChange.change_id.desc()).limit(limit)
    return [_change_dict(c) for c in (await session.execute(stmt)).scalars()]


async def change_detail(session: AsyncSession, change_id: int) -> dict | None:
    change = await session.get(DataChange, change_id)
    if change is None:
        return None
    rows = (await session.execute(
        select(DataChangeRow).where(DataChangeRow.change_id == change_id).order_by(DataChangeRow.id)
    )).scalars().all()
    body = _change_dict(change)
    body["rows"] = [
        {
            "row_key": r.row_key,
            "action": r.action,
            "before": json.loads(r.before) if r.before else None,
            "after": json.loads(r.after) if r.after else None,
        }
        for r in rows
    ]
    body["undo_check"] = await undo_blockers(session, change)
    return body


# ------------------------------------------------------------------ 되돌리기
class UndoError(ValueError):
    pass


async def _recorded_before_schema_change(session: AsyncSession, change: DataChange) -> bool:
    """설비 변경 기록의 입력 컬럼 이름이 지금 유형의 입력 컬럼과 다른지 — 입력 항목이 바뀐 뒤(예: Stage 22 EF3 개정)
    옛 기록을 되돌리면 없어진 칸은 버려지고 새 칸은 비어 점수가 조용히 틀어지므로 막는다."""
    try:
        module = get_module(change.ef_code)
    except Exception:  # 등록이 빠진 유형 — 되돌릴 계산기가 없다
        return True
    current = {c["name"] for c in module.INPUT_COLUMNS}
    rows = (await session.execute(
        select(DataChangeRow.before, DataChangeRow.after).where(DataChangeRow.change_id == change.change_id)
    )).all()
    for before, after in rows:
        for text in (before, after):
            if text and {k for k in json.loads(text) if not k.startswith("_")} != current:
                return True
    return False


async def undo_blockers(session: AsyncSession, change: DataChange) -> dict:
    """되돌릴 수 있는지와, 못 하면 이유."""
    if change.kind == "undo":
        return {"possible": False, "reason": "되돌리기 기록은 다시 되돌릴 수 없습니다 — 필요하면 데이터를 다시 입력해 주세요."}
    if change.status != "applied":
        return {"possible": False, "reason": "이미 되돌린 변경입니다."}
    if not change.target_table and await _recorded_before_schema_change(session, change):
        return {
            "possible": False,
            "reason": "입력 항목 구성이 바뀌기 전의 기록이라 되돌릴 수 없습니다 — 필요하면 지금 양식으로 데이터를 다시 입력해 주세요.",
        }
    keys = set((await session.execute(select(DataChangeRow.row_key).where(DataChangeRow.change_id == change.change_id))).scalars())
    later = (await session.execute(
        select(DataChange).where(
            DataChange.change_id > change.change_id,
            DataChange.status == "applied",
            DataChange.ef_code == change.ef_code,
            # 되돌리기 기록은 막지 않는다 — 그 뒤 변경을 없앤 것이라, 앞선 변경 입장에서는 "그 뒤 변경이 없어진" 상태다
            DataChange.kind != "undo",
        ).order_by(DataChange.change_id)
    )).scalars().all()
    for other in later:
        same_target = other.target_table == change.target_table or "all" in (other.target_table, change.target_table)
        if not same_target:
            continue
        other_keys = set((await session.execute(select(DataChangeRow.row_key).where(DataChangeRow.change_id == other.change_id))).scalars())
        if other.kind == "replace" or change.kind == "replace" or keys & other_keys:
            return {
                "possible": False,
                "reason": f"그 뒤의 변경 #{other.change_id}({KIND_LABEL.get(other.kind, other.kind)})이 같은 데이터를 바꿨습니다 — 그 변경부터 되돌려 주세요.",
            }
    return {"possible": True, "reason": None}


async def delete_equipment(session: AsyncSession, module, equipment_id: int) -> None:
    """설비 한 대와 딸린 행을 지운다(점수 이력·변경 이력은 남긴다). commit하지 않는다."""
    for model in [*module.DOMAIN_TABLES, ScoreSnapshot, EquipmentExtraAttribute]:
        await session.execute(delete(model).where(model.equipment_id == equipment_id))
    await session.execute(delete(Equipment).where(Equipment.equipment_id == equipment_id))


async def _restore_equipment(session: AsyncSession, module, data: dict, options: dict) -> None:
    from app.services.ingest import ingest_row, save_scores  # 순환 import 방지

    inputs = {k: v for k, v in data.items() if not k.startswith("_")}
    as_of = data.get("_as_of") or today_kst()
    # 입력을 되살리고, 입력 테이블 반영일 칸을 그때 값으로 돌린 뒤(진단 데이터 반영일 복원), 점수는 오늘 기준으로
    eq_id = await ingest_row(module.calculate(inputs, as_of=as_of, **options), session)
    models = {m.__tablename__: m for m in _input_models(module)}
    for table, cols in (data.get("_dates") or {}).items():
        model = models.get(table)
        if model is None:
            continue
        values = {c: date.fromisoformat(v) if isinstance(v, str) else v for c, v in cols.items() if hasattr(model, c)}
        if values:
            await session.execute(update(model).where(model.equipment_id == eq_id).values(**values))
    await session.execute(delete(EquipmentExtraAttribute).where(EquipmentExtraAttribute.equipment_id == eq_id))
    for name, value in (data.get("_extras") or {}).items():
        session.add(EquipmentExtraAttribute(equipment_id=eq_id, column_name=name, value=value, source_file="되돌리기"))
    today = today_kst()
    if as_of != today:
        await save_scores(module.calculate(inputs, as_of=today, **options), eq_id, session)


def _reference_row(spec: dict, raw: dict) -> dict:
    dtypes = {c["name"]: c.get("dtype") for c in spec["columns"]}
    return {name: _typed(raw.get(name), dtype) for name, dtype in dtypes.items()}


async def undo_change(session: AsyncSession, change_id: int, actor: str) -> int | None:
    """변경을 되돌린다(같은 트랜잭션, commit하지 않음). 되돌리기 기록의 change_id를 돌려준다."""
    change = await session.get(DataChange, change_id)
    if change is None:
        raise UndoError("없는 변경입니다.")
    check = await undo_blockers(session, change)
    if not check["possible"]:
        raise UndoError(check["reason"])
    module = get_module(change.ef_code)
    rows = (await session.execute(
        select(DataChangeRow).where(DataChangeRow.change_id == change_id).order_by(DataChangeRow.id.desc())
    )).scalars().all()
    draft = ChangeDraft(kind="undo", ef_code=change.ef_code, actor=actor, target_table=change.target_table,
                        source=f"#{change_id} 되돌리기")

    if not change.target_table:  # 설비 데이터
        options = await calc_options(session, module)
        # 추가된 설비부터 지우고(교체면 새로 넣은 설비 전부), 갱신·삭제된 설비를 이전 값으로 되살린다
        for r in sorted(rows, key=lambda r: r.action != "insert"):
            factory_code, name = r.row_key.split("|", 1)
            current = await find_equipment(session, module.EF_CODE, factory_code, name)
            now = await capture_equipment(session, module, current.equipment_id) if current else None
            if r.action == "insert":
                if current is not None:
                    await delete_equipment(session, module, current.equipment_id)
                    draft.add(r.row_key, "delete", now, None)
            else:
                before = _load_inputs_json(module, r.before)
                if current is not None and r.action == "delete":
                    await delete_equipment(session, module, current.equipment_id)
                await _restore_equipment(session, module, before, options)
                draft.add(r.row_key, "update" if now else "insert", now, before)
    else:  # 참고표
        from app.services.reference_service import recalculate_type  # 순환 import 방지

        specs = reference_specs(module)
        for r in rows:
            table, key_text = r.row_key.split("|", 1)
            spec = specs[table]
            model = spec["model"]
            source = _reference_row(spec, json.loads(r.after or r.before))
            cond = and_(*(getattr(model, k) == source[k] for k in spec["key"]))
            existing = (await session.execute(select(model).where(cond))).scalar_one_or_none()
            now = {c["name"]: getattr(existing, c["name"]) for c in spec["columns"]} if existing else None
            if r.action == "insert":
                if existing is not None:
                    await session.delete(existing)
                    draft.add(r.row_key, "delete", now, None)
            else:
                before = _reference_row(spec, json.loads(r.before))
                if existing is None:
                    session.add(model(**before))
                    draft.add(r.row_key, "insert", None, before)
                else:
                    for name, value in before.items():
                        setattr(existing, name, value)
                    draft.add(r.row_key, "update", now, before)
        await session.flush()
        await recalculate_type(session, module)

    change.status = "undone"
    change.undone_at = now_kst_naive()
    change.undone_by = actor
    return await save_draft(session, draft, undo_of=change_id)
