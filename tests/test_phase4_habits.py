"""Phase 4 Habit System Tests — 36 tests."""
import pytest
from datetime import date


class TestHabitLibrary:
    def test_library_has_120_habits(self):
        from app.services.habit_library import HABIT_LIBRARY
        assert len(HABIT_LIBRARY) == 120

    def test_all_habits_have_required_fields(self):
        from app.services.habit_library import HABIT_LIBRARY
        required = ["key", "name", "category", "habit_type", "difficulty", "target_count"]
        for h in HABIT_LIBRARY:
            for f in required:
                assert f in h, f"Missing {f} in habit {h.get('key','?')}"

    def test_all_keys_unique(self):
        from app.services.habit_library import HABIT_LIBRARY
        keys = [h["key"] for h in HABIT_LIBRARY]
        assert len(keys) == len(set(keys))

    def test_all_habit_types_valid(self):
        from app.services.habit_library import HABIT_LIBRARY
        valid = {"binary", "quantity", "duration", "avoid", "checklist"}
        for h in HABIT_LIBRARY:
            assert h["habit_type"] in valid, f"{h['key']} has invalid type {h['habit_type']}"

    def test_all_difficulties_valid(self):
        from app.services.habit_library import HABIT_LIBRARY
        valid = {"easy", "medium", "hard", "epic"}
        for h in HABIT_LIBRARY:
            assert h["difficulty"] in valid

    def test_avoid_habits_have_target_zero(self):
        from app.services.habit_library import HABIT_LIBRARY
        for h in HABIT_LIBRARY:
            if h["habit_type"] == "avoid":
                assert h["target_count"] == 0, f"{h['key']} should have target 0"

    def test_category_distribution(self):
        from app.services.habit_library import HABIT_LIBRARY
        cats = {}
        for h in HABIT_LIBRARY:
            cats[h["category"]] = cats.get(h["category"], 0) + 1
        assert cats.get("ibadah", 0) >= 8
        assert cats.get("quran", 0) >= 8
        assert cats.get("dhikr", 0) >= 8

    def test_dhikr_presets(self):
        from app.services.habit_library import DHIKR_PRESETS
        assert len(DHIKR_PRESETS) == 7
        for p in DHIKR_PRESETS:
            assert "type" in p and "label" in p and "arabic" in p and "target" in p


class TestStreakCalculation:
    def test_empty_logs_zero_streak(self):
        from app.routers.habits import _streak
        result = _streak([], 1)
        assert result == {"current_streak": 0, "longest_streak": 0}

    def test_single_today_streak_1(self):
        from app.routers.habits import _streak

        class FakeLog:
            def __init__(self, d, completed=True, count=1):
                self.log_date = d; self.completed = completed; self.count = count

        today = date.today()
        result = _streak([FakeLog(today)], 1)
        assert result["current_streak"] == 1

    def test_consecutive_5_days(self):
        from app.routers.habits import _streak
        from datetime import timedelta

        class FL:
            def __init__(self, d): self.log_date=d; self.completed=True; self.count=1

        today = date.today()
        logs = [FL(today - timedelta(days=i)) for i in range(5)]
        r = _streak(logs, 1)
        assert r["current_streak"] == 5
        assert r["longest_streak"] == 5

    def test_broken_streak_resets(self):
        from app.routers.habits import _streak
        from datetime import timedelta

        class FL:
            def __init__(self, d): self.log_date=d; self.completed=True; self.count=1

        today = date.today()
        # Gap at day 3
        logs = [FL(today), FL(today-timedelta(1)), FL(today-timedelta(5))]
        r = _streak(logs, 1)
        assert r["current_streak"] == 2
        assert r["longest_streak"] == 2


