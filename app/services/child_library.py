"""
Child Upbringing Library Service
================================
Pre-built templates for Milestones and Activities categorized by age group.
"""

# Age groups: toddler (2-4), young (4-6), middle (7-9), preteen (10-12), teen (13+)

MILESTONE_LIBRARY = [
    # ── Toddler (2-4 years) ──────────────────────────────────────────────────
    {"key": "t_bismillah", "title": "Says 'Bismillah' before eating", "category": "dua", "age_group": "toddler", "target_age_months": 30, "description": "Child independently says Bismillah before meals"},
    {"key": "t_alhamdulillah", "title": "Says 'Alhamdulillah' after eating", "category": "dua", "age_group": "toddler", "target_age_months": 32, "description": ""},
    {"key": "t_right_hand", "title": "Eats with right hand", "category": "akhlaq", "age_group": "toddler", "target_age_months": 36, "description": ""},
    {"key": "t_salam", "title": "Says 'As-salamu alaykum'", "category": "akhlaq", "age_group": "toddler", "target_age_months": 36, "description": ""},
    {"key": "t_allah_one", "title": "Knows Allah is One", "category": "aqeedah", "age_group": "toddler", "target_age_months": 40, "description": "Understands Tawheed in a simple way"},
    {"key": "t_prophet_name", "title": "Knows Prophet Muhammad's ﷺ name", "category": "seerah", "age_group": "toddler", "target_age_months": 42, "description": ""},
    {"key": "t_mimic_salah", "title": "Mimics Sujud in Salah", "category": "salah", "age_group": "toddler", "target_age_months": 24, "description": ""},
    {"key": "t_arabic_alphabet_song", "title": "Sings the Arabic Alphabet", "category": "arabic", "age_group": "toddler", "target_age_months": 48, "description": ""},
    {"key": "t_share_toys", "title": "Shares toys (Sadaqah concept)", "category": "social", "age_group": "toddler", "target_age_months": 48, "description": ""},

    # ── Young (4-6 years) ────────────────────────────────────────────────────
    {"key": "y_fatiha", "title": "Memorizes Surah Al-Fatihah", "category": "quran", "age_group": "young", "target_age_months": 60, "description": "Recites Fatiha from memory"},
    {"key": "y_ikhlas", "title": "Memorizes Surah Al-Ikhlas", "category": "quran", "age_group": "young", "target_age_months": 54, "description": ""},
    {"key": "y_wudu_basics", "title": "Knows basic steps of Wudu", "category": "salah", "age_group": "young", "target_age_months": 60, "description": ""},
    {"key": "y_angels", "title": "Knows about Angels (Jibreel)", "category": "aqeedah", "age_group": "young", "target_age_months": 60, "description": ""},
    {"key": "y_parents_dua", "title": "Dua for Parents", "category": "dua", "age_group": "young", "target_age_months": 65, "description": "Rabbi irhamhuma kama rabbayani sagheera"},
    {"key": "y_respect_elders", "title": "Shows respect to elders", "category": "akhlaq", "age_group": "young", "target_age_months": 60, "description": ""},
    {"key": "y_arabic_letters", "title": "Recognizes Arabic alphabet visually", "category": "arabic", "age_group": "young", "target_age_months": 65, "description": ""},
    {"key": "y_masjid_adab", "title": "Understands Masjid etiquette", "category": "akhlaq", "age_group": "young", "target_age_months": 72, "description": "Quiet in the masjid, walking calmly"},
    {"key": "y_first_salah", "title": "Prays one complete Salah with parent", "category": "salah", "age_group": "young", "target_age_months": 72, "description": ""},
    {"key": "y_five_pillars", "title": "Can list the 5 Pillars of Islam", "category": "aqeedah", "age_group": "young", "target_age_months": 72, "description": ""},

    # ── Middle (7-9 years) ───────────────────────────────────────────────────
    {"key": "m_pray_regularly", "title": "Prays regularly (Starts 5 daily)", "category": "salah", "age_group": "middle", "target_age_months": 84, "description": "Age of commanded prayer"},
    {"key": "m_wudu_perfect", "title": "Performs perfect Wudu independently", "category": "salah", "age_group": "middle", "target_age_months": 84, "description": ""},
    {"key": "m_juz_amma_half", "title": "Memorizes half of Juz Amma", "category": "quran", "age_group": "middle", "target_age_months": 96, "description": ""},
    {"key": "m_quran_reading", "title": "Reads Quran in Arabic independently", "category": "quran", "age_group": "middle", "target_age_months": 100, "description": ""},
    {"key": "m_seerah_makkan", "title": "Knows the Makkan period of Seerah", "category": "seerah", "age_group": "middle", "target_age_months": 108, "description": ""},
    {"key": "m_fast_half_day", "title": "Fasts a half-day in Ramadan", "category": "fiqh", "age_group": "middle", "target_age_months": 96, "description": ""},
    {"key": "m_halal_haram", "title": "Knows basic Halal and Haram foods", "category": "fiqh", "age_group": "middle", "target_age_months": 96, "description": ""},
    {"key": "m_prophets_names", "title": "Can name 10 Prophets from the Quran", "category": "seerah", "age_group": "middle", "target_age_months": 108, "description": ""},
    {"key": "m_truthful", "title": "Practice speaking the truth always", "category": "akhlaq", "age_group": "middle", "target_age_months": 100, "description": ""},

    # ── Pre-teen (10-12 years) ───────────────────────────────────────────────
    {"key": "p_pray_all_fard", "title": "Prays all 5 Fard Salahs", "category": "salah", "age_group": "preteen", "target_age_months": 120, "description": "Consistent with Fard prayers"},
    {"key": "p_fast_ramadan", "title": "Fasts the whole month of Ramadan", "category": "fiqh", "age_group": "preteen", "target_age_months": 132, "description": ""},
    {"key": "p_juz_amma_complete", "title": "Completes memorization of Juz Amma", "category": "quran", "age_group": "preteen", "target_age_months": 132, "description": ""},
    {"key": "p_meaning_fatiha", "title": "Knows translation of Surah Al-Fatihah", "category": "quran", "age_group": "preteen", "target_age_months": 120, "description": ""},
    {"key": "p_seerah_madinan", "title": "Knows the Madinan period of Seerah", "category": "seerah", "age_group": "preteen", "target_age_months": 130, "description": ""},
    {"key": "p_ghusl", "title": "Knows how to perform Ghusl", "category": "fiqh", "age_group": "preteen", "target_age_months": 140, "description": "Important fiqh for coming of age"},
    {"key": "p_articles_faith", "title": "Explains the 6 Articles of Faith", "category": "aqeedah", "age_group": "preteen", "target_age_months": 132, "description": ""},
    {"key": "p_ayat_kursi", "title": "Memorizes Ayatul Kursi", "category": "dua", "age_group": "preteen", "target_age_months": 125, "description": ""},
]

