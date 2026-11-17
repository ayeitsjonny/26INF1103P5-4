
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from data_manager import DataManager
from models import IncidentReport


# Submission rule constants
MAX_REPORTS_PER_TRIP = 2
SPAM_MAX_REPORTS = 5
SPAM_WINDOW_DAYS = 7


class RuleOutcome:
    def __init__(self, allowed: bool, message: str = ""):
        self.allowed: bool = allowed
        self.message: str = message


class SubmissionRule(ABC):

    @abstractmethod
    def check(self, report: IncidentReport) -> RuleOutcome:
        pass


class ReportLimitRule(SubmissionRule):

    def __init__(
        self,
        data_manager: DataManager,
        max_reports: int = MAX_REPORTS_PER_TRIP
    ):
        self._data_manager: DataManager = data_manager
        self._max_reports: int = max_reports

    def check(self, report: IncidentReport) -> RuleOutcome:
        existing = self._data_manager.count_reports_for_trip(
            report.trip_id,
            report.user_id
        )

        if existing >= self._max_reports:
            return RuleOutcome(
                False,
                f"You have already submitted {existing} report(s) for trip {report.trip_id}. "
                f"The limit is {self._max_reports} reports per trip.",
            )

        return RuleOutcome(True)


class SpamFloodRule(SubmissionRule):

    def __init__(
        self,
        data_manager: DataManager,
        max_reports: int = SPAM_MAX_REPORTS,
        window_days: int = SPAM_WINDOW_DAYS,
        clock=datetime.now
    ):
        self._data_manager: DataManager = data_manager
        self._max_reports: int = max_reports
        self._window: timedelta = timedelta(days=window_days)
        self._clock = clock

    def check(self, report: IncidentReport) -> RuleOutcome:
        since = self._clock() - self._window

        recent = self._data_manager.get_reports_by_user(
            report.user_id,
            since=since
        )

        if len(recent) >= self._max_reports:
            return RuleOutcome(
                False,
                f"Account {report.user_id} has submitted {len(recent)} reports in the last "
                f"{self._window.days} days and has been flagged for suspected spam. "
                f"Further reports are temporarily blocked.",
            )

        return RuleOutcome(True)
