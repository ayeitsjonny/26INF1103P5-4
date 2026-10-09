import os
import json
import re
import time
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

# ============================================================
# SETUP — runs once when this file is imported by main.py
# ============================================================

# Load .env from the same folder as this file; override=True so the .env
# value wins over any stale key already set in Windows/terminal.
load_dotenv(Path(__file__).parent / ".env", override=True)

# strip() and quote-stripping guard against stray spaces/quotes in .env
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip().strip('"').strip("'") or None

# IMPORTANT: if you swap models, check the new model's name on Google AI
# Studio first — an outdated/retired model name causes a 404, not a 401,
# which looks like an auth problem but isn't.
MODEL = "gemini-3.6-flash"

REQUEST_TIMEOUT_MS = 60_000  # 60 seconds — newer models can be slow, don't lower this casually
MAX_RETRIES = 3               # total extra attempts after the first try (so 4 attempts max)

# Build the Gemini client. If there's no key, _client stays None.
_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# IMPORTANT: this is a hard stop. If GEMINI_API_KEY isn't set in .env,
# importing this file (e.g. `import ai_manager` in main.py) crashes
# immediately with a clear error, instead of silently returning None
# from every API call later. This is intentional — we want the whole
# pipeline to refuse to run without a key, not quietly send every
# record to manual review.
if _client is None:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Add it to your .env file before running ai_manager."
    )

# IMPORTANT: these three sets are the single source of truth for what
# counts as a "valid" AI response. If the AI returns anything outside
# these values, validate_response() rejects it and the record gets
# retried / eventually sent to manual review. If you change the
# category list here, you MUST also update the matching list inside
# build_prompt()'s prompt text below — they are not linked
# automatically, so keep them in sync by hand.
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

