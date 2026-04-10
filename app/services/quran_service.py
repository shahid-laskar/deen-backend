"""
Quran Service
=============
- Quran.com API v4 integration for verses, surahs, audio
- SM-2 spaced repetition for Hifz scheduling
"""

from datetime import date, timedelta
from typing import Optional

import httpx

from app.core.config import settings


# ─── Quran API ────────────────────────────────────────────────────────────────

async def fetch_surah_list() -> list[dict]:
    """Fetch all 114 surahs with metadata."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.QURAN_API_URL}/chapters?language=en")
        resp.raise_for_status()
        return resp.json()["chapters"]


async def fetch_surah(
    surah_number: int,
    translation_id: int = 131,  # Saheeh International (default)
) -> dict:
    """Fetch a surah with translation."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/verses/by_chapter/{surah_number}",
            params={
                "language": "en",
                "words": "true",
                "translations": str(translation_id),
                "per_page": 300,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_ayah(surah: int, ayah: int, translation_id: int = 131) -> dict:
    """Fetch a single ayah with translation and audio."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/verses/by_key/{surah}:{ayah}",
            params={
                "language": "en",
                "words": "true",
                "translations": str(translation_id),
                "audio": "1",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def search_quran(query: str, language: str = "en") -> dict:
    """Search Quran by keyword."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/search",
            params={"q": query, "language": language, "size": 20},
        )
        resp.raise_for_status()
        return resp.json()


# ─── SM-2 Spaced Repetition ───────────────────────────────────────────────────

def sm2_next_review(
    quality: int,           # 0–5 rating
    ease_factor: float,     # current ease factor (starts at 2.5)
    interval_days: int,     # current interval
    review_count: int,      # how many times reviewed
) -> tuple[float, int, date]:
    """
    SM-2 algorithm: returns (new_ease_factor, new_interval_days, next_review_date).
    quality: 0=blackout, 1=wrong, 2=hard, 3=ok, 4=good, 5=perfect
    """
    if quality < 2:
        # Total blackout/wrong — reset interval, preserve EF
        new_interval = 1
        new_ef = ease_factor
    else:
        # quality 2–5: update EF and advance interval
        new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)

        if review_count == 0:
            new_interval = 1
        elif review_count == 1:
            new_interval = 6
        else:
            new_interval = round(interval_days * new_ef)

    next_date = date.today() + timedelta(days=new_interval)
    return new_ef, new_interval, next_date


# ─── Dua Dataset ──────────────────────────────────────────────────────────────
# Static duas — in production these would be in a JSON file / DB seed.
# Keys are stable identifiers referenced by DuaFavorite.dua_key.

DUA_LIBRARY: list[dict] = [
    # Morning
    {
        "key": "morning_waking",
        "category": "morning_evening",
        "title": "Upon waking",
        "arabic": "الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ",
        "transliteration": "Alhamdu lillahil-ladhi ahyana ba'da ma amatana wa ilayhin-nushoor",
        "translation": "All praise is for Allah who gave us life after having taken it from us and unto Him is the Resurrection.",
        "reference": "Bukhari 6312",
    },
    {
        "key": "morning_supplication",
        "category": "morning_evening",
        "title": "Morning supplication",
        "arabic": "اللَّهُمَّ بِكَ أَصْبَحْنَا وَبِكَ أَمْسَيْنَا وَبِكَ نَحْيَا وَبِكَ نَمُوتُ وَإِلَيْكَ النُّشُورُ",
        "transliteration": "Allahumma bika asbahna wa bika amsayna wa bika nahya wa bika namootu wa ilaykan-nushoor",
        "translation": "O Allah, by Your leave we have reached the morning and by Your leave we have reached the evening, by Your leave we live and die and unto You is our resurrection.",
        "reference": "Abu Dawud 5068, Tirmidhi 3391",
    },
    # Evening
    {
        "key": "evening_supplication",
        "category": "morning_evening",
        "title": "Evening supplication",
        "arabic": "اللَّهُمَّ بِكَ أَمْسَيْنَا وَبِكَ أَصْبَحْنَا وَبِكَ نَحْيَا وَبِكَ نَمُوتُ وَإِلَيْكَ الْمَصِيرُ",
        "transliteration": "Allahumma bika amsayna wa bika asbahna wa bika nahya wa bika namootu wa ilaykal-maseer",
        "translation": "O Allah, by Your leave we have reached the evening and by Your leave we have reached the morning, by Your leave we live and die and unto You is our return.",
        "reference": "Abu Dawud 5068",
    },
    # Travel
    {
        "key": "travel_start",
        "category": "travel",
        "title": "Beginning a journey",
        "arabic": "اللَّهُ أَكْبَرُ، اللَّهُ أَكْبَرُ، اللَّهُ أَكْبَرُ، سُبْحَانَ الَّذِي سَخَّرَ لَنَا هَذَا",
        "transliteration": "Allahu Akbar (x3), Subhanal-ladhi sakhkhara lana hadha",
        "translation": "Allah is the greatest (x3). How perfect He is, the One Who has placed this (transport) at our service.",
        "reference": "Muslim 1342",
    },
    # Eating
    {
        "key": "before_eating",
        "category": "food",
        "title": "Before eating",
        "arabic": "بِسْمِ اللَّهِ",
        "transliteration": "Bismillah",
        "translation": "In the name of Allah.",
        "reference": "Bukhari 5376",
    },
    {
        "key": "after_eating",
        "category": "food",
        "title": "After eating",
        "arabic": "الْحَمْدُ لِلَّهِ الَّذِي أَطْعَمَنِي هَذَا وَرَزَقَنِيهِ مِنْ غَيْرِ حَوْلٍ مِنِّي وَلَا قُوَّةٍ",
        "transliteration": "Alhamdu lillahil-ladhi at'amani hadha wa razaqanihi min ghayri hawlin minni wa la quwwah",
        "translation": "All praise is for Allah who fed me this and provided it for me without any strength or power on my part.",
        "reference": "Abu Dawud 4023",
    },
    # Anxiety / Distress
    {
        "key": "anxiety_dua",
        "category": "distress",
        "title": "For anxiety and sorrow",
        "arabic": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ، وَالْعَجْزِ وَالْكَسَلِ",
        "transliteration": "Allahumma inni a'udhu bika minal-hammi wal-hazan, wal-'ajzi wal-kasal",
        "translation": "O Allah, I seek refuge with You from worry and grief, from incapacity and laziness.",
        "reference": "Bukhari 6363",
    },
    # Istikhara
    {
        "key": "istikhara",
        "category": "guidance",
        "title": "Istikhara (seeking guidance)",
        "arabic": "اللَّهُمَّ إِنِّي أَسْتَخِيرُكَ بِعِلْمِكَ وَأَسْتَقْدِرُكَ بِقُدْرَتِكَ وَأَسْأَلُكَ مِنْ فَضْلِكَ الْعَظِيمِ",
        "transliteration": "Allahumma inni astakhiruka bi'ilmika, wa astaqdiruka bi-qudratika, wa as'aluka min fadlikal-'adheem",
        "translation": "O Allah, I seek Your guidance by virtue of Your knowledge, and I seek ability by virtue of Your power, and I ask You of Your great bounty.",
        "reference": "Bukhari 6382",
    },
]


def get_duas_by_category(category: Optional[str] = None) -> list[dict]:
    if category:
        return [d for d in DUA_LIBRARY if d["category"] == category]
    return DUA_LIBRARY


def get_dua_by_key(key: str) -> Optional[dict]:
    return next((d for d in DUA_LIBRARY if d["key"] == key), None)
