import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from agent.graph_agent import InvestigationAgent
agent = InvestigationAgent(evaluation_mode="DEMO_INTEGRATION")

status, res = agent._call_mcp_query("tigergraph__get_node", {
    "vertex_type": "Transaction",
    "vertex_id": "5298"
})

print(f"Status: {status}")
print(f"Result: {res}")
