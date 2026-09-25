import os
import sys
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
try:
    import pyTigerGraph as tg
except ImportError:
    print("pyTigerGraph not installed")
    sys.exit(1)

host = os.environ.get("TG_HOST")
graph = "HHGOA_Fraud_Official"
user = os.environ.get("TG_USERNAME", "tigergraph")
pw = os.environ.get("TG_PASSWORD", "tigergraph")
secret = os.environ.get("TG_SECRET")

try:
    if secret:
        conn = tg.TigerGraphConnection(host=host, graphname=graph, gsqlSecret=secret)
        conn.apiToken = conn.getToken(secret)[0]
    else:
        conn = tg.TigerGraphConnection(host=host, graphname=graph, username=user, password=pw)
        conn.apiToken = conn.getToken(conn.createSecret())
except Exception as e:
    print(f"Error connecting: {e}")
    sys.exit(1)

benchmark_ids = [
    "3514030", "3478782", "3530164", "3583227", "3523199",
    "3476682", "3514948", "3558054", "3581141", "3506725",
    "3583368", "3553342", "3526826", "3478561", "3464869",
    "3534820", "3450629", "3491361", "3503878", "3509359"
]

results = []

for tx_id in benchmark_ids:
    try:
        tx_node = conn.getVertices("O_Transaction", {"id": tx_id})
        found = isinstance(tx_node, list) and len(tx_node) > 0
    except Exception as e:
        found = False
        
    if not found:
        results.append({"Case ID": tx_id, "Found": False})
        continue
    
    # Check edges
    try:
        edges = conn.getEdges("O_Transaction", tx_id)
        if isinstance(edges, dict):
            edges = [] # Handle error dict
        edge_types = [e["e_type"] for e in edges if isinstance(e, dict) and "e_type" in e]
    except Exception:
        edges = []
        edge_types = []
    
    has_card = "O_MADE_REVERSE" in edge_types
    has_device = "O_FROM_DEVICE" in edge_types
    has_region = "O_BILLED_IN" in edge_types
    has_email = "O_PURCHASER_EMAIL" in edge_types
    
    # Try 2 hops (Card -> Customer)
    card_edges = [e for e in edges if e["e_type"] == "O_MADE_REVERSE"]
    has_customer = False
    if card_edges:
        card_id = card_edges[0]["to_id"]
        c_edges = conn.getEdges("O_Card", card_id)
        if "O_OWNS_REVERSE" in [ce["e_type"] for ce in c_edges]:
            has_customer = True

    # Check closed case link
    case_edges = conn.getEdges("O_Transaction", tx_id, edgeType="O_INVOLVED_IN")
    has_case = len(case_edges) > 0
    
    results.append({
        "Transaction ID": tx_id,
        "Found": found,
        "Has Card": has_card,
        "Has Customer": has_customer,
        "Has Device": has_device,
        "Has Email": has_email,
        "Has Region": has_region,
        "Involved in Prior Case": has_case
    })

df = pd.DataFrame(results)
print(df.to_markdown())

with open("docs/official_graph_verification.md", "w") as f:
    f.write("# Official Graph Verification\n\n")
    f.write(df.to_markdown())
print("Saved to docs/official_graph_verification.md")
