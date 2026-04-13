"""
Phase 2 Prayer Ecosystem Tests
===============================
Tests: offline prayer times, enhanced logging (congregation/khushu),
       heatmap, stats, travel mode, Islamic events.
"""
import pytest
from datetime import date
from math import radians, sin, cos, sqrt, atan2


# ─── Utility: Haversine ───────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


class TestHaversineDistance:
    def test_mecca_to_london(self):
        dist = haversine_km(21.4225, 39.8262, 51.5074, -0.1278)
        assert 4500 < dist < 5500   # ~4857 km

    def test_same_point_is_zero(self):
        assert haversine_km(10.0, 10.0, 10.0, 10.0) == pytest.approx(0.0, abs=0.01)

    def test_100km_north_exceeds_threshold(self):
        dist = haversine_km(51.0, 0.0, 51.9, 0.0)
        assert dist > 80

    def test_short_trip_below_threshold(self):
        dist = haversine_km(51.0, 0.0, 51.09, 0.0)
        assert dist < 80


# ─── Travel mode ──────────────────────────────────────────────────────────────

class TestTravelMode:
    @pytest.mark.anyio
    async def test_travel_mode_with_location(self, client, auth_headers):
        # First set user location
        await client.patch(
            "/api/v1/users/me",
            json={"latitude": 21.4, "longitude": 39.8},
            headers=auth_headers,
        )
        # Now check travel (100km away)
        resp = await client.get(
            "/api/v1/prayer/travel-mode",
            params={"lat": 22.4, "lng": 39.8},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "is_travelling" in data
        assert "distance_from_home_km" in data
        assert "qasr_applicable" in data
        assert "madhab_notes" in data
        assert data["distance_from_home_km"] > 0

    @pytest.mark.anyio
    async def test_travel_mode_no_location_422(self, client, auth_headers):
        # User has no location set by default → 422
        resp = await client.get(
            "/api/v1/prayer/travel-mode",
            params={"lat": 22.0, "lng": 40.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_same_location_not_travelling(self, client, auth_headers):
        await client.patch("/api/v1/users/me", json={"latitude": 51.5, "longitude": -0.12}, headers=auth_headers)
        resp = await client.get("/api/v1/prayer/travel-mode", params={"lat": 51.5, "lng": -0.12}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_travelling"] is False


# ─── Enhanced prayer logging ──────────────────────────────────────────────────

class TestEnhancedPrayerLogging:
    @pytest.mark.anyio
    async def test_log_with_congregation_and_khushu(self, client, auth_headers):
        payload = {
            "prayer_name": "fajr",
            "log_date": str(date.today()),
            "status": "on_time",
            "with_congregation": True,
            "khushu_rating": 4,
            "location_name": "Al-Noor Mosque",
        }
        resp = await client.post("/api/v1/prayer/log", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["with_congregation"] is True
        assert data["khushu_rating"] == 4
        assert data["location_name"] == "Al-Noor Mosque"
        assert data["status"] == "on_time"

    @pytest.mark.anyio
    async def test_log_without_optional_fields(self, client, auth_headers):
        payload = {"prayer_name": "dhuhr", "log_date": str(date.today()), "status": "late"}
        resp = await client.post("/api/v1/prayer/log", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["with_congregation"] is False
        assert data["khushu_rating"] is None
        assert data["location_name"] is None

    @pytest.mark.anyio
    async def test_upsert_updates_existing(self, client, auth_headers):
        log_date = str(date.today())
        await client.post("/api/v1/prayer/log", json={"prayer_name": "asr", "log_date": log_date, "status": "late"}, headers=auth_headers)
        resp = await client.post("/api/v1/prayer/log", json={"prayer_name": "asr", "log_date": log_date, "status": "on_time", "khushu_rating": 5}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["status"] == "on_time"
        assert resp.json()["khushu_rating"] == 5

    @pytest.mark.anyio
    async def test_excused_status_allowed(self, client, auth_headers):
        payload = {"prayer_name": "maghrib", "log_date": str(date.today()), "status": "excused"}
        resp = await client.post("/api/v1/prayer/log", json=payload, headers=auth_headers)
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_missed_status_allowed(self, client, auth_headers):
        payload = {"prayer_name": "isha", "log_date": str(date.today()), "status": "missed"}
        resp = await client.post("/api/v1/prayer/log", json=payload, headers=auth_headers)
        assert resp.status_code == 201


# ─── Stats, heatmap, weekly summary ──────────────────────────────────────────

class TestPrayerStats:
    @pytest.mark.anyio
    async def test_stats_returns_list(self, client, auth_headers):
        resp = await client.get("/api/v1/prayer/stats", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.anyio
    async def test_stats_with_data_has_correct_shape(self, client, auth_headers):
        # Log a prayer first
        await client.post("/api/v1/prayer/log", json={"prayer_name": "fajr", "log_date": str(date.today()), "status": "on_time", "with_congregation": True, "khushu_rating": 3}, headers=auth_headers)
        resp = await client.get("/api/v1/prayer/stats", headers=auth_headers)
        data = resp.json()
        fajr = next((r for r in data if r["prayer_name"] == "fajr"), None)
        assert fajr is not None
        assert "on_time_count" in fajr
        assert "on_time_rate" in fajr
        assert "congregation_rate" in fajr

    @pytest.mark.anyio
    async def test_heatmap_returns_list(self, client, auth_headers):
        resp = await client.get("/api/v1/prayer/heatmap", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.anyio
    async def test_heatmap_cell_shape(self, client, auth_headers):
        await client.post("/api/v1/prayer/log", json={"prayer_name": "fajr", "log_date": str(date.today()), "status": "on_time"}, headers=auth_headers)
        resp = await client.get("/api/v1/prayer/heatmap", headers=auth_headers)
        data = resp.json()
        assert len(data) >= 1
        cell = data[0]
        assert "date" in cell
        assert "count" in cell
        assert "on_time" in cell

    @pytest.mark.anyio
    async def test_weekly_summary_structure(self, client, auth_headers):
        resp = await client.get("/api/v1/prayer/weekly-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        required = ["week_start", "week_end", "total_prayers_possible", "total_prayed", "total_on_time", "on_time_pct", "congregation_count"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.anyio
    async def test_on_time_pct_is_percentage(self, client, auth_headers):
        resp = await client.get("/api/v1/prayer/weekly-summary", headers=auth_headers)
        pct = resp.json()["on_time_pct"]
        assert 0 <= pct <= 100


# ─── Islamic events ───────────────────────────────────────────────────────────

class TestIslamicEvents:
    @pytest.mark.anyio
    async def test_seed_returns_200(self, client, auth_headers):
        resp = await client.post("/api/v1/prayer/events/seed", headers=auth_headers)
        assert resp.status_code == 200
        assert "message" in resp.json()

    @pytest.mark.anyio
    async def test_list_events_after_seed(self, client, auth_headers):
        await client.post("/api/v1/prayer/events/seed", headers=auth_headers)
        resp = await client.get("/api/v1/prayer/events", headers=auth_headers)
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 13

    @pytest.mark.anyio
    async def test_seed_is_idempotent(self, client, auth_headers):
        await client.post("/api/v1/prayer/events/seed", headers=auth_headers)
        count1 = len((await client.get("/api/v1/prayer/events", headers=auth_headers)).json())
        await client.post("/api/v1/prayer/events/seed", headers=auth_headers)
        count2 = len((await client.get("/api/v1/prayer/events", headers=auth_headers)).json())
        assert count1 == count2

    @pytest.mark.anyio
    async def test_current_events_ramadan(self, client, auth_headers):
        await client.post("/api/v1/prayer/events/seed", headers=auth_headers)
        resp = await client.get("/api/v1/prayer/events/current", params={"hijri_month": 9, "hijri_day": 15}, headers=auth_headers)
        assert resp.status_code == 200
        events = resp.json()
        names = [e["name"] for e in events]
        assert any("Ramadan" in n for n in names)

    @pytest.mark.anyio
    async def test_events_have_required_fields(self, client, auth_headers):
        await client.post("/api/v1/prayer/events/seed", headers=auth_headers)
        events = (await client.get("/api/v1/prayer/events", headers=auth_headers)).json()
        for event in events:
            assert "name" in event
            assert "hijri_month" in event
            assert "hijri_day" in event
            assert "event_type" in event

    @pytest.mark.anyio
    async def test_no_events_outside_season(self, client, auth_headers):
        await client.post("/api/v1/prayer/events/seed", headers=auth_headers)
        # Month 5, day 15 has no events in seed data
        resp = await client.get("/api/v1/prayer/events/current", params={"hijri_month": 5, "hijri_day": 15}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ─── Pure unit tests on seed data ────────────────────────────────────────────

class TestIslamicEventSeedData:
    def test_all_have_required_fields(self):
        from app.services.islamic_events import ISLAMIC_EVENTS_SEED
        for e in ISLAMIC_EVENTS_SEED:
            assert "name" in e
            assert 1 <= e["hijri_month"] <= 12, f"Bad month in {e['name']}"
            assert 1 <= e["hijri_day"] <= 30,   f"Bad day in {e['name']}"
            assert "event_type" in e

    def test_ramadan_is_month_9_day_1(self):
        from app.services.islamic_events import ISLAMIC_EVENTS_SEED
        ramadan = next(e for e in ISLAMIC_EVENTS_SEED if e["name"] == "Ramadan begins")
        assert ramadan["hijri_month"] == 9
        assert ramadan["hijri_day"] == 1
        assert ramadan["duration_days"] == 30

    def test_two_eid_events(self):
        from app.services.islamic_events import ISLAMIC_EVENTS_SEED
        eids = [e for e in ISLAMIC_EVENTS_SEED if e["event_type"] == "eid"]
        assert len(eids) == 2

    def test_arafah_is_dhul_hijjah_9(self):
        from app.services.islamic_events import ISLAMIC_EVENTS_SEED
        arafah = next(e for e in ISLAMIC_EVENTS_SEED if "Arafah" in e["name"])
        assert arafah["hijri_month"] == 12
        assert arafah["hijri_day"] == 9

    def test_all_events_have_deed_or_notification(self):
        from app.services.islamic_events import ISLAMIC_EVENTS_SEED
        for e in ISLAMIC_EVENTS_SEED:
            has_content = e.get("deed_of_day") or e.get("notification_template") or e.get("description")
            assert has_content, f"{e['name']} has no deed/notification/description"

    def test_seed_count_is_13(self):
        from app.services.islamic_events import ISLAMIC_EVENTS_SEED
        assert len(ISLAMIC_EVENTS_SEED) == 13
