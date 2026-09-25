import os
import pyTigerGraph as tg
from dotenv import load_dotenv

load_dotenv()
conn = tg.TigerGraphConnection(
    host=os.environ.get('TG_HOST'),
    graphname='HHGOA_Fraud_Official',
    gsqlSecret=os.environ.get('TG_SECRET')
)
conn.apiToken = conn.getToken(os.environ.get('TG_SECRET'))[0]

schema = conn.getSchema(force=True)
print("Vertex Counts:")
for v in schema["VertexTypes"]:
    v_type = v["Name"]
    count = conn.getVertexCount(v_type)
    print(f"{v_type}: {count}")

print("\nEdge Counts:")
for e in schema["EdgeTypes"]:
    e_type = e["Name"]
    count = conn.getEdgeCount(e_type)
    print(f"{e_type}: {count}")
