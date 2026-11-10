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