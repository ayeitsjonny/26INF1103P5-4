from datetime import datetime
import pandas as pd
import re

#Regex for User,Trip,License plate
SINGAPORE_LICENSE_PLATE_REGEX = re.compile(r"\bS[A-Z]{0,3}\s*\d{1,4}\s*[A-Z]\b", re.IGNORECASE)
TRIP_ID_PATTERN = re.compile(r"^trip[A-Za-z0-9]{1,6}$", re.IGNORECASE)
USER_ID_PATTERN = re.compile(r"^user[A-Za-z0-9]{1,6}$", re.IGNORECASE)

#Sets minimum and maximum require characters for report
REPORT_MIN_CHARACTERS = 10
REPORT_MAX_CHARACTERS = 2000

# ASSUMPTION: fixed category list. Change to match your actual taxonomy.
VALID_CATEGORIES = {"unsafe_driving", "verbal_harassment", "long_hauling", "physical_assault", "sexual_harassment", "stalking", "misc"}

SEVERITY_MIN, SEVERITY_MAX = 0, 2

YES_NO = {"y": True, "yes": True, "n": False, "no": False}

#Banner before the user starts the report
def print_banner():
    print("=" * 40)
    print("       AI-ASSISTED SAFETY REPORTING")
    print("=" * 40)

#Ensures input field is not empty else reject user input
def non_empty_input(prompt):
    while True:
        user_input = input(prompt).strip()
        if user_input:
            return user_input
        print("Input cannot be empty. Please try again.")

#Prompt until the input passes the supplied validation function
def get_valid_field(prompt, validator, error_msg):
    while True:
        raw = non_empty_input(prompt)
        result = validator(raw)
        if result is not None:
            return result
        print(error_msg)


# --- validators ---
#Ensure that the tripid is in the required format
def validate_trip_id(trip_id):
    match = TRIP_ID_PATTERN.match(trip_id)
    return match.group() if match else None

#Ensures that userid is in the required format
def validate_user_id(user_id):
    match = USER_ID_PATTERN.match(user_id)
    return match.group() if match else None

#Check that the report is within the allowed length before saving it
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
    """Map yes/no answers to booleans so the app can store a simple flag."""
    return YES_NO.get(answer.strip().lower())

#Checks for license plate inside the report details and ensures it's in SXX1234A format
def get_license_plate(report_details):
    """Extract the vehicle plate from the incident text and normalize it to SG format."""
    match = SINGAPORE_LICENSE_PLATE_REGEX.search(report_details)
    while not match:
        report_details = input("No license plate found. Please enter the license in (SXX1234A): ")
        match = SINGAPORE_LICENSE_PLATE_REGEX.search(report_details)
    return re.sub(r"\s+", "", match.group()).upper()


# --- field getters ---
#Collect and validate the reporting user's ID
def get_user_id():
    return get_valid_field(
        "Please input your user ID (user123): ",
        validate_user_id,
        "Invalid user ID. It must start with 'user' followed by 1-6 letters or numbers.",
    )
    
#Collect and validate the trip identifier tied to the incident
def get_trip_id():
    return get_valid_field(
        "Please input your Trip ID (trip123): ",
        validate_trip_id,
        "Invalid trip ID. It must start with 'trip' followed by 1-6 letters or numbers.",
    )


def get_report_details():
    """Prompt the user for the incident narrative and sanitize it before validation."""
    while True:
        print("Please tell us what happened during the incident.")
        print("Press Enter on an empty line when you have finished.")

        report_lines = []
        while True:
            line = input()
            if not line:
                break
            report_lines.append(line)

        report_details = sanitize_report_details("\n".join(report_lines))
        if validate_report_details(report_details) is not None:
            return report_details

        print(f"Report details must be between {REPORT_MIN_CHARACTERS} and {REPORT_MAX_CHARACTERS} characters. Please try again.")


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

#Function to build the report and return a dict for ai manager
def build_report():
    print_banner()
    user_id = get_user_id()
    trip_id = get_trip_id()
    report_details = get_report_details()
    license_plate = get_license_plate(report_details)

    record = {
        "user_id": user_id,
        "trip_id": trip_id,
        "report_details": report_details,
        "license_plate": license_plate,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    print("Report captured.\n")
    return record

#Remove control characters such as \n and normalize line endings before validation.
def sanitize_report_details(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()

#Print a table of incident records, handling both a single dict and a list.
def report_summary(records):
    if isinstance(records, dict):
        records = [records]

    if not records:
        print("\nIncident Report Summary — 0 reports")
        print("No reports to display.")
        return

    summary_fields = [
        "user_id", "trip_id", "license_plate", "category", "severity",
        "confidence", "second_opinion_required",
        "immediate_attention_required", "timestamp",
    ]
    summary_records = [
        {field: record.get(field, "unknown") for field in summary_fields}
        for record in records
    ]
    summary = pd.DataFrame(summary_records)

    print(f"\nIncident Report Summary — {len(records)} report(s)")
    print(summary.to_string(index=False))

#Print a single incident record in a readable user-facing format
def display_record(record):
    print("=" * 50)
    print("\nIncident Report Record")
    print(f"User ID: {record['user_id']}")
    print(f"Trip ID: {record['trip_id']}")
    print(f"Report Details: {record['report_details']}")
    print(f"License Plate: {record['license_plate']}")
    print("=" * 50)

if __name__ == "__main__":
    try:
        report = build_report()
        display_record(report)
        report_summary(report)
    except EOFError:
        print("\nInput ended unexpectedly. Report cancelled.")