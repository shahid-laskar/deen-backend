"""
Shafi'i Madhab — Hayd/Tuhr Calculation Engine
==============================================
Key rules (Shafi'i):
- Minimum hayd: 1 day (24 hours)
- Maximum hayd: 15 days
- Minimum tuhr: 15 days
- Reciting Quran from memory during hayd: some scholars permit for teaching/learning
- References: Al-Majmu', Minhaj al-Talibin, Tuhfat al-Muhtaj
"""

from datetime import date
from typing import Optional

from app.services.fiqh_engine.base import BaseMadhab, CycleInput, FiqhRuling


class ShafiEngine(BaseMadhab):
    HAYD_MIN_DAYS = 1
    HAYD_MAX_DAYS = 15
    TUHR_MIN_DAYS = 15

    @property
    def name(self) -> str:
        return "Shafi'i"

    def classify_cycle(self, cycle: CycleInput) -> FiqhRuling:
        duration = self._duration_days(cycle)
        notes: list[str] = []
        confidence = "certain"

        if duration is None:
            days_so_far = (date.today() - cycle.start_date).days + 1
            classification = "hayd" if days_so_far <= self.HAYD_MAX_DAYS else "istihadah"
            if classification == "istihadah":
                notes.append(
                    f"Bleeding has exceeded {self.HAYD_MAX_DAYS} days (Shafi'i maximum). "
                    "Revert to your habitual cycle length. Remaining days = istihadah."
                )
                confidence = "probable"
        else:
            if cycle.previous_tuhr_days is not None and cycle.previous_tuhr_days < self.TUHR_MIN_DAYS:
                classification = "istihadah"
                notes.append(
                    f"Tuhr gap ({cycle.previous_tuhr_days}d) is less than the Shafi'i "
                    f"minimum of {self.TUHR_MIN_DAYS} days. Classified as istihadah."
                )
                confidence = "probable"
            elif duration < self.HAYD_MIN_DAYS:
                classification = "istihadah"
                notes.append("Bleeding lasted less than 1 full day — classified as istihadah.")
            elif duration <= self.HAYD_MAX_DAYS:
                classification = "hayd"
            else:
                classification = "hayd"  # up to habitual; remainder istihadah
                notes.append(
                    f"Bleeding exceeded {self.HAYD_MAX_DAYS} days. "
                    "Count hayd up to your habitual duration; rest is istihadah."
                )
                confidence = "probable"

        can_pray, can_fast, can_read_quran = self._build_worship_gates(classification, notes)
        ghusl_required = classification == "hayd" and cycle.end_date is not None

        return FiqhRuling(
            classification=classification,
            madhab=self.name,
            can_pray=can_pray,
            can_fast=can_fast,
            can_read_quran=can_read_quran,
            ghusl_required=ghusl_required,
            ruling_summary=self._build_summary(classification, duration),
            notes=notes + [self._make_referral_note()],
            confidence=confidence,
        )

    def _build_worship_gates(self, classification: str, notes: list[str]) -> tuple[bool, bool, bool]:
        if classification == "hayd":
            notes.append("Salah and sawm are suspended during hayd. Missed fasts require qadha.")
            notes.append(
                "Shafi'i position: reciting Quran during hayd is not permitted as a rule "
                "though some scholars allow it for learning purposes — consult your scholar."
            )
            return False, False, False
        if classification == "istihadah":
            notes.append("Istihadah: renew wudu for each salah. All ibadah continues normally.")
            return True, True, True
        return True, True, True

    def _build_summary(self, classification: str, duration: Optional[int]) -> str:
        dur_str = f" ({duration} days)" if duration else ""
        return {
            "hayd": f"Classified as hayd{dur_str} per Shafi'i fiqh.",
            "istihadah": "Classified as istihadah. Continue worship with wudu per prayer.",
            "tuhr": "In state of purity (tuhr). All worship applies normally.",
        }.get(classification, "Classification pending.")


# ──────────────────────────────────────────────────────────────────────────────

"""
Maliki Madhab — Hayd/Tuhr Calculation Engine
============================================
Key rules (Maliki):
- Minimum hayd: no strict minimum (even 1 day accepted)
- Maximum hayd: 15 days (some narrations: up to 15 with preference for customary)
- Minimum tuhr: 15 days
- Women rely heavily on their aadah (habit/custom)
- References: Mudawwana, Al-Risalah, Al-Fiqh al-Maliki fi Thawbihi al-Jadid
"""


