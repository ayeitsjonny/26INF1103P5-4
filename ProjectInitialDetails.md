<h1 style="border-bottom: none; text-decoration: underline;">Project Initial Details</h1>

# Problem Statement & Target Users:
```
On ride-hailing platforms such as Grab, Gojek, and Tada, reports of harassment and abuse arrive as unstructured free text. Trust & Safety teams handle them manually alongside ordinary complaints; severity isn't sorted reliably when reports come in. This creates harms such as high-risk reports sitting in the same queue as minor ones. In Singapore, the Protection from Harassment Act (POHA) covers harassment, and operators owe duty-of-care obligations to LTA-licensed drivers and passengers. An undocumented or delayed response is a compliance liability, not just an efficiency issue. 

Through the use of an AI-assisted workflow, our solution allows user inputs to be properly tagged and categorised into classifications based on severity, providing a sanitised list of reports for customer support to filter through.
```

## Target Users:
- Reporting Users (Passengers): File confidential hazard or harassment incident observations from the field.
- Trust & Safety teams: Review prioritized, categorized safety output, automated escalation queues, recurring-offender alerts, and mandatory corrective actions.

# User Inputs (io_manager.py)
- Free-text description of the incident (required, sanitised before reaching the AI)
- Trip ID (required, validated against the active/recent trip log)
- User ID (required)
- Driver’s License Plate number (required)
- Timestamp (auto-captured)
- Possible future implementation:  
    * Severity self-assessment (low/medium/high) — stored for audit, never overrides the AI's classification
    * Evidence Attachments(filenames/IDs only, not the files themselves)


# Use of AI (ai_manager.py)
**<ins>How will AI be utilised within the application?</ins>**
- The AI will process user input and produce a structured JSON object based on the incident severity, in a format that can be stored in a CSV file.

**<ins>What outputs, insights, or recommendations will the AI generate from the user inputs?</ins>**
```
Outputs:
User’s Free Text Input(e.g. Report_Details) —> AI structured JSON response output containing:
- Category (AI interprets free text input and assesses the category, stored as a string)
- Severity: low, medium, high (Stored as an integer from 0-2, with 0 being the lowest and 2 being  
the highest)
- Confidence: 0-1 (0 means low confidence and 1 means high confidence. Stored as a float)
```

# Business Rules (logic_manager.py)
| Rule    | Condition | Outcome |
| -------- | ------- | ------- |
| Immediate safety escalation  | severity == high AND category ∈ {physical_assault, sexual_harassment, stalking}   | Automatically escalate to the emergency response queue and temporarily flag the driver's account for restriction pending review.    |
| Low confidence rating | AI confidence score < 0.5     | Send to the manual safety-triage queue; flag "second opinion required" instead of auto-actioning the report.    |
| Spam / Flood suppression    | Same user_id submits >5 reports within a 7-day window   | Flag account for suspected spam/false reporting; rate limit further submissions from that account    |
| Default    | None of the above conditions applies    | Log the record and include it in the standard triage queue at normal priority    |

Repository URL: [26INF1103P5-4](https://github.com/ayeitsjonny/26INF1103P5-4)