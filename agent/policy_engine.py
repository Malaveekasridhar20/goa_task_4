import os
from typing import Dict, List, Any

# Policy constants
ACTIONS = [
    "ALLOW_TRANSACTION", "DECLINE_TRANSACTION", "MONITOR_CARD", "MONITOR_CONNECTED_CARDS",
    "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH", "BLOCK_CARD", "BLOCK_ALL_CARDS",
    "GENERATE_REPORT", "CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD"
]

def check_policy(recommendation: str, risk: float, exposure_usd: float, evidence: List[Dict], confidence: float) -> Dict[str, Any]:
    """
    Evaluates a recommendation against the strict fraud policy.
    Returns the valid actions and the required approval route.
    """
    actions = []
    
    # R1: Verify before you block on a weak signal
    if ("BLOCK" in recommendation or "DECLINE" in recommendation) and confidence < 0.70:
        actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: weak signal, verifying before blocking"})
        return {"actions": actions, "policy_reference": "R1"}

    # R2: Escalation if uncertain and exhausted verification (assuming evidence has verification exhausted)
    # We will simulate "exhausted verification" if VERIFY is recommended again but confidence is very low.
    if ("VERIFY" in recommendation or confidence < 0.50) and len(evidence) > 2 and not ("BLOCK" in recommendation or "ALLOW" in recommendation):
        actions.append({"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "R2: Uncertain and exhausted verification"})
        return {"actions": actions, "policy_reference": "R2"}

    # R7: Disputed but legitimate recurring pattern
    if "LEGITIMATE RECURRING" in recommendation.upper() or ("DISPUTE" in recommendation.upper() and "LEGITIMATE" in recommendation.upper()):
        actions.append({"action": "ALLOW_TRANSACTION", "route": "L1", "reason": "R7: Disputed but legitimate recurring pattern"})
        return {"actions": actions, "policy_reference": "R7"}

    # R10: BLOCK_ALL_CARDS restrictions
    if "BLOCK_ALL_CARDS" in recommendation:
        actions.append({"action": "BLOCK_ALL_CARDS", "route": "L2", "reason": "R10: BLOCK_ALL_CARDS restrictions"})
        return {"actions": actions, "policy_reference": "R10"}

    if "BLOCK" in recommendation:
        # R4: Exposure > $2500
        if exposure_usd > 2500:
            actions.append({"action": "BLOCK_CARD", "route": "L2", "reason": "R4: Exposure > $2500 requires L2"})
            policy = "R4"
        # R3: Exposure <= $2500
        else:
            actions.append({"action": "BLOCK_CARD", "route": "L1", "reason": "R3: L1 required for blocking card <= $2500"})
            policy = "R3"
            
        actions.append({"action": "CREATE_CASE", "route": "auto", "reason": "Required when blocking"})

        # R5: Confirmed fraud and exposure > $1000
        if exposure_usd > 1000 and confidence >= 0.85:
            actions.append({"action": "FILE_REPORT", "route": "L2", "reason": "R5: Confirmed fraud and exposure > $1000"})
            
        return {"actions": actions, "policy_reference": policy}

    if "ALLOW" in recommendation or "LEGITIMATE" in recommendation:
        # R6: Legitimate Closure
        actions.append({"action": "CLOSE_NO_FRAUD", "route": "auto", "reason": "R6: Deemed legitimate"})
        return {"actions": actions, "policy_reference": "R6"}

    if "VERIFY" in recommendation:
        actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "Verifying transaction with customer"})
        return {"actions": actions, "policy_reference": "R1"}
        
    # R9: Undocumented patterns
    if "UNDOCUMENTED" in recommendation.upper() or confidence < 0.30:
        actions.append({"action": "ESCALATE_TO_ANALYST", "route": "L2", "reason": "R9: Undocumented patterns"})
        return {"actions": actions, "policy_reference": "R9"}

    # R8: Escalate when uncertain and exposed
    if confidence < 0.60 and exposure_usd > 1000:
        actions.append({"action": "ESCALATE_TO_ANALYST", "route": "L2", "reason": "R8: Escalate when uncertain and exposed"})
        return {"actions": actions, "policy_reference": "R8"}

    # Default fallback
    actions.append({"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "Uncertain, escalated"})
    return {"actions": actions, "policy_reference": "R2"}

def determine_approval_route(actions: List[Dict]) -> str:
    routes = [a["route"] for a in actions]
    if "L2" in routes:
        return "L2"
    if "L1" in routes:
        return "L1"
    return "auto"
