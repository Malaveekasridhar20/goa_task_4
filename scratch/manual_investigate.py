import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.graph_agent import InvestigationAgent
from dotenv import load_dotenv

load_dotenv()

agent = InvestigationAgent(evaluation_mode="OFFICIAL_BENCHMARK")

case_input = {
    "case_id": "HHG-001",
    "flagged_txn_id": "3514030",
    "risk_score": 0.8
}

print("1. Trigger: HHG-001 (Txn 3514030)")
res = agent.investigate(case_input)

print("\n--- INVESTIGATION TRACE ---")

# Pull items from the result
print("2. Initial evidence:")
for ev in res.get("graph_evidence", []):
    print(f"   - {ev.get('query')}: {ev.get('finding')}")

print(f"\n3. Initial fraud probability: {res.get('final_nba', {}).get('actions', [])} (This was overriden, checking case output...)")
print(f"3/4. Initial probability & pattern usually found before simulation.")

if res.get("evidence_requests"):
    req = res["evidence_requests"][0]
    print(f"\n6. Evidence request: {req.get('type')} ({req.get('asked_after_step')})")
    print(f"7. Assumed response: {req.get('assumed_response')}")

print(f"\n8. Additional evidence generated: {bool(res.get('evidence_requests'))}")

c = res.get("case", {})
print(f"9. Updated fraud probability: {c.get('fraud_probability')}")
print(f"10. Updated pattern: {c.get('pattern')} - {c.get('pattern_description')}")

pd = res.get("policy_results", {})
print(f"\n11. Final policy evaluation: Rule {pd.get('policy_rule')} -> {pd.get('approval_route')}")
print(f"12. Final NBA: {pd.get('explanation')}")

sar = res.get("sar", {})
print(f"13. SAR decision: File={sar.get('file')} Reason={sar.get('reason')}")

print(f"14. Stop reason: {res.get('stop_reason')}")
print(f"15. Case graph write: {c.get('written_to_graph')} (ID: {c.get('graph_case_id')})")

print("\n--- FINAL JSON VALIDATION ---")
# Validation logic
required_keys = ["case_id", "execution_mode", "case", "evidence_requests", "next_best_actions", "sar", "stop_reason", "tool_calls"]
missing = [k for k in required_keys if k not in res]
if missing:
    print(f"16. Final JSON validation: FAILED. Missing keys: {missing}")
else:
    case_keys = ["status", "verdict", "fraud_probability", "pattern", "pattern_description", "affected_txn_ids", "exposure_usd", "written_to_graph", "graph_case_id"]
    missing_case = [k for k in case_keys if k not in res["case"]]
    if missing_case:
        print(f"16. Final JSON validation: FAILED in 'case' object. Missing: {missing_case}")
    else:
        print("16. Final JSON validation: PASSED. All strict schema fields present.")

print("\n--- FULL JSON DUMP ---")
print(json.dumps(res, indent=2))
