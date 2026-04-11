"""
Service Unit Tests — SM-2, Security, AI Intent
"""
import pytest
from datetime import date, timedelta

from app.services.quran_service import sm2_next_review
from app.core.security import (
    encrypt_field,
    decrypt_field,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    validate_password_strength,
)
from app.services.ai_service import is_fiqh_question, count_today_messages


# ─── SM-2 Algorithm ───────────────────────────────────────────────────────────

class TestSM2:
    def test_first_successful_review(self):
        ef, interval, next_date = sm2_next_review(
            quality=4, ease_factor=2.5, interval_days=1, review_count=0
        )
        assert interval == 1
        assert ef >= 2.5
        assert next_date == date.today() + timedelta(days=1)

    def test_second_successful_review(self):
        ef, interval, next_date = sm2_next_review(
            quality=4, ease_factor=2.5, interval_days=1, review_count=1
        )
        assert interval == 6

    def test_third_review_uses_ease_factor(self):
        ef, interval, next_date = sm2_next_review(
            quality=4, ease_factor=2.5, interval_days=6, review_count=2
        )
        assert interval == round(6 * 2.5)

    def test_failed_review_resets_interval(self):
        ef, interval, next_date = sm2_next_review(
            quality=1, ease_factor=2.5, interval_days=10, review_count=5
        )
        assert interval == 1

    def test_ease_factor_never_below_1_3(self):
        ef, _, _ = sm2_next_review(
            quality=0, ease_factor=1.3, interval_days=1, review_count=3
        )
        assert ef >= 1.3

    def test_perfect_score_increases_ease_factor(self):
        ef, _, _ = sm2_next_review(
            quality=5, ease_factor=2.5, interval_days=6, review_count=2
        )
        assert ef > 2.5

    def test_hard_score_decreases_ease_factor(self):
        # quality=2 (hard): EF is updated downward
        ef, _, _ = sm2_next_review(
            quality=2, ease_factor=2.5, interval_days=6, review_count=2
        )
        assert ef < 2.5

    def test_blackout_preserves_ease_factor(self):
        # quality=0 (blackout): EF is preserved, interval resets
        ef, interval, _ = sm2_next_review(
            quality=0, ease_factor=2.5, interval_days=10, review_count=5
        )
        assert interval == 1
        assert ef == 2.5

    def test_next_review_date_is_future(self):
        _, _, next_date = sm2_next_review(
            quality=4, ease_factor=2.5, interval_days=6, review_count=2
        )
        assert next_date > date.today()


# ─── Security ─────────────────────────────────────────────────────────────────

class TestPasswordSecurity:
    def test_hash_and_verify(self):
        pwd = "MySecurePass1"
        hashed = hash_password(pwd)
        assert hashed != pwd
        assert verify_password(pwd, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("CorrectPass1")
        assert not verify_password("WrongPass1", hashed)

    def test_validate_strong_password(self):
        valid, msg = validate_password_strength("Secure123")
        assert valid is True
        assert msg == ""

    def test_validate_too_short(self):
        valid, msg = validate_password_strength("Sh1")
        assert valid is False
        assert "8 characters" in msg

    def test_validate_no_uppercase(self):
        valid, msg = validate_password_strength("lowercase123")
        assert valid is False
        assert "uppercase" in msg

    def test_validate_no_digit(self):
        valid, msg = validate_password_strength("NoDigitHere")
        assert valid is False
        assert "digit" in msg


class TestJWTTokens:
    def test_access_token_decode(self):
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_decode(self):
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_token_hash_is_consistent(self):
        token = "sometoken"
        assert hash_token(token) == hash_token(token)

    def test_different_tokens_have_different_hashes(self):
        assert hash_token("token1") != hash_token("token2")


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        plaintext = "Mild cramps and bloating"
        ciphertext = encrypt_field(plaintext, user_id)
        assert ciphertext != plaintext.encode()
        assert decrypt_field(ciphertext, user_id) == plaintext

    def test_different_users_produce_different_ciphertext(self):
        text = "Same sensitive note"
        ct1 = encrypt_field(text, "user-id-1")
        ct2 = encrypt_field(text, "user-id-2")
        assert ct1 != ct2

    def test_wrong_user_cannot_decrypt(self):
        ct = encrypt_field("private data", "user-id-1")
        with pytest.raises(Exception):
            decrypt_field(ct, "user-id-2")

    def test_empty_string_returns_empty(self):
        assert encrypt_field("", "user-id") == b""
        assert decrypt_field(b"", "user-id") == ""


# ─── AI Intent Classifier ─────────────────────────────────────────────────────

class TestAIIntentClassifier:
    def test_detects_ruling_question(self):
        assert is_fiqh_question("Is it haram to listen to music?") is True

    def test_detects_permissibility_question(self):
        assert is_fiqh_question("Is it permissible to pray with shoes on?") is True

    def test_detects_fatwa_request(self):
        assert is_fiqh_question("What is the fatwa on cryptocurrency?") is True

    def test_allows_lifestyle_question(self):
        assert is_fiqh_question("Help me build a morning routine") is False

    def test_allows_habit_question(self):
        assert is_fiqh_question("How do I stay consistent with Quran reading?") is False

    def test_allows_wellness_question(self):
        assert is_fiqh_question("What are some healthy meal ideas for suhoor?") is False

    def test_allows_halal_food_question(self):
        assert is_fiqh_question("Suggest some nutritious foods for iftar") is False

    def test_detects_halal_ruling_question(self):
        assert is_fiqh_question("Is it halal to eat shrimp?") is True

    def test_case_insensitive(self):
        assert is_fiqh_question("IS IT HARAM?") is True

    def test_detects_sin_question(self):
        assert is_fiqh_question("Is it a sin to do X?") is True


class TestDailyUsageCounter:
    def test_counts_user_messages_today(self):
        today = date.today().isoformat()
        mock_convs = [
            type("C", (), {"messages": [
                {"role": "user", "date": today},
                {"role": "assistant"},
                {"role": "user", "date": today},
            ]})(),
        ]
        assert count_today_messages(mock_convs) == 2

    def test_ignores_old_messages(self):
        mock_convs = [
            type("C", (), {"messages": [
                {"role": "user", "date": "2024-01-01"},
                {"role": "user", "date": "2023-12-31"},
            ]})(),
        ]
        assert count_today_messages(mock_convs) == 0

    def test_empty_conversations(self):
        assert count_today_messages([]) == 0
