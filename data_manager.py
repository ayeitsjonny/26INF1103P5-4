import csv
import os
import logging
import sqlite3
from abc importABC, abstractmethod
from datatime import datetime
from pathlib import Path
from models import IncidentReport

#Paths are now relative to the current file's location, not to wherever the script is run from. 
DEFAULT_CSV_FILE = Path(__file__).parent / "logs_reports" / "reportcases.csv"
DEFAULT_DB_FILE = Path(__file__).parent / "logs_reports" / "reportcases.db"


#When a passenger submits a report, the new description AND the new AI results are written.
#The IDs and timestamp are never changed.
UPDATEABLE_COLUMNS = ("report_details", "category", "contact_type", "stated_effect",
                      "severity", "confidence", "reasoning",
                      "second_opinion_required", "immediate_attention_required")

# customs exceptions, to let the rest of thee app tell "database is down" apart from other storage issues.
class StorageError(Exception):
    """Any problem reading or writing stored reports."""

class StorageUnavailableError(StorageError):
    """The storage backend cannot be used (eg database file is corrupted or locked)."""

# RecordRespository - abstract class. Every storage backend must implement the CRUD methods.
class RecordRepository(ABC):

    def __init__(self, name: str):
        self._name: str = name

    @property
    def name(self) -> str:
        """Short name shown to the user, eg "CSV file" or "SQLite database"."""
        return self._name

    @abstractmethod
    def save(self, report: IncidentReport) -> int:
        """CREATE: stpre a new report and return its new report_id."""
        pass

    @abstractmethod
    def get_all(self) -> list[IncidentReport]:
        """READ: return every stored report."""
        pass

    @abstractmethod
    def update(self, report: IncidentReport) -> bool:
        """UPDATE: write the UPDATABLE_COLUMNS of this report. Returns False if not found."""
        pass

    @abstractmethod
    def delete(self, report_id: int) -> bool:
        """DELETE: remove one report. Returns False if not found."""
        pass

# Shared by both children, turn a stored row into an IncidentReport object.
# CSV gives everything as str such as "True" or "2", SQlite gives 1/0 and integers.
# Converting in one place means both children return the same type of object. This is addresses LSP.
def _row_to_report(self, row: dict) -> IncidentReport:
    return IncidentReport(
        report_id = self._optional(row.get("report_id"), int),
        timestamp = self._todatetime(row.get("timestamp")),
        trip_id = str(row["trip_id"]),
        user_id = str(row["user_id"]),
        license_plate = str(row["license_plate"]),
        report_details = str(row["license_plate"]),
        category = self._optional(row.get("category"), str),
        contact_type = self._optional(row.get("contact_type"), str),
        stated_effect = self._optional(row.get("stated_effect"), str),
        severity = self._optional(row.get("severity"), int),
        confidence = self._optional(row.get("confidence"), float),
        reasoning = self._optional(row.get("reasoning"), str),
        second_opinion_required = self._to_bool(row.get("second_opinion_required")),
        immediate_attention_required = self._to_bool(row.get("immediate_attention_required")),
    )

def _optional(self, value, convert):
    # Empty CSV cell or null in SQLite is None. If not None, convert to the right type.
    if value is None or str(value).strip() == "":
        return None
    return convert(value)

def _to_bool(self, value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1")
    return bool(value)

def _to_datetime(self, value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).strip())

# CSVRepository - Inheritance, a RecordRepository that uses a CSV file. 
# Refactor into class for CSV storage.

