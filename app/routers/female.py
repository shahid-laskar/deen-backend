"""
Female Module Router — refactored to use CycleRepository + FastingRepository.
Fiqh engine called from service layer only; routers hold no fiqh logic.
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import DB, FemaleUser
from app.core.security import decrypt_field, encrypt_field
from app.repositories import CycleRepo, FastingRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    CycleCreate, CycleDetailResponse, CycleResponse, CycleUpdate,
    FastingLogCreate, FastingLogResponse, FastingLogUpdate, MissedFastSummary,
)
from app.services.fiqh_engine import CycleInput, classify_cycle

router = APIRouter(prefix="/female", tags=["female"])


def _apply_ruling(cycle, ruling):
    cycle.blood_classification = ruling.classification
    cycle.hayd_tuhr_status = ruling.classification
    cycle.madhab_ruling = ruling.madhab
    cycle.can_pray = ruling.can_pray
    cycle.can_fast = ruling.can_fast
    cycle.can_read_quran = ruling.can_read_quran
    cycle.ghusl_required = ruling.ghusl_required


def _to_response(cycle, user_id: str, include_details=False):
    base = dict(
        id=cycle.id, user_id=cycle.user_id, start_date=cycle.start_date,
        end_date=cycle.end_date, duration_days=cycle.duration_days,
        blood_classification=cycle.blood_classification, hayd_tuhr_status=cycle.hayd_tuhr_status,
        madhab_ruling=cycle.madhab_ruling, can_pray=cycle.can_pray, can_fast=cycle.can_fast,
        can_read_quran=cycle.can_read_quran, ghusl_required=cycle.ghusl_required,
        ghusl_done=cycle.ghusl_done, ghusl_date=cycle.ghusl_date,
        cycle_length=cycle.cycle_length, created_at=cycle.created_at, updated_at=cycle.updated_at,
    )
    if include_details:
        base["notes"] = decrypt_field(cycle.encrypted_notes, user_id) if cycle.encrypted_notes else None
        base["symptoms"] = decrypt_field(cycle.encrypted_symptoms, user_id) if cycle.encrypted_symptoms else None
        return CycleDetailResponse(**base)
    return CycleResponse(**base)


def _build_fiqh_input(cycle, history, previous_tuhr=None):
    return CycleInput(
        start_date=cycle.start_date,
        end_date=cycle.end_date,
        previous_cycles=[
            {"start_date": h.start_date, "duration_days": h.duration_days,
             "blood_classification": h.blood_classification}
            for h in history
        ],
        previous_tuhr_days=previous_tuhr,
    )


# ─── Cycles ───────────────────────────────────────────────────────────────────

@router.get("/cycles", response_model=list[CycleResponse])
async def list_cycles(current_user: FemaleUser, db: DB, cycle_repo: CycleRepo, limit: int = Query(default=12, le=60), offset: int = 0):
    cycles = await cycle_repo.get_history(current_user.id, limit=limit, offset=offset)
    return [_to_response(c, str(current_user.id)) for c in cycles]


@router.post("/cycles", response_model=CycleDetailResponse, status_code=201)
async def start_cycle(payload: CycleCreate, current_user: FemaleUser, db: DB, cycle_repo: CycleRepo):
    if await cycle_repo.get_open_cycle(current_user.id):
        raise HTTPException(status_code=409, detail="You have an open cycle. Please close it before starting a new one.")

    history = await cycle_repo.get_recent_for_fiqh(current_user.id)
    previous_tuhr = None
    if history and history[0].end_date:
        previous_tuhr = (payload.start_date - history[0].end_date).days

    duration = (payload.end_date - payload.start_date).days + 1 if payload.end_date else None

    cycle = await cycle_repo.create(
        user_id=current_user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=duration,
        previous_cycle_tuhr_days=previous_tuhr,
        blood_classification="uncertain",
        hayd_tuhr_status="hayd",
        can_pray=False, can_fast=False, can_read_quran=True,
        ghusl_required=False, ghusl_done=False,
    )

    fiqh_input = _build_fiqh_input(cycle, history, previous_tuhr)
    ruling = classify_cycle(current_user.madhab, fiqh_input)
    _apply_ruling(cycle, ruling)

    if payload.notes:
        cycle.encrypted_notes = encrypt_field(payload.notes, str(current_user.id))
    if payload.symptoms:
        cycle.encrypted_symptoms = encrypt_field(payload.symptoms, str(current_user.id))

    await db.flush()
    await db.refresh(cycle)
    return _to_response(cycle, str(current_user.id), include_details=True)


@router.get("/cycles/current", response_model=CycleDetailResponse)
async def get_current_cycle(current_user: FemaleUser, db: DB, cycle_repo: CycleRepo):
    cycle = await cycle_repo.get_open_cycle(current_user.id)
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle. You are currently in a state of purity (tuhr).")
    return _to_response(cycle, str(current_user.id), include_details=True)


@router.get("/cycles/{cycle_id}", response_model=CycleDetailResponse)
async def get_cycle(cycle_id: UUID, current_user: FemaleUser, db: DB, cycle_repo: CycleRepo):
    cycle = await cycle_repo.get_owned_or_404(cycle_id, current_user.id)
    return _to_response(cycle, str(current_user.id), include_details=True)


@router.patch("/cycles/{cycle_id}", response_model=CycleDetailResponse)
async def update_cycle(cycle_id: UUID, payload: CycleUpdate, current_user: FemaleUser, db: DB, cycle_repo: CycleRepo):
    cycle = await cycle_repo.get_owned_or_404(cycle_id, current_user.id)

    if payload.end_date:
        cycle.end_date = payload.end_date
        cycle.duration_days = (payload.end_date - cycle.start_date).days + 1
        history = await cycle_repo.get_recent_for_fiqh(current_user.id, exclude_id=cycle_id)
        ruling = classify_cycle(current_user.madhab, _build_fiqh_input(cycle, history, cycle.previous_cycle_tuhr_days))
        _apply_ruling(cycle, ruling)

    if payload.ghusl_done is not None:
        cycle.ghusl_done = payload.ghusl_done
    if payload.ghusl_date:
        cycle.ghusl_date = payload.ghusl_date
    if payload.notes:
        cycle.encrypted_notes = encrypt_field(payload.notes, str(current_user.id))
    if payload.symptoms:
        cycle.encrypted_symptoms = encrypt_field(payload.symptoms, str(current_user.id))

    await db.flush()
    await db.refresh(cycle)
    return _to_response(cycle, str(current_user.id), include_details=True)


@router.delete("/cycles/{cycle_id}", response_model=MessageResponse)
async def delete_cycle(cycle_id: UUID, current_user: FemaleUser, db: DB, cycle_repo: CycleRepo):
    cycle = await cycle_repo.get_owned_or_404(cycle_id, current_user.id)
    await cycle_repo.delete(cycle)
    return MessageResponse(message="Cycle deleted.")


# ─── Fasting ──────────────────────────────────────────────────────────────────

@router.get("/fasting", response_model=list[FastingLogResponse])
async def list_fasting_logs(current_user: FemaleUser, db: DB, fasting_repo: FastingRepo, year: int = Query(default=None), fast_type: str = Query(default=None)):
    logs = await fasting_repo.get_for_user(current_user.id, year=year, fast_type=fast_type)
    return [FastingLogResponse.model_validate(f) for f in logs]


@router.post("/fasting", response_model=FastingLogResponse, status_code=201)
async def log_fast(payload: FastingLogCreate, current_user: FemaleUser, db: DB, fasting_repo: FastingRepo):
    data = payload.model_dump()
    if not data.get("completed") and data.get("reason_missed") in ("hayd", "nifas"):
        data["fidya_applicable"] = True
    fast = await fasting_repo.create(user_id=current_user.id, **data)
    return FastingLogResponse.model_validate(fast)


@router.patch("/fasting/{log_id}", response_model=FastingLogResponse)
async def update_fast(log_id: UUID, payload: FastingLogUpdate, current_user: FemaleUser, db: DB, fasting_repo: FastingRepo):
    fast = await fasting_repo.get_owned_or_404(log_id, current_user.id)
    fast = await fasting_repo.update(fast, **payload.model_dump(exclude_none=True))
    return FastingLogResponse.model_validate(fast)


@router.get("/fasting/missed-summary", response_model=MissedFastSummary)
async def missed_fast_summary(current_user: FemaleUser, db: DB, fasting_repo: FastingRepo, year: int = Query(default=date.today().year)):
    summary = await fasting_repo.get_missed_summary(current_user.id, year)
    return MissedFastSummary(**summary)
