import csv
import io_manager
import ai_manager

USE_MOCK = False  # set True to test without a Gemini API key

def main():
    if USE_MOCK:
        ai_manager.call_api = ai_manager.call_api_mock

    record = io_manager.user_input()
    result = ai_manager.process(record)

    print("\n--- Report ---")
    print(f"Trip: {record['trip_id']} | User: {record['user_id']} | Plate: {record['license_plate']}")

    print("\n--- AI Summary ---")
    if result is None:
        print("AI could not classify this report. Route to manual review.")
    else:
        print(f"Category:      {result['category']}")
        print(f"Severity:      {result['severity']}")
        print(f"Contact type:  {result['contact_type']}")
        print(f"Stated effect: {result['stated_effect']}")
        print(f"Confidence:    {result['confidence']:.2f}")
        print(f"Reasoning:     {result['reasoning']}")

        record.update(result)  # merge AI fields into the record for logic_manager later

if __name__ == "__main__":
    main()

