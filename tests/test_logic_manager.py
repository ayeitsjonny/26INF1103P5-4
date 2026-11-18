# Tests for the Logic Manager: escalation rules, routing, the multi-condition
# emergency rule (uses severity + category + confidence), edit permission, and the submission rules (report limit, spam flood)

import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_manager import LogicManager
from submission_rules import ReportLimitRule, SpamFloodRule
from models import IncidentReport


class FakeDataManager:
    # Stand-in for DataManager so submission rules run without real storage.
    def __init__(self, trip_count=0, user_reports=None):
        self._trip_count = trip_count
        self._user_reports = user_reports or []

    def count_reports_for_trip(self, trip_id, user_id):
        return self._trip_count

    def get_reports_by_user(self, user_id, since=None):
        return self._user_reports


def make_report(severity=1, category="verbal_harassment", confidence=0.8,
                user_id="u1", trip_id="t1"):
    report = IncidentReport(
        user_id=user_id,
        trip_id=trip_id,
        license_plate="SGX1234A",
        report_details="placeholder text",
    )
    # Simulate the AI Manager having filled these in.
    report.category = category
    report.severity = severity
    report.confidence = confidence
    report.contact_type = "verbal"
    report.stated_effect = "distress"
    report.reasoning = "test"
    return report


class EvaluateAndRouteTests(unittest.TestCase):

    def setUp(self):
        self.logic = LogicManager(FakeDataManager())

    def test_evaluate_requires_ai_result(self):
        report = IncidentReport("u1", "t1", "SGX1", "no ai yet")
        with self.assertRaises(ValueError):
            self.logic.evaluate(report)

    def test_emergency_rule_multi_condition_all_met(self):
        # Multi-condition rule: high severity AND emergency category AND confidence >= 0.5.
        report = make_report(severity=2, category="physical_assault", confidence=0.9)
        self.logic.evaluate(report)
        self.assertTrue(report.immediate_attention_required)
        self.assertEqual(self.logic.route(report),
                         "Emergency response queue (driver flagged pending review)")

    def test_emergency_rule_not_triggered_when_low_confidence(self):
        # Emergency category + high severity but confidence < 0.5 -> not immediate,
        # and low confidence triggers a second opinion instead.
        report = make_report(severity=2, category="physical_assault", confidence=0.3)
        self.logic.evaluate(report)
        self.assertFalse(report.immediate_attention_required)
        self.assertTrue(report.second_opinion_required)
        self.assertEqual(self.logic.route(report),
                         "Manual safety-triage queue (second opinion required)")

    def test_emergency_rule_not_triggered_for_non_emergency_category(self):
        report = make_report(severity=2, category="unsafe_driving", confidence=0.9)
        self.logic.evaluate(report)
        self.assertFalse(report.immediate_attention_required)

    def test_low_confidence_sets_second_opinion(self):
        report = make_report(severity=1, category="verbal_harassment", confidence=0.4)
        self.logic.evaluate(report)
        self.assertTrue(report.second_opinion_required)

    def test_standard_routing(self):
        report = make_report(severity=1, category="verbal_harassment", confidence=0.8)
        self.logic.evaluate(report)
        self.assertEqual(self.logic.route(report),
                         "Standard triage queue (normal priority)")

    def test_evaluate_resets_flags_before_applying(self):
        # Stale flags from a previous run must be cleared by evaluate().
        report = make_report(severity=0, category="misc", confidence=0.9)
        report.immediate_attention_required = True
        report.second_opinion_required = True
        self.logic.evaluate(report)
        self.assertFalse(report.immediate_attention_required)
        self.assertFalse(report.second_opinion_required)


class CanEditTests(unittest.TestCase):

    def setUp(self):
        self.logic = LogicManager(FakeDataManager())

    def test_owner_can_edit_case_insensitive(self):
        report = make_report(user_id="Alice")
        self.assertTrue(self.logic.can_edit(report, "alice"))

    def test_non_owner_cannot_edit(self):
        report = make_report(user_id="Alice")
        self.assertFalse(self.logic.can_edit(report, "bob"))


class SubmissionRuleTests(unittest.TestCase):

    def test_report_limit_allows_under_limit(self):
        rule = ReportLimitRule(FakeDataManager(trip_count=1), max_reports=2)
        outcome = rule.check(make_report())
        self.assertTrue(outcome.allowed)

    def test_report_limit_blocks_at_limit(self):
        rule = ReportLimitRule(FakeDataManager(trip_count=2), max_reports=2)
        outcome = rule.check(make_report())
        self.assertFalse(outcome.allowed)
        self.assertIn("limit", outcome.message.lower())

    def test_spam_flood_blocks_over_threshold(self):
        recent = [make_report() for _ in range(5)]
        rule = SpamFloodRule(FakeDataManager(user_reports=recent),
                             max_reports=5, window_days=7)
        outcome = rule.check(make_report())
        self.assertFalse(outcome.allowed)

    def test_spam_flood_allows_under_threshold(self):
        recent = [make_report() for _ in range(2)]
        rule = SpamFloodRule(FakeDataManager(user_reports=recent),
                             max_reports=5, window_days=7)
        outcome = rule.check(make_report())
        self.assertTrue(outcome.allowed)

    def test_check_submission_returns_first_blocking_outcome(self):
        # trip_count at limit -> ReportLimitRule blocks first.
        logic = LogicManager(FakeDataManager(trip_count=2))
        outcome = logic.check_submission(make_report())
        self.assertFalse(outcome.allowed)

    def test_check_submission_allows_when_all_rules_pass(self):
        logic = LogicManager(FakeDataManager(trip_count=0, user_reports=[]))
        outcome = logic.check_submission(make_report())
        self.assertTrue(outcome.allowed)


if __name__ == "__main__":
    unittest.main()
