import re

class InputValidator:
    #Regex for User,Trip,License plate
    LICENSE_PLATE_PATTERN = r"\bS[A-Z]{0,3}\s*\d{1,4}\s*[A-Z]\b"
    TRIP_ID_PATTERN = r"^(TRIP)[0-9]{1,6}$"
    USER_ID_PATTERN = r"^(USER)[0-9]{1,6}$"
    
    #Sets minimum and maximum require characters for report
    REPORT_MIN_CHARACTERS = 10
    REPORT_MAX_CHARACTERS = 2000
    
    #List down valid categories and severity maximum & minimum
    VALID_CATEGORIES = [
        "long_hauling", "misc", "physical_assault", "sexual_harassment",
        "stalking", "unsafe_driving", "verbal_harassment",
    ]
    SEVERITY_MIN = 0
    SEVERITY_MAX = 2

    
    def non_empty_input(self, prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("Input cannot be empty. Please try again.")

    def get_valid_field(self, prompt: str, check, error_msg: str):
        # `check` is one of the InputValidator methods. Keeps asking until it returns a value.
        while True:
            result = check(self.non_empty_input(prompt))
            if result is not None:
                return result
            print(error_msg)
            
    #Ensures that License plate matches Singaporean License plate & is valid
    def license_plate(self, value: str) -> str | None:
        match = re.match(self.LICENSE_PLATE_PATTERN, value, re.IGNORECASE)
        if match is None:
            return None
        # [CHANGED] Stored upper-case without spaces, e.g. "sab 1234 c" -> "SAB1234C".
        return match.group().replace(" ", "").upper()

    #Ensures Trip ID follows TRIP123 format
    def trip_id(self, value: str) -> str | None:
        match = re.match(self.TRIP_ID_PATTERN, value, re.IGNORECASE)
        if match is None:
            return None
        return match.group().lower()

    #Ensures that User ID follows the USER123 format
    def user_id(self, value: str) -> str | None:
        match = re.match(self.USER_ID_PATTERN, value, re.IGNORECASE)
        if match is None:
            return None
        return match.group().lower()

    #Checks if the report lengeth is between the min & max characters
    def report_details(self, value: str) -> str | None:
        if self.REPORT_MIN_CHARACTERS <= len(value) <= self.REPORT_MAX_CHARACTERS:
            return value
        return None

    #Cleans category spaces and convert to lowercase
    def category(self, value: str) -> str | None:
        cleaned = value.strip().lower()
        if cleaned in self.VALID_CATEGORIES:
            return cleaned
        return None

    #Ensures that serverity is returned back as int
    def severity(self, value: str) -> int | None:
        if not value.strip().isdigit():
            return None
        number = int(value)
        if self.SEVERITY_MIN <= number <= self.SEVERITY_MAX:
            return number
        return None

    #Checks if report ID is a digit and > 0
    def report_id(self, value: str) -> int | None:
        if value.strip().isdigit() and int(value) > 0:
            return int(value)
        return None

    #Choice selection for admins
    def filter_choice(self, value: str) -> str | None:
        if value in ("1", "2"):
            return value
        return None

    #Returns True/False
    def yes_no(self, value: str) -> bool | None:
        answer = value.strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        return None
    
    # Remove control characters and normalise line endings.
    def sanitize_report_details(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()