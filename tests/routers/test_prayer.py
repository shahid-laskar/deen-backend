"""
Prayer Router Tests
"""
import pytest
from datetime import date
from httpx import AsyncClient


class TestPrayerTimes:
    async def test_prayer_times_no_location(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/prayer/times", headers=auth_headers)
        assert resp.status_code == 422
        assert "Location not set" in resp.json()["detail"]


class TestPrayerLog:
    async def test_log_prayer(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/prayer/log",
            headers=auth_headers,
            json={
                "prayer_name": "fajr",
                "log_date": str(date.today()),
                "status": "on_time",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["prayer_name"] == "fajr"
        assert data["status"] == "on_time"

    async def test_log_prayer_upsert(self, client: AsyncClient, auth_headers):
        """Logging same prayer twice should update, not duplicate."""
        today = str(date.today())
        await client.post(
            "/api/v1/prayer/log",
            headers=auth_headers,
            json={"prayer_name": "fajr", "log_date": today, "status": "on_time"},
        )
        resp = await client.post(
            "/api/v1/prayer/log",
            headers=auth_headers,
            json={"prayer_name": "fajr", "log_date": today, "status": "late"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "late"

    async def test_get_prayer_logs(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/prayer/log",
            headers=auth_headers,
            json={"prayer_name": "dhuhr", "log_date": str(date.today()), "status": "on_time"},
        )
        resp = await client.get("/api/v1/prayer/log", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_prayer_summary_today(self, client: AsyncClient, auth_headers):
        today = str(date.today())
        for prayer in ["fajr", "dhuhr", "asr", "maghrib", "isha"]:
            await client.post(
                "/api/v1/prayer/log",
                headers=auth_headers,
                json={"prayer_name": prayer, "log_date": today, "status": "on_time"},
            )
        resp = await client.get("/api/v1/prayer/summary/today", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_logged"] == 5
        assert data["total_on_time"] == 5
        assert data["completion_pct"] == 100.0

    async def test_prayer_streak(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/prayer/streak", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "current_streak" in data
        assert "longest_streak" in data

    async def test_unauthenticated_prayer_log(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/prayer/log",
            json={"prayer_name": "fajr", "log_date": str(date.today())},
        )
        assert resp.status_code == 401
