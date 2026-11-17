import csv
import os
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
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
            timestamp = self._to_datetime(row.get("timestamp")),
            trip_id = str(row["trip_id"]),
            user_id = str(row["user_id"]),
            license_plate = str(row["license_plate"]),
            report_details = str(row["report_details"]),
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
        self._csv_path: Path = Path(csv_path)
        if not self._csv_path.exists():
            self._write_rows([])  # Create the file with headers if it doesn't exist.

    def _read_rows(self) -> list[dict]:
        # A file with the wrong header is backed up and replaced.
        if not self._csv_path.exists():
            self._write_rows([]) 
        with open(self._csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            header = reader.fieldnames
        if header is not None and tuple(header) != IncidentReport.FIELDNAMES:
            backup = self._csv_path.with_name(f"{self._csv_path.stem}.corrupt-{datetime.now():%Y%m%d%H%M%S}.csv")
            os.replace(self._csv_path, backup)
            logging.warning(f"CSV had an unexpected header. Backed up to '{backup.name}', started a new file.")
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
                reports.append(self._row_to_report(row))
            except (KeyError, ValueError, TypeError) as e:
                logging.warning(f"Skipping invalid row in '{self._csv_path}': {e}")
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

# Database integration
# Inheritance is practiced here, a RecordRepository that uses an SQLite database.

class SqliteRepository(RecordRepository):

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS reportcases (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            trip_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            license_plate TEXT NOT NULL,
            report_details TEXT NOT NULL,
            category TEXT,
            contact_type TEXT,
            stated_effect TEXT,
            severity INTEGER,
            confidence REAL,
            reasoning TEXT,
            second_opinion_required INTEGER NOT NULL DEFAULT 0,
            immediate_attention_required INTEGER NOT NULL DEFAULT 0
        )
    """

    def __init__(self, db_path = DEFAULT_DB_FILE):
        super().__init__("SQLite")
        self.__db_path: Path = Path(db_path)
        try:
            self.__db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageUnavailableError(f"Cannot create directory for database: {e}")
        # Create the table on first run so we dont have to set it up manually.
        # A corrupted or unreadable db file will fail here, and the factory will fall back to using CSV to store reports.
        self._execute(self.CREATE_TABLE_SQL)

    def _execute(self, sql: str, params: tuple = ()):
        # Opens the database file, runs one sql statement, saves it and always closes.
        # Returns rows for select, cursor.rowcount for insert/update/delete
        try:
            connection = sqlite3.connect(self.__db_path, timeout=5)
        except sqlite3.Error as e:
            raise StorageUnavailableError(f"Cannot open the database: {e}")
        try:
            #the row behave like dictionary : row["trip_id"]
            connection.row_factory = sqlite3.Row
            # ? placeholders will safe against sql injection
            cursor = connection.execute(sql, params)
            rows = [dict(row) for row in cursor.fetchall()]
            connection.commit()
            return rows, cursor
        except sqlite3.Error as e:
            raise StorageUnavailableError(f"Database error: {e}")
        finally:
            connection.close()

    # For CRUD operation
    def save(self, report: IncidentReport) -> int:
        rows, cursor = self._execute(
            "INSERT INTO reportcases (timestamp, trip_id, user_id, license_plate, report_details, category, contact_type, stated_effect," \
            "severity, confidence, reasoning, second_opinion_required, immediate_attention_required)"
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (report.timestamp.isoformat(timespec="seconds"), report.trip_id, report.user_id, report.license_plate, report.report_details,
             report.category, report.contact_type, report.stated_effect, report.severity, report.confidence, report.reasoning,
             report.second_opinion_required, report.immediate_attention_required),
        )
        # Sqlite generates the reportid (autoincrement)
        new_id = cursor.lastrowid
        if new_id is None:
            raise StorageError("The database did not return an ID for the new report.")
        report.report_id = new_id
        return new_id
    def get_all(self) -> list[IncidentReport]:
        rows, cursor = self._execute("SELECT * FROM reportcases ORDER BY report_id")
        return [self._row_to_report(row) for row in rows]

    def update(self, report: IncidentReport) -> bool:
        # Only the UPDATEABLE_COLUMNS will be in this sql. User, trip, licenseplate and time will never change.
        rows, cursor = self._execute(
            "UPDATE reportcases SET report_details = ?, category = ?, contact_type = ?,"
            "stated_effect = ?, severity = ?, confidence = ?, reasoning = ?, "
            "second_opinion_required = ?, immediate_attention_required = ? WHERE report_id = ?",
            (report.report_details, report.category, report.contact_type, report.stated_effect, report.severity, report.confidence, 
             report.reasoning, report.second_opinion_required, report.immediate_attention_required, report.report_id),
        )
        return cursor.rowcount > 0

    def delete(self, report_id: int) -> bool:
        rows, cursor = self._execute("DELETE FROM reportcases WHERE report_id = ?", (report_id,))
        return cursor.rowcount > 0
    
# Class DataManager class which other managers will talk to.
# Aggregation and polymorphism is used here. 
class DataManager:
    def __init__(self, primary: RecordRepository, fallback: RecordRepository | None = None,
                 status_message: str | None = None):
        self._active: RecordRepository = primary
        self._fallback: RecordRepository | None = fallback
        self._status_message: str |None = status_message

    @property
    def storage_name(self) -> str:
        return self._active.name

    def pop_status_message(self) -> str | None:
        # Returns the message one so IO manager wont repeat it
        message = self._status_message
        self._status_message = None
        return message

    def _switch_to_fallback(self, error: StorageUnavailableError) -> None:
        # If the database fails while the program is running, switch to csv so the user's report will go somewhere instead of nowhere
        # the CRUD methods below catch the error, call this then tries again
        if self._fallback is None or self._active is self._fallback:
            raise error
        logging.warning(f"Database became unavailable, switching to CSV: {error}")
        self._active = self._fallback
        self._status_message = "Database error - switched to local CSV storage."

    #CRUD operation
    def save_report(self, report: IncidentReport) -> int:
        try:
            return self._active.save(report)
        except StorageUnavailableError as e:
            self._switch_to_fallback(e)
            return self._active.save(report)

    def get_all_reports(self) -> list[IncidentReport]:
        try:
            return self._active.get_all()
        except StorageUnavailableError as e:
            self._switch_to_fallback(e)
            return self._active.get_all()

    def update_report(self, report: IncidentReport) -> bool:
        try:
            return self._active.update(report)
        except StorageUnavailableError as e:
            self._switch_to_fallback(e)
            return self._active.update(report)

    def delete_report(self, report_id: int) -> bool:
        try:
            return self._active.delete(report_id)
        except StorageUnavailableError as e:
            self._switch_to_fallback(e)
            return self._active.delete(report_id)
    #searching / filtering 
    def get_report(self, report_id: int) -> IncidentReport | None:
        for report in self.get_all_reports():
            if report.report_id == report_id:
                return report
        return None

    def get_reports_by_trip(self, trip_id: str) -> list[IncidentReport]:
        return [r for r in self.get_all_reports() if r.trip_id.lower() == trip_id.lower()]

    def get_reports_by_user(self, user_id: str, since: datetime | None = None) -> list[IncidentReport]:
        results = []
        for report in self.get_all_reports():
            if report.user_id.lower() == user_id.lower():
                if since is None or report.timestamp >= since:
                    results.append(report)
        return results

    def count_reports_for_trip(self, trip_id: str, user_id: str) -> int:
        # Used by ReportLimitRule in Logic manager
        count = 0
        for report in self.get_reports_by_trip(trip_id):
            if report.user_id.lower() == user_id.lower():
                count += 1
        return count

    def filter_by_severity(self, severity: int) -> list[IncidentReport]:
        #returns IncidentReport objects
        return [r for r in self.get_all_reports() if r.severity == severity]
    
    def filter_by_category(self, category: str) -> list[IncidentReport]:
        #Case sensitive partial match
        return [r for r in self.get_all_reports() if category.lower() in (r.category or "").lower()]
    
#StorageFactory class, hides the "SQlite first, CSV as fallback" decision from main.py
class StorageFactory:
    def __init__(self, csv_path=DEFAULT_CSV_FILE, db_path=DEFAULT_DB_FILE):
        self._csv_path = csv_path
        self._db_path = db_path

    def create_data_manager(self) -> DataManager:
        csv_repository = CSVRepository(self._csv_path)
        try:
            sqlite_repository = SqliteRepository(self._db_path)
            return DataManager(sqlite_repository, fallback=csv_repository)
        except StorageError as e:
            logging.warning(f"Database unavailable now, using CSV fallback: {e}")
            return DataManager(csv_repository, status_message="Database unavailable - using local CSV storage instead.")
        