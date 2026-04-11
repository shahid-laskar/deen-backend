"""
Repository Layer Tests
======================
Tests repos directly against the in-memory SQLite DB — no HTTP, no routers.
This is the key advantage of the repo pattern: pure data-layer testing.
"""
import pytest
from datetime import date, timedelta
from uuid import uuid4

from app.repositories.user import UserRepository
from app.repositories.prayer import PrayerRepository
from app.repositories.habit import HabitRepository, HabitLogRepository
from app.repositories.repos import JournalRepository, TaskRepository, CycleRepository, FastingRepository


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def make_user(db, email="test@deen.app", madhab="hanafi", gender="male"):
    from app.core.security import hash_password
    repo = UserRepository(db)
    user = await repo.create(
        email=email,
        password_hash=hash_password("TestPass1"),
        gender=gender,
        madhab=madhab,
        timezone="UTC",
    )
    await repo.upsert_profile(user.id)
    return user


# ─── UserRepository ───────────────────────────────────────────────────────────

class TestUserRepository:
    async def test_create_and_get_by_email(self, db_session):
        repo = UserRepository(db_session)
        user = await make_user(db_session)
        found = await repo.get_by_email(user.email)
        assert found is not None
        assert found.id == user.id

    async def test_email_exists(self, db_session):
        repo = UserRepository(db_session)
        await make_user(db_session, email="unique@deen.app")
        assert await repo.email_exists("unique@deen.app") is True
        assert await repo.email_exists("nobody@deen.app") is False

    async def test_get_with_profile(self, db_session):
        repo = UserRepository(db_session)
        user = await make_user(db_session)
        full = await repo.get_with_profile(user.id)
        assert full is not None
        assert full.profile is not None

    async def test_get_with_profile_or_404_raises(self, db_session):
        repo = UserRepository(db_session)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await repo.get_with_profile_or_404(uuid4())
        assert exc.value.status_code == 404

    async def test_update_user_fields(self, db_session):
        repo = UserRepository(db_session)
        user = await make_user(db_session)
        updated = await repo.update(user, madhab="shafii", timezone="Asia/Kolkata")
        assert updated.madhab == "shafii"
        assert updated.timezone == "Asia/Kolkata"

    async def test_upsert_profile_creates_if_missing(self, db_session):
        from app.models.user import User
        from app.core.security import hash_password
        repo = UserRepository(db_session)
        # Create user without a profile
        user = await repo.create(
            email="noprofile@deen.app",
            password_hash=hash_password("TestPass1"),
            madhab="hanafi",
            timezone="UTC",
        )
        profile = await repo.upsert_profile(user.id, display_name="Ahmad")
        assert profile.display_name == "Ahmad"
        assert profile.user_id == user.id

    async def test_upsert_profile_updates_if_exists(self, db_session):
        repo = UserRepository(db_session)
        user = await make_user(db_session, email="update@deen.app")
        await repo.upsert_profile(user.id, display_name="First")
        profile = await repo.upsert_profile(user.id, display_name="Second")
        assert profile.display_name == "Second"

    async def test_refresh_token_lifecycle(self, db_session):
        from datetime import datetime, timezone, timedelta
        from app.core.security import hash_token, create_refresh_token
        repo = UserRepository(db_session)
        user = await make_user(db_session, email="token@deen.app")
        raw = create_refresh_token(str(user.id))
        hashed = hash_token(raw)
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        await repo.create_refresh_token(user.id, hashed, expires)
        stored = await repo.get_refresh_token_by_hash(hashed)
        assert stored is not None
        assert stored.is_revoked is False
        await repo.revoke_all_refresh_tokens(user.id)
        revoked = await repo.get_refresh_token_by_hash(hashed)
        assert revoked is None  # filtered out by is_revoked=False


# ─── PrayerRepository ─────────────────────────────────────────────────────────

class TestPrayerRepository:
    async def test_create_and_get_by_prayer_date(self, db_session):
        user = await make_user(db_session, email="prayer@deen.app")
        repo = PrayerRepository(db_session)
        log = await repo.create(
            user_id=user.id, prayer_name="fajr",
            log_date=date.today(), status="on_time",
        )
        found = await repo.get_by_prayer_and_date(user.id, "fajr", date.today())
        assert found is not None
        assert found.id == log.id

    async def test_upsert_updates_existing(self, db_session):
        user = await make_user(db_session, email="upsert@deen.app")
        repo = PrayerRepository(db_session)
        await repo.upsert(user.id, prayer_name="dhuhr", log_date=date.today(), status="on_time")
        updated = await repo.upsert(user.id, prayer_name="dhuhr", log_date=date.today(), status="late")
        assert updated.status == "late"
        # Only one row should exist
        logs = await repo.get_today(user.id)
        dhuhr_logs = [l for l in logs if l.prayer_name == "dhuhr"]
        assert len(dhuhr_logs) == 1

    async def test_get_for_date_range(self, db_session):
        user = await make_user(db_session, email="range@deen.app")
        repo = PrayerRepository(db_session)
        yesterday = date.today() - timedelta(days=1)
        await repo.create(user_id=user.id, prayer_name="fajr", log_date=yesterday, status="on_time")
        await repo.create(user_id=user.id, prayer_name="fajr", log_date=date.today(), status="late")
        logs = await repo.get_for_date_range(user.id, yesterday, date.today())
        assert len(logs) == 2

    async def test_get_for_streak_filters_obligatory(self, db_session):
        user = await make_user(db_session, email="streak@deen.app")
        repo = PrayerRepository(db_session)
        await repo.create(user_id=user.id, prayer_name="fajr", log_date=date.today(), status="on_time")
        await repo.create(user_id=user.id, prayer_name="tahajjud", log_date=date.today(), status="on_time")
        logs = await repo.get_for_streak(user.id)
        names = [l.prayer_name for l in logs]
        assert "tahajjud" not in names
        assert "fajr" in names

    async def test_get_owned_or_404_raises_for_wrong_user(self, db_session):
        user = await make_user(db_session, email="owner@deen.app")
        other = await make_user(db_session, email="other@deen.app")
        repo = PrayerRepository(db_session)
        log = await repo.create(user_id=user.id, prayer_name="asr", log_date=date.today(), status="on_time")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await repo.get_owned_or_404(log.id, other.id)
        assert exc.value.status_code == 404


