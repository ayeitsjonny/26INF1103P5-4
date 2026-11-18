# Tests for the IO Manager is tested using
# unittest.mock (patching builtins.input) and captured stdout, so these tests
# run headless ugh :<

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from io_manager import IOManager
from models import IncidentReport


def make_report(report_id=1, severity=1, category="verbal_harassment",
                immediate=False, second_opinion=False, user_id="user123",
                trip_id="trip123"):
    report = IncidentReport(
        user_id=user_id,
        trip_id=trip_id,
        license_plate="SHA8996A",
        report_details="the driver kept shouting at me for the whole trip",
    )
    report.report_id = report_id
    report.category = category
    report.severity = severity
    report.confidence = 0.9
    report.contact_type = "verbal"
    report.stated_effect = "distress"
    report.reasoning = "test"
    report.immediate_attention_required = immediate
    report.second_opinion_required = second_opinion
    return report


class MenuChoiceTests(unittest.TestCase):

    def setUp(self):
        self.io = IOManager()

    @patch("builtins.input", side_effect=["1"])
    def test_menu_choice_user(self, _):
        self.assertEqual(self.io.get_menu_choice(), "user")

    @patch("builtins.input", side_effect=["2"])
    def test_menu_choice_admin(self, _):
        self.assertEqual(self.io.get_menu_choice(), "admin")

    @patch("builtins.input", side_effect=["3"])
    def test_menu_choice_quit(self, _):
        self.assertEqual(self.io.get_menu_choice(), "quit")

    @patch("builtins.input", side_effect=["x", "9", "1"])
    def test_menu_choice_retries_until_valid(self, _):
        # Invalid entries are rejected and re-prompted until a valid one is given.
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.io.get_menu_choice(), "user")


class MenuOptionTests(unittest.TestCase):

    def setUp(self):
        self.io = IOManager()

    @patch("builtins.input", side_effect=["1"])
    def test_first_user_option(self, _):
        self.assertEqual(self.io.get_menu_option("user"), 1)

    @patch("builtins.input", side_effect=["0", "99", "abc", "2"])
    def test_rejects_out_of_range_and_non_digit(self, _):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.io.get_menu_option("user"), 2)

    @patch("builtins.input", side_effect=["6"])
    def test_admin_last_option_in_range(self, _):
        # ADMIN_OPTIONS has 6 entries, so 6 is valid.
        self.assertEqual(self.io.get_menu_option("admin"), 6)


class FieldValidationThroughIOTests(unittest.TestCase):

    def setUp(self):
        self.io = IOManager()

    @patch("builtins.input", side_effect=["notanid", "user123"])
    def test_user_id_retries_until_valid(self, _):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.io.get_user_id(), "user123")

    @patch("builtins.input", side_effect=["bad", "trip42"])
    def test_trip_id_retries_until_valid(self, _):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.io.get_trip_id(), "trip42")

    @patch("builtins.input", side_effect=["sxx 1234 a"])
    def test_license_plate_normalised(self, _):
        # Spaces removed and upper-cased
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.io.get_license_plate(), "SXX1234A")

    @patch("builtins.input", side_effect=["0", "5", "2"])
    def test_report_id_rejects_zero_and_non_positive(self, _):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.io.get_report_id(), 5)


class ReportDetailsTests(unittest.TestCase):

    def setUp(self):
        self.io = IOManager()

    @patch("builtins.input", side_effect=[
        "the driver was extremely rude and aggressive", ""])
    def test_valid_multiline_details_accepted(self, _):
        with redirect_stdout(io.StringIO()):
            details = self.io.get_report_details()
        self.assertIn("aggressive", details)

    @patch("builtins.input", side_effect=[
        "short", "",                                   #Short report
        "this description is now easily long enough", ""])#long report
    def test_too_short_details_rejected_then_accepted(self, _):
        with redirect_stdout(io.StringIO()):
            details = self.io.get_report_details()
        self.assertTrue(len(details) >= self.io._validator.REPORT_MIN_CHARACTERS)


class ConsentTests(unittest.TestCase):

    def setUp(self):
        self.io = IOManager()

    @patch("builtins.input", side_effect=["y"])
    def test_consent_yes(self, _):
        with redirect_stdout(io.StringIO()):
            self.assertTrue(self.io.confirm_consent())

    @patch("builtins.input", side_effect=["n"])
    def test_consent_no(self, _):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(self.io.confirm_consent())

    def test_build_report_returns_none_when_consent_declined(self):
        with patch("builtins.input", side_effect=["n"]), redirect_stdout(io.StringIO()):
            self.assertIsNone(self.io.build_report())

    def test_build_report_collects_all_fields_on_consent(self):
        answers = [
            "y",                                             # consent
            "user123",                                       # user id
            "trip123",                                       # trip id
            "SGX1234A",                                      # license plate
            "the driver kept shouting at me the whole trip", ""  # details + blank
        ]
        with patch("builtins.input", side_effect=answers), redirect_stdout(io.StringIO()):
            report = self.io.build_report()
        self.assertIsInstance(report, IncidentReport)
        self.assertEqual(report.user_id, "user123")
        self.assertEqual(report.trip_id, "trip123")
        self.assertEqual(report.license_plate, "SGX1234A")


class FilterChoiceTests(unittest.TestCase):

    def setUp(self):
        self.io = IOManager()

    @patch("builtins.input", side_effect=["1", "2"])
    def test_filter_by_severity(self, _):
        with redirect_stdout(io.StringIO()):
            kind, value = self.io.get_filter_choice()
        self.assertEqual(kind, "severity")
        self.assertEqual(value, 2)

    @patch("builtins.input", side_effect=["2", "stalking"])
    def test_filter_by_category(self, _):
        with redirect_stdout(io.StringIO()):
            kind, value = self.io.get_filter_choice()
        self.assertEqual(kind, "category")
        self.assertEqual(value, "stalking")


class OutputTests(unittest.TestCase):

    def setUp(self):
        self.io = IOManager()

    def test_report_summary_empty(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.io.report_summary([])
        self.assertIn("0 reports", buffer.getvalue())

    def test_report_summary_sorts_urgent_first(self):
        reports = [
            make_report(report_id=1, severity=0, immediate=False),
            make_report(report_id=2, severity=2, immediate=True,
                        category="physical_assault"),
        ]
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.io.report_summary(reports)
        output = buffer.getvalue()
        self.assertIn("2 report(s)", output)
        # The urgent (immediate) report must appear before the non-urgent one.
        self.assertLess(output.index("physical_assault"),
                        output.index("verbal_harassment"))

    def test_display_record_shows_key_fields(self):
        buffer = io.StringIO()
        with patch("builtins.input", side_effect=[""]), redirect_stdout(buffer):
            self.io.display_record(make_report(immediate=True))
        output = buffer.getvalue()
        self.assertIn("Incident Report #1", output)
        self.assertIn("Immediate attention: YES", output)


if __name__ == "__main__":
    unittest.main()
