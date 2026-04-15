"""
Prayer Router — Phase 2
=======================
Endpoints:
  GET  /prayer/times            — prayer times (proxies aladhan, cached)
  POST /prayer/log              — log/upsert a prayer (Phase 2: khushu, congregation)
  GET  /prayer/log              — fetch logs for a date range
  GET  /prayer/summary/today    — today's 5-prayer status
  GET  /prayer/streak           — current + longest streak
  PATCH /prayer/log/{id}        — update log
  DELETE /prayer/log/{id}       — delete log
  GET  /prayer/stats            — 30-day per-prayer stats
  GET  /prayer/heatmap          — 52-week heatmap data
  GET  /prayer/weekly-summary   — this week's summary
  GET  /prayer/travel-mode      — travel detection + qasr notes
  GET  /prayer/events           — Islamic calendar events
  GET  /prayer/events/current   — events active today
  POST /prayer/events/seed      — admin: seed events
"""

from datetime import date, timedelta
from math import radians, sin, cos, sqrt, atan2
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DB
from app.repositories import PrayerRepo, IslamicEventRepo
from app.schemas.base import MessageResponse
from app.schemas.prayer import (
    DailyPrayerSummary,
    PrayerLogCreate,
    PrayerLogCreateV2,
    PrayerLogResponse,
    PrayerLogResponseV2,
    PrayerLogUpdate,
    PrayerLogUpdateV2,
    PrayerStreakResponse,
    PrayerTimesResponse,
    PrayerStatsResponse,
    WeeklyPrayerSummary,
    HeatmapCell,
    IslamicEventResponse,
    TravelModeResponse,
)
from app.services.prayer_service import fetch_prayer_times, calculate_prayer_streak

router = APIRouter(prefix="/prayer", tags=["prayer"])
OBLIGATORY = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


MADHAB_QASR_NOTES = {
    "hanafi":  "Hanafi: travel is permitted when destination is ≥77 km away and you intend to stay <15 days.",
    "shafii":  "Shafi'i: travel is permitted when destination is ≥81 km (48 miles) away and stay is <4 days.",
    "maliki":  "Maliki: travel is permitted for journeys of ≥81 km; no fixed stay limit but generally <4 days.",
    "hanbali": "Hanbali: travel is permitted for journeys ≥81 km; intention to stay <4 days.",
}

# ─── 2.1 Prayer Times ─────────────────────────────────────────────────────────

