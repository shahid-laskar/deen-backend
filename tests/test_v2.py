"""
V2 + V3 Tests
=============
Covers: Qibla calculation, Cycle-sync, Recitation scoring,
Meal/Workout/Child/Community/Waqf repository layer.
"""
import math
import pytest
from datetime import date, timedelta
from uuid import uuid4

from app.services.qibla_service import calculate_qibla, _haversine_distance
from app.services.cycle_sync_service import get_ibadah_recommendations, get_phase_from_cycle
from app.services.recitation_service import compute_basic_score
from app.repositories.v2 import (
    FoodItemRepository, MealPlanRepository, MealEntryRepository,
    WorkoutPlanRepository, WorkoutSessionRepository,
    ChildRepository, MilestoneRepository, DuaTeachingRepository,
    WaqfProjectRepository, DonationRepository,
    CommunityGroupRepository, PostRepository,
)
from app.core.security import hash_password
from app.repositories.user import UserRepository


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def make_user(db, email="v2test@deen.app", gender="male"):
    repo = UserRepository(db)
    user = await repo.create(
        email=email,
        password_hash=hash_password("TestPass1"),
        gender=gender,
        madhab="hanafi",
        timezone="UTC",
    )
    await repo.upsert_profile(user.id)
    return user


# ─── Qibla Service ────────────────────────────────────────────────────────────

class TestQiblaService:
    def test_london_qibla_bearing(self):
        """London → Mecca should be roughly SE (119-122°)."""
        result = calculate_qibla(51.5074, -0.1278)
        assert 115 < result["qibla_bearing"] < 125
        assert result["compass_direction"] in ("ESE", "SE")

    def test_new_york_qibla_bearing(self):
        """New York → Mecca should be roughly NE (~58°)."""
        result = calculate_qibla(40.7128, -74.0060)
        assert 50 < result["qibla_bearing"] < 70
        assert result["distance_to_kaaba_km"] > 9000

    def test_jakarta_qibla_bearing(self):
        """Jakarta → Mecca should be roughly NW (~295°)."""
        result = calculate_qibla(-6.2088, 106.8456)
        assert 280 < result["qibla_bearing"] < 310

    def test_mecca_itself(self):
        """At Mecca, bearing is ~undefined; distance near zero."""
        result = calculate_qibla(21.4225, 39.8262)
        assert result["distance_to_kaaba_km"] < 1.0

    def test_bearing_range(self):
        """Bearing is always 0-360."""
        for lat, lng in [(0, 0), (90, 0), (-90, 0), (0, 180), (0, -180)]:
            r = calculate_qibla(lat, lng)
            assert 0 <= r["qibla_bearing"] < 360

    def test_haversine_london_paris(self):
        """London–Paris distance ~340 km."""
        d = _haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
        assert 330_000 < d < 350_000  # metres

    def test_response_has_required_fields(self):
        result = calculate_qibla(51.5, -0.1)
        for field in ("qibla_bearing", "compass_direction", "distance_to_kaaba_km", "latitude", "longitude"):
            assert field in result

    def test_distance_increases_with_distance(self):
        near = calculate_qibla(21.5, 39.9)   # near Mecca
        far = calculate_qibla(51.5, -0.1)    # London
        assert far["distance_to_kaaba_km"] > near["distance_to_kaaba_km"]


# ─── Cycle-Sync Service ───────────────────────────────────────────────────────

class TestCycleSyncService:
    def test_hayd_phase_no_prayer(self):
        recs = get_ibadah_recommendations("hayd")
        assert any("salah" in item.lower() or "Salah" in item for item in recs.not_permitted)
        assert recs.phase == "hayd"

    def test_hayd_dua_always_permitted(self):
        recs = get_ibadah_recommendations("hayd")
        permitted_text = " ".join(recs.permitted).lower()
        assert "dua" in permitted_text

    def test_istihadah_can_pray(self):
        recs = get_ibadah_recommendations("istihadah")
        permitted_text = " ".join(recs.permitted).lower()
        assert "salah" in permitted_text
        assert len(recs.not_permitted) == 0

    def test_tuhr_all_open(self):
        recs = get_ibadah_recommendations("tuhr")
        assert len(recs.not_permitted) == 0
        assert len(recs.recommended_now) > 0

    def test_nifas_similar_to_hayd(self):
        recs = get_ibadah_recommendations("nifas")
        assert recs.phase == "nifas"
        assert any("salah" in item.lower() or "Salah" in item for item in recs.not_permitted)

    def test_all_phases_have_dhikr(self):
        for phase in ("hayd", "tuhr", "istihadah", "nifas"):
            recs = get_ibadah_recommendations(phase)
            assert len(recs.dhikr_suggestions) > 0

    def test_all_phases_have_motivation(self):
        for phase in ("hayd", "tuhr", "istihadah", "nifas"):
            recs = get_ibadah_recommendations(phase)
            assert len(recs.motivational_reminder) > 50

    def test_unknown_phase_defaults_to_tuhr(self):
        recs = get_ibadah_recommendations("unknown_phase")
        assert recs.phase == "tuhr"

    def test_get_phase_from_none_cycle(self):
        assert get_phase_from_cycle(None) == "tuhr"

    def test_get_phase_from_open_cycle(self):
        class FakeCycle:
            end_date = None
            blood_classification = "hayd"
            ghusl_required = False
            ghusl_done = False
        assert get_phase_from_cycle(FakeCycle()) == "hayd"

    def test_get_phase_closed_cycle_ghusl_pending(self):
        class FakeCycle:
            end_date = date.today() - timedelta(days=1)
            blood_classification = "hayd"
            ghusl_required = True
            ghusl_done = False
        assert get_phase_from_cycle(FakeCycle()) == "hayd"

    def test_get_phase_closed_cycle_ghusl_done(self):
        class FakeCycle:
            end_date = date.today() - timedelta(days=1)
            blood_classification = "hayd"
            ghusl_required = True
            ghusl_done = True
        assert get_phase_from_cycle(FakeCycle()) == "tuhr"


