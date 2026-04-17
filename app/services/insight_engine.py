"""
Insight Engine — Phase 5
=========================
Rules-based daily personalised insights engine.

Design principles:
- Requires 14+ days of user data before generating insights
- All insights are warm and encouraging — never guilt-tripping
- Every insight is paired with Quranic or Hadith encouragement
- v1: rules-based | v2 upgrade path: collaborative filtering on user ratings
"""

from datetime import date, timedelta, datetime, time, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import InsightCategory


# ─── Quran verses by theme ────────────────────────────────────────────────────

ENCOURAGING_AYAT = {
    "patience":   ("2:153", "O you who believe! Seek help through patience and prayer. Indeed, Allah is with the patient."),
    "consistency": ("3:139", "Do not weaken or grieve, for you will be superior if you are true believers."),
    "fajr":       ("17:78", "Establish prayer at the decline of the sun until the darkness of the night, and the Quran of dawn — indeed, the recitation of dawn is ever witnessed."),
    "quran":      ("2:2",   "This is the Book about which there is no doubt, a guidance for those conscious of Allah."),
    "gratitude":  ("14:7",  "If you are grateful, I will surely increase you in favour."),
    "tawakkul":   ("65:3",  "And whoever relies upon Allah — then He is sufficient for him."),
    "sabr":       ("39:10", "Indeed, the patient will be given their reward without account."),
    "dua":        ("40:60", "Call upon Me; I will respond to you."),
    "hope":       ("39:53", "Do not despair of the mercy of Allah. Indeed, Allah forgives all sins."),
    "morning":    ("73:6",  "Indeed, the hours of the night are more effective for concurrence and more suitable for words."),
    "habits":     ("3:134", "Those who spend in ease and in adversity and who restrain anger and who pardon people — Allah loves the doers of good."),
    "spiritual":  ("2:286", "Allah does not burden a soul beyond that it can bear."),
}

ENCOURAGING_HADITHS = {
    "consistency": ("Bukhari 6464", "The most beloved deeds to Allah are the most regular and constant even though they may be few."),
    "small_deeds": ("Bukhari 6464", "Do not belittle any good deed, even meeting your brother with a cheerful face."),
    "fajr":        ("Muslim 657",   "The most burdensome prayers for the hypocrites are Isha and Fajr — if they knew what was in them, they would come even if crawling."),
    "quran":       ("Tirmidhi 2910","Whoever reads one letter from the Book of Allah gets one good deed worth ten like it."),
}


# ─── Insight Generator ────────────────────────────────────────────────────────

