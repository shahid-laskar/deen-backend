from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DB
from app.repositories import PrayerRepo
from app.schemas.base import MessageResponse
from app.schemas.prayer import (
    DailyPrayerSummary,
    PrayerLogCreate,
    PrayerLogResponse,
    PrayerLogUpdate,
    PrayerStreakResponse,
    PrayerTimesResponse,
)
from app.services.prayer_service import fetch_prayer_times, calculate_prayer_streak

router = APIRouter(prefix="/prayer", tags=["prayer"])
OBLIGATORY = ["fajr", "dhuhr", "asr", "maghrib", "isha"]


@router.get("/times", response_model=PrayerTimesResponse)
async def get_prayer_times(
    current_user: CurrentUser,
    target_date: Optional[date] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lng: Optional[float] = Query(default=None),
):
    latitude = lat or current_user.latitude
    longitude = lng or current_user.longitude
    if not latitude or not longitude:
        raise HTTPException(status_code=422, detail="Location not set. Update your profile with latitude and longitude.")
    try:
        return await fetch_prayer_times(latitude=latitude, longitude=longitude, madhab=current_user.madhab, target_date=target_date)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Prayer times service unavailable: {e}")


@router.post("/log", response_model=PrayerLogResponse, status_code=201)
async def log_prayer(payload: PrayerLogCreate, current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    log = await prayer_repo.upsert(current_user.id, **payload.model_dump())
    return PrayerLogResponse.model_validate(log)


@router.get("/log", response_model=list[PrayerLogResponse])
async def get_prayer_logs(
    current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=6))
    logs = await prayer_repo.get_for_date_range(current_user.id, start, end)
    return [PrayerLogResponse.model_validate(l) for l in logs]


@router.get("/summary/today", response_model=DailyPrayerSummary)
async def get_today_summary(current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    logs = await prayer_repo.get_today(current_user.id)
    by_name = {l.prayer_name: l for l in logs}
    obligatory_logs = [l for l in logs if l.prayer_name in OBLIGATORY]
    total_logged = len(obligatory_logs)
    total_on_time = len([l for l in obligatory_logs if l.status == "on_time"])
    return DailyPrayerSummary(
        date=date.today(),
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
async def get_prayer_streak(current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    logs = await prayer_repo.get_for_streak(current_user.id)
    streak_data = calculate_prayer_streak(logs)
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_logs = [l for l in logs if l.log_date >= week_start]
    week_on_time = len([l for l in week_logs if l.status in ("on_time", "late")])
    days_elapsed = date.today().weekday() + 1
    week_pct = round((week_on_time / (days_elapsed * 5)) * 100, 1) if week_logs else 0.0
    return PrayerStreakResponse(
        current_streak=streak_data["current_streak"],
        longest_streak=streak_data["longest_streak"],
        total_logged=len(logs),
        this_week_completion=min(week_pct, 100.0),
    )


@router.patch("/log/{log_id}", response_model=PrayerLogResponse)
async def update_prayer_log(log_id: UUID, payload: PrayerLogUpdate, current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    log = await prayer_repo.get_owned_or_404(log_id, current_user.id)
    log = await prayer_repo.update(log, **payload.model_dump(exclude_none=True))
    return PrayerLogResponse.model_validate(log)


@router.delete("/log/{log_id}", response_model=MessageResponse)
async def delete_prayer_log(log_id: UUID, current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    log = await prayer_repo.get_owned_or_404(log_id, current_user.id)
    await prayer_repo.delete(log)
    return MessageResponse(message="Prayer log deleted.")
