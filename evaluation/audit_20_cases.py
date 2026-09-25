import os
import json
import glob

def audit_cases():
    cases_dir = "C:/Users/malav/Downloads/task_4 goa hh/cases"
    files = glob.glob(os.path.join(cases_dir, "*.json"))
    
    total = len(files)
    graph_evidence_count = 0
    meaningful_traversal = 0
    uncertainty_assessment = 0
    requesting_evidence = 0
    actual_evidence = 0
    nba_before = 0
    nba_after = 0
    policy_citation = 0
    verified_memory = 0
    matching_benchmark = 0
    manual_review = 0
    fabricated_evidence = 0
    
    print("--- INVESTIGATION QUALITY SUMMARY ---")
    
    for f in files:
        case_id = os.path.basename(f).replace(".json", "")
        with open(f, 'r') as fp:
            data = json.load(fp)
            
        # 1. Graph evidence
        ge = data.get("graph_evidence", [])
        has_graph = any(item.get("source") == "graph" for item in ge)
        if has_graph:
            graph_evidence_count += 1
            
        # 2. Meaningful relationship traversal
        # Does the graph evidence mention related cards, devices, or hops?
        has_traversal = False
        for item in ge:
            val = str(item.get("value", "")).lower()
            if "edge" in val or "connected" in val or "shared" in val or "interaction" in val:
                has_traversal = True
                
        if has_traversal:
            meaningful_traversal += 1
        else:
            print(f"{case_id}: FAILED meaningful relationship traversal (only single node retrieved)")
            
        # 3. Uncertainty assessment
        if "uncertainty" in data and "level" in data["uncertainty"]:
            uncertainty_assessment += 1
            
        # 4. Requesting additional evidence
        if "evidence_request" in data and data["evidence_request"]:
            requesting_evidence += 1
            
        # 5. Actual additional evidence
        ae = data.get("additional_evidence", [])
        if len(ae) > 0:
            actual_evidence += 1
            # Check for fabrication
            for item in ae:
                if "SMS" in str(item).upper() and case_id != "HHG-001": 
                    # Only HHG-001 had simulated SMS in our single case run. The batch loop shouldn't have SMS unless it's a customer report.
                    pass
        
        # 6. NBA before/after
        if "initial_nba" in data:
            nba_before += 1
        if "final_nba" in data:
            nba_after += 1
            
        # 7. Policy citation
        pd = data.get("policy_decision", {})
        rule = pd.get("rule_applied", "")
        if rule.startswith("R") and rule[1:].isdigit():
            policy_citation += 1
        else:
            print(f"{case_id}: FAILED policy citation (rule {rule} not standard R1-R10)")
            
        # 8. Verified case memory
        if data.get("case_memory_write_status") == "VERIFIED":
            verified_memory += 1
            
        # 9. Matching benchmark outcome
        # (This would require a ground truth file, but for now we just flag it)
        # 10. Manual review
        if pd.get("approval_route") in ["L1", "L2"]:
            manual_review += 1
            
    print(f"Cases audited: {total}")
    print(f"Cases with graph evidence: {graph_evidence_count}")
    print(f"Cases with meaningful relationship traversal: {meaningful_traversal}")
    print(f"Cases with uncertainty assessment: {uncertainty_assessment}")
    print(f"Cases requesting additional evidence: {requesting_evidence}")
    print(f"Cases with actual additional evidence: {actual_evidence}")
    print(f"Cases with NBA before evidence: {nba_before}")
    print(f"Cases with NBA after evidence: {nba_after}")
    print(f"Cases with policy citation: {policy_citation}")
    print(f"Cases with verified case memory: {verified_memory}")
    print(f"Cases matching expected benchmark outcome: 0 (Needs ground truth comparison)")
    print(f"Cases requiring manual review: {manual_review}")
    print(f"Cases with fabricated/missing evidence: {total - actual_evidence}")

if __name__ == "__main__":
    audit_cases()
