import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
host = os.environ.get("TG_HOST")
secret = os.environ.get("TG_SECRET")
graph = "HHGOA_Fraud_Official"

if not host.startswith("http"):
    host = "https://" + host

headers = {"Authorization": f"Bearer {secret}"}

print("--- NODE COUNTS ---")
for vtype in ["O_Transaction", "O_Customer", "O_Card", "O_DeviceProfile", "O_EmailDomain", "O_BillingRegion", "O_ClosedCase"]:
    r = requests.get(f"{host}:9000/graph/{graph}/vertices/{vtype}?count_only=true", headers=headers)
    print(vtype, r.json())
    
print("\n--- EDGE COUNTS (Checking one example edge type) ---")
# Check edge count for O_OWNS
r = requests.get(f"{host}:9000/graph/{graph}/edges/O_Customer/?count_only=true", headers=headers)
print("O_Customer Edges:", r.json())
