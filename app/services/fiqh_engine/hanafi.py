"""
Hanafi Madhab — Hayd/Tuhr Calculation Engine
=============================================
Key rules (Hanafi):
- Minimum hayd: 3 days (72 hours)
- Maximum hayd: 10 days
- Minimum tuhr (purity) between two hayd periods: 15 days
- Istihadah: bleeding outside these limits is abnormal
- Can read Quran during hayd: scholars differ; conservative view = no touching mushaf
- Ghusl is obligatory at end of hayd

References: Al-Hidayah, Bada'i al-Sana'i, Fatawa Hindiyya
"""

from datetime import date
from typing import Optional

from app.services.fiqh_engine.base import BaseMadhab, CycleInput, FiqhRuling


class HanafiEngine(BaseMadhab):
    HAYD_MIN_DAYS = 3
    HAYD_MAX_DAYS = 10
    TUHR_MIN_DAYS = 15

    @property
    def name(self) -> str:
        return "Hanafi"

    def classify_cycle(self, cycle: CycleInput) -> FiqhRuling:
        duration = self._duration_days(cycle)
        notes: list[str] = []
        confidence = "certain"

        # Ongoing cycle — classify based on what we know so far
        if duration is None:
            days_so_far = (date.today() - cycle.start_date).days + 1
            if days_so_far <= self.HAYD_MAX_DAYS:
                classification = "hayd"
                notes.append("Cycle is ongoing and within the valid hayd period.")
            else:
                classification = "istihadah"
                notes.append(
                    f"Bleeding has exceeded {self.HAYD_MAX_DAYS} days. "
                    "In the Hanafi school, this is classified as istihadah. "
                    "You should resume worship based on your habitual cycle (aadah)."
                )
                confidence = "probable"
        else:
            classification, confidence = self._classify_completed(duration, cycle, notes)

        can_pray, can_fast, can_read_quran = self._build_worship_gates(
            classification, notes
        )
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

    def _classify_completed(
        self, duration: int, cycle: CycleInput, notes: list[str]
    ) -> tuple[str, str]:
        """Returns (classification, confidence)."""
        if (
            cycle.previous_tuhr_days is not None
            and cycle.previous_tuhr_days < self.TUHR_MIN_DAYS
        ):
            notes.append(
                f"Tuhr gap of {cycle.previous_tuhr_days} days is less than "
                f"the Hanafi minimum of {self.TUHR_MIN_DAYS} days. "
                "This cycle may be istihadah — please consult a scholar."
            )
            return "istihadah", "probable"

        if self.HAYD_MIN_DAYS <= duration <= self.HAYD_MAX_DAYS:
            return "hayd", "certain"

        if duration < self.HAYD_MIN_DAYS:
            notes.append(
                f"Bleeding lasted only {duration} day(s), which is less than "
                f"the Hanafi minimum of {self.HAYD_MIN_DAYS} days. "
                "This is classified as istihadah."
            )
            return "istihadah", "certain"

        # duration > 10 days
        habitual = self._get_habitual_duration(cycle.previous_cycles)
        if habitual:
            notes.append(
                f"Bleeding exceeded 10 days. Hayd counted as {habitual} days "
                f"(your habitual cycle). Remaining days are istihadah."
            )
        else:
            notes.append(
                "Bleeding exceeded 10 days and no habitual cycle is recorded. "
                "Hanafi default: 10 days counted as hayd, remainder as istihadah."
            )
        return "hayd", "probable"

    def _get_habitual_duration(self, previous_cycles: list[dict]) -> Optional[int]:
        """Return the most recent hayd duration from cycle history."""
        hayd_cycles = [
            c for c in previous_cycles if c.get("blood_classification") == "hayd"
        ]
        if hayd_cycles:
            most_recent = sorted(hayd_cycles, key=lambda c: c["start_date"])[-1]
            return most_recent.get("duration_days")
        return None

    def _build_worship_gates(
        self, classification: str, notes: list[str]
    ) -> tuple[bool, bool, bool]:
        if classification == "hayd":
            notes.append(
                "During hayd: salah and sawm are not performed. "
                "Missed fasts must be made up (qadha). Missed salah are not made up."
            )
            notes.append(
                "Regarding Quran recitation: the majority Hanafi position is that "
                "reciting Quranic verses during hayd is not permitted, but "
                "du'a verses and dhikr are allowed."
            )
            return False, False, False  # can_read_quran=False (mushaf touching)
        if classification == "istihadah":
            notes.append(
                "During istihadah: perform wudu before each salah time, "
                "as wudu breaks at each prayer time. All worship continues normally."
            )
            return True, True, True
        return True, True, True

    def _build_summary(self, classification: str, duration: Optional[int]) -> str:
        dur_str = f" ({duration} days)" if duration else ""
        summaries = {
            "hayd": f"Classified as hayd{dur_str} according to Hanafi fiqh.",
            "istihadah": f"Classified as istihadah{dur_str}. Worship continues with wudu at each prayer time.",
            "tuhr": "Currently in tuhr (purity). All worship obligations apply normally.",
        }
        return summaries.get(classification, "Classification pending.")
