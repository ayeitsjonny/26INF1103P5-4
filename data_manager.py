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

print(FIELDNAMES)