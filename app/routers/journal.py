"""
Journal Router — Phase 5
========================
Extended journal with 5 modes, E2E encryption support,
AI verse suggestion, analytics, insights engine,
monthly letters, and female wellness cycle integration.
"""

from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.core.dependencies import CurrentUser, DB
from app.repositories import JournalRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    JournalEntryCreate, JournalEntryResponse, JournalEntryUpdate,
    JournalEntryCreateV2, JournalEntryResponseV2, JournalEntryUpdateV2,
    JournalAnalyticsResponse, DailyInsightResponse, MonthlyLetterResponse,
    InsightRatingRequest,
)

router = APIRouter(prefix="/journal", tags=["journal"])

# ─── CRUD (backward-compatible + Phase 5) ────────────────────────────────────

@router.get("", response_model=list[JournalEntryResponseV2])
async def list_entries(
    current_user: CurrentUser, db: DB, journal_repo: JournalRepo,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    mood: Optional[str] = Query(default=None),
    journal_mode: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
    from app.models.journal import JournalEntry
    end   = end_date   or date.today()
    start = start_date or (end - timedelta(days=30))
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.id,
               JournalEntry.entry_date >= start,
               JournalEntry.entry_date <= end)
        .order_by(JournalEntry.entry_date.desc())
        .limit(limit).offset(offset)
    )
    if mood:         stmt = stmt.where(JournalEntry.mood == mood)
    if journal_mode: stmt = stmt.where(JournalEntry.journal_mode == journal_mode)
    result = await db.execute(stmt)
    return [JournalEntryResponseV2.model_validate(e) for e in result.scalars().all()]


@router.post("", response_model=JournalEntryResponseV2, status_code=201)
async def create_entry(
    payload: JournalEntryCreateV2,
    current_user: CurrentUser, db: DB, journal_repo: JournalRepo,
):
    data = payload.model_dump()
    data["entry_date"] = data.get("entry_date") or date.today()
    entry = await journal_repo.create(user_id=current_user.id, **data)
    return JournalEntryResponseV2.model_validate(entry)


@router.get("/muhasabah-prompt")
async def get_muhasabah_prompt():
    """Returns the structured Muhasabah form fields."""
    return {
        "sections": [
            {"key": "prayers_completed", "label": "How many of the 5 prayers did I complete today?", "type": "number", "max": 5},
            {"key": "prayers_on_time",   "label": "How many were on time?", "type": "number", "max": 5},
            {"key": "quran_pages",       "label": "How many pages of Quran did I read?", "type": "number"},
            {"key": "dhikr_done",        "label": "Did I complete my morning/evening adhkar?", "type": "boolean"},
            {"key": "wronged_anyone",    "label": "Did I wrong anyone today? How?", "type": "textarea"},
            {"key": "extra_good",        "label": "What extra good did I do today?", "type": "textarea"},
            {"key": "tomorrow_intention","label": "What is my intention for tomorrow?", "type": "textarea"},
            {"key": "gratitude_1",       "label": "I am grateful for (1):", "type": "text"},
            {"key": "gratitude_2",       "label": "I am grateful for (2):", "type": "text"},
            {"key": "gratitude_3",       "label": "I am grateful for (3):", "type": "text"},
        ]
    }


@router.get("/guided-prompts")
async def get_guided_prompts(category: Optional[str] = Query(default=None)):
    """Returns AI-style guided reflection prompts by category."""
    prompts = {
        "gratitude": [
            "What specific blessing did you notice today that you might usually overlook?",
            "Who in your life are you most grateful for right now, and why?",
            "What difficulty from the past are you now grateful for because of how it shaped you?",
        ],
        "prayer": [
            "How was your presence of heart (khushu) in today's prayers?",
            "Which prayer felt most meaningful today, and what made it so?",
            "What is one thing you could change about your prayer routine to increase focus?",
        ],
        "quran": [
            "Which verse or surah has been on your mind recently? What does it mean to you personally?",
            "What is one teaching from the Quran you want to embody more fully this week?",
            "If you could ask Allah one question about the Quran, what would it be?",
        ],
        "accountability": [
            "Where did you fall short of your values today, and what would you do differently?",
            "What is one habit you promised yourself to build — how is it going?",
            "If your best self were watching your day, what would they say?",
        ],
        "muhasabah": [
            "What actions today drew you closer to Allah, and what distanced you?",
            "Did you fulfil the rights of those around you today — family, colleagues, strangers?",
            "What is one thing you want to seek forgiveness for today?",
        ],
        "sabr": [
            "What is the hardest thing you are enduring right now, and how are you finding sabr?",
            "Where do you see Allah's wisdom in a difficulty you faced recently?",
            "How has patience shown up as a strength in your life this week?",
        ],
        "tawakkul": [
            "Where in your life are you holding on too tightly, resisting tawakkul?",
            "What decision are you facing where you need to put your full trust in Allah?",
            "How does remembering Allah's control over all things change your anxiety?",
        ],
    }
    if category and category in prompts:
        return {"category": category, "prompts": prompts[category]}
    return {"all_prompts": prompts}