# ─── Recitation Service ───────────────────────────────────────────────────────

class TestRecitationService:
    def test_perfect_match(self):
        result = compute_basic_score("بسم الله الرحمن الرحيم", "بسم الله الرحمن الرحيم", 0.95)
        assert result["overlap_score"] == 100.0

    def test_empty_transcript(self):
        result = compute_basic_score("بسم الله", "", 0.0)
        assert result["overlap_score"] == 0.0

    def test_partial_match(self):
        result = compute_basic_score("a b c d", "a b", 1.0)
        assert result["overlap_score"] == 50.0

    def test_confidence_affects_adjusted_score(self):
        r1 = compute_basic_score("a b c d", "a b c d", 1.0)
        r2 = compute_basic_score("a b c d", "a b c d", 0.5)
        assert r1["confidence_adjusted_score"] > r2["confidence_adjusted_score"]

    def test_both_empty(self):
        result = compute_basic_score("", "", 0.0)
        assert result["overlap_score"] == 0.0


# ─── Meal Repository ──────────────────────────────────────────────────────────

class TestMealRepository:
    async def test_create_and_get_food_item(self, db_session):
        user = await make_user(db_session, "meal_food@deen.app")
        repo = FoodItemRepository(db_session)
        item = await repo.create(
            user_id=user.id,
            name="Dates",
            category="fruit",
            is_halal_certified=True,
            calories_per_100g=282.0,
        )
        assert item.name == "Dates"
        assert item.is_halal_certified is True

    async def test_meal_entry_daily_totals(self, db_session):
        user = await make_user(db_session, "meal_totals@deen.app")
        entry_repo = MealEntryRepository(db_session)
        today = date.today()
        await entry_repo.create(
            user_id=user.id, entry_date=today,
            meal_type="suhoor", food_name="Oats",
            calories=300.0, protein_g=10.0, carbs_g=55.0, fat_g=5.0,
        )
        await entry_repo.create(
            user_id=user.id, entry_date=today,
            meal_type="iftar", food_name="Dates",
            calories=120.0, protein_g=1.0, carbs_g=30.0, fat_g=0.2,
        )
        totals = await entry_repo.get_daily_totals(user.id, today)
        assert totals["calories"] == pytest.approx(420.0)
        assert totals["protein_g"] == pytest.approx(11.0)

    async def test_meal_plan_create_and_get_active(self, db_session):
        user = await make_user(db_session, "meal_plan@deen.app")
        plan_repo = MealPlanRepository(db_session)
        plan = await plan_repo.create(
            user_id=user.id,
            name="Ramadan Plan",
            start_date=date.today(),
            is_ramadan_mode=True,
            daily_calorie_goal=1800,
        )
        active = await plan_repo.get_active_for_user(user.id)
        assert active is not None
        assert active.is_ramadan_mode is True
        assert active.daily_calorie_goal == 1800


# ─── Workout Repository ───────────────────────────────────────────────────────

class TestWorkoutRepository:
    async def test_create_session_and_get_weekly_count(self, db_session):
        user = await make_user(db_session, "workout@deen.app")
        repo = WorkoutSessionRepository(db_session)
        await repo.create(
            user_id=user.id, session_date=date.today(),
            session_name="Fajr workout", duration_minutes=30, completed=True,
        )
        await repo.create(
            user_id=user.id,
            session_date=date.today() - timedelta(days=1),
            session_name="Asr run", duration_minutes=25, completed=True,
        )
        weekly = await repo.get_weekly_count(user.id)
        assert weekly >= 1  # today's session definitely this week

    async def test_workout_plan_active(self, db_session):
        user = await make_user(db_session, "wplan@deen.app")
        repo = WorkoutPlanRepository(db_session)
        plan = await repo.create(
            user_id=user.id, name="Strength 3x/week",
            days_per_week=3, is_active=True, is_ramadan_mode=False,
        )
        active = await repo.get_active(user.id)
        assert active is not None
        assert active.id == plan.id


