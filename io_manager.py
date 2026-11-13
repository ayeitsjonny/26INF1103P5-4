from datetime import datetime
from InputValidator import InputValidator
from models import IncidentReport
import pandas as pd

class IOManager:
    
    RETURN_OPTION = "Return to Menu Selection"
    QUIT_OPTION = "Quit Program"

    #User's Menu
    USER_OPTIONS = (
        "Write a report",
        "Edit my report",
        RETURN_OPTION,
        QUIT_OPTION,
    )
    
    #Admin's Menu
    ADMIN_OPTIONS = (
        "Display reports from Trip ID",
        "Display reports table",
        "Filter reports by severity or category",
        "Delete a report",
        RETURN_OPTION,
        QUIT_OPTION,
    )
    
    def __init__(self):
        self._validator: InputValidator = InputValidator()
        
    #Displays the menu
    def show_menu(self, storage_name: str) -> None:
        print("=" * 40)
        print("       AI-ASSISTED SAFETY REPORTING")
        print(f"       Storage: {storage_name}")
        print("=" * 40)
        print("Select Menu:")
        print("1. User Functions")
        print("2. Admin Functions")
        print("3. Quit Program")

    #For proof of concept. There's a User menu and a Admin menu
    def get_menu_choice(self) -> str:
        while True:
            raw = input("Select Menu: ").strip()
            if raw == "1":
                return "user"
            if raw == "2":
                return "admin"
            if raw == "3":
                return "quit"
            print("Please select 1, 2, or 3.")

    #Show the menu they are "login" as
    def show_menu_options(self, menu_type: str) -> None:
        options = self.USER_OPTIONS if menu_type == "user" else self.ADMIN_OPTIONS
        title = "User Functions" if menu_type == "user" else "Admin Functions"
        print(f"\n{title}:")
        for number, label in enumerate(options, start=1):
            print(f"{number}. {label}")

    #Selection from menu
    def get_menu_option(self, menu_type: str) -> int:
        options = self.USER_OPTIONS if menu_type == "user" else self.ADMIN_OPTIONS
        while True:
            raw = input("Select Option: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return int(raw)
            print(f"Please select a valid option (1-{len(options)}).")

    def pause(self) -> None:
        input("Press enter to continue")

    # ---------- Field getters ----------
    #Gets License Plate from user
    def get_license_plate(self) -> str:
        return self._validator.get_valid_field(
            "Please enter the incident car license plate in (SXX1234A): ",
            self._validator.license_plate,
            "No license plate found. Please enter the license in (SXX1234A): ",
        )

    #Get User's userID
    def get_user_id(self) -> str:
        return self._validator.get_valid_field(
            "Please input your user ID (user123): ",
            self._validator.user_id,
            "Invalid user ID. It must start with 'user' followed by 1-6 numbers.",
        )

    #Gets tripID
    def get_trip_id(self) -> str:
        return self._validator.get_valid_field(
            "Please input your Trip ID (trip123): ",
            self._validator.trip_id,
            "Invalid trip ID. It must start with 'trip' followed by 1-6 numbers.",
        )

    #Gets report ID
    def get_report_id(self) -> int:
        return self._validator.get_valid_field(
            "Please enter the report ID: ",
            self._validator.report_id,
            "Report ID must be a positive whole number.",
        )

    #Gets report details from users
    def get_report_details(self) -> str:
        while True:
            print("Please tell us what happened during the incident.")
            print("Press Enter on an empty line when you have finished.")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)

            details = self._validator.sanitize_report_details("\n".join(lines))
            if self._validator.report_details(details) is not None:
                return details
            print(f"Report details must be between {self._validator.REPORT_MIN_CHARACTERS} and "
                  f"{self._validator.REPORT_MAX_CHARACTERS} characters. Please try again.")

    #Builds the report from user provided information
    def build_report(self) -> IncidentReport:
        report = IncidentReport(
            user_id=self.get_user_id(),
            trip_id=self.get_trip_id(),
            license_plate=self.get_license_plate(),
            report_details=self.get_report_details(),
        )
        print("\nReport captured. Analysing...")
        return report

    #Filters report by severity or category
    def get_filter_choice(self) -> tuple:
        choice = self._validator.get_valid_field(
            "Filter by (1) severity or (2) category: ",
            self._validator.filter_choice,
            "Please enter 1 or 2.",
        )
        if choice == "1":
            severity = self._validator.get_valid_field(
                "Severity (0-2): ", self._validator.severity, "Severity must be 0, 1 or 2.")
            return "severity", severity
        options = ", ".join(self._validator.VALID_CATEGORIES)
        category = self._validator.get_valid_field(
            f"Category ({options}): ", self._validator.category, f"Choose one of: {options}.")
        return "category", category

    #Confirmation to delete report
    def confirm(self, prompt: str) -> bool:
        return self._validator.get_valid_field(f"{prompt} (y/n): ", self._validator.yes_no, "Please answer y or n.")

    # ---------- Output ----------
    #Displays a report
    def display_record(self, report: IncidentReport) -> None:
        immediate = "YES" if report.immediate_attention_required else "no"
        second_opinion = "YES" if report.second_opinion_required else "no"
        print("=" * 50)
        print(f"Incident Report #{report.report_id}")
        print(f"Submitted: {report.timestamp:%Y-%m-%d %H:%M:%S}")
        print(f"User ID: {report.user_id}")
        print(f"Trip ID: {report.trip_id}")
        print(f"License Plate: {report.license_plate}")
        print(f"Report Details: {report.report_details}")
        print(f"Category: {report.category}   Severity: {report.severity}   Confidence: {report.confidence}")
        print(f"Immediate attention: {immediate}   Second opinion: {second_opinion}")
        print("=" * 50)

    def display_records(self, reports: list[IncidentReport]) -> None:
        if not reports:
            self.show_result("No reports found.")
            return
        for report in reports:
            self.display_record(report)
            self.pause()

    #Display summary of all reports
    def report_summary(self, reports: list[IncidentReport], title: str = "Incident Report Summary") -> None:
        if not reports:
            print(f"\n{title} - 0 reports")
            print("No reports to display.")
            return

        columns = ["report_id", "user_id", "trip_id", "license_plate", "category", "severity",
                   "confidence", "second_opinion_required", "immediate_attention_required", "timestamp"]
        summary = pd.DataFrame([r.to_dict() for r in reports])[columns]

        summary = summary.sort_values(
            by=["immediate_attention_required", "severity", "timestamp"],
            ascending=[False, False, True],
        )

        print(f"\n{title} - {len(reports)} report(s)")
        print(summary.to_string(index=False))
        print(f"\nImmediate Attention Needed - {int(summary['immediate_attention_required'].sum())}")
        print(f"Manual Review - {int(summary['second_opinion_required'].sum())}\n")

    
    def show_saved(self, report: IncidentReport, route: str, action: str = "submitted") -> None:
        print(f"\nReport #{report.report_id} {action} successfully.")
        print(f"AI classification: {report.category} (severity {report.severity}, confidence {report.confidence})")
        print(f"Routed to: {route}")
        self.pause()
    
    #Shows any information
    def show_info(self, message: str) -> None:
        print(message)

    #Shows any printed message
    def show_result(self, message: str) -> None:
        print(f"\n{message}")
        self.pause()

    #If there are any warnings
    def show_warning(self, message: str) -> None:
        print(f"\n[WARNING] {message}")
        self.pause()
        
    #If there are any errors
    def show_error(self, message: str) -> None:
        print(f"\n[ERROR] {message}")
        input("Press enter to return to the menu")