# ─── HabitRepository ─────────────────────────────────────────────────────────

class TestHabitRepository:
    async def test_create_and_list(self, db_session):
        user = await make_user(db_session, email="habit@deen.app")
        repo = HabitRepository(db_session)
        await repo.create(user_id=user.id, name="Read Quran", category="quran", frequency="daily", target_count=1)
        await repo.create(user_id=user.id, name="Exercise", category="health", frequency="daily", target_count=1)
        habits = await repo.get_all_for_user(user.id)
        assert len(habits) == 2

    async def test_archived_habits_excluded_by_default(self, db_session):
        user = await make_user(db_session, email="arch@deen.app")
        repo = HabitRepository(db_session)
        active = await repo.create(user_id=user.id, name="Active", category="personal", frequency="daily", target_count=1, is_active=True)
        archived = await repo.create(user_id=user.id, name="Archived", category="personal", frequency="daily", target_count=1, is_active=False)
        habits = await repo.get_all_for_user(user.id)
        ids = [h.id for h in habits]
        assert active.id in ids
        assert archived.id not in ids
        all_habits = await repo.get_all_for_user(user.id, include_archived=True)
        assert len(all_habits) == 2


class TestHabitLogRepository:
    async def test_upsert_creates_new(self, db_session):
        user = await make_user(db_session, email="hlog@deen.app")
        habit_repo = HabitRepository(db_session)
        log_repo = HabitLogRepository(db_session)
        habit = await habit_repo.create(user_id=user.id, name="Test", category="personal", frequency="daily", target_count=1)
        log = await log_repo.upsert(habit.id, user.id, date.today(), completed=True, count=1)
        assert log.completed is True

    async def test_upsert_updates_existing(self, db_session):
        user = await make_user(db_session, email="hlog2@deen.app")
        habit_repo = HabitRepository(db_session)
        log_repo = HabitLogRepository(db_session)
        habit = await habit_repo.create(user_id=user.id, name="Test2", category="personal", frequency="daily", target_count=1)
        await log_repo.upsert(habit.id, user.id, date.today(), completed=False, count=1)
        updated = await log_repo.upsert(habit.id, user.id, date.today(), completed=True, count=1)
        assert updated.completed is True
        # Still only one log
        logs = await log_repo.get_for_habit(habit.id)
        assert len(logs) == 1


# ─── CycleRepository ─────────────────────────────────────────────────────────

class TestCycleRepository:
    async def test_get_open_cycle(self, db_session):
        user = await make_user(db_session, email="cycle@deen.app", gender="female")
        repo = CycleRepository(db_session)
        assert await repo.get_open_cycle(user.id) is None
        await repo.create(
            user_id=user.id, start_date=date.today(),
            blood_classification="hayd", hayd_tuhr_status="hayd",
            can_pray=False, can_fast=False, can_read_quran=True,
            ghusl_required=False, ghusl_done=False,
        )
        cycle = await repo.get_open_cycle(user.id)
        assert cycle is not None

    async def test_get_history_ordered_newest_first(self, db_session):
        user = await make_user(db_session, email="cycleh@deen.app", gender="female")
        repo = CycleRepository(db_session)
        past = date.today() - timedelta(days=30)
        await repo.create(user_id=user.id, start_date=past, end_date=past + timedelta(days=5),
            blood_classification="hayd", hayd_tuhr_status="hayd", can_pray=False,
            can_fast=False, can_read_quran=True, ghusl_required=True, ghusl_done=True)
        await repo.create(user_id=user.id, start_date=date.today(),
            blood_classification="hayd", hayd_tuhr_status="hayd", can_pray=False,
            can_fast=False, can_read_quran=True, ghusl_required=False, ghusl_done=False)
        history = await repo.get_history(user.id)
        assert history[0].start_date > history[1].start_date


# ─── BaseRepository generic behaviour ────────────────────────────────────────

class TestBaseRepository:
    async def test_get_returns_none_for_missing(self, db_session):
        repo = UserRepository(db_session)
        result = await repo.get(uuid4())
        assert result is None

    async def test_get_or_404_raises(self, db_session):
        repo = UserRepository(db_session)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await repo.get_or_404(uuid4())
        assert exc.value.status_code == 404

    async def test_delete_removes_record(self, db_session):
        user = await make_user(db_session, email="del@deen.app")
        repo = UserRepository(db_session)
        await repo.delete(user)
        result = await repo.get(user.id)
        assert result is None

    async def test_update_persists_changes(self, db_session):
        user = await make_user(db_session, email="upd@deen.app")
        repo = UserRepository(db_session)
        updated = await repo.update(user, timezone="Asia/Dubai")
        assert updated.timezone == "Asia/Dubai"
        refetched = await repo.get(user.id)
        assert refetched.timezone == "Asia/Dubai"
