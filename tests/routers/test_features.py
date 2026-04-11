"""
Habits Router Tests
"""
import pytest
from datetime import date
from httpx import AsyncClient


class TestHabits:
    async def test_create_habit(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/habits",
            headers=auth_headers,
            json={
                "name": "Read Quran",
                "category": "quran",
                "frequency": "daily",
                "target_count": 1,
                "icon": "📖",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Read Quran"
        assert data["category"] == "quran"
        return data["id"]

    async def test_list_habits(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/habits",
            headers=auth_headers,
            json={"name": "Morning Dhikr", "category": "dhikr"},
        )
        resp = await client.get("/api/v1/habits", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_habit(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/habits",
            headers=auth_headers,
            json={"name": "Tahajjud", "category": "ibadah"},
        )
        habit_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/habits/{habit_id}",
            headers=auth_headers,
            json={"name": "Tahajjud Prayer", "target_count": 2},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Tahajjud Prayer"

    async def test_delete_habit(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/habits",
            headers=auth_headers,
            json={"name": "To Delete", "category": "personal"},
        )
        habit_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/habits/{habit_id}", headers=auth_headers)
        assert resp.status_code == 200

        # Should be gone
        resp2 = await client.get(f"/api/v1/habits/{habit_id}", headers=auth_headers)
        assert resp2.status_code == 404

    async def test_log_habit(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/habits",
            headers=auth_headers,
            json={"name": "Exercise", "category": "health"},
        )
        habit_id = create.json()["id"]
        resp = await client.post(
            "/api/v1/habits/log",
            headers=auth_headers,
            json={
                "habit_id": habit_id,
                "log_date": str(date.today()),
                "completed": True,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["completed"] is True

    async def test_habit_streak_shows_completed_today(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/habits",
            headers=auth_headers,
            json={"name": "Walk", "category": "health"},
        )
        habit_id = create.json()["id"]
        await client.post(
            "/api/v1/habits/log",
            headers=auth_headers,
            json={"habit_id": habit_id, "log_date": str(date.today()), "completed": True},
        )
        resp = await client.get(f"/api/v1/habits/{habit_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["completed_today"] is True


"""
Journal Router Tests
"""


class TestJournal:
    async def test_create_journal_entry(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/journal",
            headers=auth_headers,
            json={
                "content": "Today was a blessed day. Alhamdulillah.",
                "mood": "grateful",
                "entry_date": str(date.today()),
                "gratitude": "Health, family, and deen.",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["mood"] == "grateful"
        assert "Alhamdulillah" in data["content"]

    async def test_list_journal_entries(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/journal",
            headers=auth_headers,
            json={"content": "Entry 1", "entry_date": str(date.today())},
        )
        resp = await client.get("/api/v1/journal", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_journal_entry(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/journal",
            headers=auth_headers,
            json={"content": "Initial content", "entry_date": str(date.today())},
        )
        entry_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/journal/{entry_id}",
            headers=auth_headers,
            json={"content": "Updated content with more reflection."},
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated content with more reflection."

    async def test_delete_journal_entry(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/journal",
            headers=auth_headers,
            json={"content": "To be deleted", "entry_date": str(date.today())},
        )
        entry_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/journal/{entry_id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_cannot_access_other_users_entry(
        self, client: AsyncClient, auth_headers, registered_female_user
    ):
        create = await client.post(
            "/api/v1/journal",
            headers=auth_headers,
            json={"content": "Private thoughts", "entry_date": str(date.today())},
        )
        entry_id = create.json()["id"]
        female_headers = {"Authorization": f"Bearer {registered_female_user['access_token']}"}
        resp = await client.get(f"/api/v1/journal/{entry_id}", headers=female_headers)
        assert resp.status_code == 404


"""
Tasks Router Tests
"""


class TestTasks:
    async def test_create_task(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={
                "title": "Prepare Friday khutbah notes",
                "priority": "high",
                "due_date": str(date.today()),
                "time_block": "after_fajr",
                "category": "ibadah",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Prepare Friday khutbah notes"
        assert data["time_block"] == "after_fajr"

    async def test_list_today_tasks(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"title": "Task today", "due_date": str(date.today())},
        )
        resp = await client.get("/api/v1/tasks/today", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_complete_task(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"title": "Complete me", "due_date": str(date.today())},
        )
        task_id = create.json()["id"]
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/complete", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["completed"] is True
        assert resp.json()["completed_at"] is not None

    async def test_filter_tasks_by_priority(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"title": "Urgent task", "priority": "urgent"},
        )
        await client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"title": "Low task", "priority": "low"},
        )
        resp = await client.get(
            "/api/v1/tasks?priority=urgent", headers=auth_headers
        )
        assert resp.status_code == 200
        tasks = resp.json()
        assert all(t["priority"] == "urgent" for t in tasks)


"""
Female Module Router Tests
"""


class TestFemaleModule:
    async def test_male_user_cannot_access_female_endpoints(
        self, client: AsyncClient, auth_headers
    ):
        resp = await client.get("/api/v1/female/cycles", headers=auth_headers)
        assert resp.status_code == 403

    async def test_start_cycle(self, client: AsyncClient, female_auth_headers):
        resp = await client.post(
            "/api/v1/female/cycles",
            headers=female_auth_headers,
            json={
                "start_date": str(date.today()),
                "notes": "Feeling well.",
                "symptoms": "Mild cramps",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["hayd_tuhr_status"] == "hayd"
        assert data["can_pray"] is False
        assert data["can_fast"] is False
        assert data["ghusl_required"] is False  # No end date yet
        assert data["notes"] == "Feeling well."    # Decrypted

    async def test_cannot_start_two_open_cycles(self, client: AsyncClient, female_auth_headers):
        await client.post(
            "/api/v1/female/cycles",
            headers=female_auth_headers,
            json={"start_date": str(date.today())},
        )
        resp = await client.post(
            "/api/v1/female/cycles",
            headers=female_auth_headers,
            json={"start_date": str(date.today())},
        )
        assert resp.status_code == 409

    async def test_close_cycle_triggers_ghusl(self, client: AsyncClient, female_auth_headers):
        from datetime import timedelta
        start = date.today() - timedelta(days=5)
        create = await client.post(
            "/api/v1/female/cycles",
            headers=female_auth_headers,
            json={"start_date": str(start)},
        )
        cycle_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/female/cycles/{cycle_id}",
            headers=female_auth_headers,
            json={"end_date": str(date.today())},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ghusl_required"] is True
        assert data["duration_days"] == 6

    async def test_mark_ghusl_done(self, client: AsyncClient, female_auth_headers):
        from datetime import timedelta
        start = date.today() - timedelta(days=4)
        create = await client.post(
            "/api/v1/female/cycles",
            headers=female_auth_headers,
            json={"start_date": str(start)},
        )
        cycle_id = create.json()["id"]
        await client.patch(
            f"/api/v1/female/cycles/{cycle_id}",
            headers=female_auth_headers,
            json={"end_date": str(date.today())},
        )
        resp = await client.patch(
            f"/api/v1/female/cycles/{cycle_id}",
            headers=female_auth_headers,
            json={"ghusl_done": True, "ghusl_date": str(date.today())},
        )
        assert resp.status_code == 200
        assert resp.json()["ghusl_done"] is True

    async def test_get_current_cycle(self, client: AsyncClient, female_auth_headers):
        await client.post(
            "/api/v1/female/cycles",
            headers=female_auth_headers,
            json={"start_date": str(date.today())},
        )
        resp = await client.get("/api/v1/female/cycles/current", headers=female_auth_headers)
        assert resp.status_code == 200

    async def test_current_cycle_404_in_tuhr(self, client: AsyncClient, female_auth_headers):
        resp = await client.get("/api/v1/female/cycles/current", headers=female_auth_headers)
        assert resp.status_code == 404
        assert "tuhr" in resp.json()["detail"]

    async def test_log_missed_ramadan_fast(self, client: AsyncClient, female_auth_headers):
        resp = await client.post(
            "/api/v1/female/fasting",
            headers=female_auth_headers,
            json={
                "fast_date": str(date.today()),
                "fast_type": "ramadan",
                "completed": False,
                "reason_missed": "hayd",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["fidya_applicable"] is True

    async def test_missed_fast_summary(self, client: AsyncClient, female_auth_headers):
        from datetime import timedelta
        for i in range(3):
            await client.post(
                "/api/v1/female/fasting",
                headers=female_auth_headers,
                json={
                    "fast_date": str(date.today() - timedelta(days=i)),
                    "fast_type": "ramadan",
                    "completed": False,
                    "reason_missed": "hayd",
                },
            )
        resp = await client.get(
            f"/api/v1/female/fasting/missed-summary?year={date.today().year}",
            headers=female_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_missed"] == 3
        assert data["remaining_qadha"] == 3