# ─── Child Repository ─────────────────────────────────────────────────────────

class TestChildRepository:
    async def test_create_child_and_milestones(self, db_session):
        user = await make_user(db_session, "child@deen.app")
        child_repo = ChildRepository(db_session)
        ms_repo = MilestoneRepository(db_session)

        child = await child_repo.create(
            user_id=user.id,
            name="Ahmad",
            date_of_birth=date(2020, 3, 15),
            gender="male",
        )
        assert child.name == "Ahmad"

        ms = await ms_repo.create(
            child_id=child.id, user_id=user.id,
            title="First Kalimah recited",
            category="aqeedah",
            target_age_months=24,
        )
        assert ms.achieved is False

        ms = await ms_repo.update(ms, achieved=True, achieved_date=date.today())
        assert ms.achieved is True

        milestones = await ms_repo.get_for_child(child.id)
        assert len(milestones) == 1

    async def test_dua_teaching_lifecycle(self, db_session):
        user = await make_user(db_session, "duachild@deen.app")
        child_repo = ChildRepository(db_session)
        dua_repo = DuaTeachingRepository(db_session)

        child = await child_repo.create(user_id=user.id, name="Fatima")
        log = await dua_repo.create(
            child_id=child.id, user_id=user.id,
            dua_key="before_eating", dua_name="Dua before eating",
            status="learning", started_date=date.today(),
        )
        assert log.status == "learning"

        log = await dua_repo.update(log, status="mastered", mastered_date=date.today())
        assert log.status == "mastered"

        logs = await dua_repo.get_for_child(child.id)
        assert len(logs) == 1


# ─── Waqf Repository ──────────────────────────────────────────────────────────

class TestWaqfRepository:
    async def test_create_project_and_donate(self, db_session):
        user = await make_user(db_session, "waqf@deen.app")
        proj_repo = WaqfProjectRepository(db_session)
        don_repo = DonationRepository(db_session)

        project = await proj_repo.create(
            title="Build a Masjid in Kenya",
            description="Clean water and masjid for a village of 500.",
            category="masjid",
            goal_amount=50000.0,
            raised_amount=0.0,
            currency="USD",
            start_date=date.today(),
            is_active=True,
            is_verified=True,
        )
        assert project.goal_amount == 50000.0

        donation = await don_repo.create(
            user_id=user.id,
            project_id=project.id,
            amount=100.0,
            currency="USD",
            donation_date=date.today(),
            status="confirmed",
            niyyah="For the sake of Allah",
        )
        assert donation.amount == 100.0

        total = await don_repo.get_user_total(user.id)
        assert total == pytest.approx(100.0)

    async def test_get_all_projects_filtered(self, db_session):
        repo = WaqfProjectRepository(db_session)
        await repo.create(
            title="Water Project", description="Wells", category="water",
            goal_amount=10000.0, raised_amount=0.0, currency="USD",
            start_date=date.today(), is_active=True,
        )
        await repo.create(
            title="Masjid Project", description="Masjid", category="masjid",
            goal_amount=20000.0, raised_amount=0.0, currency="USD",
            start_date=date.today(), is_active=True,
        )
        all_projects = await repo.get_all()
        assert len(all_projects) >= 2
        water = await repo.get_all(category="water")
        assert all(p.category == "water" for p in water)


# ─── Community Repository ──────────────────────────────────────────────────────

class TestCommunityRepository:
    async def test_create_group_and_posts(self, db_session):
        user = await make_user(db_session, "community@deen.app")
        group_repo = CommunityGroupRepository(db_session)
        post_repo = PostRepository(db_session)

        group = await group_repo.create(
            name="Quran Study Circle",
            slug="quran-study-circle",
            description="Weekly Quran study",
            category="quran",
            created_by=user.id,
        )
        assert group.member_count == 0

        post = await post_repo.create(
            user_id=user.id,
            group_id=group.id,
            content="Assalamu Alaikum! Today we study Surah Al-Baqarah.",
            post_type="text",
        )
        assert post.like_count == 0
        assert post.is_active is True

        posts = await post_repo.get_for_group(group.id)
        assert len(posts) == 1

    async def test_group_not_member_initially(self, db_session):
        user = await make_user(db_session, "notmember@deen.app")
        group_repo = CommunityGroupRepository(db_session)
        group = await group_repo.create(
            name="Sisters Circle", slug="sisters-circle",
            category="sisters", created_by=user.id,
        )
        other = await make_user(db_session, "other_community@deen.app")
        assert not await group_repo.is_member(group.id, other.id)
