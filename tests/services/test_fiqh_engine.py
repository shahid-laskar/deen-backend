"""
Fiqh Engine Unit Tests
=======================
Tests all four madhab implementations with standard cases, edge cases,
and boundary conditions. These are the most critical tests in the suite.
"""
import pytest
from datetime import date, timedelta

from app.services.fiqh_engine import CycleInput, classify_cycle, get_fiqh_engine
from app.services.fiqh_engine.base import FiqhRuling


def make_cycle(
    duration_days: int | None = None,
    start_offset: int = 0,
    previous_tuhr: int | None = None,
    previous_cycles: list | None = None,
) -> CycleInput:
    """Helper to build CycleInput for tests."""
    start = date.today() - timedelta(days=start_offset)
    end = (start + timedelta(days=duration_days - 1)) if duration_days else None
    return CycleInput(
        start_date=start,
        end_date=end,
        previous_cycles=previous_cycles or [],
        previous_tuhr_days=previous_tuhr,
    )


# ─── Hanafi Tests ─────────────────────────────────────────────────────────────

class TestHanafiEngine:
    def test_valid_hayd_3_days(self):
        ruling = classify_cycle("hanafi", make_cycle(duration_days=3))
        assert ruling.classification == "hayd"
        assert ruling.can_pray is False
        assert ruling.can_fast is False
        assert ruling.ghusl_required is True

    def test_valid_hayd_7_days(self):
        ruling = classify_cycle("hanafi", make_cycle(duration_days=7))
        assert ruling.classification == "hayd"

    def test_valid_hayd_10_days(self):
        ruling = classify_cycle("hanafi", make_cycle(duration_days=10))
        assert ruling.classification == "hayd"

    def test_below_minimum_is_istihadah(self):
        """Hanafi minimum is 3 days; 2 days = istihadah."""
        ruling = classify_cycle("hanafi", make_cycle(duration_days=2))
        assert ruling.classification == "istihadah"
        assert ruling.can_pray is True
        assert ruling.can_fast is True

    def test_above_maximum_is_hayd_with_note(self):
        """11 days exceeds Hanafi max of 10; still classified as hayd (habitual rule)."""
        ruling = classify_cycle("hanafi", make_cycle(duration_days=11))
        assert ruling.classification == "hayd"
        assert any("10 days" in note or "exceeded" in note for note in ruling.notes)

    def test_insufficient_tuhr_is_istihadah(self):
        """Tuhr less than 15 days = istihadah in Hanafi."""
        ruling = classify_cycle("hanafi", make_cycle(duration_days=5, previous_tuhr=10))
        assert ruling.classification == "istihadah"

    def test_exact_tuhr_minimum_is_hayd(self):
        """Exactly 15 days tuhr = valid; bleeding classified normally."""
        ruling = classify_cycle("hanafi", make_cycle(duration_days=5, previous_tuhr=15))
        assert ruling.classification == "hayd"

    def test_ongoing_cycle_within_max(self):
        """Ongoing cycle, 5 days in = hayd."""
        ruling = classify_cycle("hanafi", make_cycle(duration_days=None, start_offset=5))
        assert ruling.classification == "hayd"

    def test_ghusl_not_required_for_ongoing(self):
        """Ghusl is only required after cycle ends."""
        ruling = classify_cycle("hanafi", make_cycle(duration_days=None, start_offset=3))
        assert ruling.ghusl_required is False

    def test_ghusl_required_after_completed_hayd(self):
        ruling = classify_cycle("hanafi", make_cycle(duration_days=5))
        assert ruling.ghusl_required is True

    def test_madhab_name(self):
        engine = get_fiqh_engine("hanafi")
        assert engine.name == "Hanafi"

    def test_ruling_has_referral_note(self):
        ruling = classify_cycle("hanafi", make_cycle(duration_days=5))
        assert any("scholar" in note.lower() or "consult" in note.lower() for note in ruling.notes)

    def test_confidence_is_certain_for_standard_case(self):
        ruling = classify_cycle("hanafi", make_cycle(duration_days=6))
        assert ruling.confidence == "certain"

    def test_confidence_is_probable_for_exceeded_max(self):
        ruling = classify_cycle("hanafi", make_cycle(duration_days=12))
        assert ruling.confidence == "probable"


# ─── Shafi'i Tests ────────────────────────────────────────────────────────────

