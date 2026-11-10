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

    class MockProvider(AIProvider):
        # [CHANGED] Part 1 call_api_mock(). Now a proper provider used by the tests,
        # so tests run without a live API (brief section 8).
        # It is NOT used by the running app (brief section 7: no hard-coded AI answers).

        def __init__(self, responses: list):
            # responses: raw strings (or None) returned in order. The last one repeats.
            self._responses: list = responses
            self.calls: int = 0

        def generate(self, prompt: str) -> str | None:
            index = self.calls
            if index >= len(self._responses):
                index = len(self._responses) - 1
            self.calls += 1
            return self._responses[index]

class PromptBuilder:

    def build(self, report: IncidentReport) -> str:
        """
        Only report_details is sent. trip_id, user_id, plate and timestamp are
        not needed by the AI because it classifies the free text only.
        Severity is derived from contact_type, repetition and stated_effect
        (POHA research), except sexual_harassment which is always severity 2.
        """
        report_details = report.report_details

        return f"""You are classifying a safety report submitted on a ride-hailing platform, using a fixed rubric based on Singapore's Protection from Harassment Act (POHA). Do not make a subjective overall judgment — apply the criteria below mechanically.

Report text: "{report_details}"

Step 1 — extract two signals from the text:
- contact_type: "physical" if any unwanted physical contact is described, "verbal" if the harm is spoken/written only (comments, threats, messages), "none" if no harassment is actually described.
- stated_effect: "fear_for_safety" if the report explicitly describes fear, being followed, threats of future harm, or similar; "distress" if it describes being upset, uncomfortable, or offended without fear of safety; "none" if no emotional impact is stated.

Step 2 — assign severity using this rubric:
- severity 2 (high): physical_assault, stalking, or sexual_harassment of any kind (spoken, written, or physical contact — sexual harassment is always severity 2 minimum regardless of contact_type) — matches POHA Section 5 (fear of violence) or Section 7 (unlawful stalking), or is treated as high severity given its sensitivity. Heaviest tier — immediate escalation.
- severity 1 (medium): unsafe_driving, verbal_harassment, threats, indecent remarks not of a sexual nature, or unwanted contact without physical assault — matches POHA Section 3 (intentional harassment). Causes distress or fear without physical contact.
- severity 0 (low): general service complaints, rudeness, fare disputes — no harassment under POHA.

Step 3 — assign category as the closest match: unsafe_driving, verbal_harassment, long_hauling, physical_assault, sexual_harassment, stalking, or misc.

Two worked examples for calibration:
1. "The driver made an inappropriate sexual comment" -> contact_type: "verbal", stated_effect: "distress", category: "sexual_harassment", severity: 2 (any sexual_harassment is severity 2 minimum, even a single verbal remark with no physical contact and no stated fear).
2. "The driver threatened to sexually assault me and followed me home" -> contact_type: "verbal" (threat, not actual contact), stated_effect: "fear_for_safety", category: "sexual_harassment", severity: 2 (sexual_harassment is always severity 2 regardless of contact type; the explicit threat plus following someone home would also independently meet the fear-of-violence bar under Section 5).

Return ONLY a JSON object, with no other text, no markdown code fences, and no explanation. Use exactly this format:

{{
  "category": one of ["unsafe_driving", "verbal_harassment", "long_hauling", "physical_assault", "sexual_harassment", "stalking", "misc"],
  "contact_type": one of ["none", "verbal", "physical"],
  "stated_effect": one of ["none", "distress", "fear_for_safety"],
  "severity": integer, 0 (low), 1 (medium), or 2 (high),
  "confidence": float between 0.0 and 1.0,
  "reasoning": a short string (max ~2000 characters) stating which signals drove the severity call
}}

If the text is too vague to classify confidently, still return your best guess for every field but reflect that uncertainty in a low confidence value."""