import csv
import os
import logging

CSV_FILE ="reportcases.csv"

FIELDNAMES = [
    "INCIDENT_ID",
    "TIMESTAMP",
    "USER_ID",
    "TRIP_ID",
    "LICENSE_PLATE",
    "RAW_TEXT",
    "VALID_CATEGORIES",
    "SEVERITY",
    "CONFIDENCE",
    "STATUS"
]

def initialize_csv():
    #Initializes the CSV file with headers if it doesn't exist or is empty.
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
        logging.info(f"CSV file '{CSV_FILE}' initialized with headers.")
    else:
        logging.info(f"CSV file '{CSV_FILE}' already exists and is not empty.")


def load_all_records():
    #Loads all records from the CSV file and returns them as a list of dictionaries.
    initialize_csv()
    records = []
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            records.append(row)
        return records

def save_record(record_data):
    #Appends a new record to the CSV file.
    initialize_csv()

    #Fill missing fields with defaults if not provided
    full_record = {field: record_data.get(field, "") for field in FIELDNAMES}

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writerow(full_record)
    return True

def update_record(incident_id, ai_results):
    #Updates an existing incident record in the CSV file based on the provided incident_id and AI results.
    records = load_all_records()
    updated = False

    for record in records:
        if record["INCIDENT_ID"] == str(incident_id):
            record["VALID_CATEGORIES"] = ai_results.get("VALID_CATEGORIES", record["VALID_CATEGORIES"])
            record["SEVERITY"] = ai_results.get("SEVERITY", record["SEVERITY"])
            record["CONFIDENCE"] = ai_results.get("CONFIDENCE", record["CONFIDENCE"])
            record["STATUS"] = "PROCESSED"
            updated = True
            break

    if updated:
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(records)

    return updated

def filter_by_severity(severity_level):
    #Filters records in the CSV file based on the provided severity level.
    records = load_all_records()
    return [record for record in records if str(record.get("SEVERITY")) == str(severity_level)]

def filter_by_category(category):
    #Filters records in the CSV file based on the provided category.
    records = load_all_records()
    return [record for record in records if category in record.get("VALID_CATEGORIES", "").lower() == target_category.lower()]

def get_records_by_user(user_id):
    #Retrieves all records associated with the provided user_id.
    records = load_all_records()
    return [record for record in records if str(record.get("USER_ID")) == str(user_id)]