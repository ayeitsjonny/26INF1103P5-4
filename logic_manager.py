# logic_manager.py — Logic Manager (Part 2)

from abc import ABC, abstractmethod
from datetime import timedelta

from data_manager import DataManager
from models import IncidentReport, sgt_now

# Same values as Part 1, moved to named constants.
EMERGENCY_CATEGORIES = ["physical_assault", "sexual_harassment", "stalking"]
HIGH_SEVERITY = 2
LOW_CONFIDENCE_THRESHOLD = 0.5

# Values for the two submission rules.
MAX_REPORTS_PER_TRIP = 2
SPAM_MAX_REPORTS = 5
SPAM_WINDOW_DAYS = 7

class RuleOutcome:
    # [NEW] Result of a submission rule: allowed or not, plus the reason.

    def __init__(self, allowed: bool, message: str = ""):
        self.allowed: bool = allowed
        self.message: str = message

# ======================================================================
# INTERFACES (abstract base classes with only abstract methods)
# ======================================================================
class SubmissionRule(ABC):
    """Decides whether a new report may be submitted at all."""

    @abstractmethod
    def check(self, report: IncidentReport) -> RuleOutcome:
        pass


class EscalationRule(ABC):
    """Looks at an AI-enriched report and sets routing flags on it."""

    @abstractmethod
    def apply(self, report: IncidentReport) -> None:
        pass

# ======================================================================
# Submission rules (run BEFORE the AI, so a rejected report costs no API call)
# ASSOCIATION: these rules USE the DataManager to look up past reports,
# but do not own it.
# ======================================================================
class ReportLimitRule(SubmissionRule):
    # A passenger may file at most 2 reports for the same trip.
    # The third attempt with the same trip ID is denied.

    def __init__(self, data_manager: DataManager, max_reports: int = MAX_REPORTS_PER_TRIP):
        self._data_manager: DataManager = data_manager
        self._max_reports: int = max_reports

    def check(self, report: IncidentReport) -> RuleOutcome:
        existing = self._data_manager.count_reports_for_trip(report.trip_id, report.user_id)
        if existing >= self._max_reports:
            return RuleOutcome(
                False,
                f"You have already submitted {existing} report(s) for trip {report.trip_id}. "
                f"The limit is {self._max_reports} reports per trip.",
            )
        return RuleOutcome(True)


class SpamFloodRule(SubmissionRule):
    # Part 1 business rule "Same user_id submits >5 reports within a 7-day window".
    # It was in ProjectInitialDetails.md but was never implemented in Part 1.

    def __init__(self, data_manager: DataManager, max_reports: int = SPAM_MAX_REPORTS,
                 window_days: int = SPAM_WINDOW_DAYS, clock=sgt_now):
        self._data_manager: DataManager = data_manager
        self._max_reports: int = max_reports
        self._window: timedelta = timedelta(days=window_days)
        self._clock = clock  # a function that returns "now"; tests pass a fixed time

    def check(self, report: IncidentReport) -> RuleOutcome:
        since = self._clock() - self._window
        recent = self._data_manager.get_reports_by_user(report.user_id, since=since)
        if len(recent) >= self._max_reports:
            return RuleOutcome(
                False,
                f"Account {report.user_id} has submitted {len(recent)} reports in the last "
                f"{self._window.days} days and has been flagged for suspected spam. "
                f"Further reports are temporarily blocked.",
            )
        return RuleOutcome(True)


# ======================================================================
# Escalation rules (run AFTER the AI)
# ======================================================================
class EmergencyEscalationRule(EscalationRule):
    # [KEPT] Part 1 multi-condition rule (uses 3 AI fields):
    # severity == high AND category in emergency list AND confidence >= 0.5

    def apply(self, report: IncidentReport) -> None:
        if (report.severity >= HIGH_SEVERITY
                and report.category in EMERGENCY_CATEGORIES
                and report.confidence >= LOW_CONFIDENCE_THRESHOLD):
            report.immediate_attention_required = True


class LowConfidenceRule(EscalationRule):
    # [KEPT] Part 1 rule: AI confidence < 0.5 -> second opinion required.

    def apply(self, report: IncidentReport) -> None:
        if report.confidence < LOW_CONFIDENCE_THRESHOLD:
            report.second_opinion_required = True


# ======================================================================
# LogicManager
# COMPOSITION: LogicManager creates and owns its rule objects; they are
# not shared and are discarded together with the LogicManager.
# ======================================================================
class LogicManager:

    def __init__(self, data_manager: DataManager):
        self._submission_rules: list[SubmissionRule] = [
            ReportLimitRule(data_manager),
            SpamFloodRule(data_manager),
        ]
        self._escalation_rules: list[EscalationRule] = [
            EmergencyEscalationRule(),
            LowConfidenceRule(),
        ]

    def check_submission(self, report: IncidentReport) -> RuleOutcome:
        # POLYMORPHISM: each rule's check() behaves differently,
        # but this loop never needs to know which rule it is calling.
        for rule in self._submission_rules:
            outcome = rule.check(report)
            if not outcome.allowed:
                return outcome
        return RuleOutcome(True)

    def evaluate(self, report: IncidentReport) -> IncidentReport:
        # Part 1 escalation(): returned False on bad input.
        # Now raises ValueError, which main.py catches and reports.
        if not report.has_ai_result():
            raise ValueError("Report has no AI result; it must pass through the AI Manager first.")

        report.second_opinion_required = False
        report.immediate_attention_required = False
        for rule in self._escalation_rules:
            rule.apply(report)
        return report

    def can_edit(self, report: IncidentReport, user_id: str) -> bool:
        # CRUD Update rule: only the passenger who wrote a report may edit it.
        # Nobody can change the AI's classification by hand; an edited report is
        # simply sent through the AI and evaluate() again.
        return report.user_id.lower() == user_id.lower()

    def route(self, report: IncidentReport) -> str:
        # Names the queue from the Part 1 business rules table, so the
        # user can see where the report went. Last row = the "Default" rule.
        if report.immediate_attention_required:
            return "Emergency response queue (driver flagged pending review)"
        if report.second_opinion_required:
            return "Manual safety-triage queue (second opinion required)"
        return "Standard triage queue (normal priority)"