class CSVRepository(RecordRepository):

    def __init__(self, csv_path = DEFAULT_CSV_FILE):
        super().__init__("CSV")
        self.csv_path: Path = Path(csv_path)
        if not self._csv_path.exists():
            self._write_rows([])  # Create the file with headers if it doesn't exist.

    def _read_rows(self) -> list[dict]:
        # A file with the wrong header is backed up and replaced.
        if not self._csv_path.exists():
            self.write_rows([]) 
        with open(self._csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            header = reader.fieldnames
        if header is not None and tuple(header) ! = IncidentReport.FIELDNAMES:
            backup = se;f._csv_path.with_name(f"{self._csv_path.stem}.corrupt-{datetime.now():%Y%m%d%H%M%S}.csv")
            os.replace(self._csv_path, backup)
            logging,logging.warning(f"CSV had an unexpected header. Backed up to '{backup.name}', started a new file.")
            self._write_rows([])  
            return []
        return rows
    
    def _write_rows(self, rows: list[dict]) -> None:
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=IncidentReport.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    def _to_row(self, report: IncidentReport) -> dict:
        #CSV only stores strings: None -> "", datetime -> "2026-11-09T12:00:00".
        row = {}
        for key, value in report.__dict__.items():
            if value is None:
                row[key] = ""
            elif isinstance(value, datetime):
                row[key] = value.isoformat(timespec="seconds")
            else:
                row[key] = str(value)
        return row

# CRUD Operation
def save(self, report: IncidentReport) -> int:
    rows = self._read_rows()
    highest_id = 0
    for row in rows:
        if row["report_id"].isdigit() and int(row["report_id"]) > highest_id:
            highest_id = int(row["report_id"])
    new_id = highest_id + 1
    report.report_id = new_id
    rows.append(self._to_row(report))
    self._write_rows(rows)
    return new_id

def get_all(self) -> list[IncidentReport]:
    reports = []
    for row in self._read_rows():
        try:
            reports.append
        except (KeyError, ValueError, TypeError) as e:
            logging.warning(f"Skipping invalid row in '{self.csv_path}': {e}")
    return reports

def update(self, report: IncidentReport) -> bool:
    # Part 1 matched on trip_id, but we matching it on report_id now.
    rows = self._read_rows()
    new_values = self._to_row(report)
    for row in rows:
        if row["report_id"] == str(report.report_id):
            for column in UPDATEABLE_COLUMNS:
                row[column] = new_values[column]
            self._write_rows(rows)
            return True
    return False

def delete(self, report_id: int) -> bool:
    # Delete by report_id, not trip_id. This is more reliable because trip_id may not be unique.
    rows = self._read_rows()
    remaining = [r for r in rows if r["report_id"] != str(report_id)]
    if len(remaining) == len(rows):
        return False  # No row was deleted.
    self._write_rows(remaining)
    return True


        











def load_all_records():
    #Loads all records from the CSV file and returns them as a list of dictionaries.
    initialize_csv() #just to ensure the file actually exists. If not, it will create.
    records = []
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile) #built in CSV parser tool so it automatically pairs each value with the corresponding header in the CSV.
        for row in reader:
            records.append(row) #takes each row and appends it to the records list.
        return records #sends the list of records back to the calling function.

def save_record(record_data):
    #Appends a new record to the CSV file.
    initialize_csv()

    #Fill missing fields with defaults if not provided
    full_record = {field: record_data.get(field, "") for field in FIELDNAMES}

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writerow(full_record) #takes the full_record dictionary and writes it as a new row in the CSV file.
    return True

#when AI and business rules have processed the incident, this function will update the record with the results.
def update_record(trip_id, ai_results):
    #Updates an existing incident record in the CSV file based on the provided incident_id and AI results.
    records = load_all_records() #loads all records from the CSV file into a list of dictionaries.
    updated = False #if the record is found and updated, this will be set to True.

    for entry in records:
        if entry["trip_id"] == str(trip_id): #converts the target ID to a string to prevent type mismatch bugs (e.g., matching integer 123 against string "123") 
            entry["category"] = ai_results.get("category", entry["category"])
            entry["severity"] = ai_results.get("severity", entry["severity"])
            entry["confidence"] = ai_results.get("confidence", entry["confidence"])
            # entry["STATUS"] = "PROCESSED" # status is not utilized
            updated = True
            break

    if updated:
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(records)

    return updated

#Delete function 
def delete_record(trip_id):
    #deletes an incident record from the CSV file based on its ID
    records = load_all_records()
    initial_count = len(records) #counts how many rows exist before deletion.

    #keep every record except the one that matches the incident_id that we are deleting
    filtered_records = [record for record in records if record["INCIDENT_ID"] != str(trip_id)]

    #if the list is shorter, it means the record is deleted
    if len(filtered_records) < initial_count:
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(filtered_records)
        return True
    
    return False

def filter_by_severity(severity_level):
    #Filters records in the CSV file based on the provided severity level.
    records = load_all_records()
    return [record for record in records if str(record.get("severity")) == str(severity_level)]

def filter_by_category(category):
    #Filters records in the CSV file based on the provided category.
    records = load_all_records()
    return [record for record in records if category.lower() in record.get("category", "").lower()]

def get_records_by_user(user_id):
    #Retrieves all records associated with the provided user_id.
    records = load_all_records()
    return [record for record in records if str(record.get("user_id").lower()) == str(user_id).lower()]

def get_records_by_trip(trip_id):
    #Retrieves all records associated with the provided trip_id.
    records = load_all_records()
    return [record for record in records if str(record.get("trip_id").lower()) == str(trip_id).lower()]