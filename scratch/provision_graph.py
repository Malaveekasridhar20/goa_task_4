import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
import pyTigerGraph as tg

host = os.environ.get("TG_HOST")
user = os.environ.get("TG_USERNAME", "tigergraph")
pw = os.environ.get("TG_PASSWORD", "tigergraph")
secret = os.environ.get("TG_SECRET")

# Use a default graphname to connect if secret doesn't require a specific graph, 
# or use Transaction_Fraud to bootstrap the new graph.
# Since we are creating a new graph HHGOA_Fraud_Official, we can connect without a graph first, or just connect to the existing one to run GSQL.

conn = tg.TigerGraphConnection(host=host, username=user, password=pw)
# Try to get token
try:
    conn.apiToken = conn.getToken(conn.createSecret())
except Exception as e:
    print(f"Token generation issue (maybe using secret?): {e}")
    if secret:
        conn = tg.TigerGraphConnection(host=host, gsqlSecret=secret)
        conn.apiToken = conn.getToken(secret)[0]

with open("tigergraph/schema_official.gsql", "r") as f:
    gsql_script = f.read()

print("Executing GSQL schema creation... This may take a minute.")
res = conn.gsql(gsql_script)
print(res)

print("Schema provisioned successfully.")
