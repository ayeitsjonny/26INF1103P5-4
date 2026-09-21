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