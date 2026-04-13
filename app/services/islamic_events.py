"""
Islamic Events Seeder
=====================
Seeds IslamicEvent table with the canonical recurring events.
All dates are Hijri (month, day). duration_days is how many days the event spans.
"""

ISLAMIC_EVENTS_SEED = [
    # ─── Ramadan ────────────────────────────────────────────────────────────────
    {
        "name": "Ramadan begins",
        "name_ar": "بداية رمضان",
        "hijri_month": 9, "hijri_day": 1, "duration_days": 30,
        "event_type": "ramadan",
        "description": "The blessed month of fasting, the month in which the Quran was revealed.",
        "notification_template": "Ramadan Mubarak! The blessed month has begun.",
        "deed_of_day": "Renew your intention for the month. Set a Quran khatam goal.",
    },
    {
        "name": "Laylat ul-Qadr (27th night)",
        "name_ar": "ليلة القدر",
        "hijri_month": 9, "hijri_day": 27, "duration_days": 1,
        "event_type": "blessed_night",
        "description": "The Night of Power — better than a thousand months. Most likely candidate night.",
        "notification_template": "Tonight is the 27th of Ramadan — seek Laylat ul-Qadr with worship.",
        "deed_of_day": "Pray Qiyam al-Layl, recite Quran, make abundant dua.",
    },
    {
        "name": "Last 10 nights of Ramadan begin",
        "name_ar": "العشر الأواخر من رمضان",
        "hijri_month": 9, "hijri_day": 21, "duration_days": 10,
        "event_type": "blessed_night",
        "description": "The Prophet ﷺ would increase his worship in the last 10 nights more than any other time.",
        "notification_template": "The last 10 nights of Ramadan have begun. Seek Laylat ul-Qadr.",
        "deed_of_day": "Increase Quran recitation, night prayer, and dua.",
    },
    # ─── Eid ─────────────────────────────────────────────────────────────────────
    {
        "name": "Eid ul-Fitr",
        "name_ar": "عيد الفطر",
        "hijri_month": 10, "hijri_day": 1, "duration_days": 3,
        "event_type": "eid",
        "description": "The festival of breaking the fast. A day of gratitude and celebration.",
        "notification_template": "Eid Mubarak! Taqabbal Allahu minna wa minkum.",
        "deed_of_day": "Perform Eid prayer. Pay Zakat ul-Fitr if not already done. Visit family.",
    },
    {
        "name": "Eid ul-Adha",
        "name_ar": "عيد الأضحى",
        "hijri_month": 12, "hijri_day": 10, "duration_days": 3,
        "event_type": "eid",
        "description": "The festival of sacrifice, commemorating Prophet Ibrahim's ﷺ submission.",
        "notification_template": "Eid ul-Adha Mubarak! May Allah accept your devotion.",
        "deed_of_day": "Perform Eid prayer. Offer sacrifice (udhiyya) if able.",
    },
    # ─── Dhul Hijjah ──────────────────────────────────────────────────────────────
    {
        "name": "First 10 days of Dhul Hijjah",
        "name_ar": "العشر من ذي الحجة",
        "hijri_month": 12, "hijri_day": 1, "duration_days": 9,
        "event_type": "significant_day",
        "description": "The best days of the year for good deeds. The Prophet ﷺ said no days are better for worship.",
        "notification_template": "The blessed 10 days of Dhul Hijjah have begun!",
        "deed_of_day": "Fast if able. Increase dhikr: Takbeer, Tahmeed, Tahleel, Tasbeeh.",
    },
    {
        "name": "Day of Arafah",
        "name_ar": "يوم عرفة",
        "hijri_month": 12, "hijri_day": 9, "duration_days": 1,
        "event_type": "fasting",
        "description": "The greatest day. Fasting expiates sins of the previous and coming year.",
        "notification_template": "Today is the Day of Arafah — fast and make abundant dua.",
        "deed_of_day": "Fast. Make dua from Dhuhr to Maghrib. Recite Surah al-Kahf.",
    },
    # ─── Islamic New Year ─────────────────────────────────────────────────────────
    {
        "name": "Islamic New Year",
        "name_ar": "رأس السنة الهجرية",
        "hijri_month": 1, "hijri_day": 1, "duration_days": 1,
        "event_type": "significant_day",
        "description": "1 Muharram marks the Hijri New Year, commemorating the migration of the Prophet ﷺ.",
        "notification_template": "Islamic New Year 1447 AH. Reflect and set intentions.",
        "deed_of_day": "Set spiritual goals for the new Hijri year. Review last year's growth.",
    },
    {
        "name": "Day of Ashura",
        "name_ar": "يوم عاشوراء",
        "hijri_month": 1, "hijri_day": 10, "duration_days": 1,
        "event_type": "fasting",
        "description": "The day Allah saved Musa ﷺ from Pharaoh. Fasting expiates the previous year's sins.",
        "notification_template": "Today is Ashura. Fast and also fast the 9th or 11th.",
        "deed_of_day": "Fast on the 9th and 10th (or 10th and 11th) of Muharram.",
    },
    # ─── Rajab ────────────────────────────────────────────────────────────────────
    {
        "name": "Isra wal-Miraj",
        "name_ar": "الإسراء والمعراج",
        "hijri_month": 7, "hijri_day": 27, "duration_days": 1,
        "event_type": "significant_day",
        "description": "The night journey of the Prophet ﷺ from Makkah to Jerusalem and ascension to the heavens.",
        "notification_template": "Tonight marks the Night Journey of the Prophet ﷺ.",
        "deed_of_day": "Reflect on the gift of Salah. Perform additional night prayer.",
    },
    # ─── Sha'ban ──────────────────────────────────────────────────────────────────
    {
        "name": "Shab-e-Barat (Night of Records)",
        "name_ar": "ليلة النصف من شعبان",
        "hijri_month": 8, "hijri_day": 15, "duration_days": 1,
        "event_type": "blessed_night",
        "description": "Mid-Sha'ban night. Scholars differ on its significance; fasting the day after is established.",
        "notification_template": "15th Sha'ban — a night of worship and seeking forgiveness.",
        "deed_of_day": "Seek forgiveness. Consider fasting on the 13th, 14th, and 15th (white days).",
    },
    # ─── Rabi' al-Awwal ───────────────────────────────────────────────────────────
    {
        "name": "Month of Rabi' al-Awwal",
        "name_ar": "ربيع الأول",
        "hijri_month": 3, "hijri_day": 1, "duration_days": 30,
        "event_type": "significant_day",
        "description": "The birth month of the Prophet Muhammad ﷺ. A time to increase Salawat.",
        "notification_template": "Rabi' al-Awwal has begun. Increase your Salawat upon the Prophet ﷺ.",
        "deed_of_day": "Read Seerah. Recite Salawat 100 times today.",
    },
    # ─── Fasting days ─────────────────────────────────────────────────────────────
    {
        "name": "6 days of Shawwal",
        "name_ar": "ست من شوال",
        "hijri_month": 10, "hijri_day": 2, "duration_days": 29,
        "event_type": "fasting",
        "description": "Whoever fasts Ramadan then follows it with 6 days of Shawwal — it is as if he fasted the whole year.",
        "notification_template": "Shawwal has begun. Don't forget the 6 fasts of Shawwal!",
        "deed_of_day": "Fast today if you have not yet completed your 6 Shawwal fasts.",
    },
]


async def seed_islamic_events(db):
    """
    Idempotent seeder: inserts events that don't already exist by name.
    Call from an alembic migration or a startup task.
    """
    from sqlalchemy import select
    from app.models.prayer import IslamicEvent

    existing_names_result = await db.execute(select(IslamicEvent.name))
    existing_names = {row[0] for row in existing_names_result.all()}

    to_insert = [
        IslamicEvent(**e)
        for e in ISLAMIC_EVENTS_SEED
        if e["name"] not in existing_names
    ]

    if to_insert:
        db.add_all(to_insert)
        await db.flush()

    return len(to_insert)
