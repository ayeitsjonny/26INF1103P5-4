
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from data_manager import DataManager
from models import IncidentReport

from submission_rules import (
    RuleOutcome,
    SubmissionRule,
    ReportLimitRule,
    SpamFloodRule
)



# [KEPT] Same values as Part 1, moved to named constants.
EMERGENCY_CATEGORIES = ["physical_assault", "sexual_harassment", "stalking"]
HIGH_SEVERITY = 2
LOW_CONFIDENCE_THRESHOLD = 0.5








# Abstract parent class for escalation rules
class EscalationRule(ABC):

    @abstractmethod
    def apply(self, report: IncidentReport) -> None:
        pass

# Emergency escalation rule
class EmergencyEscalationRule(EscalationRule):

    def apply(self, report: IncidentReport) -> None:
        if report.severity >= HIGH_SEVERITY and report.category in EMERGENCY_CATEGORIES and report.confidence >= LOW_CONFIDENCE_THRESHOLD:
            report.immediate_attention_required = True


# Low confidence rule
class LowConfidenceRule(EscalationRule):

    def apply(self, report: IncidentReport) -> None:
        if report.confidence < LOW_CONFIDENCE_THRESHOLD:
            report.second_opinion_required = True



# Main Logic Manager
class LogicManager:

    def __init__(self, data_manager: DataManager):

        self._submission_rules: list[SubmissionRule] = [
            ReportLimitRule(data_manager),
            SpamFloodRule(data_manager)
        ]

        self._escalation_rules: list[EscalationRule] = [
            EmergencyEscalationRule(),
            LowConfidenceRule()
        ]

    def check_submission(self, report: IncidentReport) -> RuleOutcome:

        for rule in self._submission_rules:
            outcome = rule.check(report)

            if not outcome.allowed:
                return outcome

        return RuleOutcome(True)

    def evaluate(self, report: IncidentReport) -> IncidentReport:

        if not report.has_ai_result():
            raise ValueError(
                "Report has no AI result; it must pass through the AI Manager first."
            )

        report.second_opinion_required = False
        report.immediate_attention_required = False

        for rule in self._escalation_rules:
            rule.apply(report)

        return report

    def can_edit(self, report: IncidentReport, user_id: str) -> bool:
        return report.user_id.lower() == user_id.lower()

    def route(self, report: IncidentReport) -> str:

        if report.immediate_attention_required:
            return "Emergency response queue (driver flagged pending review)"

        if report.second_opinion_required:
            return "Manual safety-triage queue (second opinion required)"

        return "Standard triage queue (normal priority)"







