from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, and_, delete

from app.core.dependencies import CurrentUser, DB
from app.models.prayer import PrayerLog
from app.schemas.base import MessageResponse
from app.schemas.prayer import (
    DailyPrayerSummary,
    PrayerLogCreate,
    PrayerLogResponse,
    PrayerLogUpdate,
    PrayerStreakResponse,
    PrayerTimesResponse,
)
from app.services.prayer_service import (
    fetch_prayer_times,
    calculate_prayer_streak,
)

router = APIRouter(prefix="/prayer", tags=["prayer"])

OBLIGATORY_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]


@router.get("/times", response_model=PrayerTimesResponse)
async def get_prayer_times(
    current_user: CurrentUser,
    target_date: Optional[date] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lng: Optional[float] = Query(default=None),
):
    """
    Get prayer times for user's location and madhab.
    Optionally override coordinates for travel.
    """
    latitude = lat or current_user.latitude
    longitude = lng or current_user.longitude

    if not latitude or not longitude:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location not set. Please update your profile with latitude and longitude.",
        )

    try:
        return await fetch_prayer_times(
            latitude=latitude,
            longitude=longitude,
            madhab=current_user.madhab,
            target_date=target_date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Prayer times service unavailable: {str(e)}",
        )


@router.post("/log", response_model=PrayerLogResponse, status_code=status.HTTP_201_CREATED)
async def log_prayer(payload: PrayerLogCreate, current_user: CurrentUser, db: DB):
    """Log a prayer. Upserts if a log for this prayer+date already exists."""
    # Check existing
    result = await db.execute(
        select(PrayerLog).where(
            PrayerLog.user_id == current_user.id,
            PrayerLog.prayer_name == payload.prayer_name,
            PrayerLog.log_date == payload.log_date,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing log
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        log = existing
    else:
        log = PrayerLog(user_id=current_user.id, **payload.model_dump())
        db.add(log)

    await db.flush()
    await db.refresh(log)
    return PrayerLogResponse.model_validate(log)


@router.get("/log", response_model=list[PrayerLogResponse])
async def get_prayer_logs(
    current_user: CurrentUser,
    db: DB,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Get prayer logs for a date range (default: last 7 days)."""
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=6))

    result = await db.execute(
        select(PrayerLog).where(
            PrayerLog.user_id == current_user.id,
            PrayerLog.log_date >= start,
            PrayerLog.log_date <= end,
        ).order_by(PrayerLog.log_date.desc(), PrayerLog.prayer_name)
    )
    return [PrayerLogResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/summary/today", response_model=DailyPrayerSummary)
async def get_today_summary(current_user: CurrentUser, db: DB):
    """Get today's prayer completion summary."""
    today = date.today()
    result = await db.execute(
        select(PrayerLog).where(
            PrayerLog.user_id == current_user.id,
            PrayerLog.log_date == today,
        )
    )
    logs = result.scalars().all()

    by_name = {log.prayer_name: log for log in logs}
    total_logged = len([l for l in logs if l.prayer_name in OBLIGATORY_PRAYERS])
    total_on_time = len([
        l for l in logs
        if l.prayer_name in OBLIGATORY_PRAYERS and l.status == "on_time"
    ])

    return DailyPrayerSummary(
        date=today,
        fajr=PrayerLogResponse.model_validate(by_name["fajr"]) if "fajr" in by_name else None,
        dhuhr=PrayerLogResponse.model_validate(by_name["dhuhr"]) if "dhuhr" in by_name else None,
        asr=PrayerLogResponse.model_validate(by_name["asr"]) if "asr" in by_name else None,
        maghrib=PrayerLogResponse.model_validate(by_name["maghrib"]) if "maghrib" in by_name else None,
        isha=PrayerLogResponse.model_validate(by_name["isha"]) if "isha" in by_name else None,
        total_logged=total_logged,
        total_on_time=total_on_time,
        completion_pct=round((total_logged / 5) * 100, 1),
    )


@router.get("/streak", response_model=PrayerStreakResponse)
async def get_prayer_streak(current_user: CurrentUser, db: DB):
    """Get current and longest prayer streak."""
    # Fetch last 90 days for streak calculation
    start = date.today() - timedelta(days=90)
    result = await db.execute(
        select(PrayerLog).where(
            PrayerLog.user_id == current_user.id,
            PrayerLog.log_date >= start,
            PrayerLog.prayer_name.in_(OBLIGATORY_PRAYERS),
        )
    )
    logs = result.scalars().all()
    streak_data = calculate_prayer_streak(logs)

    # This week completion
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_logs = [l for l in logs if l.log_date >= week_start]
    week_on_time = len([l for l in week_logs if l.status in ("on_time", "late")])
    week_pct = round((week_on_time / (date.today().weekday() + 1) / 5) * 100, 1) if logs else 0.0

    return PrayerStreakResponse(
        current_streak=streak_data["current_streak"],
        longest_streak=streak_data["longest_streak"],
        total_logged=len(logs),
        this_week_completion=min(week_pct, 100.0),
    )


@router.patch("/log/{log_id}", response_model=PrayerLogResponse)
async def update_prayer_log(
    log_id: UUID,
    payload: PrayerLogUpdate,
    current_user: CurrentUser,
    db: DB,
):
    """Update a specific prayer log entry."""
    result = await db.execute(
        select(PrayerLog).where(
            PrayerLog.id == log_id,
            PrayerLog.user_id == current_user.id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prayer log not found.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(log, field, value)

    await db.flush()
    await db.refresh(log)
    return PrayerLogResponse.model_validate(log)


@router.delete("/log/{log_id}", response_model=MessageResponse)
async def delete_prayer_log(log_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(PrayerLog).where(
            PrayerLog.id == log_id,
            PrayerLog.user_id == current_user.id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Prayer log not found.")
    await db.delete(log)
    return MessageResponse(message="Prayer log deleted.")
