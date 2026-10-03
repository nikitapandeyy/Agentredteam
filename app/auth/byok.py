"""Bring Your Own Keys (BYOK) support for AgentRedTeam.

Users can provide their own Gemini and Groq API keys in the request.
Keys are used for that request only and never stored anywhere.
"""
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def use_api_keys(gemini_key: str | None, groq_key: str | None):
    """Context manager that temporarily overrides API keys for one request."""
    original_gemini = os.environ.get("GEMINI_API_KEY")
    original_groq = os.environ.get("GROQ_API_KEY")
    keys_overridden = []

    try:
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
            keys_overridden.append("GEMINI")
            logger.info("BYOK: Using caller Gemini key (%d chars)", len(gemini_key))

        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key
            keys_overridden.append("GROQ")
            logger.info("BYOK: Using caller Groq key (%d chars)", len(groq_key))

        yield keys_overridden

    finally:
        if gemini_key:
            if original_gemini is not None:
                os.environ["GEMINI_API_KEY"] = original_gemini
            else:
                os.environ.pop("GEMINI_API_KEY", None)

        if groq_key:
            if original_groq is not None:
                os.environ["GROQ_API_KEY"] = original_groq
            else:
                os.environ.pop("GROQ_API_KEY", None)

        if keys_overridden:
            logger.info("BYOK: Keys cleared, originals restored")


def validate_key_format(key: str, provider: str) -> tuple[bool, str]:
    """Basic format validation before using a key. No API calls."""
    if not key or not key.strip():
        return False, f"{provider} key cannot be empty"

    key = key.strip()

    if provider == "groq":
        if not key.startswith("gsk_"):
            return False, "Groq keys must start with 'gsk_'"
        if len(key) < 20:
            return False, "Groq key appears too short"

    if provider == "gemini":
        if len(key) < 10:
            return False, "Gemini key appears too short"
        # Note: Gemini key formats vary by region and API version
        # We only do minimal validation to avoid false rejections

    return True, ""


def validate_user_keys(
    gemini_key: str | None,
    groq_key: str | None,
) -> list[str]:
    """Validate user-provided keys. Returns list of errors (empty = valid)."""
    errors = []

    if gemini_key:
        valid, msg = validate_key_format(gemini_key, "gemini")
        if not valid:
            errors.append(f"Gemini key invalid: {msg}")

    if groq_key:
        valid, msg = validate_key_format(groq_key, "groq")
        if not valid:
            errors.append(f"Groq key invalid: {msg}")

    return errors
