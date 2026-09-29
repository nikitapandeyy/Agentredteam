"""Tests for BYOK (Bring Your Own Keys). No API calls."""
import os
import pytest
from app.auth.byok import use_api_keys, validate_user_keys, validate_key_format


class TestKeyFormatValidation:

    def test_valid_groq_key(self):
        valid, msg = validate_key_format("gsk_abc123xyz456def789ghi012jkl345", "groq")
        assert valid is True

    def test_groq_key_wrong_prefix(self):
        valid, msg = validate_key_format("AIzaSyABC123", "groq")
        assert valid is False
        assert "gsk_" in msg

    def test_gemini_key_looks_like_groq(self):
        valid, msg = validate_key_format("gsk_something", "gemini")
        assert valid is False
        assert "Groq" in msg

    def test_empty_key_invalid(self):
        valid, msg = validate_key_format("", "groq")
        assert valid is False

    def test_short_key_invalid(self):
        valid, msg = validate_key_format("gsk_short", "groq")
        assert valid is False


class TestValidateUserKeys:

    def test_no_keys_is_valid(self):
        errors = validate_user_keys(None, None)
        assert errors == []

    def test_valid_keys_no_errors(self):
        errors = validate_user_keys(
            "AIzaSyABC123DEF456GHI789JKL012MNO345PQR",
            "gsk_abc123xyz456def789ghi012jkl345mno678",
        )
        assert errors == []

    def test_invalid_groq_key_returns_error(self):
        errors = validate_user_keys(None, "not-a-groq-key")
        assert len(errors) == 1
        assert "Groq" in errors[0]

    def test_multiple_invalid_keys_returns_multiple_errors(self):
        errors = validate_user_keys("x", "y")
        assert len(errors) == 2


class TestUseApiKeys:

    def test_overrides_gemini_key(self):
        original = os.environ.get("GEMINI_API_KEY", "original")
        os.environ["GEMINI_API_KEY"] = "original"

        with use_api_keys("new-gemini-key", None):
            assert os.environ["GEMINI_API_KEY"] == "new-gemini-key"

        assert os.environ["GEMINI_API_KEY"] == "original"

    def test_overrides_groq_key(self):
        original = os.environ.get("GROQ_API_KEY", "original")
        os.environ["GROQ_API_KEY"] = "original"

        with use_api_keys(None, "new-groq-key"):
            assert os.environ["GROQ_API_KEY"] == "new-groq-key"

        assert os.environ["GROQ_API_KEY"] == "original"

    def test_restores_keys_on_exception(self):
        os.environ["GEMINI_API_KEY"] = "original"

        try:
            with use_api_keys("temp-key", None):
                assert os.environ["GEMINI_API_KEY"] == "temp-key"
                raise ValueError("something went wrong")
        except ValueError:
            pass

        # Key must be restored even after exception
        assert os.environ["GEMINI_API_KEY"] == "original"

    def test_no_keys_changes_nothing(self):
        os.environ["GEMINI_API_KEY"] = "unchanged"
        os.environ["GROQ_API_KEY"] = "unchanged"

        with use_api_keys(None, None):
            assert os.environ["GEMINI_API_KEY"] == "unchanged"
            assert os.environ["GROQ_API_KEY"] == "unchanged"

    def test_none_key_not_set_in_env(self):
        # If key wasn't in env before, it shouldn't be after
        os.environ.pop("GEMINI_API_KEY", None)

        with use_api_keys(None, None):
            pass

        assert "GEMINI_API_KEY" not in os.environ
