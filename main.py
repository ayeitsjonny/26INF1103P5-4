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

    # def __init__(self):
    #     # [MOVED] .env loading and logging setup used to happen inside ai_manager.py on import.
    #     load_dotenv(BASE_DIR / ".env", override=True)
    #     LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    #     logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
    #                         format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    #     self._data: DataManager = StorageFactory().create_data_manager()   # SQLite, or CSV fallback
    #     self._io: IOManager = IOManager()
    #     self._ai: AIManager = AIManager(GeminiProvider())   # raises AIConfigurationError without a key
    #     self._logic: LogicManager = LogicManager(self._data)

    #     # [NEW] Menu number -> method to run. Replaces the match/case in Part 1.
    #     self._actions: dict = {
    #         ("user", 1): self._submit_report,
    #         ("user", 2): self._edit_report,
    #         ("admin", 1): self._show_reports_for_trip,
    #         ("admin", 2): self._show_all_reports,
    #         ("admin", 3): self._filter_reports,
    #         ("admin", 4): self._delete_report,
# ---------- Main loop ----------
    # def run(self) -> None:
    #     while True:
    #         self._show_storage_messages()
    #         self._io.show_menu(self._data.storage_name)
    #         menu_type = self._io.get_menu_choice()
    #         if menu_type == "quit":
    #             print("Quitting the program...")
    #             return
    #         self._io.show_menu_options(menu_type)
    #         option = self._io.get_menu_option(menu_type)
    #         menu_options = (
    #             IOManager.USER_OPTIONS if menu_type == "user" else IOManager.ADMIN_OPTIONS
    #         )
    #         selected_option = menu_options[option - 1]
    #         if selected_option == IOManager.RETURN_OPTION:
    #             continue
    #         if selected_option == IOManager.QUIT_OPTION:
    #             print("Quitting the program...")
    #             return
    #         try:
    #             self._actions[(menu_type, option)]()
    #         except StorageError as e:
    #             # [NEW] Storage problems no longer crash the app (Part 1 used a bare except).
    #             logging.error(f"Storage error: {e}")
    #             self._io.show_error(f"Could not access stored reports ({e})")

    # def _show_storage_messages(self) -> None:
    #     message = self._data.pop_status_message()
    #     if message:
    #         self._io.show_warning(message)

if __name__ == "__main__":
    main()
