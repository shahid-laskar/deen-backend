"""
Child Dua Library Service
=========================
Contains pre-seeded duas for teaching children.
"""

DUA_LIBRARY = [
    {
        "key": "before_eating",
        "name": "Before Eating",
        "arabic": "بِسْمِ اللَّهِ",
        "transliteration": "Bismillah",
        "translation": "In the name of Allah",
        "category": "daily",
        "age_groups": ["toddler", "young", "middle", "preteen", "teen"],
        "source": "Abu Dawud 3767",
        "difficulty": "easy",
        "xp": 10
    },
    {
        "key": "after_eating",
        "name": "After Eating",
        "arabic": "الْحَمْدُ لِلَّهِ الَّذِي أَطْعَمَنَا وَسَقَانَا وَجَعَلَنَا مُسْلِمِينَ",
        "transliteration": "Alhamdulillahil-ladhi at'amana wa saqana wa ja'alana Muslimeen",
        "translation": "Praise be to Allah Who has fed us, given us drink, and made us Muslims",
        "category": "daily",
        "age_groups": ["young", "middle", "preteen", "teen"],
        "source": "Abu Dawud 3850",
        "difficulty": "medium",
        "xp": 20
    },
    {
        "key": "waking_up",
        "name": "Waking Up",
        "arabic": "الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ",
        "transliteration": "Alhamdulillahil-ladhi ahyana ba'da ma amatana wa ilaihin-nushur",
        "translation": "All praise is due to Allah who brought us back to life after He has caused us to die, and to Him is the return",
        "category": "daily",
        "age_groups": ["young", "middle", "preteen", "teen"],
        "source": "Bukhari 6312",
        "difficulty": "medium",
        "xp": 20
    },
    {
        "key": "before_sleeping",
        "name": "Before Sleeping",
        "arabic": "بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا",
        "transliteration": "Bismika Allahumma amutu wa ahya",
        "translation": "In Your name, O Allah, I die and I live",
        "category": "daily",
        "age_groups": ["toddler", "young", "middle", "preteen", "teen"],
        "source": "Bukhari 6312",
        "difficulty": "easy",
        "xp": 15
    },
    {
        "key": "parents",
        "name": "For Parents",
        "arabic": "رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا",
        "transliteration": "Rabbir-hamhuma kama rabbayani sagheera",
        "translation": "My Lord, have mercy upon them as they brought me up [when I was] small",
        "category": "special",
        "age_groups": ["young", "middle", "preteen", "teen"],
        "source": "Quran 17:24",
        "difficulty": "medium",
        "xp": 30
    },
    {
        "key": "knowledge",
        "name": "For Knowledge",
        "arabic": "رَبِّ زِدْنِي عِلْمًا",
        "transliteration": "Rabbi zidni 'ilma",
        "translation": "My Lord, increase me in knowledge",
        "category": "special",
        "age_groups": ["toddler", "young", "middle", "preteen", "teen"],
        "source": "Quran 20:114",
        "difficulty": "easy",
        "xp": 15
    },
    {
        "key": "entering_home",
        "name": "Entering Home",
        "arabic": "بِسْمِ اللَّهِ وَلَجْنَا، وَبِسْمِ اللَّهِ خَرَجْنَا، وَعَلَى رَبِّنَا تَوَكَّلْنَا",
        "transliteration": "Bismillahi walajna, wa bismillahi kharajna, wa 'ala Rabbina tawakkalna",
        "translation": "In the name of Allah we enter, in the name of Allah we leave, and upon our Lord we depend",
        "category": "daily",
        "age_groups": ["middle", "preteen", "teen"],
        "source": "Abu Dawud 5096",
        "difficulty": "hard",
        "xp": 40
    },
    {
        "key": "sneezing",
        "name": "When Sneezing",
        "arabic": "الْحَمْدُ لِلَّهِ",
        "transliteration": "Alhamdulillah",
        "translation": "All praise is due to Allah",
        "category": "daily",
        "age_groups": ["toddler", "young", "middle", "preteen", "teen"],
        "source": "Bukhari 6224",
        "difficulty": "easy",
        "xp": 10
    },
]

def get_dua_library(age_group: str | None = None, category: str | None = None) -> list[dict]:
    res = DUA_LIBRARY
    if age_group:
        res = [d for d in res if age_group in d["age_groups"]]
    if category:
        res = [d for d in res if d["category"] == category]
    return res

def get_dua_by_key(key: str) -> dict | None:
    for d in DUA_LIBRARY:
        if d["key"] == key:
            return d
    return None
