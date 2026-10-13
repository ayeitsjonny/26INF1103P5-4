import csv
import time
from pathlib import Path

import io_manager
import ai_manager
import data_manager
import logic_manager

BASE_DIR = Path(__file__).parent          # so files are found no matter where you run from
INPUT_FILE = BASE_DIR / "data.csv"
OUTPUT_FILE = BASE_DIR / "results.csv"

USE_MOCK = False         # True = fake AI responses, no API key needed
MAX_ROWS = None             # e.g. 3 to test on the first 3 rows only; None = all rows
DELAY_BETWEEN_CALLS = 5   # seconds to wait between AI calls (helps avoid 429 rate limits)

# Column headers in data.csv (must match exactly)
COL_REPORT_ID = "report_id"
COL_TRIP_ID = "trip_id"
COL_USER_ID = "user_id"
COL_REPORT = "report_details"
COL_PLATE = "license_plate"

AI_FIELDS = ["category", "contact_type", "stated_effect", "severity", "confidence", "reasoning"]
AI_COLS = [f"ai_{f}" for f in AI_FIELDS]   # prefixed so your original columns aren't overwritten


def row_to_record(row):
    report_text = (row.get(COL_REPORT) or "").strip()
    csv_plate = (row.get(COL_PLATE) or "").strip()
    return {
        "report_id": (row.get(COL_REPORT_ID) or "").strip(),
        "trip_id": (row.get(COL_TRIP_ID) or "").strip(),
        "user_id": (row.get(COL_USER_ID) or "").strip(),
        "report_text": report_text,
        # use the plate from the CSV if there is one, otherwise try to find it in the text
        "license_plate": csv_plate or io_manager.get_license_plate_from_report(report_text),
    }


def validation_error(record):
    """Return a string describing the problem, or None if the record is fine."""
    if not io_manager.validate_user_id(record["user_id"]):
        return "invalid user_id"
    if not io_manager.validate_trip_id(record["trip_id"]):
        return "invalid trip_id"
    n = len(record["report_text"])
    if n < io_manager.REPORT_MIN_CHARACTERS:
        return "report too short"
    if n > io_manager.REPORT_MAX_CHARACTERS:
        return "report too long"
    return None


def main():
    data_manager.initialize_csv()

    while True:

        io_manager.print_banner()
        option = io_manager.get_options()

        match option:
            case 1:
                report = io_manager.build_report()
                analysis = ai_manager.process(report)
                if analysis is None:
                    io_manager.misc_outputs("AM_Null")
                    continue

                result = logic_manager.escalation(analysis)
                if result is False:
                    io_manager.misc_outputs("LM_Invalid")
                    continue

                report_entry = report | result
                try: data_manager.save_record(report_entry)
                except:
                    io_manager.misc_outputs("DM_Savefail")
                    continue
                io_manager.misc_outputs("Ent_Success")
            case 2:
                search = io_manager.get_trip_id()
                result = data_manager.get_records_by_trip(search)
                for i in range(len(result)):
                    entry = io_manager.display_record(result[i])
                    input("Press enter to continue")
            case 3:
                # print("Display a table of all reports")
                io_manager.report_summary(data_manager.load_all_records())
                input("Press enter to continue")

            case 4:
                print("Quitting the program...")
                break
            case _:
                continue


if __name__ == "__main__":
    main()
