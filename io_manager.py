import re
from datetime import datetime

# Singapore registration plates: 1-3 letters, 1-4 digits, and a suffix letter.
SINGAPORE_LICENSE_PLATE_REGEX = re.compile(r"^[A-Z]{1,3}\s*\d{1,4}\s*[A-Z]$", re.IGNORECASE)
report_min_characters = 10
report_max_characters = 2000
TRIP_ID_PATTERN  = re.compile(r"^[A-Za-z0-9]{6,20}$")
USER_ID_PATTERN  = re.compile(r"^[A-Za-z0-9_\-]{3,30}$")

#Variables
# send help if you're reading this, I have no idea what I'm doing
# trip_id = str(trip_id)✔️
# user_id = int(user_id)✔️
# license_id = str(license_id)✔️
# report_details = str(report_details)✔️

# category = str(category)
# severity = int(severity)
# confidence = float(confidence)
# second_opinion_required = bool(second_opinion_required)
# immediate_attention_required = bool(immediate_attention_required)

# trip_id = input("Please enter the trip ID: ")
# user_id = input("Please enter the user ID: ")

timestamp = datetime.now().isoformat(timespec="seconds")

def non_empty_input(prompt): #ensure user doesn't type empty input
    while True:
        user_input = input(prompt).strip()
        if user_input:
            return user_input
        print("Input cannot be empty. Please try again.")

def get_license_plate_from_report(report_details):
    license_plate_match = SINGAPORE_LICENSE_PLATE_REGEX.search(report_details)
    if license_plate_match:
        return license_plate_match.group()
    else:
        return None

def validate_trip_id (trip_id):
    trip_id = TRIP_ID_PATTERN.search(trip_id)
    if trip_id:
        return trip_id.group()
    else:
        return None

def user_input():
    while True:
        user_id = non_empty_input("Please enter the user ID: ")
        trip_id = non_empty_input("Please enter the trip ID: ")
        report_details = non_empty_input("Please enter the report details: ")
        validated_trip_id = validate_trip_id(trip_id)
        license_plate = get_license_plate_from_report(report_details)
        
        print(f"Validated Trip ID: {validated_trip_id}")
        print(f"Extracted License Plate: {license_plate}")
        if len(report_details) < report_min_characters:
                print(f"Report details must be at least {report_min_characters} characters long. Please provide more information.")
        elif len(report_details) > report_max_characters:
            print(f"Report details exceed the maximum character limit of {report_max_characters}. Please shorten your report.")
        
        if license_plate:
            print(f"The license plate: {license_plate}")
            
        record = {
                "report_details": report_details,
                "trip_id": trip_id,
                "user_id": user_id,
                "license_plate": license_plate,
                # "timestamp": timestamp,
                # "self_severity": self_severity,
                # "evidence": evidence,
            }
        
        print("Report captured.\n")
        return record

if __name__ == "__main__":
    user_input()
