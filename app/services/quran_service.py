from datetime import date, timedelta
from typing import Optional

import httpx

from app.core.config import settings


# ─── Static metadata lists ────────────────────────────────────────────────────

RECITERS_LIST = [
    {"id": 7,   "name": "Mishari Rashid Al-Afasy", "style": "Murattal"},
    {"id": 1,   "name": "AbdulBaset AbdulSamad",   "style": "Murattal"},
    {"id": 5,   "name": "Mahmoud Khalil Al-Husary", "style": "Murattal"},
    {"id": 3,   "name": "Mohamed Siddiq Al-Minshawi", "style": "Murattal"},
    {"id": 10,  "name": "Yasser Ad-Dossari",        "style": "Murattal"},
    {"id": 11,  "name": "Saad Al-Ghamdi",           "style": "Murattal"},
    {"id": 12,  "name": "Ali Abdur-Rahman Al-Huthaify", "style": "Murattal"},
    {"id": 4,   "name": "Nasser Al-Qatami",         "style": "Murattal"},
]

TRANSLATIONS_LIST = [
    {"id": 20,  "language": "en", "author": "Saheeh International"},
    {"id": 131, "language": "en", "author": "Clear Quran (Dr. Mustafa Khattab)"},
    {"id": 85,  "language": "en", "author": "Pickthall"},
    {"id": 95,  "language": "en", "author": "Yusuf Ali"},
    {"id": 101, "language": "en", "author": "Dr. Mustafa Khattab"},
    {"id": 149, "language": "en", "author": "T.B. Irving"},
    {"id": 167, "language": "en", "author": "The Monotheist Group"},
    {"id": 22,  "language": "ur", "author": "Maulana Fateh Muhammad Jalandhari"},
    {"id": 54,  "language": "tr", "author": "Nureddin Uzunoglu"},
    {"id": 31,  "language": "fr", "author": "Hamidullah"},
]



async def fetch_surah_list() -> list[dict]:
    """Fetch all 114 surahs with metadata."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.QURAN_API_URL}/chapters?language=en")
        resp.raise_for_status()
        return resp.json()["chapters"]


import json
import os

CLEAR_QURAN_CACHE = None

def get_local_clear_quran(surah_number: int):
    global CLEAR_QURAN_CACHE
    if CLEAR_QURAN_CACHE is None:
        try:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "clear_quran.json")
            with open(path, "r", encoding="utf-8") as f:
                CLEAR_QURAN_CACHE = json.load(f).get("data", {}).get("surahs", [])
        except Exception:
            return None
    for s in CLEAR_QURAN_CACHE:
        if s["number"] == surah_number:
            return s.get("ayahs", [])
    return None

def override_translations(data: dict, surah_number: int):
    local_ayahs = get_local_clear_quran(surah_number)
    if not local_ayahs:
        return data
    ayah_lookup = { a["numberInSurah"]: a["text"] for a in local_ayahs }
    if "verses" in data:
        for v in data["verses"]:
            ayah_num = int(v["verse_key"].split(":")[1])
            if ayah_num in ayah_lookup:
                if not v.get("translations"):
                    v["translations"] = [{"text": ""}]
                v["translations"][0]["text"] = ayah_lookup[ayah_num]
    return data

def override_ayah_translation(data: dict, surah_number: int, ayah_number: int):
    local_ayahs = get_local_clear_quran(surah_number)
    if not local_ayahs:
        return data
    for a in local_ayahs:
        if a["numberInSurah"] == ayah_number:
            if "verse" in data:
                if not data["verse"].get("translations"):
                    data["verse"]["translations"] = [{"text": ""}]
                data["verse"]["translations"][0]["text"] = a["text"]
            return data
    return data

async def fetch_surah(
    surah_number: int,
    translation_id: int = 20,  # Saheeh International (20) Default
    reciter_id: int = 7,       # Alafasy Default
) -> dict:
    """Fetch a surah with translation."""
    actual_translation_id = 20 if translation_id == 131 else translation_id
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/verses/by_chapter/{surah_number}",
            params={
                "language": "en",
                "words": "true",
                "translations": str(actual_translation_id),
                "fields": "text_uthmani,text_imlaei",
                "audio": str(reciter_id),
                "per_page": 300,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if translation_id == 131:
            data = override_translations(data, surah_number)
        return data


async def fetch_ayah(surah: int, ayah: int, translation_id: int = 20) -> dict:
    """Fetch a single ayah with translation and audio."""
    actual_translation_id = 20 if translation_id == 131 else translation_id
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/verses/by_key/{surah}:{ayah}",
            params={
                "language": "en",
                "words": "true",
                "translations": str(actual_translation_id),
                "fields": "text_uthmani,text_imlaei",
                "audio": "1",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if translation_id == 131:
            data = override_ayah_translation(data, surah, ayah)
        return data


async def search_quran(query: str, language: str = "en", size: int = 50, page: int = 1) -> dict:
    """Search Quran by keyword."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/search",
            params={"q": query, "language": language, "size": size, "page": page},
        )
        resp.raise_for_status()
        return resp.json()

async def fetch_tafsir(surah: int, ayah: int, tafsir_id: int = 169) -> dict:
    """Fetch tafsir (Ibn Kathir English default 169) for a specific ayah."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/tafsirs/{tafsir_id}/by_ayah/{surah}:{ayah}",
            params={"language": "en"}
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_juz(juz_number: int, translation_id: int = 20) -> dict:
    """Fetch all verses in a juz (1-30) with translation."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/verses/by_juz/{juz_number}",
            params={
                "language": "en",
                "words": "true",
                "translations": str(translation_id),
                "fields": "text_uthmani",
                "per_page": 300,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_page(page_number: int, translation_id: int = 20) -> dict:
    """Fetch all verses on a Mushaf page (1-604) with translation."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/verses/by_page/{page_number}",
            params={
                "language": "en",
                "words": "true",
                "translations": str(translation_id),
                "fields": "text_uthmani",
                "per_page": 50,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_word_by_word(surah: int, ayah: int) -> dict:
    """Fetch word-level breakdown with transliteration and translation."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.QURAN_API_URL}/verses/by_key/{surah}:{ayah}",
            params={
                "language": "en",
                "words": "true",
                "word_fields": "text_uthmani,transliteration,translation,audio_url",
                "word_translation_language": "en",
                "fields": "text_uthmani",
            },
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