@router.get("/analytics", response_model=JournalAnalyticsResponse)
async def get_journal_analytics(current_user: CurrentUser, db: DB):
    from app.models.journal import JournalEntry
    today      = date.today()
    month_start = today.replace(day=1)

    result = await db.execute(
        select(JournalEntry).where(JournalEntry.user_id == current_user.id)
        .order_by(JournalEntry.entry_date.desc())
    )
    all_entries = result.scalars().all()
    if not all_entries:
        return JournalAnalyticsResponse(
            total_entries=0, entries_this_month=0, current_streak=0,
            longest_streak=0, mood_counts={}, mood_trend=[], modes_used={},
            avg_content_length=0,
        )

    this_month = [e for e in all_entries if e.entry_date >= month_start]

    # Streak calculation
    entry_dates = sorted({e.entry_date for e in all_entries}, reverse=True)
    cur_streak, lng_streak, run = 0, 0, 0
    prev = None
    for d in entry_dates:
        if prev is None or (prev - d).days == 1:
            run += 1
        else:
            run = 1
        lng_streak = max(lng_streak, run)
        prev = d
    # current streak
    check = today
    for d in entry_dates:
        if d == check:
            cur_streak += 1
            check -= timedelta(days=1)
        elif d < check:
            break

    # Mood counts
    mood_counts: dict = {}
    for e in all_entries:
        if e.mood:
            mood_counts[e.mood] = mood_counts.get(e.mood, 0) + 1

    # 30-day mood trend
    cutoff_30 = today - timedelta(days=30)
    recent = [e for e in all_entries if e.entry_date >= cutoff_30]
    mood_trend = [{"date": str(e.entry_date), "mood": e.mood} for e in recent if e.mood]

    # Modes used
    modes_used: dict = {}
    for e in all_entries:
        m = getattr(e, "journal_mode", None) or "free_write"
        modes_used[m] = modes_used.get(m, 0) + 1

    avg_len = round(sum(len(e.content or "") for e in all_entries) / max(len(all_entries), 1))

    return JournalAnalyticsResponse(
        total_entries=len(all_entries),
        entries_this_month=len(this_month),
        current_streak=cur_streak,
        longest_streak=lng_streak,
        mood_counts=mood_counts,
        mood_trend=mood_trend,
        modes_used=modes_used,
        avg_content_length=avg_len,
    )


@router.get("/mood-trend")
async def get_mood_trend(
    current_user: CurrentUser, db: DB,
    days: int = Query(default=30, le=90),
):
    from app.models.journal import JournalEntry
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(JournalEntry.entry_date, JournalEntry.mood)
        .where(JournalEntry.user_id == current_user.id,
               JournalEntry.entry_date >= cutoff,
               JournalEntry.mood.isnot(None))
        .order_by(JournalEntry.entry_date)
    )
    rows = result.all()
    return [{"date": str(r.entry_date), "mood": r.mood} for r in rows]


