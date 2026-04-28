# app/services/child_curriculum.py

CURRICULUM = {
    "toddler": [
        {
            "subject": "Aqeedah",
            "topics": [
                "Allah made everything",
                "Allah sees me",
                "Allah loves me",
                "Who is Prophet Muhammad (saw)?"
            ]
        },
        {
            "subject": "Akhlaq",
            "topics": [
                "Saying Bismillah before eating",
                "Saying Alhamdulillah after eating",
                "Saying Salam to everyone",
                "Sharing toys",
                "Being kind to animals"
            ]
        }
    ],
    "young": [
        {
            "subject": "Aqeedah",
            "topics": [
                "The 5 Pillars of Islam",
                "The 6 Articles of Faith",
                "The Names of Allah (Asma-ul-Husna) - First 10",
                "The Angels and their duties"
            ]
        },
        {
            "subject": "Salah",
            "topics": [
                "How to perform Wudu",
                "The 5 daily prayers (names and times)",
                "Prayer positions (Qiyam, Ruku, Sujud)",
                "Short surahs for salah (Al-Fatihah, Al-Ikhlas)"
            ]
        },
        {
            "subject": "Seerah",
            "topics": [
                "Birth of Prophet Muhammad (saw)",
                "Halimah Sadia (The wet nurse)",
                "First revelation at Cave Hira",
                "The Hijrah to Madinah"
            ]
        }
    ],
    "middle": [
        {
            "subject": "Aqeedah",
            "topics": [
                "Tawheed (Oneness of Allah) in depth",
                "The Day of Judgement",
                "Prophets of Allah (Ulul 'Azm)",
                "Understanding Qadar (Divine Decree)"
            ]
        },
        {
            "subject": "Salah",
            "topics": [
                "Conditions of Salah (Shurut)",
                "Fard acts of Wudu and Salah",
                "Sunnah acts of Salah",
                "How to pray in congregation (Jama'ah)"
            ]
        },
        {
            "subject": "Seerah",
            "topics": [
                "The boycott of Banu Hashim",
                "The Year of Sorrow",
                "Al-Isra wal-Mi'raj (The Night Journey)",
                "The Battle of Badr and Uhud"
            ]
        },
        {
            "subject": "Quran",
            "topics": [
                "Rules of Tajweed (Makharij)",
                "Rules of Nun Sakinah and Tanween",
                "Tafsir of Surah Al-Fatihah",
                "Tafsir of Al-Mu'awwidhatayn (Falaq & Nas)"
            ]
        }
    ],
    "preteen": [
        {
            "subject": "Fiqh",
            "topics": [
                "Ghusl (Purification) - When it becomes mandatory",
                "Fiqh of Fasting (Ramadan rules)",
                "Understanding Zakat basics",
                "Halal and Haram foods"
            ]
        },
        {
            "subject": "Seerah & History",
            "topics": [
                "The Treaty of Hudaybiyyah",
                "The Conquest of Makkah",
                "The Farewell Sermon",
                "The Rightly Guided Caliphs (Khulafa Ar-Rashidun)"
            ]
        },
        {
            "subject": "Akhlaq",
            "topics": [
                "Lowering the gaze",
                "Respecting parents (Birr al-Walidayn)",
                "The danger of backbiting (Gheebah) and lying",
                "Choosing righteous friends"
            ]
        }
    ]
}

def get_curriculum(age_group: str) -> list:
    """Returns curriculum for a specific age group. Defaults to young if not found."""
    return CURRICULUM.get(age_group.lower(), CURRICULUM["young"])
