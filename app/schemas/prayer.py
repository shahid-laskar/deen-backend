from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from app.schemas.base import AppBaseModel, IDSchema, TimestampSchema


class PrayerTimesResponse(AppBaseModel):
    """Response from Aladhan API, normalized."""
    date: str
    hijri_date: str
    fajr: str
    sunrise: str
    dhuhr: str
    asr: str
    sunset: str
    maghrib: str
    isha: str
    midnight: str
    timezone: str
    prayer_method: str


class PrayerLogCreate(AppBaseModel):
    prayer_name: str
    log_date: date
    status: str = "on_time"
    prayed_at: Optional[datetime] = None
    is_qadha: bool = False
    notes: Optional[str] = None


class PrayerLogUpdate(AppBaseModel):
    status: Optional[str] = None
    prayed_at: Optional[datetime] = None
    is_qadha: Optional[bool] = None
    notes: Optional[str] = None


class PrayerLogResponse(IDSchema, TimestampSchema):
    user_id: UUID
    prayer_name: str
    log_date: date
    status: str
    prayed_at: Optional[datetime] = None
    is_qadha: bool
    notes: Optional[str] = None


class DailyPrayerSummary(AppBaseModel):
    """Summary for the dashboard."""
    date: date
    fajr: Optional[PrayerLogResponse] = None
    dhuhr: Optional[PrayerLogResponse] = None
    asr: Optional[PrayerLogResponse] = None
    maghrib: Optional[PrayerLogResponse] = None
    isha: Optional[PrayerLogResponse] = None
    total_logged: int
    total_on_time: int
    completion_pct: float


class PrayerStreakResponse(AppBaseModel):
    current_streak: int
    longest_streak: int
    total_logged: int
    this_week_completion: float
