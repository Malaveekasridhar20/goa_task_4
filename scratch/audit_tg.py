import os
import requests
from dotenv import load_dotenv

load_dotenv()
host = os.environ.get("TG_HOST")
secret = os.environ.get("TG_SECRET")
graph = "HHGOA_Fraud_Official"

if not host.startswith("http"):
    host = "https://" + host

headers = {"Authorization": f"Bearer {secret}"}
url = f"{host}:9000/query/{graph}"

def run_query(query_name, params=None):
    if params is None:
        params = {}
    r = requests.get(f"{url}/{query_name}", headers=headers, params=params)
    return r.json()

print("--- DATASET COUNTS ---")
for vtype in ["O_Transaction", "O_Customer", "O_Card", "O_DeviceProfile", "O_EmailDomain", "O_BillingRegion", "O_ClosedCase"]:
    r = requests.get(f"{host}:9000/graph/{graph}/vertices/{vtype}?count_only=true", headers=headers)
    print(vtype, r.json())
    
print("\n--- EDGES FOR TXN 3514030 ---")
r = requests.get(f"{host}:9000/graph/{graph}/edges/O_Transaction/3514030", headers=headers)
print(r.json())
