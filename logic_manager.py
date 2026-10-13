
def getAi_output(ai_object):                # function to get data from ai output
    category = ai_object["category"]        # variable category contains the category of harrassment from ai output
    severity = ai_object["severity"]        # variable severity contains the severity rating from ai output
    confidence = ai_object["confidence"]    # variable confidence contains the confidence scalefrom ai output
    return category,severity,confidence



def validate_AIoutput(ai_object): # function to validate ai output
    if not isinstance(ai_object, dict) or not ai_object: #if output is not a dictionary or is empty dictionary
        return False
    else:
        return True

    # keys=("category","severity","confidence")
    # for key in keys:
    #     if key not in ai_object:
    #         print("key not in dictionary") #testing
    #         return False
    #     if key not in ai_object[key]=="": #missing dictionary value
    #         print("key has missing value")#testing
    #         return False


def escalation(assess_object): # parse ai output as an input
    if validate_AIoutput(assess_object) == True:
        category, severity, confidence = getAi_output(assess_object)

        emergency_categories = (
        "physical_assault",
        "sexual_harassment",
        "stalking",
        )

        # Initialize both flags to false
        emergency_escalation = False    # boolean value to indicate whether emergency escalation is required
        second_opinion = False          # boolean value to indicate whether second opinion is required

        if severity >= 2 and category in emergency_categories and confidence >= 0.5:
            emergency_escalation = True # boolean

        elif confidence < 0.5:
            second_opinion = True # boolean value to indicate whether second opinion is required

        assess_object.update({
        "second_opinion_required" : second_opinion, 
        "immediate_attention_required" : emergency_escalation})

        return assess_object # returns original sample with new flags raised and appended
        
    else:
        return False