class TestHabitCRUD:
    @pytest.mark.anyio
    async def test_create_binary_habit(self, client, auth_headers):
        resp = await client.post("/api/v1/habits", json={"name": "Read Quran", "category": "quran", "habit_type": "binary", "difficulty": "easy", "target_count": 1, "icon": "📖"}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["name"] == "Read Quran"
        assert d["habit_type"] == "binary"
        assert d["difficulty"] == "easy"
        assert d["rahmah_tokens"] == 0

    @pytest.mark.anyio
    async def test_create_quantity_habit(self, client, auth_headers):
        resp = await client.post("/api/v1/habits", json={"name": "Drink water", "category": "health", "habit_type": "quantity", "difficulty": "easy", "target_count": 8, "unit": "glasses"}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["habit_type"] == "quantity"

    @pytest.mark.anyio
    async def test_create_avoid_habit(self, client, auth_headers):
        resp = await client.post("/api/v1/habits", json={"name": "No backbiting", "category": "avoid", "habit_type": "avoid", "difficulty": "hard", "target_count": 0}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["target_count"] == 0

    @pytest.mark.anyio
    async def test_habit_with_implementation_intention(self, client, auth_headers):
        resp = await client.post("/api/v1/habits", json={"name": "Morning adhkar", "category": "dhikr", "habit_type": "checklist", "difficulty": "medium", "target_count": 1, "implementation_intention": "After Fajr prayer, I will recite morning adhkar"}, headers=auth_headers)
        assert resp.status_code == 201
        assert "After Fajr" in resp.json()["implementation_intention"]

    @pytest.mark.anyio
    async def test_habit_with_islamic_source(self, client, auth_headers):
        resp = await client.post("/api/v1/habits", json={"name": "Fajr on time", "category": "ibadah", "habit_type": "binary", "difficulty": "hard", "target_count": 1, "islamic_source": "Bukhari 543"}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["islamic_source"] == "Bukhari 543"

    @pytest.mark.anyio
    async def test_log_habit_updates_streak(self, client, auth_headers):
        add = await client.post("/api/v1/habits", json={"name": "Test habit", "category": "personal", "habit_type": "binary", "difficulty": "easy", "target_count": 1}, headers=auth_headers)
        hid = add.json()["id"]
        log = await client.post("/api/v1/habits/log", json={"habit_id": hid, "log_date": str(date.today()), "count": 1, "completed": True}, headers=auth_headers)
        assert log.status_code == 201
        detail = await client.get(f"/api/v1/habits/{hid}", headers=auth_headers)
        assert detail.json()["completed_today"] is True

    @pytest.mark.anyio
    async def test_reorder_habit(self, client, auth_headers):
        add = await client.post("/api/v1/habits", json={"name": "Stack habit", "category": "personal", "habit_type": "binary", "difficulty": "easy", "target_count": 1}, headers=auth_headers)
        hid = add.json()["id"]
        resp = await client.post(f"/api/v1/habits/{hid}/reorder?order=3", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["habit_stack_order"] == 3


class TestHabitLibraryEndpoints:
    @pytest.mark.anyio
    async def test_browse_library(self, client, auth_headers):
        resp = await client.get("/api/v1/habits/library", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 120

    @pytest.mark.anyio
    async def test_filter_by_category(self, client, auth_headers):
        resp = await client.get("/api/v1/habits/library?category=quran", headers=auth_headers)
        assert resp.status_code == 200
        for h in resp.json():
            assert h["category"] == "quran"

    @pytest.mark.anyio
    async def test_filter_by_difficulty(self, client, auth_headers):
        resp = await client.get("/api/v1/habits/library?difficulty=easy", headers=auth_headers)
        assert resp.status_code == 200
        for h in resp.json():
            assert h["difficulty"] == "easy"

    @pytest.mark.anyio
    async def test_add_from_library(self, client, auth_headers):
        resp = await client.post("/api/v1/habits/from-library?key=fajr_ontime", headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["name"] == "Pray Fajr on time"
        assert d["is_preset"] is True
        assert d["islamic_source"] is not None

    @pytest.mark.anyio
    async def test_add_nonexistent_library_key_404(self, client, auth_headers):
        resp = await client.post("/api/v1/habits/from-library?key=does_not_exist", headers=auth_headers)
        assert resp.status_code == 404


class TestAnalytics:
    @pytest.mark.anyio
    async def test_weekly_review_structure(self, client, auth_headers):
        resp = await client.get("/api/v1/habits/analytics/weekly", headers=auth_headers)
        assert resp.status_code == 200
        d = resp.json()
        for f in ["week_start", "week_end", "total_habits", "completion_rate", "habit_health_score"]:
            assert f in d

    @pytest.mark.anyio
    async def test_health_score_no_habits(self, client, auth_headers):
        resp = await client.get("/api/v1/habits/analytics/health", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["score"] == 0

    @pytest.mark.anyio
    async def test_per_habit_analytics(self, client, auth_headers):
        add = await client.post("/api/v1/habits", json={"name": "Analytics test", "category": "personal", "habit_type": "binary", "difficulty": "easy", "target_count": 1}, headers=auth_headers)
        hid = add.json()["id"]
        await client.post("/api/v1/habits/log", json={"habit_id": hid, "log_date": str(date.today()), "count": 1, "completed": True}, headers=auth_headers)
        resp = await client.get(f"/api/v1/habits/{hid}/analytics", headers=auth_headers)
        assert resp.status_code == 200
        d = resp.json()
        assert "heatmap" in d
        assert len(d["heatmap"]) == 365
        assert "day_of_week_rates" in d
        assert d["total_logs"] >= 1


class TestChecklistHabits:
    @pytest.mark.anyio
    async def test_add_checklist_item(self, client, auth_headers):
        add = await client.post("/api/v1/habits", json={"name": "Morning adhkar", "category": "dhikr", "habit_type": "checklist", "difficulty": "medium", "target_count": 1}, headers=auth_headers)
        hid = add.json()["id"]
        item = await client.post(f"/api/v1/habits/{hid}/checklist", json={"label": "Ayat al-Kursi", "sort_order": 0, "repetition_count": 1}, headers=auth_headers)
        assert item.status_code == 201
        assert item.json()["label"] == "Ayat al-Kursi"

    @pytest.mark.anyio
    async def test_list_checklist_items(self, client, auth_headers):
        add = await client.post("/api/v1/habits", json={"name": "Checklist habit", "category": "dhikr", "habit_type": "checklist", "difficulty": "easy", "target_count": 1}, headers=auth_headers)
        hid = add.json()["id"]
        await client.post(f"/api/v1/habits/{hid}/checklist", json={"label": "Step 1", "sort_order": 0}, headers=auth_headers)
        await client.post(f"/api/v1/habits/{hid}/checklist", json={"label": "Step 2", "sort_order": 1}, headers=auth_headers)
        resp = await client.get(f"/api/v1/habits/{hid}/checklist", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.anyio
    async def test_toggle_checklist_item(self, client, auth_headers):
        add = await client.post("/api/v1/habits", json={"name": "Toggle test", "category": "dhikr", "habit_type": "checklist", "difficulty": "easy", "target_count": 1}, headers=auth_headers)
        hid = add.json()["id"]
        item = await client.post(f"/api/v1/habits/{hid}/checklist", json={"label": "Step A", "sort_order": 0}, headers=auth_headers)
        iid = item.json()["id"]
        resp = await client.post(f"/api/v1/habits/{hid}/checklist/{iid}/log", headers=auth_headers)
        assert resp.status_code == 200


class TestDhikrCounter:
    @pytest.mark.anyio
    async def test_presets_returned(self, client, auth_headers):
        resp = await client.get("/api/v1/dhikr/presets", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 7

    @pytest.mark.anyio
    async def test_start_dhikr_session(self, client, auth_headers):
        resp = await client.post("/api/v1/dhikr/sessions", json={"dhikr_type": "subhanallah", "target_count": 33}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["dhikr_type"] == "subhanallah"
        assert d["target_count"] == 33
        assert d["current_count"] == 0
        assert d["is_completed"] is False

    @pytest.mark.anyio
    async def test_increment_dhikr(self, client, auth_headers):
        start = await client.post("/api/v1/dhikr/sessions", json={"dhikr_type": "alhamdulillah", "target_count": 33}, headers=auth_headers)
        sid = start.json()["id"]
        resp = await client.post(f"/api/v1/dhikr/sessions/{sid}/increment", json={"increment": 10}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["current_count"] == 10

    @pytest.mark.anyio
    async def test_dhikr_auto_completes_at_target(self, client, auth_headers):
        start = await client.post("/api/v1/dhikr/sessions", json={"dhikr_type": "allahu_akbar", "target_count": 5}, headers=auth_headers)
        sid = start.json()["id"]
        resp = await client.post(f"/api/v1/dhikr/sessions/{sid}/increment", json={"increment": 5}, headers=auth_headers)
        assert resp.json()["is_completed"] is True
        assert resp.json()["current_count"] == 5

    @pytest.mark.anyio
    async def test_dhikr_cannot_exceed_target(self, client, auth_headers):
        start = await client.post("/api/v1/dhikr/sessions", json={"dhikr_type": "istighfar", "target_count": 10}, headers=auth_headers)
        sid = start.json()["id"]
        # Try to add more than target
        resp = await client.post(f"/api/v1/dhikr/sessions/{sid}/increment", json={"increment": 50}, headers=auth_headers)
        assert resp.json()["current_count"] == 10  # capped at target

    @pytest.mark.anyio
    async def test_dhikr_history(self, client, auth_headers):
        start = await client.post("/api/v1/dhikr/sessions", json={"dhikr_type": "salawat", "target_count": 100}, headers=auth_headers)
        sid = start.json()["id"]
        await client.post(f"/api/v1/dhikr/sessions/{sid}/increment", json={"increment": 50}, headers=auth_headers)
        resp = await client.get("/api/v1/dhikr/history", headers=auth_headers)
        assert resp.status_code == 200
        history = {r["dhikr_type"]: r for r in resp.json()}
        assert "salawat" in history
        assert history["salawat"]["total_count"] == 50