# All errors/info from this module go to ai_manager.log, not the
# console. Check this file first when something fails silently.
logging.basicConfig(
    filename="ai_manager.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def build_prompt(record: dict) -> str:
    """
    Build a prompt from an io_manager record dict.

    Expects record to contain at least 'report_text'. Other fields
    (trip_id, user_id, plate, timestamp) are not needed by the AI and
    are not sent, since the AI is classifying the free text, not the
    metadata.

    The rubric below is built from the team's POHA research: severity
    is derived from contact_type, repetition, and stated_effect rather
    than judged from subject matter alone, so "a sexual comment" and
    "a sexual comment repeated with a threat of violence" don't both
    collapse into the same severity just because they share a category.

    Exception: sexual_harassment is always severity 2 minimum, even
    when contact_type is "verbal" or "none". Unlike other categories,
    sexual harassment is treated as high severity regardless of
    whether contact was physical, given its sensitivity.
    """
    report_text = record.get("report_text", "")

    # IMPORTANT: this whole f-string IS the prompt sent to Gemini.
    # The JSON schema described near the end must match VALID_CATEGORIES /
    # VALID_CONTACT_TYPES / VALID_STATED_EFFECTS above exactly, since
    # validate_response() will reject anything that doesn't match.
    prompt = f"""You are classifying a safety report submitted on a ride-hailing platform, using a fixed rubric based on Singapore's Protection from Harassment Act (POHA). Do not make a subjective overall judgment — apply the criteria below mechanically.

Report text: "{report_text}"

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

    return prompt


def call_api(prompt: str) -> Optional[str]:
    """
    Send prompt to the Gemini API. Returns the raw text content of the
    response, or None on any failure. Never raises.

    Uses response_mime_type="application/json" to push Gemini toward
    returning a clean JSON object, though parse_response() still has
    to handle cases where it doesn't.
    """
    try:
        response = _client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,  # deterministic output — same report should classify the same way every time
                response_mime_type="application/json",
                http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
            ),
        )
        return response.text

    except genai_errors.APIError as e:
        # Covers connection failures, timeouts, rate limits, and bad
        # responses from Google's side — the SDK folds these into one
        # exception type with a status code attached.
        # NOTE: check ai_manager.log for the status code when debugging —
        # 401/403 = auth problem, 404 = wrong model name, 429 = rate
        # limit, 503/504 = Google's servers are busy/slow (temporary).
        logging.error(f"Gemini API error (status={getattr(e, 'code', '?')}): {e}")
        return None
    except (KeyError, IndexError, ValueError, AttributeError) as e:
        # Catches cases where the SDK's response object doesn't have the
        # shape we expect (e.g. missing .text) — rare, but we don't want
        # an unexpected shape to crash the whole pipeline.
        logging.error(f"Unexpected Gemini response shape: {e}")
        return None


def parse_response(raw: Optional[str]) -> Optional[dict]:
    """
    Extract and parse a JSON object out of the raw API text.

    Handles the common failure modes: None input, markdown code fences
    around the JSON, or stray text before/after the object. Returns a
    dict on success, None on any failure.
    """
    if raw is None:
        return None

    # Even with response_mime_type="application/json", the model can
    # occasionally wrap the JSON in ```json fences or add stray text.
    # This regex grabs just the {...} block, ignoring anything around it.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logging.error(f"No JSON object found in AI response: {raw!r}")
        return None

    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from AI response: {e} | raw={raw!r}")
        return None


def validate_response(data: Optional[dict]) -> Optional[dict]:
    """
    Check that a parsed response has the required keys, correct types,
    and values in range. Returns the validated dict on success, None
    on any failure.
    """
    if data is None:
        return None

    # IMPORTANT: this is the full contract the AI's JSON must satisfy.
    # If you add/remove a field from the prompt's JSON schema, update
    # this set too, or valid responses will get rejected as "missing keys".
    required_keys = {
        "category", "contact_type",
        "stated_effect", "severity", "confidence", "reasoning",
    }
    missing = required_keys - data.keys()
    if missing:
        logging.error(f"AI response missing keys: {missing} | data={data}")
        return None

    category = data["category"]
    if category not in VALID_CATEGORIES:
        logging.error(f"AI response has invalid category: {category!r}")
        return None

    contact_type = data["contact_type"]
    if contact_type not in VALID_CONTACT_TYPES:
        logging.error(f"AI response has invalid contact_type: {contact_type!r}")
        return None

    stated_effect = data["stated_effect"]
    if stated_effect not in VALID_STATED_EFFECTS:
        logging.error(f"AI response has invalid stated_effect: {stated_effect!r}")
        return None

    severity = data["severity"]
    # isinstance(severity, bool) check matters because in Python,
    # bool is a subclass of int — without this check, True/False would
    # silently pass an "isinstance(severity, int)" test.
    if isinstance(severity, bool) or not isinstance(severity, int) or severity not in (0, 1, 2):
        logging.error(f"AI response has invalid severity: {severity!r}")
        return None

    # IMPORTANT — POLICY RULE: Enforce the "sexual_harassment is always
    # severity 2" rule in code too, not just via the prompt — belt-and-
    # braces in case the model ever drifts from the rubric on this
    # specific category. This OVERRIDES whatever severity the model
    # returned if the category is sexual_harassment — it does not ask
    # the model again, it just forces the value.
    if category == "sexual_harassment" and severity != 2:
        logging.info(
            f"Overriding severity for sexual_harassment record from {severity} to 2 "
            f"(model returned a lower severity than the rubric requires)"
        )
        severity = 2

    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        logging.error(f"AI response has invalid confidence type: {confidence!r}")
        return None
    if not (0.0 <= float(confidence) <= 1.0):
        logging.error(f"AI response confidence out of range: {confidence!r}")
        return None

    reasoning = data["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        logging.error(f"AI response has invalid reasoning: {reasoning!r}")
        return None

    # Only returns a clean, fully-validated dict — nothing before this
    # point can leak an unchecked field through to main.py.
    return {
        "category": category,
        "contact_type": contact_type,
        "stated_effect": stated_effect,
        "severity": severity,
        "confidence": float(confidence),
        "reasoning": reasoning.strip(),
    }


def process(record: dict) -> Optional[dict]:
    """
    Run one record through the full AI pipeline: build prompt, call
    API, parse, validate. Retries on failure before giving up.

    Returns a dict of AI fields (category, contact_type, stated_effect,
    severity, confidence, reasoning) to merge into the record, or None
    if the AI could not produce a usable result after retries.
    logic_manager is responsible for deciding what happens to a record
    with a None AI result (e.g. route to manual review).
    """
    # IMPORTANT — this is the ONLY function other files should call.
    # Everything above (build_prompt, call_api, parse_response,
    # validate_response) is an internal step — main.py only ever calls
    # ai_manager.process(record).
    attempts = 0
    while attempts <= MAX_RETRIES:
        prompt = build_prompt(record)
        raw = call_api(prompt)
        parsed = parse_response(raw)
        validated = validate_response(parsed)

        if validated is not None:
            return validated

        attempts += 1
        if attempts <= MAX_RETRIES:
            logging.info(f"Retrying AI call for record (attempt {attempts + 1})")
            time.sleep(4 * attempts)  # waits 4s, 8s, 12s between retries — backs off longer each time

    # If every attempt failed, return None. Caller (main.py, via
    # logic_manager) is responsible for routing this to manual review —
    # this function does not decide that itself.
    logging.error(f"AI processing failed after {MAX_RETRIES + 1} attempt(s) for record: {record}")
    return None


def call_api_mock(prompt: str) -> str:
    """
    Drop-in replacement for call_api() during development or testing,
    when no live Gemini API connection is available or wanted.
    Returns a fixed, valid response regardless of prompt content.
    """
    # NOTE: this always returns the SAME result no matter what the
    # report says — it only proves the plumbing works end-to-end, it
    # does NOT test classification accuracy. Don't rely on it to judge
    # whether the rubric logic is correct.
    return json.dumps({
        "category": "verbal_harassment",
        "contact_type": "verbal",
        "stated_effect": "distress",
        "severity": 1,
        "confidence": 0.75,
        "reasoning": "Verbal complaint only, single incident, no stated fear for safety.",
    })


# ============================================================
# Lets you test this file on its own: `python ai_manager.py`
# runs one sample record through the mock, without touching
# the real API or needing a valid key beyond the hard check
# at the top of this file.
# ============================================================
if __name__ == "__main__":
    sample_record = {
        "report_text": "The driver made an inappropriate sexual comment during the ride.",
    }

    original_call_api = call_api
    globals()["call_api"] = call_api_mock  # swap in the mock for this run

    result = process(sample_record)

    globals()["call_api"] = original_call_api  # restore, in case this gets imported later

    print("Input record:")
    print(sample_record)
    print("\nAI result:")
    print(json.dumps(result, indent=2) if result else "None (processing failed)")
