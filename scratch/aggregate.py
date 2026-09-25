import json
import os
import glob
from collections import Counter

def aggregate():
    cases_dir = "cases_official"
    if not os.path.exists(cases_dir):
        print(f"Directory {cases_dir} not found.")
        return
        
    files = glob.glob(os.path.join(cases_dir, "*.json"))
    if len(files) == 0:
        print("No cases found.")
        return
        
    stats = {
        "total_cases": len(files),
        "completed": 0,
        "data_unavailable": 0,
        "blocked_dataset_mismatch": 0,
        "real_graph_evidence_count": 0,
        "graph_algorithm_evidence_count": 0,
        "multi_hop_evidence_count": 0,
        "graphrag_evidence_count": 0,
        "evidence_requests": 0,
        "additional_evidence_supplied": 0,
        "final_nba_distribution": Counter(),
        "verified_policy_count": 0,
        "case_memory_success_count": 0,
        "fabricated_evidence_count": 0,
        "unsupported_risk_claims": 0,
        "mapping_inconsistencies": 0
    }
    
    representative_cases = {}
    
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        case_id = data.get("case_id")
        inv_status = data.get("investigation_status")
        exec_mode = data.get("execution_mode")
        
        # Mapping consistency check
        if exec_mode != "REAL_GRAPH_DEMO" or data.get("is_official_benchmark") or data.get("mapping_method") != "DEMO_MAPPING" or data.get("mapping_confidence") != 0:
            stats["mapping_inconsistencies"] += 1
            
        if inv_status == "COMPLETED":
            stats["completed"] += 1
        elif inv_status == "DATA_UNAVAILABLE":
            stats["data_unavailable"] += 1
        elif inv_status == "BLOCKED_DATASET_MISMATCH" or exec_mode == "BLOCKED_DATASET_MISMATCH":
            stats["blocked_dataset_mismatch"] += 1
            
        # Evidence checks
        graph_evidence = data.get("graph_evidence", [])
        graphrag_ev = data.get("graphrag_evidence", [])
        
        real_graph = any(ev.get("source") == "TigerGraph_MCP" for ev in graph_evidence if ev)
        algo_graph = any(ev.get("source") == "TigerGraph_GraphAlgorithm" for ev in graph_evidence if ev)
        multi_hop = any(ev.get("query") in ["get_merchant_context", "get_party_device_ip_context"] for ev in graph_evidence if ev)
        
        if real_graph: stats["real_graph_evidence_count"] += 1
        if algo_graph: stats["graph_algorithm_evidence_count"] += 1
        if multi_hop: stats["multi_hop_evidence_count"] += 1
        if graphrag_ev: stats["graphrag_evidence_count"] += 1
        
        if data.get("evidence_request"):
            stats["evidence_requests"] += 1
            
        if data.get("additional_evidence"):
            stats["additional_evidence_supplied"] += 1
            
        # Fabrication checks (no risk score used in NBA, policy is verified)
        if "risk_score" in json.dumps(data.get("final_nba", {})).lower():
            stats["unsupported_risk_claims"] += 1
            
        final_nba = data.get("final_nba", {})
        actions = final_nba.get("actions", [])
        action = actions[0].get("action", "NONE") if actions else "NONE"
        stats["final_nba_distribution"][action] += 1
        
        policy_decision = data.get("policy_decision", {})
        if policy_decision.get("policy_status") == "VERIFIED":
            stats["verified_policy_count"] += 1
        elif final_nba.get("policy_rule") and policy_decision.get("policy_status") != "VERIFIED":
            stats["fabricated_evidence_count"] += 1
            
        if data.get("case_memory_written"):
            stats["case_memory_success_count"] += 1
            
        # Select 3 representative cases
        # 1. Strong graph evidence (has algo and multi hop)
        if algo_graph and multi_hop and "strong" not in representative_cases:
            representative_cases["strong"] = data
        # 2. High uncertainty
        elif data.get("uncertainty", {}).get("level") == "HIGH" and "uncertain" not in representative_cases:
            representative_cases["uncertain"] = data
        # 3. Different pattern/context
        elif "different" not in representative_cases:
            representative_cases["different"] = data

    print("--- Aggregate Summary ---")
    for k, v in stats.items():
        if isinstance(v, Counter):
            print(f"{k}: {dict(v)}")
        else:
            print(f"{k}: {v}")
            
    print("\n--- 3 Representative Cases ---")
    for category, case_data in representative_cases.items():
        print(f"\n[{category.upper()} CASE] - {case_data.get('case_id')}")
        print("investigation:", case_data.get("investigation_status"))
        print("graph evidence:", len(case_data.get("graph_evidence", [])))
        print("algorithm evidence:", any(ev.get("source") == "TigerGraph_GraphAlgorithm" for ev in case_data.get("graph_evidence", []) if ev))
        print("GraphRAG:", len(case_data.get("graphrag_evidence", [])))
        print("pattern assessment:", json.dumps(case_data.get("pattern_assessment"), indent=2))
        print("uncertainty:", case_data.get("uncertainty"))
        print("evidence request:", case_data.get("evidence_request"))
        print("NBA:", case_data.get("final_nba"))
        print("policy rule:", case_data.get("policy_decision", {}).get("policy_rule"))
        print("case memory:", case_data.get("case_memory_written"))

if __name__ == "__main__":
    aggregate()