@router.post("/ai-suggest-verses", response_model=dict)
async def suggest_verses_for_entry(
    current_user: CurrentUser, db: DB,
    entry_id: UUID = Query(...),
):
    """
    Analyses journal entry tone and suggests 1-3 relevant Quran verses.
    Uses keyword matching for v1; Claude API for v2.
    """
    from app.models.journal import JournalEntry

    result = await db.execute(
        select(JournalEntry)
        .where(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry not found.")

    # Skip encrypted entries
    if getattr(entry, "is_encrypted", False):
        return {"verses": [], "note": "Verse suggestion not available for encrypted entries."}

    text = (entry.content or "").lower() + " " + (entry.mood or "")

    VERSE_MAP = {
        ("anxious", "worried", "fear", "scared", "stressed"): [
            {"ref": "2:286", "text": "Allah does not burden a soul beyond that it can bear."},
            {"ref": "94:5",  "text": "For indeed, with hardship will be ease."},
        ],
        ("sad", "grief", "loss", "crying", "pain"): [
            {"ref": "2:153", "text": "Seek help through patience and prayer. Allah is with the patient."},
            {"ref": "93:3",  "text": "Your Lord has not forsaken you, nor has He detested you."},
        ],
        ("grateful", "thankful", "blessed", "alhamdulillah", "shukr"): [
            {"ref": "14:7",  "text": "If you are grateful, I will surely increase you in favour."},
            {"ref": "55:13", "text": "So which of the favours of your Lord would you deny?"},
        ],
        ("hopeful", "hope", "pray", "dua", "asking"): [
            {"ref": "40:60", "text": "Call upon Me; I will respond to you."},
            {"ref": "3:173", "text": "Allah is sufficient for us, and He is the best Disposer of affairs."},
        ],
        ("motivated", "goal", "working", "striving", "effort"): [
            {"ref": "53:39", "text": "That there is not for man except that for which he strives."},
            {"ref": "2:286", "text": "It is rewarded what good it earns, and against it is what evil it earns."},
        ],
        ("reflective", "thinking", "muhasabah", "self", "account"): [
            {"ref": "59:18", "text": "O you who believe! Fear Allah, and let every soul consider what it has sent ahead for tomorrow."},
            {"ref": "75:2",  "text": "And I do swear by the reproaching soul."},
        ],
    }

    matches = []
    for keywords, verses in VERSE_MAP.items():
        if any(kw in text for kw in keywords):
            matches.extend(verses)

    # Deduplicate and limit to 3
    seen = set()
    unique = []
    for v in matches:
        if v["ref"] not in seen:
            seen.add(v["ref"])
            unique.append(v)
        if len(unique) == 3:
            break

    if not unique:
        # Default encouraging verse
        unique = [{"ref": "2:286", "text": "Allah does not burden a soul beyond that it can bear."}]

    return {"verses": unique}


@router.get("/{entry_id}", response_model=JournalEntryResponseV2)
async def get_entry(entry_id: UUID, current_user: CurrentUser, db: DB, journal_repo: JournalRepo):
    entry = await journal_repo.get_owned_or_404(entry_id, current_user.id)
    return JournalEntryResponseV2.model_validate(entry)


@router.patch("/{entry_id}", response_model=JournalEntryResponseV2)
async def update_entry(
    entry_id: UUID, payload: JournalEntryUpdateV2,
    current_user: CurrentUser, db: DB, journal_repo: JournalRepo,
):
    entry = await journal_repo.get_owned_or_404(entry_id, current_user.id)
    entry = await journal_repo.update(entry, **payload.model_dump(exclude_none=True))
    return JournalEntryResponseV2.model_validate(entry)


@router.delete("/{entry_id}", response_model=MessageResponse)
async def delete_entry(entry_id: UUID, current_user: CurrentUser, db: DB, journal_repo: JournalRepo):
    entry = await journal_repo.get_owned_or_404(entry_id, current_user.id)
    await journal_repo.delete(entry)
    return MessageResponse(message="Journal entry deleted.")


# ─── Daily Insights ──────────────────────────────────────────────────────────

insights_router = APIRouter(prefix="/insights", tags=["insights"])


@insights_router.get("/today", response_model=Optional[DailyInsightResponse])
async def get_today_insight(current_user: CurrentUser, db: DB):
    from app.services.insight_engine import get_or_generate_insight
    insight = await get_or_generate_insight(db, current_user.id)
    if not insight:
        return None
    await db.commit()
    return DailyInsightResponse.model_validate(insight)


@insights_router.get("", response_model=list[DailyInsightResponse])
async def list_insights(
    current_user: CurrentUser, db: DB,
    days: int = Query(default=30, le=90),
    dismissed: bool = Query(default=False),
):
    from app.models.journal import DailyInsight
    cutoff = date.today() - timedelta(days=days)
    stmt = (
        select(DailyInsight)
        .where(DailyInsight.user_id == current_user.id, DailyInsight.generated_at >= cutoff)
        .order_by(DailyInsight.generated_at.desc())
    )
    if not dismissed:
        stmt = stmt.where(DailyInsight.is_dismissed == False)
    result = await db.execute(stmt)
    return [DailyInsightResponse.model_validate(i) for i in result.scalars().all()]


@insights_router.post("/{insight_id}/dismiss", response_model=DailyInsightResponse)
async def dismiss_insight(insight_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.journal import DailyInsight
    result = await db.execute(
        select(DailyInsight)
        .where(DailyInsight.id == insight_id, DailyInsight.user_id == current_user.id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(404, "Insight not found.")
    insight.is_dismissed = True
    await db.flush()
    await db.refresh(insight)
    return DailyInsightResponse.model_validate(insight)


@insights_router.post("/{insight_id}/rate", response_model=DailyInsightResponse)
async def rate_insight(
    insight_id: UUID, payload: InsightRatingRequest,
    current_user: CurrentUser, db: DB,
):
    from app.models.journal import DailyInsight
    if payload.rating not in (-1, 0, 1):
        raise HTTPException(422, "Rating must be -1, 0, or 1.")
    result = await db.execute(
        select(DailyInsight)
        .where(DailyInsight.id == insight_id, DailyInsight.user_id == current_user.id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(404, "Insight not found.")
    insight.user_rating = payload.rating
    await db.flush()
    await db.refresh(insight)
    return DailyInsightResponse.model_validate(insight)


# ─── Monthly Letters ─────────────────────────────────────────────────────────

letters_router = APIRouter(prefix="/letters", tags=["letters"])


@letters_router.get("", response_model=list[MonthlyLetterResponse])
async def list_letters(current_user: CurrentUser, db: DB):
    from app.models.journal import MonthlyLetter
    result = await db.execute(
        select(MonthlyLetter)
        .where(MonthlyLetter.user_id == current_user.id)
        .order_by(MonthlyLetter.year.desc(), MonthlyLetter.month.desc())
    )
    return [MonthlyLetterResponse.model_validate(l) for l in result.scalars().all()]


@letters_router.post("/generate", response_model=MonthlyLetterResponse, status_code=201)
async def generate_monthly_letter(
    current_user: CurrentUser, db: DB, journal_repo: JournalRepo,
    year: int = Query(default=None),
    month: int = Query(default=None),
):
    from app.models.journal import JournalEntry, MonthlyLetter
    today = date.today()
    y = year  or today.year
    m = month or today.month

    # Check already exists
    existing_result = await db.execute(
        select(MonthlyLetter)
        .where(MonthlyLetter.user_id == current_user.id,
               MonthlyLetter.year == y, MonthlyLetter.month == m)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(409, "Letter for this month already exists.")

    # Get entries for month
    from calendar import monthrange
    _, last_day = monthrange(y, m)
    start_d = date(y, m, 1)
    end_d   = date(y, m, last_day)

    entries_result = await db.execute(
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.id,
               JournalEntry.entry_date >= start_d,
               JournalEntry.entry_date <= end_d,
               JournalEntry.is_encrypted == False)
        .order_by(JournalEntry.entry_date)
    )
    entries = entries_result.scalars().all()
    count   = len(entries)

    if count < 3:
        raise HTTPException(422, f"Need at least 3 journal entries in month {m}/{y} to generate a letter. Found {count}.")

    # Mood summary
    moods = [e.mood for e in entries if e.mood]
    mood_counts: dict = {}
    for mood in moods:
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
    top_mood = max(mood_counts, key=mood_counts.__getitem__) if mood_counts else "reflective"

    # Extract themes (simple keyword matching for v1)
    all_text = " ".join(e.content or "" for e in entries).lower()
    theme_keywords = {
        "family": ["family","mother","father","child","wife","husband","son","daughter"],
        "work":   ["work","job","career","business","project","deadline"],
        "health": ["health","exercise","sleep","water","food","diet","tired"],
        "quran":  ["quran","verse","surah","recite","memorise","hifz","ayah"],
        "prayer": ["prayer","fajr","dhuhr","asr","maghrib","isha","salah","namaz"],
        "sabr":   ["patience","sabr","difficult","hard","struggle","challenge","trial"],
        "gratitude": ["grateful","thankful","blessed","alhamdulillah","shukr","blessing"],
    }
    themes = [theme for theme, kws in theme_keywords.items() if any(kw in all_text for kw in kws)]

    # Build letter text
    month_name  = date(y, m, 1).strftime("%B %Y")
    mood_phrase = top_mood if top_mood else "reflective"
    letter  = f"Dear seeker,\n\n"
    letter += f"Looking back at {month_name}, you wrote {count} journal entries "
    letter += "\u2014 each one a moment of honest reflection. "
    letter += f"Your heart was most often '{mood_phrase}' this month. "
    if themes:
        letter += f"The themes that wove through your writing: {', '.join(themes[:4])}. "
    letter += (
        f"\n\nYou showed up for yourself {count} times. That is not small. "
        "The Prophet said: 'The most beloved deeds are the most regular and constant.' "
        "Your journaling is exactly that.\n\n"
        "May Allah seal this month with His mercy and open the next with His barakah.\n\n"
        "Bismillah \u2014 keep writing."
    )
    ml = MonthlyLetter(
        user_id=current_user.id, year=y, month=m,
        letter_text=letter, mood_summary=top_mood,
        top_themes=themes[:5], entry_count=count,
        is_ai_generated=True,
    )
    db.add(ml)
    await db.flush()
    await db.refresh(ml)
    await db.commit()
    return MonthlyLetterResponse.model_validate(ml)


@letters_router.get("/{letter_id}", response_model=MonthlyLetterResponse)
async def get_letter(letter_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.journal import MonthlyLetter
    result = await db.execute(
        select(MonthlyLetter)
        .where(MonthlyLetter.id == letter_id, MonthlyLetter.user_id == current_user.id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(404, "Letter not found.")
    return MonthlyLetterResponse.model_validate(letter)