class MalikiEngine(BaseMadhab):
    HAYD_MIN_DAYS = 1
    HAYD_MAX_DAYS = 15
    TUHR_MIN_DAYS = 15

    @property
    def name(self) -> str:
        return "Maliki"

    def classify_cycle(self, cycle: CycleInput) -> FiqhRuling:
        duration = self._duration_days(cycle)
        notes: list[str] = []
        confidence = "certain"

        if duration is None:
            days_so_far = (date.today() - cycle.start_date).days + 1
            classification = "hayd" if days_so_far <= self.HAYD_MAX_DAYS else "istihadah"
            if classification == "istihadah":
                notes.append(
                    "Bleeding exceeds 15 days. Maliki fiqh: revert to your aadah "
                    "(habitual cycle). Days beyond aadah = istihadah."
                )
                confidence = "probable"
        else:
            if cycle.previous_tuhr_days is not None and cycle.previous_tuhr_days < self.TUHR_MIN_DAYS:
                classification = "istihadah"
                notes.append(
                    f"Tuhr of {cycle.previous_tuhr_days} days is below the 15-day Maliki minimum. "
                    "The Maliki school treats this as istihadah — aadah-based ruling applies."
                )
                confidence = "probable"
            elif duration <= self.HAYD_MAX_DAYS:
                classification = "hayd"
                notes.append(
                    "Maliki fiqh places strong emphasis on aadah (custom). "
                    "If this differs significantly from your habitual cycle, consult a scholar."
                )
            else:
                classification = "hayd"
                notes.append(
                    f"Bleeding of {duration} days exceeds 15 days. "
                    "Count hayd per your habitual duration; rest is istihadah."
                )
                confidence = "probable"

        can_pray, can_fast, can_read_quran = self._build_worship_gates(classification, notes)
        ghusl_required = classification == "hayd" and cycle.end_date is not None

        return FiqhRuling(
            classification=classification,
            madhab=self.name,
            can_pray=can_pray,
            can_fast=can_fast,
            can_read_quran=can_read_quran,
            ghusl_required=ghusl_required,
            ruling_summary=self._build_summary(classification, duration),
            notes=notes + [self._make_referral_note()],
            confidence=confidence,
        )

    def _build_worship_gates(self, classification: str, notes: list[str]) -> tuple[bool, bool, bool]:
        if classification == "hayd":
            notes.append("During hayd: salah and fasting are suspended. Fasts must be made up.")
            notes.append(
                "Maliki position on Quran recitation during hayd: "
                "touching the mushaf is not permitted; recitation from memory is a matter "
                "of scholarly difference — consult a Maliki scholar."
            )
            return False, False, False
        if classification == "istihadah":
            notes.append("Maliki ruling on istihadah: perform wudu before each prayer.")
            return True, True, True
        return True, True, True

    def _build_summary(self, classification: str, duration: Optional[int]) -> str:
        dur_str = f" ({duration} days)" if duration else ""
        return {
            "hayd": f"Classified as hayd{dur_str} per Maliki fiqh. Aadah applies.",
            "istihadah": "Classified as istihadah (Maliki). Renew wudu at each prayer time.",
            "tuhr": "In state of tuhr (purity) per Maliki fiqh.",
        }.get(classification, "Classification pending.")


# ──────────────────────────────────────────────────────────────────────────────

"""
Hanbali Madhab — Hayd/Tuhr Calculation Engine
=============================================
Key rules (Hanbali):
- Minimum hayd: 1 day (some say even less)
- Maximum hayd: 15 days
- Minimum tuhr: 13 days (differs from other madhabs)
- Closest to Shafi'i on most points
- References: Al-Mughni, Al-Insaf, Al-Raud al-Murbi
"""


class HanbaliEngine(BaseMadhab):
    HAYD_MIN_DAYS = 1
    HAYD_MAX_DAYS = 15
    TUHR_MIN_DAYS = 13   # Hanbali-specific

    @property
    def name(self) -> str:
        return "Hanbali"

    def classify_cycle(self, cycle: CycleInput) -> FiqhRuling:
        duration = self._duration_days(cycle)
        notes: list[str] = []
        confidence = "certain"

        if duration is None:
            days_so_far = (date.today() - cycle.start_date).days + 1
            classification = "hayd" if days_so_far <= self.HAYD_MAX_DAYS else "istihadah"
            if classification == "istihadah":
                notes.append(
                    f"Bleeding exceeds {self.HAYD_MAX_DAYS} days (Hanbali max). "
                    "Revert to habitual cycle. Excess days = istihadah."
                )
                confidence = "probable"
        else:
            if cycle.previous_tuhr_days is not None and cycle.previous_tuhr_days < self.TUHR_MIN_DAYS:
                classification = "istihadah"
                notes.append(
                    f"Tuhr of {cycle.previous_tuhr_days} days is below the Hanbali minimum "
                    f"of {self.TUHR_MIN_DAYS} days. This is istihadah."
                )
                confidence = "probable"
            elif duration < self.HAYD_MIN_DAYS:
                classification = "istihadah"
                notes.append("Duration below minimum — classified as istihadah.")
            elif duration <= self.HAYD_MAX_DAYS:
                classification = "hayd"
            else:
                classification = "hayd"
                notes.append(
                    f"Bleeding ({duration}d) exceeds 15 days. "
                    "Hayd counted to habitual duration; rest is istihadah."
                )
                confidence = "probable"

        can_pray, can_fast, can_read_quran = self._build_worship_gates(classification, notes)
        ghusl_required = classification == "hayd" and cycle.end_date is not None

        return FiqhRuling(
            classification=classification,
            madhab=self.name,
            can_pray=can_pray,
            can_fast=can_fast,
            can_read_quran=can_read_quran,
            ghusl_required=ghusl_required,
            ruling_summary=self._build_summary(classification, duration),
            notes=notes + [self._make_referral_note()],
            confidence=confidence,
        )

    def _build_worship_gates(self, classification: str, notes: list[str]) -> tuple[bool, bool, bool]:
        if classification == "hayd":
            notes.append("During hayd: salah and sawm suspended. Missed fasts = qadha.")
            notes.append(
                "Hanbali position: reciting Quran during hayd without touching "
                "the mushaf is a matter of scholarly discussion — consult a scholar."
            )
            return False, False, False
        if classification == "istihadah":
            notes.append("Istihadah (Hanbali): make wudu for each prayer time.")
            return True, True, True
        return True, True, True

    def _build_summary(self, classification: str, duration: Optional[int]) -> str:
        dur_str = f" ({duration} days)" if duration else ""
        return {
            "hayd": f"Classified as hayd{dur_str} per Hanbali fiqh.",
            "istihadah": "Classified as istihadah (Hanbali). Wudu required per prayer.",
            "tuhr": "In state of purity (tuhr) — all ibadah applies.",
        }.get(classification, "Classification pending.")
