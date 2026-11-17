# [NEW] models.py
# In Part 1 every manager passed around plain dicts, and each manager had to
# guess the keys and the types (e.g. "True" string vs True bool).
# IncidentReport is ONE shared class that every manager uses, so the
# fields and their types are defined in exactly one place.

from datetime import datetime


class IncidentReport:

    # Column order used by the CSV file and the SQLite table.
    FIELDNAMES = (
        "report_id",
        "timestamp",
        "trip_id",
        "user_id",
        "license_plate",
        "report_details",
        "category",
        "contact_type",
        "stated_effect",
        "severity",
        "confidence",
        "reasoning",
        "second_opinion_required",
        "immediate_attention_required",
    )

    def __init__(self, user_id: str, trip_id: str, license_plate: str, report_details: str,
                 timestamp: datetime | None = None, report_id: int | None = None,
                 category: str | None = None, contact_type: str | None = None,
                 stated_effect: str | None = None, severity: int | None = None,
                 confidence: float | None = None, reasoning: str | None = None,
                 second_opinion_required: bool = False, immediate_attention_required: bool = False):

        # ---------- Entered by the passenger (IO Manager) ----------
        # ENCAPSULATION: private, with read-only properties below. Only the
        # description can change, and only through revise_details().
        self.__user_id: str = user_id
        self.__trip_id: str = trip_id
        self.__license_plate: str = license_plate
        self.__report_details: str = report_details
        if timestamp is None:
            # The database and the CSV both store whole seconds only.
            timestamp = datetime.now().replace(microsecond=0)
        self.__timestamp: datetime = timestamp

        # [NEW] report_id: unique ID per report. Part 1 used trip_id as the key,
        # which cannot work now that a trip may have 2 reports.
        # It stays None until the Data Manager saves the report.
        self.__report_id: int | None = report_id

        # ---------- Filled in by the AI Manager ----------
        self.category: str | None = category
        self.contact_type: str | None = contact_type
        self.stated_effect: str | None = stated_effect
        self.severity: int | None = severity
        self.confidence: float | None = confidence
        self.reasoning: str | None = reasoning

        # ---------- Set by the Logic Manager ----------
        self.second_opinion_required: bool = second_opinion_required
        self.immediate_attention_required: bool = immediate_attention_required

    # ---------- Read-only passenger fields (getter, no setter) ----------
    @property
    def user_id(self) -> str:
        return self.__user_id

    @property
    def trip_id(self) -> str:
        return self.__trip_id

    @property
    def license_plate(self) -> str:
        return self.__license_plate

    @property
    def report_details(self) -> str:
        return self.__report_details

    @property
    def timestamp(self) -> datetime:
        return self.__timestamp

    # ---------- report_id: set once, by the Data Manager when saving ----------
    @property
    def report_id(self) -> int | None:
        return self.__report_id

    @report_id.setter
    def report_id(self, value: int) -> None:
        self.__report_id = value

    # ---------- Behaviour ----------
    def revise_details(self, new_details: str) -> None:
        # [NEW] CRUD Update: the passenger corrects their description.
        # ENCAPSULATION: there is no report_details setter, so this method is the
        # ONLY way to change it. It also wipes the old AI result and flags,
        # because they described the OLD text: the report must go through the
        # AI and Logic Manager again before it can be saved.
        self.__report_details = new_details
        self.category = None
        self.contact_type = None
        self.stated_effect = None
        self.severity = None
        self.confidence = None
        self.reasoning = None
        self.second_opinion_required = False
        self.immediate_attention_required = False

    def apply_ai_result(self, ai_result: dict) -> None:
        # [NEW] Copies the validated AI output onto this report.
        # Replaces Part 1's `report | result` dict merge in main.py.
        self.category = ai_result["category"]
        self.contact_type = ai_result["contact_type"]
        self.stated_effect = ai_result["stated_effect"]
        self.severity = ai_result["severity"]
        self.confidence = ai_result["confidence"]
        self.reasoning = ai_result["reasoning"]

    def has_ai_result(self) -> bool:
        # [NEW] Used by the Logic Manager to refuse reports that skipped the AI step.
        return self.category is not None and self.severity is not None and self.confidence is not None

    def to_dict(self) -> dict:
        # Keys are in FIELDNAMES order, so CSV / SQLite / pandas can all use it.
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "trip_id": self.trip_id,
            "user_id": self.user_id,
            "license_plate": self.license_plate,
            "report_details": self.report_details,
            "category": self.category,
            "contact_type": self.contact_type,
            "stated_effect": self.stated_effect,
            "severity": self.severity,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "second_opinion_required": self.second_opinion_required,
            "immediate_attention_required": self.immediate_attention_required,
        }
