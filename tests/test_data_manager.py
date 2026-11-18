# Tests for the Data Manager: CSV CRUD roundtrip, missing-file handling,
# corrupt-file (bad header) handling, filtering, and the database-unavailable
# fallback to CSV. All tests use temporary files; no live API, no real data.

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import (
    CSVRepository,
    DataManager,
    StorageUnavailableError,
)
from models import IncidentReport


def make_report(user_id="u1", trip_id="t1", details="something happened",
                category="misc", severity=0):
    report = IncidentReport(
        user_id=user_id,
        trip_id=trip_id,
        license_plate="SGX1234A",
        report_details=details,
    )
    report.category = category
    report.severity = severity
    report.confidence = 0.5
    report.contact_type = "none"
    report.stated_effect = "none"
    report.reasoning = "test"
    return report


class CSVRepositoryTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.csv_path = Path(self._tmp.name) / "reports.csv"
        self.repo = CSVRepository(self.csv_path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_is_created_with_headers(self):
        # Constructor on a non-existent path should create an empty, valid file.
        self.assertTrue(self.csv_path.exists())
        self.assertEqual(self.repo.get_all(), [])

    def test_save_then_get_all_roundtrip(self):
        report = make_report(category="verbal_harassment", severity=1)
        new_id = self.repo.save(report)
        self.assertEqual(new_id, 1)
        all_reports = self.repo.get_all()
        self.assertEqual(len(all_reports), 1)
        self.assertEqual(all_reports[0].category, "verbal_harassment")
        self.assertEqual(all_reports[0].severity, 1)

    def test_update_existing_report(self):
        report = make_report()
        self.repo.save(report)
        report.category = "stalking"
        report.severity = 2
        self.assertTrue(self.repo.update(report))
        self.assertEqual(self.repo.get_all()[0].category, "stalking")

    def test_update_missing_report_returns_false(self):
        report = make_report()
        report.report_id = 999
        self.assertFalse(self.repo.update(report))

    def test_delete_report(self):
        report = make_report()
        new_id = self.repo.save(report)
        self.assertTrue(self.repo.delete(new_id))
        self.assertEqual(self.repo.get_all(), [])

    def test_delete_missing_returns_false(self):
        self.assertFalse(self.repo.delete(12345))

    def test_corrupt_header_is_backed_up_and_reset(self):
        # Write a file with a wrong header
        self.csv_path.write_text("totally,wrong,header\n1,2,3\n", encoding="utf-8")
        repo = CSVRepository(self.csv_path)
        self.assertEqual(repo.get_all(), [])
        backups = list(self.csv_path.parent.glob("reports.corrupt-*.csv"))
        self.assertEqual(len(backups), 1)


class DataManagerFilterTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        csv_path = Path(self._tmp.name) / "reports.csv"
        self.dm = DataManager(CSVRepository(csv_path))
        self.dm.save_report(make_report(trip_id="tA", user_id="alice",
                                        category="stalking", severity=2))
        self.dm.save_report(make_report(trip_id="tA", user_id="alice",
                                        category="misc", severity=0))
        self.dm.save_report(make_report(trip_id="tB", user_id="bob",
                                        category="unsafe_driving", severity=1))

    def tearDown(self):
        self._tmp.cleanup()

    def test_count_reports_for_trip(self):
        self.assertEqual(self.dm.count_reports_for_trip("tA", "alice"), 2)
        self.assertEqual(self.dm.count_reports_for_trip("tB", "alice"), 0)

    def test_filter_by_severity(self):
        self.assertEqual(len(self.dm.filter_by_severity(2)), 1)

    def test_filter_by_category(self):
        self.assertEqual(len(self.dm.filter_by_category("stalking")), 1)

    def test_get_reports_by_trip_case_insensitive(self):
        self.assertEqual(len(self.dm.get_reports_by_trip("TA")), 2)


class FallbackTests(unittest.TestCase):
    # Database becomes unavailable -> DataManager must switch to the CSV fallback

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.csv_repo = CSVRepository(Path(self._tmp.name) / "fallback.csv")

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_falls_back_to_csv_when_primary_unavailable(self):
        class BrokenRepo:
            name = "SQLite"
            def save(self, report):
                raise StorageUnavailableError("database locked")
            def get_all(self):
                raise StorageUnavailableError("database locked")

        dm = DataManager(BrokenRepo(), fallback=self.csv_repo)
        new_id = dm.save_report(make_report())
        self.assertEqual(new_id, 1)
        # Status message records the switch so the IO layer can tell the user.
        self.assertIn("CSV", dm.pop_status_message())
        self.assertEqual(dm.storage_name, "CSV")

    def test_no_fallback_reraises(self):
        class BrokenRepo:
            name = "SQLite"
            def save(self, report):
                raise StorageUnavailableError("database locked")

        dm = DataManager(BrokenRepo(), fallback=None)
        with self.assertRaises(StorageUnavailableError):
            dm.save_report(make_report())


if __name__ == "__main__":
    unittest.main()
