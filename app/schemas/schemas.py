from datetime import date, datetime
from typing import Optional
from uuid import UUID

from app.schemas.base import AppBaseModel, IDSchema, TimestampSchema


# ─── Quran / Hifz ─────────────────────────────────────────────────────────────

class HifzProgressCreate(AppBaseModel):
    surah_number: int
    surah_name: Optional[str] = None
    ayah_from: int = 1
    ayah_to: int
    total_ayahs: int


class HifzProgressUpdate(AppBaseModel):
    status: Optional[str] = None
    last_reviewed: Optional[date] = None
    next_review: Optional[date] = None
    review_count: Optional[int] = None
    ease_factor: Optional[float] = None
    interval_days: Optional[int] = None


class HifzReviewSubmit(AppBaseModel):
    """SM-2 review quality: 0=blackout, 1=wrong, 2=hard, 3=good, 4=easy, 5=perfect"""
    quality: int  # 0–5


class HifzProgressResponse(IDSchema, TimestampSchema):
    user_id: UUID
    surah_number: int
    surah_name: Optional[str] = None
    ayah_from: int
    ayah_to: int
    total_ayahs: int
    status: str
    last_reviewed: Optional[date] = None
    next_review: Optional[date] = None
    review_count: int
    ease_factor: float
    interval_days: int


class DuaFavoriteCreate(AppBaseModel):
    dua_key: str
    category: Optional[str] = None
    custom_note: Optional[str] = None


class DuaFavoriteResponse(IDSchema, TimestampSchema):
    user_id: UUID
    dua_key: str
    category: Optional[str] = None
    custom_note: Optional[str] = None


# ─── Habits ───────────────────────────────────────────────────────────────────

