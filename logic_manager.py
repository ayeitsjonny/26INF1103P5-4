#NO SPAM DETECTION FUNCTION

# 1. report_details -> AI_manager -> object[category, contact_type, stated_effect, severity, confidence, reasoning]
# 2. object[] -> logic_Manager
# 3. logic_Manager -> object[] + second_opinion_required, immediate_action_required + trip_id + user_id + report_details + license_id

# Hard coded info for testing, from ai manager output, passed down to logic manager, will be sent to data manager for storage
# trip_id + user_id + report_details + license_id
trip_id = "1234"#string # follow ai manager -J
user_id = "A9006111"#string
license_id = "ABCD1234"#string
report_details = "Placeholder text I want to play persona"

# all of the AI categories
## for our sanity's sake, for all the ai categories,
## we already have designated emergency categories.                         ooo you touch my tralala  mmmmm my dingdingdong
###emegensi categrills arr(physical_assault, sexual harrassment, stalking)     touch me, ooo touch me more,, huehuehue touch me HARDER
# *physical_assault
# *sexual_harrassment
# *stalking
# unsafe_driving 
# verbal_harrassment
# long_hauling
# misc

# Test 1: High severity assault, this is what logic manager uses to make decisions
sample1 = {

    "category": "physical_assault",
    "severity": 2,                   #(0-2 integer, 0 lowest 2 highest)
    "confidence": 0.5,              #(0-1 float, 0 lowest 2 highest)
    "report": "THere was an imposter amongus",
    "trip_id": 1234,
    "user_id": "A9006111"

 }

def getAi_output(assess_object): #test function to get data from ai output, REAL ai output will also be json output
    category = assess_object["category"] #variable category contains the category of harrassment from ai output
    severity = assess_object["severity"]    #variable severity contains the category of harrassment from ai output
    confidence = assess_object["confidence"]    #variable category contains the category of harrassment from ai output

    return category,severity,confidence



def escalation(assess_object): #get ai output
    category, severity, confidence = getAi_output(assess_object)
    #variable category contains the category of harrassment from ai output
    #variable severity contains the category of harrassment from ai output


    emergency_categories = (
    "physical_assault",
    "sexual_harassment",
    "stalking",
    )

    confidence = assess_object["confidence"]
    emergency_escalation = False #boolean value to indicate whether emergency escalation is required
    second_opinion = False #boolean value to indicate whether second opinion is required


    if severity >= 2 and category in emergency_categories and confidence >= 0.5:
        emergency_escalation = True #boolean
        print("emergency:", emergency_escalation,"second_opinion:", second_opinion) #for testing

        return second_opinion,emergency_escalation
    elif confidence < 0.5:
        second_opinion = True #boolean value to indicate whether second opinion is required
        print("emergency:", emergency_escalation,"second_opinion:", second_opinion) #for testing

        return second_opinion,emergency_escalation
    else:
        print("emergency:", emergency_escalation,"second_opinion:", second_opinion) #for testing

        return second_opinion, emergency_escalation


def final_output(assess_object):
    second_opinion,emergency_escalation= escalation(assess_object)
    sample1.update({
        "second_opinion ":second_opinion, 
        "emergency_escalation":emergency_escalation})

    print(sample1)#for testing
    return sample1

    





#sample1
result = escalation(sample1)
final_output(sample1)
# result = default_escalation(sample1)


