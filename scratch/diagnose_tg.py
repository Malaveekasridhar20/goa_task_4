import os
import sys
import httpx
import json
import asyncio
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

TG_HOST = os.environ.get("TG_HOST")
TG_GRAPHNAME = os.environ.get("TG_GRAPHNAME")
TG_SECRET = os.environ.get("TG_SECRET")

def get_token():
    url = f"{TG_HOST}/restpp/requesttoken"
    resp = httpx.get(url, params={"secret": TG_SECRET, "graph": TG_GRAPHNAME})
    if resp.status_code == 200:
        res = resp.json()
        if not res.get("error"):
            return res.get("token")
    return None

def test_restpp():
    print("=== 1. RESTPP health (/restpp/echo) ===")
    try:
        resp = httpx.get(f"{TG_HOST}/restpp/echo", verify=False)
        print(f"HTTP Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

    token = get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    print("\n=== 2. Exact transaction (Transaction_Fraud) ===")
    url2 = f"{TG_HOST}/restpp/graph/Transaction_Fraud/vertices/Payment_Transaction/5298"
    try:
        resp2 = httpx.get(url2, headers=headers, verify=False)
        print(f"HTTP Status: {resp2.status_code}")
        print(f"Body: {resp2.text}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== 3. Exact transaction (from .env TG_GRAPHNAME) ===")
    url3 = f"{TG_HOST}/restpp/graph/{TG_GRAPHNAME}/vertices/Payment_Transaction/5298"
    try:
        resp3 = httpx.get(url3, headers=headers, verify=False)
        print(f"HTTP Status: {resp3.status_code}")
        print(f"Body: {resp3.text}")
    except Exception as e:
        print(f"Error: {e}")

async def test_mcp():
    from agent.graph_agent import InvestigationAgent
    agent = InvestigationAgent(evaluation_mode="DEMO_INTEGRATION")
    
    print("\n=== 4. Interpreted GSQL (tigergraph__run_query) ===")
    query = '''INTERPRET QUERY () FOR GRAPH Transaction_Fraud {
  Start = {Payment_Transaction.*};
  Txn = SELECT t FROM Start:t WHERE t.id == "5298";
  PRINT Txn;
}'''
    try:
        status, res = agent._call_mcp_query("tigergraph__run_query", {"query_text": query})
        print(f"Status: {status}")
        print(f"Result: {res[:500]}...")
    except Exception as e:
        print(f"Error: {e}")
        
    print("\n=== 5. Installed Query (tigergraph__run_installed_query) ===")
    try:
        # We don't know the exact installed query name, maybe get_transaction_context?
        status, res = agent._call_mcp_query("tigergraph__run_installed_query", {
            "query_name": "get_transaction_context",
            "params": {"p_txn_id": "5298"}
        })
        print(f"Status: {status}")
        print(f"Result: {res[:500]}...")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== 6. Get Node (tigergraph__get_node) ===")
    try:
        status, res = agent._call_mcp_query("tigergraph__get_node", {
            "vertex_type": "Payment_Transaction",
            "vertex_id": "5298"
        })
        print(f"Status: {status}")
        print(f"Result: {res[:500]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_restpp()
    asyncio.run(test_mcp())