class HabitCreate(AppBaseModel):
    name: str
    description: Optional[str] = None
    category: str = "personal"
    frequency: str = "daily"
    days_of_week: Optional[str] = None
    target_count: int = 1
    unit: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class HabitUpdate(AppBaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    frequency: Optional[str] = None
    days_of_week: Optional[str] = None
    target_count: Optional[int] = None
    unit: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class HabitResponse(IDSchema, TimestampSchema):
    user_id: UUID
    name: str
    description: Optional[str] = None
    category: str
    frequency: str
    days_of_week: Optional[str] = None
    target_count: int
    unit: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: bool


class HabitLogCreate(AppBaseModel):
    habit_id: UUID
    log_date: date
    count: int = 1
    completed: bool = True
    notes: Optional[str] = None


class HabitLogResponse(IDSchema, TimestampSchema):
    habit_id: UUID
    user_id: UUID
    log_date: date
    count: int
    completed: bool
    notes: Optional[str] = None


class HabitWithStreak(HabitResponse):
    current_streak: int = 0
    longest_streak: int = 0
    completed_today: bool = False
    completion_rate_30d: float = 0.0


# ─── Journal ──────────────────────────────────────────────────────────────────

class JournalEntryCreate(AppBaseModel):
    title: Optional[str] = None
    content: str
    mood: Optional[str] = None
    tags: Optional[list[str]] = None
    entry_date: date
    gratitude: Optional[str] = None
    intentions: Optional[str] = None
    reflection: Optional[str] = None
    quran_ayah_ref: Optional[str] = None


class JournalEntryUpdate(AppBaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[str] = None
    tags: Optional[list[str]] = None
    gratitude: Optional[str] = None
    intentions: Optional[str] = None
    reflection: Optional[str] = None
    quran_ayah_ref: Optional[str] = None


class JournalEntryResponse(IDSchema, TimestampSchema):
    user_id: UUID
    title: Optional[str] = None
    content: str
    mood: Optional[str] = None
    tags: Optional[list] = None
    entry_date: date
    is_private: bool
    gratitude: Optional[str] = None
    intentions: Optional[str] = None
    reflection: Optional[str] = None
    quran_ayah_ref: Optional[str] = None


# ─── Tasks ────────────────────────────────────────────────────────────────────

class TaskCreate(AppBaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[date] = None
    time_block: Optional[str] = None
    estimated_minutes: Optional[int] = None
    parent_task_id: Optional[UUID] = None
    sort_order: int = 0


class TaskUpdate(AppBaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    time_block: Optional[str] = None
    estimated_minutes: Optional[int] = None
    completed: Optional[bool] = None
    sort_order: Optional[int] = None


class TaskResponse(IDSchema, TimestampSchema):
    user_id: UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: str
    due_date: Optional[date] = None
    time_block: Optional[str] = None
    estimated_minutes: Optional[int] = None
    completed: bool
    completed_at: Optional[datetime] = None
    parent_task_id: Optional[UUID] = None
    sort_order: int


# ─── Female Module ────────────────────────────────────────────────────────────

class CycleCreate(AppBaseModel):
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None
    symptoms: Optional[str] = None


class CycleUpdate(AppBaseModel):
    end_date: Optional[date] = None
    ghusl_done: Optional[bool] = None
    ghusl_date: Optional[date] = None
    notes: Optional[str] = None
    symptoms: Optional[str] = None


class CycleResponse(IDSchema, TimestampSchema):
    user_id: UUID
    start_date: date
    end_date: Optional[date] = None
    duration_days: Optional[int] = None
    blood_classification: str
    hayd_tuhr_status: str
    madhab_ruling: Optional[str] = None
    can_pray: bool
    can_fast: bool
    can_read_quran: bool
    ghusl_required: bool
    ghusl_done: bool
    ghusl_date: Optional[date] = None
    cycle_length: Optional[int] = None
    # notes & symptoms intentionally omitted — decrypted separately


class CycleDetailResponse(CycleResponse):
    """Includes decrypted sensitive fields — only returned to the user herself."""
    notes: Optional[str] = None
    symptoms: Optional[str] = None


class FastingLogCreate(AppBaseModel):
    fast_date: date
    fast_type: str = "ramadan"
    completed: bool = True
    reason_missed: Optional[str] = None
    is_qadha: bool = False
    original_fast_date: Optional[date] = None
    notes: Optional[str] = None


class FastingLogUpdate(AppBaseModel):
    completed: Optional[bool] = None
    reason_missed: Optional[str] = None
    fidya_paid: Optional[bool] = None
    kaffarah_completed: Optional[bool] = None
    notes: Optional[str] = None


class FastingLogResponse(IDSchema, TimestampSchema):
    user_id: UUID
    fast_date: date
    fast_type: str
    completed: bool
    reason_missed: Optional[str] = None
    is_qadha: bool
    original_fast_date: Optional[date] = None
    fidya_applicable: bool
    fidya_paid: bool
    kaffarah_applicable: bool
    kaffarah_completed: bool
    notes: Optional[str] = None


class MissedFastSummary(AppBaseModel):
    total_missed: int
    total_qadha_made: int
    remaining_qadha: int
    fidya_owed: int
    year: int


# ─── AI ───────────────────────────────────────────────────────────────────────

class AIMessageRequest(AppBaseModel):
    content: str
    conversation_id: Optional[UUID] = None
    context_module: str = "general"


class AIMessageResponse(AppBaseModel):
    conversation_id: UUID
    reply: str
    was_referred: bool = False  # True if fiqh question was redirected
    referral_links: Optional[list[dict]] = None
    messages_used_today: int
    messages_limit: int


class AIConversationResponse(IDSchema, TimestampSchema):
    user_id: UUID
    title: Optional[str] = None
    context_module: str
    messages: list
    message_count: int
    is_active: bool


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardResponse(AppBaseModel):
    user_display_name: Optional[str]
    today_date: str
    hijri_date: str
    prayer_summary: dict
    habit_summary: dict
    hifz_due_today: int
    tasks_due_today: int
    streak_days: int
    female_status: Optional[dict] = None   # only if gender=female


# ─── Phase 3: Dua schemas ─────────────────────────────────────────────────────
from app.schemas.base import AppBaseModel, IDSchema, TimestampSchema
from uuid import UUID as _UUID
from datetime import date as _date
from typing import Optional as _Opt

class DuaResponse(AppBaseModel):
    id: _UUID
    key: str
    title: str
    arabic_text: str
    transliteration: _Opt[str] = None
    translation: str
    source: _Opt[str] = None
    category: str
    when_to_recite: _Opt[str] = None
    repetition_count: int = 1
    dua_order: int = 0


class PersonalDuaCreate(AppBaseModel):
    title: str
    text: str
    date_started: _Opt[_date] = None


class PersonalDuaUpdate(AppBaseModel):
    title: _Opt[str] = None
    text: _Opt[str] = None
    is_answered: _Opt[bool] = None
    answered_date: _Opt[_date] = None
    answered_note: _Opt[str] = None
    is_shared_anonymously: _Opt[bool] = None


class PersonalDuaResponse(IDSchema, TimestampSchema):
    user_id: _UUID
    title: str
    text: str
    date_started: _date
    is_answered: bool
    answered_date: _Opt[_date] = None
    answered_note: _Opt[str] = None
    is_shared_anonymously: bool


# ─── Phase 3: Hadith schemas ──────────────────────────────────────────────────

class HadithResponse(AppBaseModel):
    id: _UUID
    collection: str
    book_name: _Opt[str] = None
    hadith_number: str
    arabic_text: _Opt[str] = None
    english_text: str
    narrator_chain: _Opt[str] = None
    grade: str
    grade_note: _Opt[str] = None
    topics: _Opt[str] = None


# ─── Phase 3: Quran Reading Log schemas ──────────────────────────────────────

class QuranReadingLogCreate(AppBaseModel):
    log_date: _Opt[_date] = None
    surah_from: int
    ayah_from: int
    surah_to: int
    ayah_to: int
    verses_read: int
    minutes_read: int = 0
    minutes_listened: int = 0
    reciter_used: _Opt[str] = None
    mode: str = "reading"


class QuranReadingLogResponse(IDSchema, TimestampSchema):
    user_id: _UUID
    log_date: _date
    surah_from: int
    ayah_from: int
    surah_to: int
    ayah_to: int
    verses_read: int
    minutes_read: int
    minutes_listened: int
    reciter_used: _Opt[str] = None
    mode: str


class QuranStatsResponse(AppBaseModel):
    total_verses_read: int
    total_minutes_read: int
    total_minutes_listened: int
    verses_this_month: int
    minutes_this_month: int
    sessions_this_month: int
    avg_daily_minutes: float
    projected_khatam_days: _Opt[int] = None   # None if no data
    khatam_progress_pct: float                  # 0-100


# ─── Phase 3: Bookmark schemas ────────────────────────────────────────────────

class QuranBookmarkCreate(AppBaseModel):
    surah_number: int
    ayah_number: int
    note: _Opt[str] = None
    highlight_color: _Opt[str] = None


class QuranBookmarkResponse(IDSchema, TimestampSchema):
    user_id: _UUID
    surah_number: int
    ayah_number: int
    note: _Opt[str] = None
    highlight_color: _Opt[str] = None


# ─── Phase 3: Hifz enhanced ──────────────────────────────────────────────────

class HifzProgressResponseV2(IDSchema, TimestampSchema):
    user_id: _UUID
    surah_number: int
    surah_name: _Opt[str] = None
    ayah_from: int
    ayah_to: int
    total_ayahs: int
    status: str
    last_reviewed: _Opt[_date] = None
    next_review: _Opt[_date] = None
    review_count: int
    ease_factor: float
    interval_days: int
    leitner_box: int = 1
