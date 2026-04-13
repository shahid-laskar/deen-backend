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


# ─── Phase 2 additions ────────────────────────────────────────────────────────

class PrayerLogCreateV2(AppBaseModel):
    """Extended prayer log with Phase 2 fields."""
    prayer_name: str
    log_date: date
    status: str = "on_time"
    prayed_at: Optional[datetime] = None
    is_qadha: bool = False
    notes: Optional[str] = None
    with_congregation: bool = False
    khushu_rating: Optional[int] = None   # 1-5
    location_name: Optional[str] = None


class PrayerLogUpdateV2(AppBaseModel):
    status: Optional[str] = None
    prayed_at: Optional[datetime] = None
    is_qadha: Optional[bool] = None
    notes: Optional[str] = None
    with_congregation: Optional[bool] = None
    khushu_rating: Optional[int] = None
    location_name: Optional[str] = None


class PrayerLogResponseV2(IDSchema, TimestampSchema):
    user_id: UUID
    prayer_name: str
    log_date: date
    status: str
    prayed_at: Optional[datetime] = None
    is_qadha: bool
    notes: Optional[str] = None
    with_congregation: bool = False
    khushu_rating: Optional[int] = None
    location_name: Optional[str] = None


class PrayerStatsResponse(AppBaseModel):
    """30-day stats per prayer + overall."""
    prayer_name: str
    total_days: int
    on_time_count: int
    late_count: int
    missed_count: int
    qadha_count: int
    on_time_rate: float           # 0-100
    congregation_rate: float      # 0-100
    avg_khushu: Optional[float]   # 1-5 or None


class WeeklyPrayerSummary(AppBaseModel):
    week_start: date
    week_end: date
    total_prayers_possible: int   # days * 5
    total_prayed: int
    total_on_time: int
    on_time_pct: float
    congregation_count: int
    best_prayer: Optional[str]
    worst_prayer: Optional[str]


class HeatmapCell(AppBaseModel):
    date: date
    count: int      # 0-5 prayers logged that day
    on_time: int    # 0-5 on-time


class IslamicEventResponse(AppBaseModel):
    id: UUID
    name: str
    name_ar: Optional[str]
    hijri_month: int
    hijri_day: int
    duration_days: int
    event_type: str
    description: Optional[str]
    deed_of_day: Optional[str]
    notification_template: Optional[str]


class TravelModeResponse(AppBaseModel):
    is_travelling: bool
    distance_from_home_km: float
    qasr_applicable: bool
    madhab_notes: str
