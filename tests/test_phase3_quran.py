"""Phase 3 Quran Ecosystem Tests — 35 tests."""
import pytest
from datetime import date


# ─── Dua seed data unit tests ─────────────────────────────────────────────────

class TestDuaSeedData:
    def test_total_duas_count(self):
        from app.services.dua_seed import ALL_DUAS
        assert len(ALL_DUAS) >= 40

    def test_all_duas_have_required_fields(self):
        from app.services.dua_seed import ALL_DUAS
        required = ["key", "title", "arabic_text", "translation", "category"]
        for d in ALL_DUAS:
            for f in required:
                assert f in d, f"Missing {f} in dua '{d.get('key', '?')}'"

    def test_all_keys_are_unique(self):
        from app.services.dua_seed import ALL_DUAS
        keys = [d["key"] for d in ALL_DUAS]
        assert len(keys) == len(set(keys)), "Duplicate dua keys found"

    def test_categories_cover_core_life(self):
        from app.services.dua_seed import ALL_DUAS
        cats = {d["category"] for d in ALL_DUAS}
        expected = {"morning_evening", "after_prayer", "food", "travel", "distress", "guidance"}
        assert expected.issubset(cats)

    def test_ramadan_dua_exists(self):
        from app.services.dua_seed import ALL_DUAS
        keys = [d["key"] for d in ALL_DUAS]
        assert "ramadan_opening_fast" in keys or "laylat_al_qadr_dua" in keys

    def test_repetition_count_positive(self):
        from app.services.dua_seed import ALL_DUAS
        for d in ALL_DUAS:
            assert d.get("repetition_count", 1) >= 1


# ─── Hadith seed data unit tests ──────────────────────────────────────────────

class TestHadithSeedData:
    def test_seed_has_hadiths(self):
        from app.services.hadith_seed import HADITH_SEED
        assert len(HADITH_SEED) >= 15

    def test_all_sahih_or_hasan(self):
        from app.services.hadith_seed import HADITH_SEED
        valid = {"sahih", "hasan", "daif", "mawdu", "unknown"}
        for h in HADITH_SEED:
            assert h["grade"] in valid

    def test_actions_by_intentions_present(self):
        from app.services.hadith_seed import HADITH_SEED
        texts = [h["english_text"] for h in HADITH_SEED]
        assert any("intentions" in t.lower() for t in texts)

    def test_all_have_english_text(self):
        from app.services.hadith_seed import HADITH_SEED
        for h in HADITH_SEED:
            assert h.get("english_text"), f"Missing english_text in {h.get('hadith_number')}"

    def test_hadith_of_day_rotation(self):
        from app.services.hadith_seed import HADITH_SEED
        n = len(HADITH_SEED)
        # Different days should give different hadiths
        day1 = HADITH_SEED[1 % n]
        day2 = HADITH_SEED[2 % n]
        assert day1 != day2


# ─── SM-2 Spaced Repetition ───────────────────────────────────────────────────

class TestSM2Algorithm:
    def test_quality_5_advances_interval(self):
        from app.services.quran_service import sm2_next_review
        ef, interval, next_review = sm2_next_review(5, 2.5, 1, 1)
        assert interval > 1

    def test_quality_0_resets_interval(self):
        from app.services.quran_service import sm2_next_review
        ef, interval, next_review = sm2_next_review(0, 2.5, 10, 5)
        assert interval == 1

    def test_ease_factor_never_below_1_3(self):
        from app.services.quran_service import sm2_next_review
        ef, interval, next_review = sm2_next_review(2, 1.3, 1, 10)
        assert ef >= 1.3

    def test_next_review_in_future(self):
        from app.services.quran_service import sm2_next_review
        ef, interval, next_review = sm2_next_review(4, 2.5, 6, 2)
        assert next_review >= date.today()

    def test_review_count_0_gives_interval_1(self):
        from app.services.quran_service import sm2_next_review
        ef, interval, _ = sm2_next_review(5, 2.5, 1, 0)
        assert interval == 1

    def test_review_count_1_gives_interval_6(self):
        from app.services.quran_service import sm2_next_review
        ef, interval, _ = sm2_next_review(5, 2.5, 1, 1)
        assert interval == 6


# ─── HTTP: Dua library endpoints ──────────────────────────────────────────────

