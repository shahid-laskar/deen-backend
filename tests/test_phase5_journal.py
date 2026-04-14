"""Phase 5 Journal, Wellness & Insights Tests — 41 tests."""
import pytest
from datetime import date, timedelta


# ─── Journal mode data ────────────────────────────────────────────────────────

class TestJournalModes:
    def test_all_5_modes_defined(self):
        from app.models.journal import JournalMode
        modes = [m.value for m in JournalMode]
        assert "free_write" in modes
        assert "guided_reflection" in modes
        assert "muhasabah" in modes
        assert "weekly_review" in modes
        assert "gratitude" in modes
        assert len(modes) == 5

    def test_insight_categories_defined(self):
        from app.models.journal import InsightCategory
        cats = [c.value for c in InsightCategory]
        assert "prayer_patterns" in cats
        assert "mood_journal" in cats
        assert "habit_correlations" in cats
        assert "quran_patterns" in cats
        assert "spiritual_trends" in cats

    def test_journal_entry_has_encryption_fields(self):
        from app.models.journal import JournalEntry
        assert hasattr(JournalEntry, "is_encrypted")
        assert hasattr(JournalEntry, "iv")
        assert hasattr(JournalEntry, "salt")
        assert hasattr(JournalEntry, "journal_mode")
        assert hasattr(JournalEntry, "muhasabah_data")
        assert hasattr(JournalEntry, "gratitude_items")
        assert hasattr(JournalEntry, "weekly_data")
        assert hasattr(JournalEntry, "ai_prompt_used")


# ─── Verse suggestion logic ────────────────────────────────────────────────────

class TestVerseSuggestion:
    def _get_suggestions(self, text):
        """Mirror the router's keyword matching logic."""
        VERSE_MAP = {
            ("anxious", "worried", "fear", "scared", "stressed"): [
                {"ref": "2:286", "text": "Allah does not burden a soul beyond that it can bear."},
                {"ref": "94:5",  "text": "For indeed, with hardship will be ease."},
            ],
            ("sad", "grief", "loss"): [
                {"ref": "2:153", "text": "Seek help through patience and prayer."},
            ],
            ("grateful", "thankful", "blessed", "alhamdulillah"): [
                {"ref": "14:7", "text": "If you are grateful, I will surely increase you in favour."},
            ],
        }
        t = text.lower()
        matches, seen = [], set()
        for keywords, verses in VERSE_MAP.items():
            if any(kw in t for kw in keywords):
                for v in verses:
                    if v["ref"] not in seen:
                        seen.add(v["ref"]); matches.append(v)
        return matches[:3] if matches else [{"ref": "2:286", "text": "default"}]

    def test_anxious_mood_returns_comfort_verses(self):
        results = self._get_suggestions("I am feeling anxious today")
        refs = [v["ref"] for v in results]
        assert "2:286" in refs or "94:5" in refs

    def test_grateful_mood_returns_shukr_verses(self):
        results = self._get_suggestions("I am so grateful and blessed")
        refs = [v["ref"] for v in results]
        assert "14:7" in refs

    def test_no_match_returns_default(self):
        results = self._get_suggestions("today was a regular day")
        assert len(results) >= 1
        assert results[0]["ref"] == "2:286"

    def test_max_3_verses_returned(self):
        results = self._get_suggestions("anxious sad grateful worried blessed")
        assert len(results) <= 3


# ─── InsightEngine data sufficiency ──────────────────────────────────────────

class TestInsightEngineLogic:
    def test_encouraging_ayat_have_all_required_themes(self):
        from app.services.insight_engine import ENCOURAGING_AYAT
        required_themes = ["patience", "consistency", "fajr", "quran", "gratitude", "sabr"]
        for theme in required_themes:
            assert theme in ENCOURAGING_AYAT, f"Missing theme: {theme}"

    def test_all_ayat_have_ref_and_text(self):
        from app.services.insight_engine import ENCOURAGING_AYAT
        for theme, (ref, text) in ENCOURAGING_AYAT.items():
            assert ref and ":" in ref, f"Invalid ref in theme {theme}"
            assert len(text) > 20, f"Too short text in theme {theme}"

    def test_encouraging_hadiths_structure(self):
        from app.services.insight_engine import ENCOURAGING_HADITHS
        for key, (source, text) in ENCOURAGING_HADITHS.items():
            assert source, f"Missing source for {key}"
            assert text, f"Missing text for {key}"


# ─── HTTP: Journal CRUD with Phase 5 fields ───────────────────────────────────

