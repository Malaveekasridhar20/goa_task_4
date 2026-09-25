import json

with open('cases/HHG-001.json') as f:
    d = json.load(f)

print("=== HHG-001 FULL RESULT ===")
print("case_id:", d.get("case_id"))
print("flagged_txn_id:", d.get("flagged_txn_id"))
print("execution_mode:", d.get("execution_mode"))
print("investigation_status:", d.get("investigation_status"))
print("uncertainty_level:", d.get("uncertainty_level"))
print("pattern_assessment:", d.get("pattern_assessment"))
print("evidence_count:", len(d.get("graph_evidence", [])))
print()
print("--- EVIDENCE ---")
for ev in d.get("graph_evidence", []):
    print("  [%s] query=%s status=%s" % (ev.get("evidence_id"), ev.get("query"), ev.get("status")))
    attrs = ev.get("attributes", {})
    for k, v in list(attrs.items())[:6]:
        print("    %s: %s" % (k, v))
print()
print("--- FINAL NBA ---")
nba = d.get("final_nba") or {}
print(json.dumps(nba, indent=2))
print()
print("--- POLICY RESULTS ---")
policy = d.get("policy_results") or {}
print(json.dumps(policy, indent=2))
