import csv
import time
from pathlib import Path

import io_manager
import ai_manager

BASE_DIR = Path(__file__).parent          # so files are found no matter where you run from
INPUT_FILE = BASE_DIR / "data.csv"
OUTPUT_FILE = BASE_DIR / "results.csv"

USE_MOCK = False          # True = fake AI responses, no API key needed
MAX_ROWS = 3              # e.g. 3 to test on the first 3 rows only; None = all rows
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
    if n < io_manager.report_min_characters:
        return "report too short"
    if n > io_manager.report_max_characters:
        return "report too long"
    return None


def main():
    if USE_MOCK:
        ai_manager.call_api = ai_manager.call_api_mock

    # utf-8-sig handles the hidden BOM character that Excel adds to CSVs
    with open(INPUT_FILE, newline="", encoding="utf-8-sig") as f_in:
        reader = csv.DictReader(f_in)
        input_fields = reader.fieldnames or []
        rows = list(reader)

    missing = [c for c in (COL_TRIP_ID, COL_USER_ID, COL_REPORT) if c not in input_fields]
    if missing:
        print(f"Column(s) not found in {INPUT_FILE.name}: {missing}")
        print(f"Columns actually in the file: {input_fields}")
        return

    if MAX_ROWS:
        rows = rows[:MAX_ROWS]

    extra_fields = [c for c in [COL_PLATE] + AI_COLS + ["status"] if c not in input_fields]
    output_fields = input_fields + extra_fields

    counts = {"ok": 0, "invalid": 0, "manual_review": 0}

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=output_fields)
        writer.writeheader()

        for i, row in enumerate(rows, start=1):
            record = row_to_record(row)
            label = record["report_id"] or f"row {i}"
            out = dict(row)
            out[COL_PLATE] = record["license_plate"] or ""

            error = validation_error(record)
            if error:
                out["status"] = f"invalid: {error}"
                counts["invalid"] += 1
                print(f"[{i}] SKIPPED ({error}) - {label}, trip {record['trip_id']}")
            else:
                result = ai_manager.process(record)

                # pause between real API calls to stay under rate limits
                if not USE_MOCK and i < len(rows):
                    time.sleep(DELAY_BETWEEN_CALLS)

                if result is None:
                    out["status"] = "manual_review"
                    counts["manual_review"] += 1
                    print(f"[{i}] AI failed - {label}, trip {record['trip_id']} -> manual review")
                else:
                    out.update({f"ai_{k}": v for k, v in result.items()})
                    out["status"] = "ok"
                    counts["ok"] += 1
                    print(
                        f"[{i}] {label}, trip {record['trip_id']}: {result['category']} | "
                        f"severity {result['severity']} | conf {result['confidence']:.2f}\n"
                        f"     {result['reasoning']}"
                    )

            writer.writerow(out)

    print(f"\nDone. {counts['ok']} classified, {counts['invalid']} invalid, "
          f"{counts['manual_review']} need manual review.")
    print(f"Results saved to {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
