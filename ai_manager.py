import os
import json
import re
import time
import logging
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT_MS = 10_000  # 10 seconds
MAX_RETRIES = 1  # one retry on malformed/invalid response before giving up
 
_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
 
VALID_CATEGORIES = {
    "physical_assault",
    "sexual_harassment",
    "stalking",
    "verbal_abuse",
    "reckless_driving",
    "other",
}

VALID_CONTACT_TYPES = {"none", "verbal", "physical"}
VALID_STATED_EFFECTS = {"none", "distress", "fear_for_safety"}
 
logging.basicConfig(
    filename="ai_manager.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def build_prompt(record):
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
    """
    report_text = record.get("report_text", "")
 
    prompt = f"""You are classifying a safety report submitted on a ride-hailing platform, using a fixed rubric based on Singapore's Protection from Harassment Act (POHA). Do not make a subjective overall judgment — apply the criteria below mechanically.
 
Report text: "{report_text}"
 
Step 1 — extract two signals from the text:
- contact_type: "physical" if any unwanted physical contact is described, "verbal" if the harm is spoken/written only (comments, threats, messages), "none" if no harassment is actually described.
- stated_effect: "fear_for_safety" if the report explicitly describes fear, being followed, threats of future harm, or similar; "distress" if it describes being upset, uncomfortable, or offended without fear of safety; "none" if no emotional impact is stated.
 
Step 2 — assign severity using this rubric:
- severity 2 (high): physical_assault, sexual_harassment involving physical contact, or stalking — matches POHA Section 5 (fear of violence) or Section 7 (unlawful stalking). Heaviest tier — immediate escalation.
- severity 1 (medium): verbal abuse, threats, indecent remarks, or unwanted contact without physical assault — matches POHA Section 3 (intentional harassment). Causes distress or fear without physical contact.
- severity 0 (low): general service complaints, rudeness, fare disputes — no harassment under POHA.
 
Step 3 — assign category as the closest match: physical_assault, sexual_harassment, stalking, verbal_abuse, reckless_driving, or other.
 
Two worked examples for calibration:
1. "The driver made an inappropriate sexual comment" -> contact_type: "verbal", stated_effect: "distress", category: "sexual_harassment", severity: 1 (a single indecent remark, no contact, no stated fear — Section 3, not Section 5).
2. "The driver threatened to sexually assault me and followed me home" -> contact_type: "verbal" (threat, not actual contact), stated_effect: "fear_for_safety", category: "sexual_harassment", severity: 2 (explicit threat plus following someone home meets the fear-of-violence bar under Section 5, even without physical contact).
 
Return ONLY a JSON object, with no other text, no markdown code fences, and no explanation. Use exactly this format:
 
{{
  "category": one of ["physical_assault", "sexual_harassment", "stalking", "verbal_abuse", "reckless_driving", "other"],
  "contact_type": one of ["none", "verbal", "physical"],
  "stated_effect": one of ["none", "distress", "fear_for_safety"],
  "severity": integer, 0 (low), 1 (medium), or 2 (high),
  "confidence": float between 0.0 and 1.0,
  "reasoning": a short string (max ~200 characters) stating which signals drove the severity call
}}
 
If the text is too vague to classify confidently, still return your best guess for every field but reflect that uncertainty in a low confidence value."""
 
    return prompt

def call_api(prompt):
    """
    Send prompt to the Gemini API. Returns the raw text content of the
    response, or None on any failure. Never raises.
 
    Uses response_mime_type="application/json" to push Gemini toward
    returning a clean JSON object, though parse_response() still has
    to handle cases where it doesn't.
    """
    if _client is None:
        logging.error("GEMINI_API_KEY not set — cannot call API")
        return None
 
    try:
        response = _client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
            ),
        )
        return response.text
 
    except genai_errors.APIError as e:
        # Covers connection failures, timeouts, rate limits, and bad
        # responses from Google's side — the SDK folds these into one
        # exception type with a status code attached.
        logging.error(f"Gemini API error (status={getattr(e, 'code', '?')}): {e}")
        return None
    except (KeyError, IndexError, ValueError, AttributeError) as e:
        logging.error(f"Unexpected Gemini response shape: {e}")
        return None

   def parse_response(raw):
    """
    Extract and parse a JSON object out of the raw API text.
 
    Handles the common failure modes: None input, markdown code fences
    around the JSON, or stray text before/after the object. Returns a
    dict on success, None on any failure.
    """
    if raw is None:
        return None
 
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logging.error(f"No JSON object found in AI response: {raw!r}")
        return None
 
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from AI response: {e} | raw={raw!r}")
        return None

def validate_response(data):
    """
    Check that a parsed response has the required keys, correct types,
    and values in range. Returns the validated dict on success, None
    on any failure.
    """
    if data is None:
        return None
 
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
    if isinstance(severity, bool) or not isinstance(severity, int) or severity not in (0, 1, 2):
        logging.error(f"AI response has invalid severity: {severity!r}")
        return None
 
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
 
    return {
        "category": category,
        "contact_type": contact_type,
        "stated_effect": stated_effect,
        "severity": severity,
        "confidence": float(confidence),
        "reasoning": reasoning.strip(),
    }
 
 
    


 
<<<<<<< HEAD
 
=======
 
>>>>>>> a7355dee6210039b2020e37477aa736cc4c6a640
