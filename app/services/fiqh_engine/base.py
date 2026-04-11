"""
Fiqh Engine — Base Interface
============================
Each madhab subclass implements this interface.
The engine is stateless; it receives cycle data and returns rulings.

All calculations are based on well-established fiqh texts and verified
against scholarly sources. Users are always encouraged to consult a
qualified scholar for their specific situation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CycleInput:
    """Input data for fiqh calculations."""
    start_date: date
    end_date: Optional[date]         # None = cycle ongoing
    previous_cycles: list[dict]      # list of past cycle dicts for habit-based rulings
    previous_tuhr_days: Optional[int] = None  # tuhr days since last cycle


@dataclass
class FiqhRuling:
    """Output of the fiqh engine for a given cycle."""
    classification: str              # "hayd" | "tuhr" | "istihadah"
    madhab: str
    can_pray: bool
    can_fast: bool
    can_read_quran: bool             # touching Quran (rules differ by madhab)
    ghusl_required: bool
    ruling_summary: str              # human-readable explanation
    notes: list[str]                 # additional guidance points
    confidence: str                  # "certain" | "probable" | "consult_scholar"


class BaseMadhab(ABC):
    """
    Abstract base that all madhab engines implement.
    Adding a new madhab = create a new subclass, zero route changes.
    """

    # Minimum/maximum hayd duration (days) — differs by madhab
    HAYD_MIN_DAYS: int
    HAYD_MAX_DAYS: int
    TUHR_MIN_DAYS: int

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the madhab name."""
        ...

    @abstractmethod
    def classify_cycle(self, cycle: CycleInput) -> FiqhRuling:
        """
        Given a cycle input, return the fiqh ruling.
        This is the core calculation method each madhab implements.
        """
        ...

    def _duration_days(self, cycle: CycleInput) -> Optional[int]:
        if cycle.end_date is None:
            return None
        return (cycle.end_date - cycle.start_date).days + 1

    def _base_worship_gates(
        self, classification: str
    ) -> tuple[bool, bool, bool]:
        """Returns (can_pray, can_fast, can_read_quran) based on classification."""
        if classification == "hayd":
            return False, False, True   # can_read_quran varies — subclass overrides
        if classification == "istihadah":
            return True, True, True     # mustahadah prays with wudu per prayer time
        # tuhr / clean
        return True, True, True

    def _make_referral_note(self) -> str:
        return (
            f"For detailed rulings specific to your situation according to the "
            f"{self.name} school, please consult a qualified scholar or visit "
            f"a trusted fatwa resource."
        )
