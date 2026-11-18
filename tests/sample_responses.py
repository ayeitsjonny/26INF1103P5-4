# Hardcoded sample AI responses used by the tests.
# These stand in for the live Gemini API so the suite runs with NO network call
# (brief section 8: tests must run without a live API).

import json

# --- Well-formed responses (valid schema) ---

EMERGENCY_PHYSICAL = json.dumps({
    "category": "physical_assault",
    "contact_type": "physical",
    "stated_effect": "fear_for_safety",
    "severity": 2,
    "confidence": 0.95,
    "reasoning": "Physical contact with fear for safety.",
})

LOW_CONFIDENCE_VAGUE = json.dumps({
    "category": "misc",
    "contact_type": "none",
    "stated_effect": "none",
    "severity": 0,
    "confidence": 0.2,
    "reasoning": "Text too vague to classify confidently.",
})

STANDARD_VERBAL = json.dumps({
    "category": "verbal_harassment",
    "contact_type": "verbal",
    "stated_effect": "distress",
    "severity": 1,
    "confidence": 0.8,
    "reasoning": "Verbal harassment causing distress.",
})

# sexual_harassment reported as severity 1 — validator must override to 2.
SEXUAL_HARASSMENT_SEVERITY_1 = json.dumps({
    "category": "sexual_harassment",
    "contact_type": "verbal",
    "stated_effect": "distress",
    "severity": 1,
    "confidence": 0.7,
    "reasoning": "Single verbal remark of a sexual nature.",
})

# Valid JSON wrapped in markdown fences and stray text (parser must still extract).
WRAPPED_IN_FENCES = (
    "Here is the result:\n```json\n" + STANDARD_VERBAL + "\n```\nThanks."
)

# --- Malformed / invalid responses (validator must reject -> None) ---

NOT_JSON = "Sorry, I cannot classify this report."

BROKEN_JSON = '{"category": "misc", "severity": 0,'  # truncated

MISSING_KEYS = json.dumps({"category": "misc", "severity": 0})

INVALID_CATEGORY = json.dumps({
    "category": "not_a_real_category",
    "contact_type": "none",
    "stated_effect": "none",
    "severity": 0,
    "confidence": 0.5,
    "reasoning": "bad category",
})

SEVERITY_OUT_OF_RANGE = json.dumps({
    "category": "misc",
    "contact_type": "none",
    "stated_effect": "none",
    "severity": 5,
    "confidence": 0.5,
    "reasoning": "bad severity",
})

CONFIDENCE_OUT_OF_RANGE = json.dumps({
    "category": "misc",
    "contact_type": "none",
    "stated_effect": "none",
    "severity": 0,
    "confidence": 1.9,
    "reasoning": "bad confidence",
})

JSON_LIST_NOT_OBJECT = json.dumps([{"category": "misc"}])
