"""
Cycle-Sync Ibadah Service
==========================
Returns phase-appropriate worship recommendations for the female module.
Based on established Islamic scholarly positions on what is permitted
and recommended during different phases.

Phases:
  hayd       — menstruation
  nifas      — post-natal bleeding (same rules as hayd)
  istihadah  — irregular/prolonged bleeding (can pray + fast)
  tuhr       — purity (full ibadah)

NOTE: This module gives lifestyle/wellness recommendations only.
Specific rulings for edge cases always point users to scholars.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class IbadahRecommendation:
    phase: str
    permitted: list[str]
    not_permitted: list[str]
    recommended_now: list[str]
    dhikr_suggestions: list[str]
    quran_engagement: list[str]  # what is still possible without physical mushaf
    wellness_tips: list[str]
    motivational_reminder: str


PHASE_RECOMMENDATIONS: dict[str, IbadahRecommendation] = {
    "hayd": IbadahRecommendation(
        phase="hayd",
        permitted=[
            "Dhikr (remembrance of Allah)",
            "Dua (supplication — no restriction)",
            "Listening to Quran",
            "Sending Salawat on the Prophet ﷺ",
            "Istighfar (seeking forgiveness)",
            "Islamic study and learning",
            "Charity and sadaqah",
            "Acts of kindness and service",
            "Learning about Islam",
            "Tasbeeh, Tahmeed, Takbeer",
        ],
        not_permitted=[
            "Salah (obligatory or voluntary)",
            "Fasting (Ramadan fasts must be made up)",
            "Tawaf around the Kaaba",
            "Entering the masjid (according to most scholars)",
            "Touching the mushaf directly (scholarly difference — refer to your madhab)",
            "Reciting Quran from memory (scholarly difference — refer to your madhab)",
        ],
        recommended_now=[
            "Make extensive dua — the door of dua is always open",
            "Keep a dhikr counter — count your tasbeeh",
            "Listen to Quran recitation and contemplate the meanings",
            "Read Islamic books, biographies of the Sahabiyat",
            "Give sadaqah — even a smile is charity",
            "Make plans for extra ibadah when you return to tuhr",
        ],
        dhikr_suggestions=[
            "SubhanAllah × 33, Alhamdulillah × 33, Allahu Akbar × 34",
            "Astaghfirullah al-Adheem × 100",
            "La ilaha illa Anta subhanaka inni kuntu minaz-zalimeen",
            "Allahumma salli 'ala Muhammad × 100",
            "HasbunAllahu wa ni'mal wakeel",
        ],
        quran_engagement=[
            "Listen to your favourite reciters on repeat",
            "Watch tafsir lessons (e.g. Nouman Ali Khan, Sheikh Dr Yasir Qadhi)",
            "Study Arabic vocabulary from the Quran",
            "Memorise duas from the Quran by meaning",
            "Journal reflections on ayahs you listen to",
        ],
        wellness_tips=[
            "Stay hydrated — especially important during this time",
            "Gentle movement and stretching can ease cramps",
            "Iron-rich foods: spinach, lentils, red meat (if you eat it)",
            "Rest — your body is doing important work",
            "Use this as a planning time for the next cycle's ibadah goals",
        ],
        motivational_reminder=(
            "The Prophet ﷺ said: 'Whoever makes wudu and does it properly, "
            "then says Subhanaka Allahumma wa bihamdika…' — but remember: "
            "Allah knows your sincere intention. Your dua and dhikr during "
            "this time carry full reward. Aisha ؓ continued to serve the "
            "Prophet ﷺ and engage in knowledge even during her cycles. "
            "This is a time of rest and renewed intention, not disconnection."
        ),
    ),

    "istihadah": IbadahRecommendation(
        phase="istihadah",
        permitted=[
            "Salah — you must pray after making wudu for each prayer",
            "Fasting — fully permitted",
            "Reading and touching the Quran",
            "Entering the masjid",
            "All forms of dhikr and dua",
            "Tawaf (according to most scholars)",
        ],
        not_permitted=[],  # No restrictions — full ibadah
        recommended_now=[
            "Perform extra voluntary prayers (Sunnah, Nawafil)",
            "Increase Quran recitation — this is a full ibadah period",
            "Attend Halaqas and Islamic study circles",
            "Fast voluntary fasts (Mondays, Thursdays, White Days)",
        ],
        dhikr_suggestions=[
            "Recite the morning and evening adhkar in full",
            "SubhanAllah × 100 after Fajr",
            "Allahu Akbar × 100 before sleep",
        ],
        quran_engagement=[
            "Follow your Hifz plan — all recitation is permitted",
            "Set a daily Quran reading target",
            "Review pages you have memorised",
        ],
        wellness_tips=[
            "Consult a doctor if bleeding is prolonged — health is a trust from Allah",
            "Make wudu fresh for each obligatory prayer",
            "Eat iron-rich foods to support energy levels",
        ],
        motivational_reminder=(
            "The scholars have ruled that a woman experiencing istihadah "
            "performs wudu for each prayer and prays normally. "
            "Your full ibadah doors are open — use this time to build "
            "closeness to Allah. 'And Allah loves those who keep themselves "
            "pure and clean.' (Quran 2:222)"
        ),
    ),

    "tuhr": IbadahRecommendation(
        phase="tuhr",
        permitted=["All acts of worship — full ibadah, alhamdulillah"],
        not_permitted=[],
        recommended_now=[
            "Establish the 5 daily prayers with khushu (focus)",
            "Add the rawatib Sunnah prayers: 12 raka'at per day",
            "Pray Tahajjud in the last third of the night",
            "Set a Quran recitation goal for this period",
            "Fast on Mondays and Thursdays (Sunnah)",
            "Fast the White Days (13th, 14th, 15th of Islamic month)",
            "Make istikharah for any important decisions",
            "Attend the masjid for Fajr and Isha when possible",
        ],
        dhikr_suggestions=[
            "Full morning and evening adhkar (from Hisnul Muslim)",
            "Salawat before and after adhan",
            "100 × SubhanAllah al-Adheem wa bihamdihi after each prayer",
            "Read Ayat al-Kursi after every obligatory prayer",
        ],
        quran_engagement=[
            "Set a daily Quran reading target (e.g. 1 juz per day)",
            "Continue your Hifz memorisation schedule",
            "Review your hifz pages daily",
            "Study tafsir for deeper understanding",
        ],
        wellness_tips=[
            "This is your peak energy time — maximise your ibadah",
            "Plan your schedule around prayer times",
            "Sleep early to wake for Tahajjud",
            "Exercise regularly — a strong body supports strong ibadah",
        ],
        motivational_reminder=(
            "Alhamdulillah — the gates of all worship are open. "
            "The Prophet ﷺ said: 'Take advantage of five before five: "
            "your youth before old age, your health before illness, "
            "your wealth before poverty, your free time before busy time, "
            "your life before death.' This is your time — use it fully."
        ),
    ),

    "nifas": IbadahRecommendation(
        phase="nifas",
        permitted=[
            "All dhikr and dua",
            "Listening to Quran",
            "Islamic study",
            "Sadaqah",
            "Sending Salawat on the Prophet ﷺ",
        ],
        not_permitted=[
            "Salah (until post-natal bleeding ceases and ghusl is performed)",
            "Fasting (must be made up later)",
            "Tawaf",
            "Touching the mushaf directly",
        ],
        recommended_now=[
            "Rest and recover — caring for yourself is caring for your baby",
            "Make dua for your new child's tarbiyah",
            "Plan their Islamic upbringing from now",
            "Listen to Quran — it is blessed for your home and baby",
            "Begin teaching your child dhikr from birth",
        ],
        dhikr_suggestions=[
            "Recite Ayat al-Kursi and the Mu'awwidhatayn for protection",
            "Say BismAllah before nursing",
            "Dhikr: 'Allahu Akbar' — Allah is greater than every difficulty",
            "Ya Lateefu × 100 — the Subtle, the Kind",
        ],
        quran_engagement=[
            "Listen to Surah Maryam — the story of a new mother in Islam",
            "Listen to Surah Luqman — a father's advice, a timeless parenting guide",
            "Listen to Juz Amma for short surahs to teach your baby early",
        ],
        wellness_tips=[
            "Post-natal care is a priority — do not rush ibadah",
            "Iron and nutrition: meat, leafy greens, dates",
            "Sleep when the baby sleeps",
            "Ask for help — the Muslim community is there for you",
            "Nifas lasts up to 40 days in most madhabs, but often ends earlier",
        ],
        motivational_reminder=(
            "Maryam ؓ, after the most difficult night of her life, "
            "was told: 'And shake the trunk of the palm tree toward you — "
            "it will drop fresh ripe dates upon you.' (Quran 19:25). "
            "Allah provides ease. Rest, recover, and know that every moment "
            "of care for your child is ibadah. The Prophet ﷺ said the mother "
            "who dies in childbirth is a martyr. You are doing sacred work."
        ),
    ),
}


def get_ibadah_recommendations(phase: str) -> IbadahRecommendation:
    """Return ibadah recommendations for the given cycle phase."""
    return PHASE_RECOMMENDATIONS.get(phase, PHASE_RECOMMENDATIONS["tuhr"])


def get_phase_from_cycle(cycle) -> str:
    """Derive the current phase string from a MenstrualCycle model instance."""
    if cycle is None:
        return "tuhr"
    if not cycle.end_date:
        # Open cycle = currently in it
        return cycle.blood_classification or "hayd"
    # Closed cycle with ghusl pending
    if cycle.ghusl_required and not cycle.ghusl_done:
        return "hayd"
    return "tuhr"