@router.get("/times", response_model=PrayerTimesResponse)
async def get_prayer_times(
    current_user: CurrentUser,
    target_date: Optional[date] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lng: Optional[float] = Query(default=None),
):
    latitude  = lat or current_user.latitude
    longitude = lng or current_user.longitude
    if not latitude or not longitude:
        raise HTTPException(status_code=422, detail="Location not set. Update your profile with latitude/longitude.")
    try:
        return await fetch_prayer_times(
            latitude=latitude, longitude=longitude,
            madhab=current_user.madhab, target_date=target_date,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Prayer times service unavailable: {e}")


# ─── 2.2 Prayer Logging ───────────────────────────────────────────────────────

@router.post("/log", response_model=PrayerLogResponseV2, status_code=201)
async def log_prayer(
    payload: PrayerLogCreateV2,
    current_user: CurrentUser,
    db: DB,
    prayer_repo: PrayerRepo,
):
    log = await prayer_repo.upsert(current_user.id, **payload.model_dump())
    return PrayerLogResponseV2.model_validate(log)


@router.get("/log", response_model=list[PrayerLogResponseV2])
async def get_prayer_logs(
    current_user: CurrentUser,
    db: DB,
    prayer_repo: PrayerRepo,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
):
    end   = end_date   or date.today()
    start = start_date or (end - timedelta(days=6))
    logs  = await prayer_repo.get_for_date_range(current_user.id, start, end)
    return [PrayerLogResponseV2.model_validate(l) for l in logs]


@router.get("/summary", response_model=DailyPrayerSummary)
async def get_summary(
    current_user: CurrentUser, 
    db: DB, 
    prayer_repo: PrayerRepo,
    date_str: Optional[date] = Query(None, alias="date")
):
    target_date = date_str or date.today()
    logs = await prayer_repo.get_for_date_range(current_user.id, target_date, target_date)
    by_name = {l.prayer_name: l for l in logs}
    obligatory_logs = [l for l in logs if l.prayer_name in OBLIGATORY]
    total_logged  = len(obligatory_logs)
    total_on_time = len([l for l in obligatory_logs if l.status == "on_time"])
    return DailyPrayerSummary(
        date=target_date,
        fajr=    PrayerLogResponse.model_validate(by_name["fajr"])    if "fajr"    in by_name else None,
        dhuhr=   PrayerLogResponse.model_validate(by_name["dhuhr"])   if "dhuhr"   in by_name else None,
        asr=     PrayerLogResponse.model_validate(by_name["asr"])     if "asr"     in by_name else None,
        maghrib= PrayerLogResponse.model_validate(by_name["maghrib"]) if "maghrib" in by_name else None,
        isha=    PrayerLogResponse.model_validate(by_name["isha"])     if "isha"    in by_name else None,
        total_logged=total_logged,
        total_on_time=total_on_time,
        completion_pct=round((total_logged / 5) * 100, 1),
    )

@router.get("/summary/today", response_model=DailyPrayerSummary)
async def get_today_summary(
    current_user: CurrentUser, 
    db: DB, 
    prayer_repo: PrayerRepo,
    date_str: Optional[date] = Query(None, alias="date")
):
    # Backward compatibility, but use the date param if provided
    target_date = date_str or date.today()
    logs = await prayer_repo.get_for_date_range(current_user.id, target_date, target_date)
    by_name = {l.prayer_name: l for l in logs}
    obligatory_logs = [l for l in logs if l.prayer_name in OBLIGATORY]
    total_logged  = len(obligatory_logs)
    total_on_time = len([l for l in obligatory_logs if l.status == "on_time"])
    return DailyPrayerSummary(
        date=target_date,
        fajr=    PrayerLogResponse.model_validate(by_name["fajr"])    if "fajr"    in by_name else None,
        dhuhr=   PrayerLogResponse.model_validate(by_name["dhuhr"])   if "dhuhr"   in by_name else None,
        asr=     PrayerLogResponse.model_validate(by_name["asr"])     if "asr"     in by_name else None,
        maghrib= PrayerLogResponse.model_validate(by_name["maghrib"]) if "maghrib" in by_name else None,
        isha=    PrayerLogResponse.model_validate(by_name["isha"])     if "isha"    in by_name else None,
        total_logged=total_logged,
        total_on_time=total_on_time,
        completion_pct=round((total_logged / 5) * 100, 1),
    )


@router.get("/streak", response_model=PrayerStreakResponse)
async def get_prayer_streak(current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    logs        = await prayer_repo.get_for_streak(current_user.id)
    streak_data = calculate_prayer_streak(logs)
    week_start  = date.today() - timedelta(days=date.today().weekday())
    week_logs   = [l for l in logs if l.log_date >= week_start]
    week_on_time = len([l for l in week_logs if l.status in ("on_time", "late")])
    days_elapsed = date.today().weekday() + 1
    week_pct = round((week_on_time / (days_elapsed * 5)) * 100, 1) if week_logs else 0.0
    return PrayerStreakResponse(
        current_streak=streak_data["current_streak"],
        longest_streak=streak_data["longest_streak"],
        total_logged=len(logs),
        this_week_completion=min(week_pct, 100.0),
    )


@router.patch("/log/{log_id}", response_model=PrayerLogResponseV2)
async def update_prayer_log(
    log_id: UUID,
    payload: PrayerLogUpdateV2,
    current_user: CurrentUser,
    db: DB,
    prayer_repo: PrayerRepo,
):
    log = await prayer_repo.get_owned_or_404(log_id, current_user.id)
    log = await prayer_repo.update(log, **payload.model_dump(exclude_none=True))
    return PrayerLogResponseV2.model_validate(log)


@router.delete("/log/{log_id}", response_model=MessageResponse)
async def delete_prayer_log(log_id: UUID, current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    log = await prayer_repo.get_owned_or_404(log_id, current_user.id)
    await prayer_repo.delete(log)
    return MessageResponse(message="Prayer log deleted.")


# ─── 2.2 Prayer Statistics ────────────────────────────────────────────────────

@router.get("/stats", response_model=list[PrayerStatsResponse])
async def get_prayer_stats(current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    rows = await prayer_repo.get_stats_30d(current_user.id)
    result = []
    for row in rows:
        total = row["total"] or 1
        congregation = row["congregation"] or 0
        result.append(PrayerStatsResponse(
            prayer_name=row["prayer_name"],
            total_days=total,
            on_time_count=row["on_time"] or 0,
            late_count=row["late"] or 0,
            missed_count=row["missed"] or 0,
            qadha_count=row["qadha"] or 0,
            on_time_rate=round(((row["on_time"] or 0) / total) * 100, 1),
            congregation_rate=round((congregation / total) * 100, 1),
            avg_khushu=round(float(row["avg_khushu"]), 1) if row["avg_khushu"] else None,
        ))
    return result


@router.get("/heatmap", response_model=list[HeatmapCell])
async def get_prayer_heatmap(
    current_user: CurrentUser,
    db: DB,
    prayer_repo: PrayerRepo,
    days: int = Query(default=365, ge=30, le=730),
):
    rows = await prayer_repo.get_heatmap(current_user.id, days=days)
    return [HeatmapCell(date=r["log_date"], count=r["count"], on_time=r["on_time"]) for r in rows]


@router.get("/weekly-summary", response_model=WeeklyPrayerSummary)
async def get_weekly_summary(current_user: CurrentUser, db: DB, prayer_repo: PrayerRepo):
    data = await prayer_repo.get_weekly_summary(current_user.id)
    return WeeklyPrayerSummary(**data)


# ─── 2.5 Travel Mode ──────────────────────────────────────────────────────────

@router.get("/travel-mode", response_model=TravelModeResponse)
async def check_travel_mode(
    current_user: CurrentUser,
    lat: float = Query(..., description="Current latitude"),
    lng: float = Query(..., description="Current longitude"),
):
    home_lat = current_user.latitude
    home_lng = current_user.longitude
    if not home_lat or not home_lng:
        raise HTTPException(status_code=422, detail="Home location not set.")

    dist_km = _haversine_km(home_lat, home_lng, lat, lng)
    is_travelling = dist_km >= 80.0   # 80 km threshold (common scholarly view)
    madhab = current_user.madhab or "hanafi"
    notes  = MADHAB_QASR_NOTES.get(madhab, MADHAB_QASR_NOTES["hanafi"])

    return TravelModeResponse(
        is_travelling=is_travelling,
        distance_from_home_km=round(dist_km, 1),
        qasr_applicable=is_travelling,
        madhab_notes=notes,
    )


# ─── 2.6 Islamic Events ───────────────────────────────────────────────────────

@router.get("/events", response_model=list[IslamicEventResponse])
async def get_islamic_events(
    db: DB,
    islamic_event_repo: IslamicEventRepo,
):
    events = await islamic_event_repo.get_all()
    return [IslamicEventResponse.model_validate(e) for e in events]


@router.get("/events/current", response_model=list[IslamicEventResponse])
async def get_current_events(
    db: DB,
    islamic_event_repo: IslamicEventRepo,
    hijri_month: int = Query(..., ge=1, le=12),
    hijri_day: int   = Query(..., ge=1, le=30),
):
    events = await islamic_event_repo.get_current_events(hijri_month, hijri_day)
    return [IslamicEventResponse.model_validate(e) for e in events]


@router.post("/events/seed", response_model=MessageResponse)
async def seed_events(db: DB, current_user: CurrentUser):
    """Admin endpoint to seed Islamic events. Idempotent."""
    from app.services.islamic_events import seed_islamic_events
    count = await seed_islamic_events(db)
    await db.commit()
    return MessageResponse(message=f"Seeded {count} new Islamic events.")


# ─── 2.4 Mosque Finder ────────────────────────────────────────────────────────

from sqlalchemy import select

@router.get("/mosques/nearby")
async def get_nearby_mosques(
    db: DB,
    current_user: CurrentUser,
    lat: float = Query(..., description="Current latitude"),
    lng: float = Query(..., description="Current longitude"),
    radius_km: float = Query(default=50000.0), # No distance restriction for demo
    limit: int = Query(default=20, le=50),
):
    """Return mosques within radius_km, sorted by distance."""
    from app.models.prayer import Mosque
    result = await db.execute(select(Mosque))
    mosques = result.scalars().all()
    nearby = []
    for m in mosques:
        dist = _haversine_km(lat, lng, m.latitude, m.longitude)
        if dist <= radius_km:
            nearby.append({
                "id": str(m.id),
                "name": m.name,
                "address": m.address,
                "city": m.city,
                "country": m.country,
                "latitude": m.latitude,
                "longitude": m.longitude,
                "phone": m.phone,
                "website": m.website,
                "is_verified": m.is_verified,
                "has_jumuah": m.has_jumuah,
                "madhab": m.madhab,
                "distance_km": round(dist, 2),
            })
    nearby.sort(key=lambda x: x["distance_km"])
    return nearby[:limit]


@router.post("/mosques/seed", response_model=MessageResponse)
async def seed_mosques(db: DB, current_user: CurrentUser):
    """Seed sample mosques for demonstration."""
    from app.models.prayer import Mosque
    existing = await db.execute(select(Mosque))
    if existing.scalars().first():
        return MessageResponse(message="Mosques already seeded.")

    sample = [
        Mosque(name="Masjid al-Haram", address="Al-Haram, Mecca, Saudi Arabia", city="Mecca", country="Saudi Arabia", latitude=21.4225, longitude=39.8262, is_verified=True, has_jumuah=True),
        Mosque(name="Masjid al-Nabawi", address="Al-Madinah Al-Munawwarah, Saudi Arabia", city="Medina", country="Saudi Arabia", latitude=24.4672, longitude=39.6112, is_verified=True, has_jumuah=True),
        Mosque(name="Masjid al-Aqsa", address="Muslim Quarter, Jerusalem", city="Jerusalem", country="Palestine", latitude=31.7781, longitude=35.2360, is_verified=True, has_jumuah=True),
        Mosque(name="Islamic Centre London", address="146 Park Rd, London NW8 7RG", city="London", country="UK", latitude=51.5274, longitude=-0.1704, is_verified=True, has_jumuah=True, madhab="hanafi"),
        Mosque(name="Islamic Cultural Centre New York", address="1711 3rd Ave, New York, NY 10029", city="New York", country="USA", latitude=40.7851, longitude=-73.9465, is_verified=True, has_jumuah=True),
    ]
    for m in sample:
        db.add(m)
    await db.commit()
    return MessageResponse(message=f"Seeded {len(sample)} sample mosques.")

