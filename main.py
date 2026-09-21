import csv
import io_manager
import ai_manager

INPUT_FILE = "data.csv"
OUTPUT_FILE = "results.csv"
USE_MOCK = False  # True = fake AI responses, no API key needed

# Column headers in YOUR data.csv (edit these to match)
COL_TRIP_ID = "trip_id"
COL_USER_ID = "user_id"
COL_REPORT = "report_text"

AI_FIELDS = ["category", "contact_type", "stated_effect", "severity", "confidence", "reasoning"]


def row_to_record(row):
    report_text = (row.get(COL_REPORT) or "").strip()
    return {
        "trip_id": (row.get(COL_TRIP_ID) or "").strip(),
        "user_id": (row.get(COL_USER_ID) or "").strip(),
        "report_text": report_text,
        "license_plate": io_manager.get_license_plate_from_report(report_text),
    }


def validation_error(record):
    """Return a string describing the problem, or None if the record is fine."""
    if not io_manager.USER_ID_PATTERN.match(record["user_id"]):
        return "invalid user_id"
    if not io_manager.TRIP_ID_PATTERN.match(record["trip_id"]):
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
        rows = list(reader)
        input_fields = reader.fieldnames or []

    extra_fields = [c for c in ["license_plate"] + AI_FIELDS + ["status"] if c not in input_fields]
    output_fields = input_fields + extra_fields

    counts = {"ok": 0, "invalid": 0, "manual_review": 0}

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=output_fields)
        writer.writeheader()

        for i, row in enumerate(rows, start=1):
            record = row_to_record(row)
            out = dict(row)
            out["license_plate"] = record["license_plate"] or ""

            error = validation_error(record)
            if error:
                out["status"] = f"invalid: {error}"
                counts["invalid"] += 1
                print(f"[{i}] SKIPPED ({error}) - trip {record['trip_id']}")
            else:
                result = ai_manager.process(record)
                if result is None:
                    out["status"] = "manual_review"
                    counts["manual_review"] += 1
                    print(f"[{i}] AI failed - trip {record['trip_id']} -> manual review")
                else:
                    out.update(result)
                    out["status"] = "ok"
                    counts["ok"] += 1
                    print(
                        f"[{i}] trip {record['trip_id']}: {result['category']} | "
                        f"severity {result['severity']} | conf {result['confidence']:.2f}\n"
                        f"     {result['reasoning']}"
                    )

            writer.writerow(out)

    print(f"\nDone. {counts['ok']} classified, {counts['invalid']} invalid, "
          f"{counts['manual_review']} need manual review.")
    print(f"Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