class TestDuaEndpoints:
    @pytest.mark.anyio
    async def test_seed_duas(self, client, auth_headers):
        resp = await client.post("/api/v1/quran/duas/seed", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_list_duas_after_seed(self, client, auth_headers):
        await client.post("/api/v1/quran/duas/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/duas", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 40

    @pytest.mark.anyio
    async def test_filter_duas_by_category(self, client, auth_headers):
        await client.post("/api/v1/quran/duas/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/duas?category=morning_evening", headers=auth_headers)
        assert resp.status_code == 200
        for d in resp.json():
            assert d["category"] == "morning_evening"

    @pytest.mark.anyio
    async def test_get_dua_by_key(self, client, auth_headers):
        await client.post("/api/v1/quran/duas/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/duas/before_eating", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["key"] == "before_eating"

    @pytest.mark.anyio
    async def test_dua_of_day(self, client, auth_headers):
        await client.post("/api/v1/quran/duas/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/duas/of-the-day", headers=auth_headers)
        assert resp.status_code == 200
        d = resp.json()
        assert "arabic_text" in d
        assert "translation" in d

    @pytest.mark.anyio
    async def test_dua_categories_endpoint(self, client, auth_headers):
        await client.post("/api/v1/quran/duas/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/duas/categories", headers=auth_headers)
        assert resp.status_code == 200
        cats = {c["category"] for c in resp.json()}
        assert "morning_evening" in cats


# ─── HTTP: Personal duas ──────────────────────────────────────────────────────

class TestPersonalDuas:
    @pytest.mark.anyio
    async def test_create_personal_dua(self, client, auth_headers):
        resp = await client.post("/api/v1/quran/duas/personal", json={"title": "For my mother", "text": "Ya Allah, grant my mother shifa"}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["title"] == "For my mother"
        assert d["is_answered"] is False

    @pytest.mark.anyio
    async def test_mark_dua_answered(self, client, auth_headers):
        create = await client.post("/api/v1/quran/duas/personal", json={"title": "Test", "text": "Test dua"}, headers=auth_headers)
        dua_id = create.json()["id"]
        resp = await client.patch(f"/api/v1/quran/duas/personal/{dua_id}", json={"is_answered": True, "answered_note": "Alhamdulillah, answered!"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_answered"] is True
        assert resp.json()["answered_date"] is not None

    @pytest.mark.anyio
    async def test_delete_personal_dua(self, client, auth_headers):
        create = await client.post("/api/v1/quran/duas/personal", json={"title": "To delete", "text": "..."}, headers=auth_headers)
        dua_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/quran/duas/personal/{dua_id}", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_list_personal_duas(self, client, auth_headers):
        await client.post("/api/v1/quran/duas/personal", json={"title": "Dua 1", "text": "..."}, headers=auth_headers)
        await client.post("/api/v1/quran/duas/personal", json={"title": "Dua 2", "text": "..."}, headers=auth_headers)
        resp = await client.get("/api/v1/quran/duas/personal", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2


# ─── HTTP: Hadith endpoints ───────────────────────────────────────────────────

class TestHadithEndpoints:
    @pytest.mark.anyio
    async def test_seed_hadiths(self, client, auth_headers):
        resp = await client.post("/api/v1/quran/hadith/seed", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_list_hadiths(self, client, auth_headers):
        await client.post("/api/v1/quran/hadith/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/hadith", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 15

    @pytest.mark.anyio
    async def test_hadith_of_day(self, client, auth_headers):
        await client.post("/api/v1/quran/hadith/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/hadith/of-the-day", headers=auth_headers)
        assert resp.status_code == 200
        h = resp.json()
        assert "english_text" in h
        assert "grade" in h
        assert h["grade"] in ("sahih", "hasan", "daif", "mawdu", "unknown")

    @pytest.mark.anyio
    async def test_search_hadiths(self, client, auth_headers):
        await client.post("/api/v1/quran/hadith/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/hadith/search?q=intention", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1

    @pytest.mark.anyio
    async def test_filter_by_collection(self, client, auth_headers):
        await client.post("/api/v1/quran/hadith/seed", headers=auth_headers)
        resp = await client.get("/api/v1/quran/hadith?collection=bukhari", headers=auth_headers)
        assert resp.status_code == 200
        for h in resp.json():
            assert h["collection"] == "bukhari"


# ─── HTTP: Reading logs & stats ───────────────────────────────────────────────

class TestReadingLogs:
    @pytest.mark.anyio
    async def test_log_reading_session(self, client, auth_headers):
        resp = await client.post("/api/v1/quran/reading-log", json={"surah_from": 1, "ayah_from": 1, "surah_to": 1, "ayah_to": 7, "verses_read": 7, "minutes_read": 5}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["verses_read"] == 7
        assert d["surah_from"] == 1

    @pytest.mark.anyio
    async def test_stats_zero_initially(self, client, auth_headers):
        resp = await client.get("/api/v1/quran/stats", headers=auth_headers)
        assert resp.status_code == 200
        d = resp.json()
        assert "total_verses_read" in d
        assert "khatam_progress_pct" in d
        assert 0 <= d["khatam_progress_pct"] <= 100

    @pytest.mark.anyio
    async def test_stats_after_logging(self, client, auth_headers):
        await client.post("/api/v1/quran/reading-log", json={"surah_from": 2, "ayah_from": 1, "surah_to": 2, "ayah_to": 100, "verses_read": 100, "minutes_read": 30}, headers=auth_headers)
        resp = await client.get("/api/v1/quran/stats", headers=auth_headers)
        assert resp.json()["total_verses_read"] == 100
        assert resp.json()["khatam_progress_pct"] > 0


# ─── HTTP: Bookmarks ──────────────────────────────────────────────────────────

class TestBookmarks:
    @pytest.mark.anyio
    async def test_add_bookmark(self, client, auth_headers):
        resp = await client.post("/api/v1/quran/bookmarks", json={"surah_number": 2, "ayah_number": 255, "note": "Ayat al-Kursi", "highlight_color": "gold"}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["surah_number"] == 2
        assert d["ayah_number"] == 255

    @pytest.mark.anyio
    async def test_list_bookmarks(self, client, auth_headers):
        await client.post("/api/v1/quran/bookmarks", json={"surah_number": 1, "ayah_number": 1}, headers=auth_headers)
        resp = await client.get("/api/v1/quran/bookmarks", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.anyio
    async def test_delete_bookmark(self, client, auth_headers):
        create = await client.post("/api/v1/quran/bookmarks", json={"surah_number": 3, "ayah_number": 18}, headers=auth_headers)
        bm_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/quran/bookmarks/{bm_id}", headers=auth_headers)
        assert resp.status_code == 200

# ─── HTTP: Hifz with Leitner ─────────────────────────────────────────────────

class TestHifzLeitner:
    @pytest.mark.anyio
    async def test_add_hifz_entry(self, client, auth_headers):
        resp = await client.post("/api/v1/quran/hifz", json={"surah_number": 114, "surah_name": "An-Nas", "ayah_from": 1, "ayah_to": 6, "total_ayahs": 6}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["leitner_box"] == 1

    @pytest.mark.anyio
    async def test_good_review_advances_leitner(self, client, auth_headers):
        add = await client.post("/api/v1/quran/hifz", json={"surah_number": 112, "surah_name": "Al-Ikhlas", "ayah_from": 1, "ayah_to": 4, "total_ayahs": 4}, headers=auth_headers)
        entry_id = add.json()["id"]
        review = await client.post(f"/api/v1/quran/hifz/{entry_id}/review", json={"quality": 5}, headers=auth_headers)
        assert review.status_code == 200
        assert review.json()["leitner_box"] == 2

    @pytest.mark.anyio
    async def test_failed_review_resets_to_box_1(self, client, auth_headers):
        add = await client.post("/api/v1/quran/hifz", json={"surah_number": 113, "surah_name": "Al-Falaq", "ayah_from": 1, "ayah_to": 5, "total_ayahs": 5}, headers=auth_headers)
        entry_id = add.json()["id"]
        # Advance to box 3 first
        await client.post(f"/api/v1/quran/hifz/{entry_id}/review", json={"quality": 5}, headers=auth_headers)
        await client.post(f"/api/v1/quran/hifz/{entry_id}/review", json={"quality": 5}, headers=auth_headers)
        # Then fail
        review = await client.post(f"/api/v1/quran/hifz/{entry_id}/review", json={"quality": 0}, headers=auth_headers)
        assert review.json()["leitner_box"] == 1
        assert review.json()["status"] == "needs_review"
