import os
import sys
import httpx
import json
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

TG_HOST = os.environ.get("TG_HOST")

def verify_health():
    print("=== 1. RESTPP health (/restpp/echo) ===")
    try:
        resp = httpx.get(f"{TG_HOST}/restpp/echo", verify=False)
        print(f"HTTP Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== 2. Card Transaction Velocity Algorithm ===")
    from agent.graph_agent import InvestigationAgent
    from agent.investigation_tools import GraphInvestigationTools
    
    # Initialize the agent and tools
    agent = InvestigationAgent(evaluation_mode="DEMO_INTEGRATION")
    investigator = GraphInvestigationTools(agent._call_mcp_query)
    
    # Run the exact algorithm query for transaction 5298
    print("Testing get_graph_algorithms_context('5298')...")
    algo_ev = investigator.get_graph_algorithms_context("5298")
    
    print("\nResulting Evidence Object:")
    print(json.dumps(algo_ev, indent=2))

if __name__ == "__main__":
    verify_health()
