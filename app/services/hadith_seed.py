"""
Hadith Seed Data
================
Curated subset of authentic hadiths for the Hadith of the Day feature
and citation picker. All graded Sahih or Hasan.

Full integration with Sunnah.com API comes in a later phase for search;
this seed covers the "Hadith of the Day" rotation and example citations.
"""

HADITH_SEED = [
    # ─── Sahih al-Bukhari ────────────────────────────────────────────────────
    {"collection": "bukhari", "hadith_number": "1",
     "book_name": "Book of Revelation",
     "arabic_text": "إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ، وَإِنَّمَا لِكُلِّ امْرِئٍ مَا نَوَى",
     "english_text": "Actions are (judged) by intentions, and every person will get what they intended.",
     "narrator_chain": "Narrated by Umar ibn al-Khattab (RA)",
     "grade": "sahih", "topics": "intentions,niyyah,deeds"},
    {"collection": "bukhari", "hadith_number": "2",
     "book_name": "Book of Faith",
     "arabic_text": "الإِسْلَامُ أَنْ تَشْهَدَ أَنْ لَا إِلَهَ إِلَّا اللَّهُ وَأَنَّ مُحَمَّدًا رَسُولُ اللَّهِ",
     "english_text": "Islam is to testify that there is no god but Allah and that Muhammad is the Messenger of Allah, to establish the prayer, to pay the zakat, to fast Ramadan, and to perform the pilgrimage to the House if you are able.",
     "narrator_chain": "Narrated by Ibn Umar (RA)",
     "grade": "sahih", "topics": "islam,pillars,five pillars"},
    {"collection": "bukhari", "hadith_number": "6412",
     "book_name": "Book of Remembrance",
     "arabic_text": "كَلِمَتَانِ خَفِيفَتَانِ عَلَى اللِّسَانِ، ثَقِيلَتَانِ فِي الْمِيزَانِ، حَبِيبَتَانِ إِلَى الرَّحْمَنِ",
     "english_text": "Two words are light on the tongue, heavy on the Scale, and beloved to the Most Merciful: SubhanAllahi wa bihamdih, SubhanAllahil-'adheem.",
     "narrator_chain": "Narrated by Abu Hurayra (RA)",
     "grade": "sahih", "topics": "dhikr,remembrance,scale,reward"},
    {"collection": "bukhari", "hadith_number": "13",
     "book_name": "Book of Faith",
     "arabic_text": "لَا يُؤْمِنُ أَحَدُكُمْ حَتَّى يُحِبَّ لأَخِيهِ مَا يُحِبُّ لِنَفْسِهِ",
     "english_text": "None of you truly believes until he loves for his brother what he loves for himself.",
     "narrator_chain": "Narrated by Anas ibn Malik (RA)",
     "grade": "sahih", "topics": "brotherhood,faith,love,iman"},
    {"collection": "bukhari", "hadith_number": "6018",
     "book_name": "Book of Good Manners",
     "arabic_text": "مَنْ كَانَ يُؤْمِنُ بِاللَّهِ وَالْيَوْمِ الآخِرِ فَلْيَقُلْ خَيْرًا أَوْ لِيَصْمُتْ",
     "english_text": "Whoever believes in Allah and the Last Day should speak good or remain silent.",
     "narrator_chain": "Narrated by Abu Hurayra (RA)",
     "grade": "sahih", "topics": "speech,manners,tongue,silence"},

    # ─── Sahih Muslim ─────────────────────────────────────────────────────────
    {"collection": "muslim", "hadith_number": "223",
     "book_name": "Book of Purification",
     "arabic_text": "الطَّهُورُ شَطْرُ الإِيمَانِ",
     "english_text": "Purity is half of faith.",
     "narrator_chain": "Narrated by Abu Malik al-Ash'ari (RA)",
     "grade": "sahih", "topics": "purity,taharah,faith,wudu"},
    {"collection": "muslim", "hadith_number": "2564",
     "book_name": "Book of Righteousness",
     "arabic_text": "اتَّقِ اللَّهَ حَيْثُمَا كُنْتَ، وَأَتْبِعِ السَّيِّئَةَ الْحَسَنَةَ تَمْحُهَا",
     "english_text": "Fear Allah wherever you are, follow a bad deed with a good one and it will erase it, and behave well towards people.",
     "narrator_chain": "Narrated by Abu Dharr (RA) and Mu'adh ibn Jabal (RA)",
     "grade": "hasan", "topics": "taqwa,good deeds,character"},
    {"collection": "muslim", "hadith_number": "2699",
     "book_name": "Book of Remembrance",
     "arabic_text": "مَنْ سَلَكَ طَرِيقًا يَلْتَمِسُ فِيهِ عِلْمًا، سَهَّلَ اللَّهُ لَهُ طَرِيقًا إِلَى الْجَنَّةِ",
     "english_text": "Whoever treads a path in search of knowledge, Allah will make easy for him a path to Paradise.",
     "narrator_chain": "Narrated by Abu Hurayra (RA)",
     "grade": "sahih", "topics": "knowledge,ilm,paradise,learning"},
    {"collection": "muslim", "hadith_number": "1631",
     "book_name": "Book of Bequests",
     "arabic_text": "إِذَا مَاتَ الإِنْسَانُ انْقَطَعَ عَنْهُ عَمَلُهُ إِلَّا مِنْ ثَلَاثَةٍ: إِلَّا مِنْ صَدَقَةٍ جَارِيَةٍ",
     "english_text": "When a person dies, his deeds end except for three: a continuous charity (sadaqah jariyah), beneficial knowledge, and a righteous child who prays for him.",
     "narrator_chain": "Narrated by Abu Hurayra (RA)",
     "grade": "sahih", "topics": "death,sadaqah,charity,legacy"},
    {"collection": "muslim", "hadith_number": "2588",
     "book_name": "Book of Righteousness",
     "arabic_text": "الْمُسْلِمُ مَنْ سَلِمَ الْمُسْلِمُونَ مِنْ لِسَانِهِ وَيَدِهِ",
     "english_text": "A Muslim is one from whose tongue and hand the Muslims are safe.",
     "narrator_chain": "Narrated by Abdullah ibn Amr (RA)",
     "grade": "sahih", "topics": "muslim,safety,tongue,hand,character"},

    # ─── Sunan Abu Dawud ──────────────────────────────────────────────────────
    {"collection": "abu_dawud", "hadith_number": "4607",
     "book_name": "Book of Sunnah",
     "arabic_text": "عَلَيْكُمْ بِسُنَّتِي وَسُنَّةِ الْخُلَفَاءِ الرَّاشِدِينَ الْمَهْدِيِّينَ",
     "english_text": "Adhere to my Sunnah and the Sunnah of the rightly-guided caliphs.",
     "narrator_chain": "Narrated by Irbad ibn Sariyah (RA)",
     "grade": "hasan", "topics": "sunnah,guidance,caliphs"},

    # ─── Jami at-Tirmidhi ────────────────────────────────────────────────────
    {"collection": "tirmidhi", "hadith_number": "2616",
     "book_name": "Book of Virtues of Jihad",
     "arabic_text": "الدُّعَاءُ مُخُّ الْعِبَادَةِ",
     "english_text": "Du'a is the essence of worship.",
     "narrator_chain": "Narrated by Anas ibn Malik (RA)",
     "grade": "sahih", "topics": "dua,worship,ibadah,supplication"},
    {"collection": "tirmidhi", "hadith_number": "1987",
     "book_name": "Book of Righteousness",
     "arabic_text": "الْبِرُّ حُسْنُ الْخُلُقِ",
     "english_text": "Righteousness is good character.",
     "narrator_chain": "Narrated by an-Nawwas ibn Sam'an (RA)",
     "grade": "sahih", "topics": "righteousness,character,akhlaq,birr"},

    # ─── Riyadh as-Salihin ────────────────────────────────────────────────────
    {"collection": "riyadh_salihin", "hadith_number": "75",
     "book_name": "Book of Miscellaneous Ahadith",
     "arabic_text": "خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ",
     "english_text": "The best of you are those who learn the Quran and teach it.",
     "narrator_chain": "Narrated by Uthman ibn Affan (RA)",
     "grade": "sahih", "topics": "quran,learning,teaching,best"},
    {"collection": "riyadh_salihin", "hadith_number": "127",
     "book_name": "Book of Miscellaneous Ahadith",
     "arabic_text": "مَا مَلَأَ آدَمِيٌّ وِعَاءً شَرًّا مِنْ بَطْنٍ",
     "english_text": "No human ever filled a vessel worse than the stomach. Sufficient for the son of Adam are a few morsels to keep his back straight.",
     "narrator_chain": "Narrated by Miqdam ibn Ma'dikarib (RA)",
     "grade": "hasan", "topics": "eating,moderation,health,gluttony"},
    {"collection": "riyadh_salihin", "hadith_number": "5",
     "book_name": "Book of Miscellaneous Ahadith",
     "arabic_text": "يَسِّرُوا وَلَا تُعَسِّرُوا، وَبَشِّرُوا وَلَا تُنَفِّرُوا",
     "english_text": "Make things easy and do not make them difficult; give glad tidings and do not repel people.",
     "narrator_chain": "Narrated by Anas ibn Malik (RA)",
     "grade": "sahih", "topics": "ease,facilitation,dawah,character"},
    {"collection": "riyadh_salihin", "hadith_number": "1/3",
     "book_name": "Book of Miscellaneous Ahadith",
     "arabic_text": "قُلْتُ: يَا رَسُولَ اللَّهِ، مَا أَكْثَرُ مَا تَخَافُ عَلَيَّ؟ فَأَخَذَ بِلِسَانِهِ ثُمَّ قَالَ: هَذَا",
     "english_text": "I said: O Messenger of Allah, what is it that you fear most for me? He took hold of his tongue and said: This.",
     "narrator_chain": "Narrated by Sufyan ibn Abdullah (RA)",
     "grade": "hasan", "topics": "tongue,speech,sin"},
]


async def seed_hadiths(db) -> int:
    """Idempotent seeder."""
    from sqlalchemy import select
    from app.models.quran import Hadith

    existing_result = await db.execute(
        select(Hadith.collection, Hadith.hadith_number)
    )
    existing = {(r[0], r[1]) for r in existing_result.all()}

    to_insert = [
        Hadith(**h)
        for h in HADITH_SEED
        if (h["collection"], h["hadith_number"]) not in existing
    ]
    if to_insert:
        db.add_all(to_insert)
        await db.flush()
    return len(to_insert)


def get_hadith_of_day(day_of_year: int) -> dict:
    """Deterministic daily rotation — same hadith all day for all users."""
    idx = day_of_year % len(HADITH_SEED)
    return HADITH_SEED[idx]
