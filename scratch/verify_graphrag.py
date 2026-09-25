import sys
import os
import json
from pprint import pprint

sys.path.append(os.getcwd())

from agent.graph_agent import InvestigationAgent
from graphrag.retriever import GraphRAGRetriever

def verify():
    # 1. Run GraphRAG directly to see raw context
    print("--- GraphRAG Raw Context ---")
    retriever = GraphRAGRetriever("C:/Users/malav/Downloads/closed_cases_history.csv")
    raw_context = retriever.build_context(["Mock Evidence"], ["testing"])
    
    print("\nPolicy Source File:", os.path.join(os.path.dirname(os.path.dirname(retriever.__module__)), "docs", "POLICY_MAPPING.md"))
    print("\nPolicy Text Retrieved (first 200 chars):", repr(raw_context.get('policy', '')[:200]) + "...")
    print("\nPatterns Retrieved:", raw_context.get('patterns'))
    print("\nRegulatory Reference:", raw_context.get('regulatory'))
    print("\nHistorical Cases Loaded:")
    for h in raw_context.get('historical_cases', []):
        print(f" - {h.get('case_id')}: {h.get('outcome')}")
        
    print("\n\n--- Agent Execution (DEMO_INTEGRATION) ---")
    case_input = {
        "case_id": "HHG-001",
        "flagged_txn_id": "5298",
        "risk_score": 0.85,
        "additional_evidence": None
    }
    
    agent = InvestigationAgent(evaluation_mode="DEMO_INTEGRATION")
    result = agent.investigate(case_input)
    
    print("\nGraphRAG Evidence in Output:")
    print(json.dumps(result.get('graphrag_evidence'), indent=2))
    
    print("\nInitial NBA:")
    print(json.dumps(result.get('initial_nba'), indent=2))
    
    print("\nFinal NBA:")
    print(json.dumps(result.get('final_nba'), indent=2))
    
    print("\nPolicy Decision:")
    print(json.dumps(result.get('policy_decision'), indent=2))

if __name__ == "__main__":
    verify()
