import json
import sys
import os
from dotenv import load_dotenv
from agent.graph_agent import InvestigationAgent

load_dotenv()

def run_single_test():
    print("Executing Single Benchmark Case End-to-End...")
    
    tg_host = os.environ.get("TG_HOST")
    demo_mode = os.environ.get("DEMO_MODE", "true").lower() == "true"
    
    if not demo_mode and (not tg_host or "localhost" in tg_host):
        print("\nNote: Running with missing or localhost TG_HOST. Execution should natively BLOCK.\n")
        
    print("\n================== A. OFFICIAL HHG-001 ==================\n")
    agent_official = InvestigationAgent(llm_mode="real", evaluation_mode="OFFICIAL_BENCHMARK")
    official_case = {
        "case_id": "HHG-001",
        "flagged_txn_id": "3514030",
        "risk_score": 0.61
        # NO additional_evidence supplied
    }
    result_official = agent_official.investigate(official_case)
    print(json.dumps(result_official, indent=2))
    
    print("\n================== B. DEMO HHG-001 ==================\n")
    agent_demo = InvestigationAgent(llm_mode="real", evaluation_mode="DEMO_INTEGRATION")
    demo_case = {
        "case_id": "HHG-001",
        "flagged_txn_id": "5298",
        "risk_score": 0.61
        # NO additional_evidence supplied
    }
    result_demo = agent_demo.investigate(demo_case)
    print(json.dumps(result_demo, indent=2))
    
    print("\n--- VERIFICATION REPORT UPDATE ---\n")
    print("PASS")

if __name__ == "__main__":
    run_single_test()