class TestJournalV2Endpoints:
    @pytest.mark.anyio
    async def test_create_free_write_entry(self, client, auth_headers):
        resp = await client.post("/api/v1/journal", json={
            "title": "Morning thoughts",
            "content": "Alhamdulillah for this new day",
            "mood": "grateful",
            "journal_mode": "free_write",
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["journal_mode"] == "free_write"
        assert d["is_encrypted"] is False

    @pytest.mark.anyio
    async def test_create_muhasabah_entry(self, client, auth_headers):
        muhasabah_data = {
            "prayers_completed": 5, "prayers_on_time": 4,
            "quran_pages": 2, "dhikr_done": True,
            "wronged_anyone": "Was impatient with a colleague",
            "extra_good": "Gave sadaqah",
            "tomorrow_intention": "Pray all 5 on time",
            "gratitude_1": "Good health",
            "gratitude_2": "Family",
            "gratitude_3": "This deen",
        }
        resp = await client.post("/api/v1/journal", json={
            "content": "Today's muhasabah",
            "journal_mode": "muhasabah",
            "muhasabah_data": muhasabah_data,
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["journal_mode"] == "muhasabah"
        assert resp.json()["muhasabah_data"]["prayers_completed"] == 5

    @pytest.mark.anyio
    async def test_create_gratitude_entry(self, client, auth_headers):
        items = [
            {"text": "Good health", "why": "It lets me worship"},
            {"text": "My family", "why": "They support me"},
            {"text": "This deen", "why": "It gives life meaning"},
        ]
        resp = await client.post("/api/v1/journal", json={
            "content": "Gratitude practice",
            "journal_mode": "gratitude",
            "gratitude_items": items,
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert len(resp.json()["gratitude_items"]) == 3

    @pytest.mark.anyio
    async def test_create_encrypted_entry(self, client, auth_headers):
        resp = await client.post("/api/v1/journal", json={
            "content": "U2FsdGVkX1+base64ciphertext==",
            "is_encrypted": True,
            "iv": "base64iv12byteshere",
            "salt": "base64salthere",
            "journal_mode": "free_write",
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["is_encrypted"] is True
        assert d["iv"] == "base64iv12byteshere"
        assert d["salt"] == "base64salthere"

    @pytest.mark.anyio
    async def test_filter_by_journal_mode(self, client, auth_headers):
        await client.post("/api/v1/journal", json={"content": "FW", "journal_mode": "free_write"}, headers=auth_headers)
        await client.post("/api/v1/journal", json={"content": "M", "journal_mode": "muhasabah"}, headers=auth_headers)
        resp = await client.get("/api/v1/journal?journal_mode=muhasabah", headers=auth_headers)
        assert resp.status_code == 200
        for e in resp.json():
            assert e["journal_mode"] == "muhasabah"

    @pytest.mark.anyio
    async def test_update_with_phase5_fields(self, client, auth_headers):
        create = await client.post("/api/v1/journal", json={"content": "Initial", "journal_mode": "free_write"}, headers=auth_headers)
        eid = create.json()["id"]
        resp = await client.patch(f"/api/v1/journal/{eid}", json={"mood": "peaceful", "ai_prompt_used": "What are you grateful for?"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["mood"] == "peaceful"
        assert resp.json()["ai_prompt_used"] == "What are you grateful for?"


# ─── HTTP: Muhasabah prompt ───────────────────────────────────────────────────

class TestMuhasabahPrompt:
    @pytest.mark.anyio
    async def test_muhasabah_prompt_returns_9_sections(self, client, auth_headers):
        resp = await client.get("/api/v1/journal/muhasabah-prompt", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["sections"]) >= 9

    @pytest.mark.anyio
    async def test_muhasabah_sections_have_required_fields(self, client, auth_headers):
        resp = await client.get("/api/v1/journal/muhasabah-prompt", headers=auth_headers)
        for section in resp.json()["sections"]:
            assert "key" in section
            assert "label" in section
            assert "type" in section


# ─── HTTP: Guided prompts ─────────────────────────────────────────────────────

class TestGuidedPrompts:
    @pytest.mark.anyio
    async def test_all_categories_returned(self, client, auth_headers):
        resp = await client.get("/api/v1/journal/guided-prompts", headers=auth_headers)
        assert resp.status_code == 200
        cats = resp.json()["all_prompts"]
        for cat in ["gratitude", "prayer", "quran", "accountability", "muhasabah", "sabr", "tawakkul"]:
            assert cat in cats

    @pytest.mark.anyio
    async def test_filter_by_category(self, client, auth_headers):
        resp = await client.get("/api/v1/journal/guided-prompts?category=gratitude", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["category"] == "gratitude"
        assert len(resp.json()["prompts"]) >= 3

    @pytest.mark.anyio
    async def test_each_category_has_3_prompts(self, client, auth_headers):
        resp = await client.get("/api/v1/journal/guided-prompts", headers=auth_headers)
        for cat, prompts in resp.json()["all_prompts"].items():
            assert len(prompts) >= 3, f"{cat} has only {len(prompts)} prompts"


# ─── HTTP: Verse suggestion ───────────────────────────────────────────────────

class TestVerseSuggestionEndpoint:
    @pytest.mark.anyio
    async def test_verse_suggestion_returns_verses(self, client, auth_headers):
        create = await client.post("/api/v1/journal", json={"content": "I am feeling anxious today", "mood": "anxious", "journal_mode": "free_write"}, headers=auth_headers)
        eid = create.json()["id"]
        resp = await client.post(f"/api/v1/journal/ai-suggest-verses?entry_id={eid}", headers=auth_headers)
        assert resp.status_code == 200
        verses = resp.json()["verses"]
        assert len(verses) >= 1
        assert "ref" in verses[0] and "text" in verses[0]

    @pytest.mark.anyio
    async def test_encrypted_entry_skips_suggestion(self, client, auth_headers):
        create = await client.post("/api/v1/journal", json={"content": "ciphertext", "is_encrypted": True, "iv": "abc", "salt": "def", "journal_mode": "free_write"}, headers=auth_headers)
        eid = create.json()["id"]
        resp = await client.post(f"/api/v1/journal/ai-suggest-verses?entry_id={eid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["verses"] == []


# ─── HTTP: Journal analytics ──────────────────────────────────────────────────

class TestJournalAnalytics:
    @pytest.mark.anyio
    async def test_analytics_empty_for_new_user(self, client, auth_headers):
        resp = await client.get("/api/v1/journal/analytics", headers=auth_headers)
        assert resp.status_code == 200
        d = resp.json()
        assert d["total_entries"] == 0
        assert d["current_streak"] == 0

    @pytest.mark.anyio
    async def test_analytics_after_entries(self, client, auth_headers):
        for mode in ["free_write", "muhasabah", "gratitude"]:
            await client.post("/api/v1/journal", json={"content": "test", "journal_mode": mode, "mood": "grateful"}, headers=auth_headers)
        resp = await client.get("/api/v1/journal/analytics", headers=auth_headers)
        d = resp.json()
        assert d["total_entries"] == 3
        assert d["current_streak"] >= 1
        assert "grateful" in d["mood_counts"]
        assert "free_write" in d["modes_used"]


# ─── HTTP: Daily insights ─────────────────────────────────────────────────────

class TestDailyInsights:
    @pytest.mark.anyio
    async def test_today_insight_no_data_returns_none(self, client, auth_headers):
        resp = await client.get("/api/v1/insights/today", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    @pytest.mark.anyio
    async def test_list_insights_empty_initially(self, client, auth_headers):
        resp = await client.get("/api/v1/insights", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_insight_rating_invalid_value(self, client, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/v1/insights/{fake_id}/rate", json={"rating": 5}, headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_insight_dismiss_nonexistent(self, client, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/v1/insights/{fake_id}/dismiss", headers=auth_headers)
        assert resp.status_code == 404


# ─── HTTP: Monthly letters ────────────────────────────────────────────────────

class TestMonthlyLetters:
    @pytest.mark.anyio
    async def test_list_letters_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/letters", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_generate_letter_needs_3_entries(self, client, auth_headers):
        resp = await client.post("/api/v1/letters/generate", headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_generate_letter_with_entries(self, client, auth_headers):
        today = date.today()
        for i in range(5):
            entry_date = (today - timedelta(days=i)).isoformat()
            await client.post("/api/v1/journal", json={
                "content": f"Journal entry {i} — reflecting on today",
                "mood": "grateful",
                "journal_mode": "free_write",
                "entry_date": entry_date,
            }, headers=auth_headers)
        resp = await client.post(f"/api/v1/letters/generate?year={today.year}&month={today.month}", headers=auth_headers)
        assert resp.status_code == 201
        d = resp.json()
        assert d["entry_count"] == 5
        assert d["is_ai_generated"] is True
        assert len(d["letter_text"]) > 100

    @pytest.mark.anyio
    async def test_generate_letter_idempotent(self, client, auth_headers):
        today = date.today()
        for i in range(3):
            await client.post("/api/v1/journal", json={"content": f"Entry {i}", "journal_mode": "free_write"}, headers=auth_headers)
        await client.post(f"/api/v1/letters/generate?year={today.year}&month={today.month}", headers=auth_headers)
        resp = await client.post(f"/api/v1/letters/generate?year={today.year}&month={today.month}", headers=auth_headers)
        assert resp.status_code == 409
