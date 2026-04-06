"""
Female Module Router
====================
All endpoints guarded by FemaleUser dependency (gender=female required).
Sensitive cycle data encrypted at rest using per-user AES-256 keys.
Fiqh rulings computed by the madhab-aware fiqh engine.
"""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.dependencies import DB, FemaleUser
from app.core.security import decrypt_field, encrypt_field
from app.models.female import FastingLog, MenstrualCycle
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    CycleCreate,
    CycleDetailResponse,
    CycleResponse,
    CycleUpdate,
    FastingLogCreate,
    FastingLogResponse,
    FastingLogUpdate,
    MissedFastSummary,
)
from app.services.fiqh_engine import CycleInput, classify_cycle

router = APIRouter(prefix="/female", tags=["female"])


def _apply_ruling(cycle: MenstrualCycle, ruling) -> None:
    """Write fiqh engine output back to the cycle model."""
    cycle.blood_classification = ruling.classification
    cycle.hayd_tuhr_status = ruling.classification
    cycle.madhab_ruling = ruling.madhab
    cycle.can_pray = ruling.can_pray
    cycle.can_fast = ruling.can_fast
    cycle.can_read_quran = ruling.can_read_quran
    cycle.ghusl_required = ruling.ghusl_required


def _to_response(cycle: MenstrualCycle, user_id: str, include_details=False):
    base = {
        "id": cycle.id,
        "user_id": cycle.user_id,
        "start_date": cycle.start_date,
        "end_date": cycle.end_date,
        "duration_days": cycle.duration_days,
        "blood_classification": cycle.blood_classification,
        "hayd_tuhr_status": cycle.hayd_tuhr_status,
        "madhab_ruling": cycle.madhab_ruling,
        "can_pray": cycle.can_pray,
        "can_fast": cycle.can_fast,
        "can_read_quran": cycle.can_read_quran,
        "ghusl_required": cycle.ghusl_required,
        "ghusl_done": cycle.ghusl_done,
        "ghusl_date": cycle.ghusl_date,
        "cycle_length": cycle.cycle_length,
        "created_at": cycle.created_at,
        "updated_at": cycle.updated_at,
    }
    if include_details:
        base["notes"] = (
            decrypt_field(cycle.encrypted_notes, user_id)
            if cycle.encrypted_notes else None
        )
        base["symptoms"] = (
            decrypt_field(cycle.encrypted_symptoms, user_id)
            if cycle.encrypted_symptoms else None
        )
        return CycleDetailResponse(**base)
    return CycleResponse(**base)


# ─── Cycle Endpoints ──────────────────────────────────────────────────────────

@router.get("/cycles", response_model=list[CycleResponse])
async def list_cycles(
    current_user: FemaleUser,
    db: DB,
    limit: int = Query(default=12, le=60),
    offset: int = Query(default=0),
):
    """List menstrual cycle history (most recent first)."""
    result = await db.execute(
        select(MenstrualCycle)
        .where(MenstrualCycle.user_id == current_user.id)
        .order_by(MenstrualCycle.start_date.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_to_response(c, str(current_user.id)) for c in result.scalars().all()]


@router.post("/cycles", response_model=CycleDetailResponse, status_code=201)
async def start_cycle(payload: CycleCreate, current_user: FemaleUser, db: DB):
    """Start a new menstrual cycle. Runs fiqh engine immediately."""
    # Check for unclosed cycle
    open_result = await db.execute(
        select(MenstrualCycle).where(
            MenstrualCycle.user_id == current_user.id,
            MenstrualCycle.end_date == None,
        )
    )
    if open_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You have an open cycle. Please close it before starting a new one.",
        )

    # Fetch recent cycle history for fiqh engine
    history_result = await db.execute(
        select(MenstrualCycle)
        .where(MenstrualCycle.user_id == current_user.id)
        .order_by(MenstrualCycle.start_date.desc())
        .limit(12)
    )
    history = history_result.scalars().all()

    # Calculate tuhr since last cycle
    previous_tuhr = None
    if history:
        last = history[0]
        if last.end_date:
            previous_tuhr = (payload.start_date - last.end_date).days

    cycle_input = CycleInput(
        start_date=payload.start_date,
        end_date=payload.end_date,
        previous_cycles=[
            {"start_date": h.start_date, "duration_days": h.duration_days,
             "blood_classification": h.blood_classification}
            for h in history
        ],
        previous_tuhr_days=previous_tuhr,
    )

    ruling = classify_cycle(current_user.madhab, cycle_input)

    duration = None
    if payload.end_date:
        duration = (payload.end_date - payload.start_date).days + 1

    cycle = MenstrualCycle(
        user_id=current_user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=duration,
        previous_cycle_tuhr_days=previous_tuhr,
    )
    _apply_ruling(cycle, ruling)

    if payload.notes:
        cycle.encrypted_notes = encrypt_field(payload.notes, str(current_user.id))
    if payload.symptoms:
        cycle.encrypted_symptoms = encrypt_field(payload.symptoms, str(current_user.id))

    db.add(cycle)
    await db.flush()
    await db.refresh(cycle)
    return _to_response(cycle, str(current_user.id), include_details=True)


@router.get("/cycles/current", response_model=CycleDetailResponse)
async def get_current_cycle(current_user: FemaleUser, db: DB):
    """Get the currently open cycle with worship status."""
    result = await db.execute(
        select(MenstrualCycle).where(
            MenstrualCycle.user_id == current_user.id,
            MenstrualCycle.end_date == None,
        )
    )
    cycle = result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle. You are currently in a state of purity (tuhr).")
    return _to_response(cycle, str(current_user.id), include_details=True)


