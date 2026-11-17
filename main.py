import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from ai_manager import AIConfigurationError, AIManager, GeminiProvider
from data_manager import RETENTION_DAYS, DataManager, StorageError, StorageFactory
from io_manager import IOManager
from logic_manager import LogicManager

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "logs_reports" / "app.log"   # was logs_reports/ai_manager.log


class ReportingApp:
    # COMPOSITION: the app creates the four managers and owns them for its whole life.

    def __init__(self):
        #.env loading and logging setup used to happen inside ai_manager.py on import.
        load_dotenv(BASE_DIR / ".env", override=True)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        self._data: DataManager = StorageFactory().create_data_manager()   # SQLite, or CSV fallback
        self._io: IOManager = IOManager()
        self._ai: AIManager = AIManager(GeminiProvider())   # raises AIConfigurationError without a key
        self._logic: LogicManager = LogicManager(self._data)

        #Menu number -> method to run. Replaces the match/case in Part 1.
        self._actions: dict = {
            ("user", 1): self._submit_report,
            ("user", 2): self._edit_report,
            ("admin", 1): self._show_reports_for_trip,
            ("admin", 2): self._show_all_reports,
            ("admin", 3): self._filter_reports,
            ("admin", 4): self._delete_report,
        }
    # ---------- Main loop ----------
    def run(self) -> None:
        self._purge_old_reports()
        while True:
            self._show_storage_messages()
            self._io.show_menu(self._data.storage_name)
            menu_type = self._io.get_menu_choice()
            if menu_type == "quit":
                print("Quitting the program...")
                return
            self._io.show_menu_options(menu_type)
            option = self._io.get_menu_option(menu_type)
            menu_options = (
                IOManager.USER_OPTIONS if menu_type == "user" else IOManager.ADMIN_OPTIONS
            )
            selected_option = menu_options[option - 1]
            if selected_option == IOManager.RETURN_OPTION:
                continue
            if selected_option == IOManager.QUIT_OPTION:
                print("Quitting the program...")
                return
            try:
                self._actions[(menu_type, option)]()
            except StorageError as e:
                # Storage problems no longer crash the app (Part 1 used a bare except).
                logging.error(f"Storage error: {e}")
                self._io.show_error(f"Could not access stored reports ({e})")

    def _show_storage_messages(self) -> None:
        message = self._data.pop_status_message()
        if message:
            self._io.show_warning(message)

    def _purge_old_reports(self) -> None:
        # Data retention: at startup, remove reports past the
        # retention period. A storage problem here is logged but does not stop
        # the app from starting.
        try:
            removed = self._data.purge_old_reports()
        except StorageError as e:
            logging.error(f"Retention purge failed: {e}")
            return
        if removed:
            self._io.data_retention_warning(
                f"Data retention: {removed} report(s) older than {RETENTION_DAYS} days were removed."
            )


    # ---------- Menu actions ----------
    def _submit_report(self) -> None:
        # CRUD: Create
        report = self._io.build_report()
        if report is None:
            # User declined the data-collection consent: nothing is collected.
            self._io.show_result("Report cancelled: consent was not given.")
            return

        # Submission rules first (2-per-trip limit, spam) — no AI call is wasted.
        outcome = self._logic.check_submission(report)
        if not outcome.allowed:
            self._io.show_error(f"Report not accepted: {outcome.message}")
            return

        if not self._analyse(report):
            return
        self._data.save_report(report)
        self._io.show_saved(report, self._logic.route(report))

    def _analyse(self, report) -> bool:
        # AI Manager -> Logic Manager. Used by BOTH "write" and "edit",
        # so every new or changed description passes through the AI.
        # Returns False (after telling the user) if the report cannot be saved.
        ai_result = self._ai.process(report)
        if ai_result is None:
            self._io.show_error("No analysis received from the AI service. Please try again later")
            return False
        report.apply_ai_result(ai_result)

        try:
            self._logic.evaluate(report)
        except ValueError as e:
            logging.error(f"Logic Manager rejected report: {e}")
            self._io.show_error("Error raised in Logic Manager")
            return False
        return True

    def _show_reports_for_trip(self) -> None:
        # CRUD: Read
        trip_id = self._io.get_trip_id()
        self._io.display_records(self._data.get_reports_by_trip(trip_id))

    def _show_all_reports(self) -> None:
        # CRUD: Read
        self._io.report_summary(self._data.get_all_reports())
        self._io.pause()

    def _filter_reports(self) -> None:
        # Uses the Part 1 filter methods that were never reachable from the menu.
        kind, value = self._io.get_filter_choice()
        if kind == "severity":
            reports = self._data.filter_by_severity(value)
        else:
            reports = self._data.filter_by_category(value)
        self._io.report_summary(reports, title=f"Reports with {kind} = {value}")
        self._io.pause()

    def _edit_report(self) -> None:
        # CRUD: Update — a passenger corrects the description of their own report.
        # The new text goes through the AI and the Logic Manager again, so the
        # classification always comes from the AI, never from a person.
        report = self._data.get_report(self._io.get_report_id())
        user_id = self._io.get_user_id()
        if report is None or not self._logic.can_edit(report, user_id):
            self._io.show_error("No report with that ID was submitted by this user")
            return

        self._io.display_record(report)
        report.revise_details(self._io.get_report_details())
        if not self._analyse(report):
            return   # nothing saved: the stored report keeps its old text and result
        self._data.update_report(report)
        self._io.show_saved(report, self._logic.route(report), action="updated")

    def _delete_report(self) -> None:
        report = self._data.get_report(self._io.get_report_id())
        if report is None:
            self._io.show_error("No report with that ID")
            return
        self._io.display_record(report)
        if self._io.confirm(f"Permanently delete report #{report.report_id}?"):
            self._data.delete_report(report.report_id)
            self._io.show_result(f"Report #{report.report_id} deleted.")
        else:
            self._io.show_result("Delete cancelled.")


if __name__ == "__main__":
    try:
        ReportingApp().run()
    except AIConfigurationError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed.")
