# 1. report_details -> AI_manager -> object[category, contact_type, stated_effect, severity, confidence, reasoning]
# 2. object[] -> logic_Manager
# 3. logic_Manager -> object[] + second_opinion_required, immediate_action_required + trip_id + user_id + report_details + license_id

# list of all ride categories
# 

# Test new AI object format
# sample0 = {
#     "category": "",
#     "contact_type": "",
#     "stated_effect": "",
#     "severity": "",
#     "confidence": "",
#     "reasoning": ""
# }

# Hard coded info for testing, from ai manager output, passed down to logic manager, will be sent to data manager for storage
# trip_id + user_id + report_details + license_id
trip_id = "1234"#string
user_id = "A9006111"#string
license_id = "ABCD1234"#string
report_details = "Placeholder text I want to play persona"

# Test 1: High severity assault
sample1 = {

    "category": "physical_assault",
    "severity": 2,
    "confidence": 0.52,
    "report": "THere was an imposter amongus",
    "trip_id": 1234,
    "user_id": "A9006111"

 }

def getAi_output(assess_object):
    category = assess_object["category"] #variable category contains the category of harrassment from ai output
    severity = assess_object["severity"]    #variable severity contains the category of harrassment from ai output
    confidence = assess_object["confidence"]    #variable category contains the category of harrassment from ai output

    return 




def safety_escalation(assess_object): #get ai output
    category = assess_object["category"] #variable category contains the category of harrassment from ai output
    severity = assess_object["severity"]    #variable severity contains the category of harrassment from ai output
    confidence = assess_object["confidence"]    #variable category contains the category of harrassment from ai output

    emergency_categories = (
    "physical_assault",
    "sexual_harassment",
    "stalking",
    )

    if severity >= 2 and category in emergency_categories and confidence >= 0.5:
        queue = "emergency_response"
        flag_driver = 'Flagged'
        second_opinion = False #boolean
        print("Emergency response required for category:", category, "with severity:", severity, "and confidence:", confidence)
        return queue, flag_driver, second_opinion

def confidence_escalation(assess_object):
    confidence = assess_object["confidence"]
    if   confidence < 0.5:
        queue ="low_confidence, manual review required"
        flag_driver = 'Not_Flagged'
        second_opinion = True #boolean
        return queue, second_opinion, flag_driver


def default_escalation(assess_object):
    severity = assess_object["severity"]
    category = assess_object["category"]
    confidence = assess_object["confidence"]
    emergency_categories = (
    "physical_assault",
    "sexual_harassment",
    "stalking"
    )
    if severity <2 and category in emergency_categories and confidence >=0.5:
        queue= "standard triage"
        flag_driver = 'Not_Flagged'
        second_opinion = False #boolean
        print("Standard triage for category:", category, "with severity:", severity, "and confidence:", confidence)
        return queue, flag_driver, second_opinion

result = safety_escalation(sample1)
result = default_escalation(sample1)
print(result)

