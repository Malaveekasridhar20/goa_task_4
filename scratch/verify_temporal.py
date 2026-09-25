import os
import pyTigerGraph as tg
from dotenv import load_dotenv

load_dotenv()
host = os.environ.get("TG_HOST")
secret = os.environ.get("TG_SECRET")
graph = "HHGOA_Fraud_Official"

conn = tg.TigerGraphConnection(host=host, graphname=graph, gsqlSecret=secret)
conn.apiToken = conn.getToken(secret)[0]

def get_edges(vtype, vid):
    try:
        edges = conn.getEdges(vtype, vid)
        return {"results": edges}
    except Exception as e:
        print(f"Error getting edges for {vtype} {vid}: {e}")
        return {"results": []}

print("--- Temporal Validation for HHG-001 (Txn: 3514030) ---")

edges = get_edges("O_Transaction", "3514030")
edges_list = edges.get("results", [])
print(f"Edges for 3514030: {len(edges_list)}")

card_id = None
device_id = None
for e in edges_list:
    if e.get("e_type") == "O_MADE_REVERSE":
        card_id = e.get("to_id")
    if e.get("e_type") == "O_FROM_DEVICE":
        device_id = e.get("to_id")

print(f"Card ID: {card_id}")
print(f"Device ID: {device_id}")

if card_id:
    card_edges = get_edges("O_Card", card_id)
    txns = [e for e in card_edges.get("results", []) if e.get("e_type") == "O_MADE"]
    print(f"Total historical transactions on card {card_id}: {len(txns)}")

if device_id:
    device_edges = get_edges("O_DeviceProfile", device_id)
    txns = [e for e in device_edges.get("results", []) if e.get("e_type") == "O_FROM_DEVICE_REVERSE"]
    print(f"Total historical transactions from device {device_id}: {len(txns)}")