ACTIVITY_LIBRARY = [
    {"key": "morning_dua", "name": "Morning Dua", "category": "dua", "xp": 10, "icon": "🌅", "age_groups": ["toddler", "young", "middle", "preteen", "teen"]},
    {"key": "quran_reading", "name": "Read Quran", "category": "quran", "xp": 25, "icon": "📖", "age_groups": ["young", "middle", "preteen", "teen"]},
    {"key": "quran_listening", "name": "Listen to Quran", "category": "quran", "xp": 15, "icon": "🎧", "age_groups": ["toddler", "young", "middle"]},
    {"key": "salah", "name": "Pray Salah", "category": "salah", "xp": 20, "icon": "🕌", "age_groups": ["young", "middle", "preteen", "teen"]},
    {"key": "salah_mimic", "name": "Join parents in Salah", "category": "salah", "xp": 15, "icon": "🤲", "age_groups": ["toddler", "young"]},
    {"key": "evening_dua", "name": "Evening Adhkar", "category": "dua", "xp": 10, "icon": "🌙", "age_groups": ["toddler", "young", "middle", "preteen", "teen"]},
    {"key": "islamic_story", "name": "Islamic Story", "category": "story", "xp": 15, "icon": "📚", "age_groups": ["toddler", "young", "middle", "preteen"]},
    {"key": "good_deed", "name": "Good Deed", "category": "akhlaq", "xp": 20, "icon": "⭐", "age_groups": ["toddler", "young", "middle", "preteen", "teen"]},
    {"key": "help_family", "name": "Help Family", "category": "akhlaq", "xp": 15, "icon": "🏠", "age_groups": ["toddler", "young", "middle", "preteen", "teen"]},
    {"key": "dua_practice", "name": "Learn a Dua", "category": "dua", "xp": 15, "icon": "🤲", "age_groups": ["toddler", "young", "middle", "preteen", "teen"]},
    {"key": "wudu_practice", "name": "Practice Wudu", "category": "salah", "xp": 15, "icon": "💧", "age_groups": ["young", "middle"]},
    {"key": "sadaqah", "name": "Give Charity (Sadaqah)", "category": "akhlaq", "xp": 25, "icon": "🪙", "age_groups": ["young", "middle", "preteen", "teen"]},
    {"key": "arabic_practice", "name": "Arabic Letters/Words", "category": "arabic", "xp": 15, "icon": "📝", "age_groups": ["toddler", "young", "middle"]},
]

def get_milestone_library(age_group: str | None = None) -> list[dict]:
    if age_group:
        return [m for m in MILESTONE_LIBRARY if m["age_group"] == age_group]
    return MILESTONE_LIBRARY

def get_activity_library(age_group: str | None = None) -> list[dict]:
    if age_group:
        return [a for a in ACTIVITY_LIBRARY if age_group in a["age_groups"]]
    return ACTIVITY_LIBRARY
