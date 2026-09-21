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
 
 
