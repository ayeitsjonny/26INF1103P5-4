import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic_manager import LogicManager
from models import IncidentReport


Emergency_Escalation = {
    "category": "sexual_harassment",
    "contact_type": "physical",
    "stated_effect": "fear_for_safety",
    "severity": 2,
    "confidence": 0.98,
    "reasoning": "Unwanted physical contact caused fear.",
}

Manual_Review = {
    "category": "misc",
    "contact_type": "none",
    "stated_effect": "none",
    "severity": 0,
    "confidence": 0.4,
    "reasoning": "The report is unclear.",
}

Default = {
    "category": "verbal_harassment",
    "contact_type": "verbal",
    "stated_effect": "distress",
    "severity": 1,
    "confidence": 0.95,
    "reasoning": "The driver repeatedly shouted at the passenger.",
}


class TestDataManager:
    def __init__(self, reports_for_trip=0, recent_reports=None):
        self.reports_for_trip = reports_for_trip
        self.recent_reports = recent_reports or []

    def count_reports_for_trip(self, trip_id, user_id):
        return self.reports_for_trip

    def get_reports_by_user(self, user_id, since=None):
        return self.recent_reports


class LogicManagerTests:
    def __init__(self):
        self.logic = LogicManager(TestDataManager())

    def make_report(self, user_id="P123"):
        return IncidentReport(
            user_id=user_id,
            trip_id="T100",
            license_plate="SAA1001A",
            report_details="Sample test report",
        )

    def test_escalation(self, name, ai_output, expected_route):
        report = self.make_report()
        report.apply_ai_result(ai_output)
        self.logic.evaluate(report)

        assert self.logic.route(report) == expected_route
        print(f"PASS: {name}")

    def test_error_without_ai_output(self):
        report = self.make_report()

        try:
            self.logic.evaluate(report)
        except ValueError:
            print("PASS: Error when there is no AI output")
            return

        raise AssertionError("Expected an error for a report without AI output")

    def test_can_edit(self):
        report = self.make_report("Passenger-123")
        assert self.logic.can_edit(report, "passenger-123")
        assert not self.logic.can_edit(report, "another-user")
        print("PASS: Check who can edit a report")

    def test_submission_limit(self):
        logic = LogicManager(TestDataManager(reports_for_trip=2))
        outcome = logic.check_submission(self.make_report())

        assert not outcome.allowed
        print("PASS: Block report when trip limit is reached")

    def run_tests(self):
        print("=" * 40)
        print("       Test for Logic Manager")
        print("=" * 40)

        self.test_escalation(
            "Emergency escalation",
            Emergency_Escalation,
            "Emergency response queue (driver flagged pending review)",
        )
        self.test_escalation(
            "Manual review",
            Manual_Review,
            "Manual safety-triage queue (second opinion required)",
        )
        self.test_escalation(
            "Default route",
            Default,
            "Standard triage queue (normal priority)",
        )
        self.test_error_without_ai_output()
        self.test_can_edit()
        self.test_submission_limit()

        print("=" * 40)
        print("All tests passed")


if __name__ == "__main__":
    LogicManagerTests().run_tests()