class InsightEngine:
    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id

    async def has_enough_data(self) -> bool:
        """Require 14+ days of any data before generating insights."""
        from app.models.habit import HabitLog
        from app.models.prayer import PrayerLog
        cutoff = date.today() - timedelta(days=14)
        result = await self.db.execute(
            select(func.count()).select_from(HabitLog)
            .where(HabitLog.user_id == self.user_id, HabitLog.log_date >= cutoff)
        )
        habit_days = result.scalar() or 0
        if habit_days >= 5:
            return True
        result2 = await self.db.execute(
            select(func.count()).select_from(PrayerLog)
            .where(PrayerLog.user_id == self.user_id, PrayerLog.prayed_at >= cutoff)
        )
        prayer_logs = result2.scalar() or 0
        return prayer_logs >= 10

    async def generate(self) -> Optional[dict]:
        """
        Generate the best insight for today. Returns dict or None if insufficient data.
        Tries each category in priority order; returns first that has enough data.
        """
        if not await self.has_enough_data():
            return None

        generators = [
            self._prayer_pattern_insight,
            self._mood_journal_insight,
            self._habit_streak_insight,
            self._quran_pattern_insight,
            self._spiritual_trend_insight,
        ]

        # Rotate which category gets priority based on day of year
        day_idx = date.today().timetuple().tm_yday % len(generators)
        ordered = generators[day_idx:] + generators[:day_idx]

        for gen in ordered:
            result = await gen()
            if result:
                return result
        return None

    async def _prayer_pattern_insight(self) -> Optional[dict]:
        from app.models.prayer import PrayerLog
        cutoff = date.today() - timedelta(days=30)
        result = await self.db.execute(
            select(PrayerLog)
            .where(PrayerLog.user_id == self.user_id, PrayerLog.prayed_at >= cutoff)
        )
        logs = result.scalars().all()
        if len(logs) < 15:
            return None

        fajr_logs = [l for l in logs if l.prayer_name == "fajr"]
        if not fajr_logs:
            return None

        on_time = [l for l in fajr_logs if l.status in ("on_time", "on_time")]
        on_time_rate = round(len(on_time) / len(fajr_logs) * 100)
        total_rate = round(len([l for l in logs if l.status == "on_time"]) / len(logs) * 100)

        ayah_ref, ayah_text = ENCOURAGING_AYAT["fajr"]

        if on_time_rate >= 80:
            text = (
                f"Your Fajr consistency is at {on_time_rate}% this month — mashAllah! "
                f"You're among those who stand before Allah at the most blessed time of day. "
                f"Overall prayer punctuality: {total_rate}%."
            )
        elif on_time_rate >= 50:
            text = (
                f"You've prayed Fajr on time {on_time_rate}% of days this month. "
                f"That's real effort — and every on-time prayer is witnessed by the angels. "
                f"Small, consistent improvements compound beautifully."
            )
        else:
            text = (
                f"Fajr on time {on_time_rate}% of days this month. "
                f"The predawn hours are the most spiritually charged of the day. "
                f"Tonight, prepare your sleep environment to make tomorrow's Fajr easier."
            )

        return {
            "insight_text": text,
            "category": InsightCategory.PRAYER_PATTERNS,
            "relevant_ayah": f"{ayah_ref} — {ayah_text}",
            "relevant_hadith": "{} — {}".format(*ENCOURAGING_HADITHS["fajr"]),
        }

    async def _mood_journal_insight(self) -> Optional[dict]:
        from app.models.journal import JournalEntry
        cutoff = date.today() - timedelta(days=14)
        result = await self.db.execute(
            select(JournalEntry)
            .where(JournalEntry.user_id == self.user_id, JournalEntry.entry_date >= cutoff)
            .order_by(JournalEntry.entry_date.desc())
        )
        entries = result.scalars().all()
        if len(entries) < 3:
            return None

        moods = [e.mood for e in entries if e.mood]
        if not moods:
            return None

        mood_counts: dict[str, int] = {}
        for m in moods:
            mood_counts[m] = mood_counts.get(m, 0) + 1
        top_mood = max(mood_counts, key=mood_counts.__getitem__)
        top_count = mood_counts[top_mood]

        negative_moods = {"anxious", "sad", "overwhelmed"}
        positive_moods = {"grateful", "peaceful", "hopeful", "motivated"}
        recent_5 = [e.mood for e in entries[:5] if e.mood]
        recent_negative = sum(1 for m in recent_5 if m in negative_moods)

        if recent_negative >= 3:
            ayah_ref, ayah_text = ENCOURAGING_AYAT["sabr"]
            text = (
                f"You've been feeling {top_mood} in several recent entries. "
                f"Your honesty with yourself is a form of courage. "
                f"Remember: after every hardship comes ease (94:5), and Allah is closer to you than you imagine. "
                f"If you'd like, the Grief & Hardship companion in Wellness can support you."
            )
        elif top_mood in positive_moods and top_count >= 3:
            ayah_ref, ayah_text = ENCOURAGING_AYAT["gratitude"]
            text = (
                f"Your last {len(entries)} entries reflect a predominantly {top_mood} heart. "
                f"This is a gift — nurture it by continuing your daily journaling and gratitude practice. "
                f"Shukr multiplies blessings."
            )
        else:
            ayah_ref, ayah_text = ENCOURAGING_AYAT["hope"]
            text = (
                f"Your journal shows a mix of emotions this fortnight — {', '.join(set(moods[:5]))}. "
                f"This range is normal and human. The act of writing itself is muhasabah in motion. "
                f"Keep reflecting."
            )

        return {
            "insight_text": text,
            "category": InsightCategory.MOOD_JOURNAL,
            "relevant_ayah": f"{ayah_ref} — {ayah_text}",
            "relevant_hadith": None,
        }

    async def _habit_streak_insight(self) -> Optional[dict]:
        from app.models.habit import Habit, HabitLog
        result = await self.db.execute(
            select(Habit).where(Habit.user_id == self.user_id, Habit.is_active == True)
        )
        habits = result.scalars().all()
        if not habits:
            return None

        cutoff = date.today() - timedelta(days=7)
        week_completions: dict[UUID, int] = {}
        for h in habits:
            log_result = await self.db.execute(
                select(func.count()).select_from(HabitLog)
                .where(HabitLog.habit_id == h.id, HabitLog.log_date >= cutoff, HabitLog.completed == True)
            )
            week_completions[h.id] = log_result.scalar() or 0

        total_possible  = len(habits) * 7
        total_completed = sum(week_completions.values())
        rate = round(total_completed / max(total_possible, 1) * 100)

        # Find longest current streak
        streaks = sorted(habits, key=lambda h: h.current_streak or 0, reverse=True)
        top_habit = streaks[0] if streaks else None

        ayah_ref, ayah_text = ENCOURAGING_AYAT["consistency"]
        ref2, text2 = ENCOURAGING_HADITHS["consistency"]

        if rate >= 70:
            text = (
                f"This week you completed {total_completed} of {total_possible} possible habit checks ({rate}%). "
                f"Strong consistency! {top_habit.name if top_habit else 'Your top habit'} is on a "
                f"{top_habit.current_streak or 0}-day streak — the angels are witnessing every repetition."
            )
        elif rate >= 40:
            text = (
                f"You completed {total_completed} habit checks this week ({rate}%). "
                f"The Prophet ﷺ loved deeds done consistently, even if small. "
                f"Pick your single most important habit and protect it above all others this week."
            )
        else:
            text = (
                f"Habit completion at {rate}% this week. No judgment — every day is a fresh start. "
                f"Rather than doing all {len(habits)} habits, choose just one to complete today with full presence. "
                f"That single action is beloved to Allah."
            )

        return {
            "insight_text": text,
            "category": InsightCategory.HABIT_CORRELATIONS,
            "relevant_ayah": f"{ayah_ref} — {ayah_text}",
            "relevant_hadith": f"{ref2} — {text2}",
        }

    async def _quran_pattern_insight(self) -> Optional[dict]:
        from app.models.quran import QuranReadingLog
        cutoff = date.today() - timedelta(days=30)
        result = await self.db.execute(
            select(QuranReadingLog)
            .where(QuranReadingLog.user_id == self.user_id, QuranReadingLog.log_date >= cutoff)
        )
        logs = result.scalars().all()
        if len(logs) < 5:
            return None

        total_minutes = sum(l.minutes_read + l.minutes_listened for l in logs)
        total_verses  = sum(l.verses_read for l in logs)
        days_read     = len({l.log_date for l in logs})

        # Weekday vs weekend split
        weekend_logs = [l for l in logs if l.log_date.weekday() >= 4]  # Fri-Sun
        weekday_logs = [l for l in logs if l.log_date.weekday() < 4]
        weekend_avg = sum(l.minutes_read for l in weekend_logs) / max(len(weekend_logs), 1)
        weekday_avg = sum(l.minutes_read for l in weekday_logs) / max(len(weekday_logs), 1)

        ayah_ref, ayah_text = ENCOURAGING_AYAT["quran"]

        if days_read >= 20:
            text = (
                f"You've engaged with the Quran on {days_read} of the last 30 days — "
                f"{total_verses} verses and {total_minutes} minutes total. "
                f"This consistency is rare and precious. The Quran intercedes for those who recite it."
            )
        elif weekend_avg > weekday_avg * 1.5 and weekday_avg < 5:
            text = (
                f"Your Quran reading is stronger on weekends ({round(weekend_avg)}min avg) "
                f"than weekdays ({round(weekday_avg)}min avg). "
                f"Consider anchoring a 5-minute Quran slot after Fajr on weekdays — "
                f"short and daily beats long and occasional."
            )
        else:
            text = (
                f"You've read {total_verses} Quran verses this month across {days_read} days. "
                f"Every letter carries 10 rewards. "
                f"What single surah could you commit to reading every day this week?"
            )

        return {
            "insight_text": text,
            "category": InsightCategory.QURAN_PATTERNS,
            "relevant_ayah": f"{ayah_ref} — {ayah_text}",
            "relevant_hadith": "{} — {}".format(*ENCOURAGING_HADITHS["quran"]),
        }

    async def _spiritual_trend_insight(self) -> Optional[dict]:
        """Weekly spiritual summary — all data combined."""
        from app.models.prayer import PrayerLog
        from app.models.habit import HabitLog
        from app.models.quran import QuranReadingLog

        cutoff = date.today() - timedelta(days=7)
        cutoff_dt = datetime.combine(cutoff, time.min).replace(tzinfo=timezone.utc)

        prayer_result = await self.db.execute(
            select(func.count()).select_from(PrayerLog)
            .where(PrayerLog.user_id == self.user_id, PrayerLog.prayed_at >= cutoff_dt, PrayerLog.status == "on_time")
        )
        prayers_on_time = prayer_result.scalar() or 0

        habit_result = await self.db.execute(
            select(func.count()).select_from(HabitLog)
            .where(HabitLog.user_id == self.user_id, HabitLog.log_date >= cutoff, HabitLog.completed == True)
        )
        habits_done = habit_result.scalar() or 0

        quran_result = await self.db.execute(
            select(func.sum(QuranReadingLog.verses_read))
            .where(QuranReadingLog.user_id == self.user_id, QuranReadingLog.log_date >= cutoff)
        )
        quran_verses = quran_result.scalar() or 0

        if prayers_on_time == 0 and habits_done == 0 and quran_verses == 0:
            return None

        ayah_ref, ayah_text = ENCOURAGING_AYAT["spiritual"]

        parts = []
        if prayers_on_time > 0:
            parts.append(f"{prayers_on_time} prayers on time")
        if quran_verses > 0:
            parts.append(f"{quran_verses} Quran verses")
        if habits_done > 0:
            parts.append(f"{habits_done} habit completions")

        summary = ", ".join(parts)
        text = (
            f"This week's spiritual summary: {summary}. "
            f"Each of these is a seed planted. Allah does not let the weight of a grain of good go unrewarded (99:7-8). "
            f"Keep going — steadiness is more beloved than intensity."
        )

        return {
            "insight_text": text,
            "category": InsightCategory.SPIRITUAL_TRENDS,
            "relevant_ayah": f"{ayah_ref} — {ayah_text}",
            "relevant_hadith": "{} — {}".format(*ENCOURAGING_HADITHS["small_deeds"]),
        }


async def get_or_generate_insight(db: AsyncSession, user_id: UUID) -> Optional["DailyInsight"]:
    """
    Returns today's insight for the user.
    Generates if none exists yet. Returns None if insufficient data.
    """
    from app.models.journal import DailyInsight
    today = date.today()

    # Check for existing insight today
    result = await db.execute(
        select(DailyInsight)
        .where(DailyInsight.user_id == user_id, DailyInsight.generated_at == today)
        .order_by(DailyInsight.created_at.desc())
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Generate new insight
    engine = InsightEngine(db, user_id)
    insight_data = await engine.generate()
    if not insight_data:
        return None

    insight = DailyInsight(
        user_id=user_id,
        generated_at=today,
        **insight_data,
    )
    db.add(insight)
    await db.flush()
    await db.refresh(insight)
    return insight
