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
    
    # R1: Step-up authentication / Verify with customer
    if ("BLOCK" in recommendation or "DECLINE" in recommendation) and confidence < 0.70:
        actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: Step-up authentication required for weak signal"})
        return {"actions": actions, "policy_reference": "R1"}

    # Escalate if uncertain and exhausted verification
    if ("VERIFY" in recommendation or confidence < 0.50) and len(evidence) > 2 and not ("BLOCK" in recommendation or "ALLOW" in recommendation):
        actions.append({"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "Uncertain and exhausted verification"})
        return {"actions": actions, "policy_reference": None}

    # R7: Disputes
    if "LEGITIMATE RECURRING" in recommendation.upper() or ("DISPUTE" in recommendation.upper() and "LEGITIMATE" in recommendation.upper()):
        actions.append({"action": "ALLOW_TRANSACTION", "route": "L1", "reason": "R7: Disputed but legitimate recurring pattern"})
        return {"actions": actions, "policy_reference": "R7"}

    if "BLOCK_ALL_CARDS" in recommendation:
        actions.append({"action": "BLOCK_ALL_CARDS", "route": "L2", "reason": "Blocking all cards requires L2 approval"})
        return {"actions": actions, "policy_reference": None}

    if "BLOCK" in recommendation:
        # Blocking limits > $2500
        if exposure_usd > 2500:
            actions.append({"action": "BLOCK_CARD", "route": "L2", "reason": "Blocking limit exceeded ($2500), requires L2"})
            policy = None
        # Blocking limits <= $2500
        else:
            actions.append({"action": "BLOCK_CARD", "route": "L1", "reason": "Blocking limit under threshold, requires L1"})
            policy = None
            
        actions.append({"action": "CREATE_CASE", "route": "auto", "reason": "Required when blocking"})

        # SAR filing thresholds
        if exposure_usd > 1000 and confidence >= 0.85:
            actions.append({"action": "FILE_REPORT", "route": "L2", "reason": "SAR filing threshold met (Confirmed fraud and exposure > $1000)"})
            
        return {"actions": actions, "policy_reference": policy}

    if "ALLOW" in recommendation or "LEGITIMATE" in recommendation:
        actions.append({"action": "CLOSE_NO_FRAUD", "route": "auto", "reason": "Deemed legitimate based on available evidence and simulated response."})
        return {"actions": actions, "policy_reference": None}

    if "VERIFY" in recommendation:
        actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: Step-up authentication required"})
        return {"actions": actions, "policy_reference": "R1"}
        
    if "UNDOCUMENTED" in recommendation.upper() or confidence < 0.30:
        actions.append({"action": "ESCALATE_TO_ANALYST", "route": "L2", "reason": "Undocumented pattern, escalation required"})
        return {"actions": actions, "policy_reference": None}

    if confidence < 0.60 and exposure_usd > 1000:
        actions.append({"action": "ESCALATE_TO_ANALYST", "route": "L2", "reason": "Escalation due to high exposure and uncertainty"})
        return {"actions": actions, "policy_reference": None}

    # Default fallback
    actions.append({"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "Uncertain, escalated"})
    return {"actions": actions, "policy_reference": None}

def determine_approval_route(actions: List[Dict]) -> str:
    routes = [a["route"] for a in actions]
    if "L2" in routes:
        return "L2"
    if "L1" in routes:
        return "L1"
    return "auto"
