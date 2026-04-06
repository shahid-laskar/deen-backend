"""
Prayer Service
==============
- Fetches prayer times from Aladhan API (madhab-aware)
- Manages prayer logs and streaks
- Caches responses in Redis
"""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.schemas.prayer import PrayerTimesResponse, PrayerStreakResponse

# Aladhan prayer method IDs
MADHAB_METHOD_MAP = {
    "hanafi": 1,     # Karachi (University of Islamic Sciences)
    "shafii": 3,     # Muslim World League
    "maliki": 3,     # Muslim World League
    "hanbali": 4,    # Umm Al-Qura, Makkah
}

# Aladhan Asr juristic method: 0=Shafi (standard), 1=Hanafi (later)
ASR_METHOD_MAP = {
    "hanafi": 1,
    "shafii": 0,
    "maliki": 0,
    "hanbali": 0,
}


async def fetch_prayer_times(
    latitude: float,
    longitude: float,
    madhab: str,
    target_date: Optional[date] = None,
) -> PrayerTimesResponse:
    """Fetch prayer times from Aladhan API for a given location and madhab."""
    target_date = target_date or date.today()
    method = MADHAB_METHOD_MAP.get(madhab, 3)
    asr_method = ASR_METHOD_MAP.get(madhab, 0)

    url = (
        f"{settings.ALADHAN_API_URL}/timings/{target_date.strftime('%d-%m-%Y')}"
        f"?latitude={latitude}&longitude={longitude}"
        f"&method={method}&school={asr_method}"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    timings = data["data"]["timings"]
    date_info = data["data"]["date"]

    return PrayerTimesResponse(
        date=date_info["readable"],
        hijri_date=(
            f"{date_info['hijri']['day']} {date_info['hijri']['month']['en']} "
            f"{date_info['hijri']['year']} AH"
        ),
        fajr=timings["Fajr"],
        sunrise=timings["Sunrise"],
        dhuhr=timings["Dhuhr"],
        asr=timings["Asr"],
        sunset=timings["Sunset"],
        maghrib=timings["Maghrib"],
        isha=timings["Isha"],
        midnight=timings["Midnight"],
        timezone=data["data"]["meta"]["timezone"],
        prayer_method=data["data"]["meta"]["method"]["name"],
    )


def calculate_prayer_streak(prayer_logs: list, required_prayers: list[str] = None) -> dict:
    """
    Calculate current and longest streak from prayer logs.
    A day counts if all 5 obligatory prayers are logged (any status except 'missed').
    """
    if required_prayers is None:
        required_prayers = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

    # Group logs by date
    by_date: dict[date, set[str]] = {}
    for log in prayer_logs:
        d = log.log_date
        if d not in by_date:
            by_date[d] = set()
        if log.status != "missed":
            by_date[d].add(log.prayer_name)

    # Determine complete days
    complete_days = {
        d for d, prayers in by_date.items()
        if all(p in prayers for p in required_prayers)
    }

    if not complete_days:
        return {"current_streak": 0, "longest_streak": 0}

    # Current streak (working backwards from today)
    today = date.today()
    current = 0
    check = today
    while check in complete_days:
        current += 1
        check = check - timedelta(days=1)

    # If today is not complete yet, check from yesterday
    if today not in complete_days:
        current = 0
        check = today - timedelta(days=1)
        while check in complete_days:
            current += 1
            check = check - timedelta(days=1)

    # Longest streak
    sorted_days = sorted(complete_days)
    longest = 1
    run = 1
    for i in range(1, len(sorted_days)):
        if (sorted_days[i] - sorted_days[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return {"current_streak": current, "longest_streak": longest}
