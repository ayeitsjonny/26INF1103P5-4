import re
from datetime import datetime

# Singapore registration plates: 1-3 letters, 1-4 digits, and a suffix letter.
SINGAPORE_LICENSE_PLATE_REGEX = re.compile(r"^[A-Z]{1,3}\s*\d{1,4}\s*[A-Z]$", re.IGNORECASE)
TRIP_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{5,20}$")
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{3,30}$")

REPORT_MIN_CHARACTERS = 10
REPORT_MAX_CHARACTERS = 2000

# ASSUMPTION: fixed category list. Change to match your actual taxonomy.
VALID_CATEGORIES = {"unsafe_driving", "verbal_harassment", "long_hauling", "physical_assault", "sexual_harassment", "stalking", "misc"}

SEVERITY_MIN, SEVERITY_MAX = 0, 2

YES_NO = {"y": True, "yes": True, "n": False, "no": False}


def non_empty_input(prompt):
    while True:
        user_input = input(prompt).strip()
        if user_input:
            return user_input
        print("Input cannot be empty. Please try again.")


def get_valid_field(prompt, validator, error_msg):
    while True:
        raw = non_empty_input(prompt)
        result = validator(raw)
        if result is not None:
            return result
        print(error_msg)


# --- validators ---

def validate_trip_id(trip_id):
    match = TRIP_ID_PATTERN.match(trip_id)
    return match.group() if match else None


def validate_user_id(user_id):
    match = USER_ID_PATTERN.match(user_id)
    return match.group() if match else None


def validate_report_details(report_details):
    if REPORT_MIN_CHARACTERS <= len(report_details) <= REPORT_MAX_CHARACTERS:
        return report_details
    return None


def validate_category(category):
    normalized = category.strip().lower()
    return normalized if normalized in VALID_CATEGORIES else None


def validate_severity(severity):
    try:
        value = int(severity)
    except ValueError:
        return None
    return value if SEVERITY_MIN <= value <= SEVERITY_MAX else None


def validate_confidence(confidence):
    try:
        value = float(confidence)
    except ValueError:
        return None
    return value if 0.0 <= value <= 1.0 else None


def validate_yes_no(answer):
    return YES_NO.get(answer.strip().lower())


def get_license_plate_from_report(report_details):
    match = SINGAPORE_LICENSE_PLATE_REGEX.search(report_details)
    return match.group() if match else None


# --- field getters ---

def get_user_id():
    return get_valid_field(
        "Please enter the user ID: ",
        validate_user_id,
        "Invalid user ID. Use 3-30 characters: letters, numbers, underscore, or hyphen.",
    )


def get_trip_id():
    return get_valid_field(
        "Please enter the trip ID: ",
        validate_trip_id,
        "Invalid trip ID. Use 6-20 alphanumeric characters.",
    )


def get_report_details():
    return get_valid_field(
        "Please enter the report details: ",
        validate_report_details,
        f"Report details must be between {REPORT_MIN_CHARACTERS} and {REPORT_MAX_CHARACTERS} characters.",
    )


def get_category():
    options = ", ".join(sorted(VALID_CATEGORIES))
    return get_valid_field(
        f"Please enter the category ({options}): ",
        validate_category,
        f"Invalid category. Choose one of: {options}.",
    )


def get_severity():
    return get_valid_field(
        f"Please enter the severity ({SEVERITY_MIN}-{SEVERITY_MAX}): ",
        validate_severity,
        f"Severity must be an integer between {SEVERITY_MIN} and {SEVERITY_MAX}.",
    )


def get_confidence():
    return get_valid_field(
        "Please enter the confidence (0.0-1.0): ",
        validate_confidence,
        "Confidence must be a number between 0.0 and 1.0.",
    )


def get_yes_no_field(prompt):
    return get_valid_field(
        prompt,
        validate_yes_no,
        "Please answer y or n.",
    )


def build_report():
    user_id = get_user_id()
    trip_id = get_trip_id()
    report_details = get_report_details()
    category = get_category()
    severity = get_severity()
    confidence = get_confidence()
    second_opinion_required = get_yes_no_field("Second opinion required? (y/n): ")
    immediate_attention_required = get_yes_no_field("Immediate attention required? (y/n): ")

    license_plate = get_license_plate_from_report(report_details)
    if license_plate:
        print(f"Extracted license plate: {license_plate}")
    else:
        print("No license plate found in report details.")

    record = {
        "user_id": user_id,
        "trip_id": trip_id,
        "report_details": report_details,
        "license_plate": license_plate,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "second_opinion_required": second_opinion_required,
        "immediate_attention_required": immediate_attention_required,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    print("Report captured.\n")
    return record


if __name__ == "__main__":
    user_input()
