import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod

from models import IncidentReport

MODEL = "gemini-3.5-flash-lite"
REQUEST_TIMEOUT_MS = 60_000  # 60 seconds — newer models can be slow, don't lower this casually
MAX_RETRIES = 3               # extra attempts after the first try (so 4 attempts max)

# IMPORTANT: these three sets are the single source of truth for what counts
# as a "valid" AI response. If you change them, also update the prompt text
# in PromptBuilder.build() — they are not linked automatically.
VALID_CATEGORIES = {
    "unsafe_driving",
    "verbal_harassment",
    "long_hauling",
    "physical_assault",
    "sexual_harassment",
    "stalking",
    "misc",
}
VALID_CONTACT_TYPES = {"none", "verbal", "physical"}
VALID_STATED_EFFECTS = {"none", "distress", "fear_for_safety"}

class AIConfigurationError(Exception):
    # [NEW] Replaces Part 1's RuntimeError on import when GEMINI_API_KEY is missing.
    # main.py catches it and shows a friendly message instead of a traceback.
    pass


# ======================================================================
# [NEW] AIProvider — INTERFACE (an ABC with only abstract methods:
# "must be able to generate an answer", not an is-a relationship)
# ======================================================================
class AIProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str | None:
        """Send the prompt, return the raw text answer, or None on failure. Never raises."""
        pass


class GeminiProvider(AIProvider):
    # [CHANGED] Part 1 call_api() + the client setup, moved into a class.

    def __init__(self, api_key: str | None = None, model: str = MODEL,
                 timeout_ms: int = REQUEST_TIMEOUT_MS):
        # strip() and quote-stripping guard against stray spaces/quotes in .env
        key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
        if not key:
            # [KEPT] Hard stop without a key, so records are never silently skipped.
            raise AIConfigurationError("GEMINI_API_KEY is not set. Add it to your .env file.")

        # Imported here so the tests (which use MockProvider) don't need the Gemini package.
        from google import genai
        from google.genai import types, errors

        self._client = genai.Client(api_key=key)   # encapsulated: internal to this class
        self._types = types
        self._errors = errors
        self._model: str = model
        self._timeout_ms: int = timeout_ms

    def generate(self, prompt: str) -> str | None:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=0,  # deterministic output
                    response_mime_type="application/json",
                    http_options=self._types.HttpOptions(timeout=self._timeout_ms),
                ),
            )
            return response.text
        except self._errors.APIError as e:
            # Connection failures, timeouts, rate limits (429), wrong model name (404), auth (401/403)
            logging.error(f"Gemini API error: {e}")
            return None
        except (KeyError, IndexError, ValueError, AttributeError) as e:
            logging.error(f"Unexpected Gemini response shape: {e}")
            return None
        except Exception as e:  # e.g. network errors raised by the HTTP library itself
            logging.error(f"Could not reach Gemini: {e}")
            return None