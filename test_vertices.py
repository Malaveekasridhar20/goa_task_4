import os
from dotenv import load_dotenv
import pyTigerGraph as tg

load_dotenv()

host = os.environ.get("TG_HOST")
graph = os.environ.get("TG_GRAPHNAME")
secret = os.environ.get("TG_SECRET")

try:
    conn = tg.TigerGraphConnection(host=host, graphname=graph)
    conn.apiToken = conn.getToken(secret)
    res = conn.getVertices("Payment_Transaction", limit=2)
    print("Found Vertices:", [v.get("v_id") for v in res])
except Exception as e:
    print("Error:", e)
