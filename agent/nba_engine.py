import json
from typing import Dict, Any, List

def calculate_uncertainty(evidence: List[Dict]) -> float:
    """
    Calculates uncertainty based on evidence.
    Returns a value between 0 (certain) and 1 (highly uncertain).
    """
    if not evidence:
        return 1.0
    
    # Placeholder for more complex uncertainty logic
    if len(evidence) >= 2:
        return 0.2
    return 0.6

def generate_nba(case_state: Dict[str, Any], policy_engine) -> Dict[str, Any]:
    """
    Generates the Next Best Action based on the current case state.
    """
    risk = case_state.get("fraud_probability", 0.5)
    exposure = case_state.get("exposure_usd", 0.0)
    evidence = case_state.get("evidence", [])
    confidence = 1.0 - calculate_uncertainty(evidence)
    
    # Make initial recommendation based on risk and confidence
    recommendation_text = ""
    if risk >= 0.85:
        recommendation_text = "BLOCK_CARD"
    elif risk <= 0.15:
        recommendation_text = "ALLOW_TRANSACTION"
    elif risk > 0.6:
        recommendation_text = "VERIFY_WITH_CUSTOMER"
    else:
        recommendation_text = "ESCALATE"

    # Run through policy engine
    policy_result = policy_engine.check_policy(
        recommendation=recommendation_text,
        risk=risk,
        exposure_usd=exposure,
        evidence=evidence,
        confidence=confidence
    )
    
    nba = {
        "actions": policy_result["actions"],
        "confidence": confidence,
        "approval_required": any(a["route"] != "auto" for a in policy_result["actions"]),
        "approval_route": policy_engine.determine_approval_route(policy_result["actions"])
    }
    
    return nba