@router.get("/cycles/{cycle_id}", response_model=CycleDetailResponse)
async def get_cycle(cycle_id: UUID, current_user: FemaleUser, db: DB):
    result = await db.execute(
        select(MenstrualCycle).where(
            MenstrualCycle.id == cycle_id, MenstrualCycle.user_id == current_user.id
        )
    )
    cycle = result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found.")
    return _to_response(cycle, str(current_user.id), include_details=True)


@router.patch("/cycles/{cycle_id}", response_model=CycleDetailResponse)
async def update_cycle(cycle_id: UUID, payload: CycleUpdate, current_user: FemaleUser, db: DB):
    """Update a cycle (e.g. close it by setting end_date, mark ghusl done)."""
    result = await db.execute(
        select(MenstrualCycle).where(
            MenstrualCycle.id == cycle_id, MenstrualCycle.user_id == current_user.id
        )
    )
    cycle = result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found.")

    if payload.end_date:
        cycle.end_date = payload.end_date
        cycle.duration_days = (payload.end_date - cycle.start_date).days + 1
        # Re-run fiqh engine with completed data
        history_result = await db.execute(
            select(MenstrualCycle)
            .where(
                MenstrualCycle.user_id == current_user.id,
                MenstrualCycle.id != cycle_id,
            )
            .order_by(MenstrualCycle.start_date.desc())
            .limit(12)
        )
        history = history_result.scalars().all()
        cycle_input = CycleInput(
            start_date=cycle.start_date,
            end_date=payload.end_date,
            previous_cycles=[
                {"start_date": h.start_date, "duration_days": h.duration_days,
                 "blood_classification": h.blood_classification}
                for h in history
            ],
            previous_tuhr_days=cycle.previous_cycle_tuhr_days,
        )
        ruling = classify_cycle(current_user.madhab, cycle_input)
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
async def delete_cycle(cycle_id: UUID, current_user: FemaleUser, db: DB):
    result = await db.execute(
        select(MenstrualCycle).where(
            MenstrualCycle.id == cycle_id, MenstrualCycle.user_id == current_user.id
        )
    )
    cycle = result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found.")
    await db.delete(cycle)
    return MessageResponse(message="Cycle deleted.")


# ─── Fasting Log (Female) ─────────────────────────────────────────────────────

@router.get("/fasting", response_model=list[FastingLogResponse])
async def list_fasting_logs(
    current_user: FemaleUser,
    db: DB,
    year: int = Query(default=None),
    fast_type: str = Query(default=None),
):
    """List fasting logs, optionally filtered by year or type."""
    import datetime as dt
    query = select(FastingLog).where(FastingLog.user_id == current_user.id)
    if year:
        query = query.where(
            FastingLog.fast_date >= date(year, 1, 1),
            FastingLog.fast_date <= date(year, 12, 31),
        )
    if fast_type:
        query = query.where(FastingLog.fast_type == fast_type)
    query = query.order_by(FastingLog.fast_date.desc())
    result = await db.execute(query)
    return [FastingLogResponse.model_validate(f) for f in result.scalars().all()]


@router.post("/fasting", response_model=FastingLogResponse, status_code=201)
async def log_fast(payload: FastingLogCreate, current_user: FemaleUser, db: DB):
    fast = FastingLog(user_id=current_user.id, **payload.model_dump())
    # Auto-flag fidya for hayd-missed fasts
    if not payload.completed and payload.reason_missed in ("hayd", "nifas"):
        fast.fidya_applicable = True
    db.add(fast)
    await db.flush()
    await db.refresh(fast)
    return FastingLogResponse.model_validate(fast)


@router.patch("/fasting/{log_id}", response_model=FastingLogResponse)
async def update_fast(log_id: UUID, payload: FastingLogUpdate, current_user: FemaleUser, db: DB):
    result = await db.execute(
        select(FastingLog).where(
            FastingLog.id == log_id, FastingLog.user_id == current_user.id
        )
    )
    fast = result.scalar_one_or_none()
    if not fast:
        raise HTTPException(status_code=404, detail="Fasting log not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(fast, field, value)
    await db.flush()
    await db.refresh(fast)
    return FastingLogResponse.model_validate(fast)


@router.get("/fasting/missed-summary", response_model=MissedFastSummary)
async def missed_fast_summary(
    current_user: FemaleUser,
    db: DB,
    year: int = Query(default=date.today().year),
):
    """Get summary of missed fasts and qadha progress for a given year."""
    result = await db.execute(
        select(FastingLog).where(
            FastingLog.user_id == current_user.id,
            FastingLog.fast_date >= date(year, 1, 1),
            FastingLog.fast_date <= date(year, 12, 31),
        )
    )
    logs = result.scalars().all()

    missed = [l for l in logs if not l.completed and l.fast_type == "ramadan"]
    qadha = [l for l in logs if l.is_qadha and l.completed]
    fidya_logs = [l for l in missed if l.fidya_applicable and not l.fidya_paid]

    return MissedFastSummary(
        total_missed=len(missed),
        total_qadha_made=len(qadha),
        remaining_qadha=max(0, len(missed) - len(qadha)),
        fidya_owed=len(fidya_logs),
        year=year,
    )
