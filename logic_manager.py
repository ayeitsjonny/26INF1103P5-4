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

# Hard coded info
# trip_id + user_id + report_details + license_id
trip_id = "1234"#string
user_id = "A9006111"#string
license_id = "ABCD1234"#string
report_details = "Placeholder text I want to play persona"

# Test 1: High severity assault
sample1 = {

    "category": "physical_assault",
    "severity": 2,
    "confidence": 0.52
 }

#queue={low_confidence, emergency_response, normal_report}

# # Test 2: Low confidence
# sample2 = {
#     "category": "verbal_abuse",
#     "severity": 1,
#     "confidence": 0.35
# }

# # Test 3: Normal report
# sample3 = {
#     "category": "reckless_driving",
#     "severity": 1,
#     "confidence": 0.87
# }


def safety_escalation(assess_object):
    category = assess_object["category"]
    severity = assess_object["severity"]
    confidence = assess_object["confidence"]

    emergency_categories = (
    "physical_assault",
    "sexual_harassment",
    "stalking"
    )

    if severity >= 2 and category in emergency_categories and confidence >= 0.8:
        queue = "emergency_response"
        flag_driver = 'Flagged'
        second_opinion = False #boolean
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
        return queue, flag_driver, second_opinion


result = safety_escalation(sample1)
result = default_escalation(sample1)
print(result)

