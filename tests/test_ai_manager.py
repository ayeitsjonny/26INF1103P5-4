# Tests for the AI Manager: response parsing, schema validation, and the 
# retry/failure behaviour of AIManager.process() using MockProvider for when no live API.

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_manager import AIManager, MockProvider, ResponseValidator
from models import IncidentReport
from tests import sample_responses as sr


def make_report(details="The driver did something.") -> IncidentReport:
    return IncidentReport(
        user_id="u1",
        trip_id="t1",
        license_plate="SGX5934A",
        report_details=details,
    )


class ResponseValidatorTests(unittest.TestCase):

    def setUp(self):
        self.validator = ResponseValidator()

    def test_valid_response_parses_and_validates(self):
        result = self.validator.parse_and_validate(sr.STANDARD_VERBAL)
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "verbal_harassment")
        self.assertEqual(result["severity"], 1)
        self.assertIsInstance(result["confidence"], float)

    def test_extracts_json_from_markdown_fences(self):
        result = self.validator.parse_and_validate(sr.WRAPPED_IN_FENCES)
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "verbal_harassment")

    def test_sexual_harassment_severity_overridden_to_2(self):
        # Policy rule: sexual_harassment is always severity 2 even if AI said 1.
        result = self.validator.parse_and_validate(sr.SEXUAL_HARASSMENT_SEVERITY_1)
        self.assertIsNotNone(result)
        self.assertEqual(result["severity"], 2)

    # --- failure / malformed cases: all must reject ---

    def test_none_input_returns_none(self):
        self.assertIsNone(self.validator.parse_and_validate(None))

    def test_non_json_text_rejected(self):
        self.assertIsNone(self.validator.parse_and_validate(sr.NOT_JSON))

    def test_broken_json_rejected(self):
        self.assertIsNone(self.validator.parse_and_validate(sr.BROKEN_JSON))

    def test_missing_required_keys_rejected(self):
        self.assertIsNone(self.validator.parse_and_validate(sr.MISSING_KEYS))

    def test_invalid_category_rejected(self):
        self.assertIsNone(self.validator.parse_and_validate(sr.INVALID_CATEGORY))

    def test_severity_out_of_range_rejected(self):
        self.assertIsNone(self.validator.parse_and_validate(sr.SEVERITY_OUT_OF_RANGE))

    def test_confidence_out_of_range_rejected(self):
        self.assertIsNone(self.validator.parse_and_validate(sr.CONFIDENCE_OUT_OF_RANGE))

    def test_json_list_not_object_rejected(self):
        self.assertIsNone(self.validator.parse_and_validate(sr.JSON_LIST_NOT_OBJECT))


class AIManagerProcessTests(unittest.TestCase):

    def _manager(self, responses):
        # sleep=lambda *a: None so retries do not actually wait.
        provider = MockProvider(responses)
        manager = AIManager(provider, max_retries=2, retry_delay_seconds=0,
                             sleep=lambda *a, **k: None)
        return manager, provider

    def test_process_returns_validated_result_on_good_response(self):
        manager, provider = self._manager([sr.STANDARD_VERBAL])
        result = manager.process(make_report())
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "verbal_harassment")
        self.assertEqual(provider.calls, 1)

    def test_process_retries_then_succeeds(self):
        # First response invalid, second valid -> should retry and succeed.
        manager, provider = self._manager([sr.NOT_JSON, sr.STANDARD_VERBAL])
        result = manager.process(make_report())
        self.assertIsNotNone(result)
        self.assertEqual(provider.calls, 2)

    def test_process_returns_none_after_all_attempts_fail(self):
        # Every attempt returns garbage -> process gives up and returns None.
        manager, provider = self._manager([sr.NOT_JSON])
        result = manager.process(make_report())
        self.assertIsNone(result)
        # max_retries=2 means 3 attempts total.
        self.assertEqual(provider.calls, 3)

    def test_process_handles_api_failure_none(self):
        # Provider returning None simulates an API connection failure.
        manager, provider = self._manager([None])
        result = manager.process(make_report())
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