class TestShafiEngine:
    def test_minimum_1_day_is_hayd(self):
        """Shafi'i minimum is 1 day."""
        ruling = classify_cycle("shafii", make_cycle(duration_days=1))
        assert ruling.classification == "hayd"

    def test_valid_hayd_15_days(self):
        ruling = classify_cycle("shafii", make_cycle(duration_days=15))
        assert ruling.classification == "hayd"

    def test_16_days_classified_as_hayd_with_note(self):
        ruling = classify_cycle("shafii", make_cycle(duration_days=16))
        assert ruling.classification == "hayd"
        assert any("15" in note or "exceeded" in note for note in ruling.notes)

    def test_insufficient_tuhr_is_istihadah(self):
        ruling = classify_cycle("shafii", make_cycle(duration_days=3, previous_tuhr=10))
        assert ruling.classification == "istihadah"

    def test_istihadah_can_pray_and_fast(self):
        ruling = classify_cycle("shafii", make_cycle(duration_days=3, previous_tuhr=10))
        assert ruling.can_pray is True
        assert ruling.can_fast is True

    def test_madhab_name(self):
        assert get_fiqh_engine("shafii").name == "Shafi'i"


# ─── Maliki Tests ─────────────────────────────────────────────────────────────

class TestMalikiEngine:
    def test_valid_hayd_5_days(self):
        ruling = classify_cycle("maliki", make_cycle(duration_days=5))
        assert ruling.classification == "hayd"

    def test_maliki_tuhr_minimum_15(self):
        ruling = classify_cycle("maliki", make_cycle(duration_days=5, previous_tuhr=14))
        assert ruling.classification == "istihadah"

    def test_maliki_15_days_valid(self):
        ruling = classify_cycle("maliki", make_cycle(duration_days=15))
        assert ruling.classification == "hayd"

    def test_madhab_name(self):
        assert get_fiqh_engine("maliki").name == "Maliki"


# ─── Hanbali Tests ────────────────────────────────────────────────────────────

class TestHanbaliEngine:
    def test_minimum_1_day(self):
        ruling = classify_cycle("hanbali", make_cycle(duration_days=1))
        assert ruling.classification == "hayd"

    def test_tuhr_minimum_13_days(self):
        """Hanbali tuhr minimum is 13 days (unique among the four madhabs)."""
        ruling = classify_cycle("hanbali", make_cycle(duration_days=5, previous_tuhr=12))
        assert ruling.classification == "istihadah"

    def test_tuhr_exactly_13_is_valid(self):
        ruling = classify_cycle("hanbali", make_cycle(duration_days=5, previous_tuhr=13))
        assert ruling.classification == "hayd"

    def test_valid_hayd_15_days(self):
        ruling = classify_cycle("hanbali", make_cycle(duration_days=15))
        assert ruling.classification == "hayd"

    def test_madhab_name(self):
        assert get_fiqh_engine("hanbali").name == "Hanbali"


# ─── Factory Tests ────────────────────────────────────────────────────────────

class TestFiqhEngineFactory:
    def test_all_madhabs_resolvable(self):
        for madhab in ["hanafi", "shafii", "maliki", "hanbali"]:
            engine = get_fiqh_engine(madhab)
            assert engine is not None

    def test_unknown_madhab_raises(self):
        with pytest.raises(ValueError, match="Unknown madhab"):
            get_fiqh_engine("unknown_school")

    def test_case_insensitive(self):
        engine = get_fiqh_engine("HANAFI")
        assert engine.name == "Hanafi"

    def test_all_madhabs_return_fiqh_ruling(self):
        cycle = make_cycle(duration_days=5)
        for madhab in ["hanafi", "shafii", "maliki", "hanbali"]:
            ruling = classify_cycle(madhab, cycle)
            assert isinstance(ruling, FiqhRuling)
            assert ruling.madhab is not None
            assert ruling.classification in ("hayd", "istihadah", "tuhr")
            assert isinstance(ruling.can_pray, bool)
            assert isinstance(ruling.can_fast, bool)
            assert isinstance(ruling.ghusl_required, bool)
            assert isinstance(ruling.notes, list)
            assert len(ruling.notes) > 0

    def test_hayd_always_prevents_prayer_across_madhabs(self):
        """Core fiqh agreement: hayd = no salah, in all four madhabs."""
        cycle = make_cycle(duration_days=5, previous_tuhr=20)
        for madhab in ["hanafi", "shafii", "maliki", "hanbali"]:
            ruling = classify_cycle(madhab, cycle)
            if ruling.classification == "hayd":
                assert ruling.can_pray is False, f"{madhab}: hayd should prevent prayer"

    def test_istihadah_always_allows_prayer_across_madhabs(self):
        """Core fiqh agreement: istihadah = worship continues, in all four madhabs."""
        # Insufficient tuhr forces istihadah in all madhabs
        cycle = make_cycle(duration_days=5, previous_tuhr=5)
        for madhab in ["hanafi", "shafii", "maliki", "hanbali"]:
            ruling = classify_cycle(madhab, cycle)
            if ruling.classification == "istihadah":
                assert ruling.can_pray is True, f"{madhab}: istihadah should allow prayer"
