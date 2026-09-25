import os
import json
import time
import requests
import pandas as pd
import pyTigerGraph as tg
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings()

load_dotenv()
host = os.environ.get("TG_HOST").rstrip("/")
secret = os.environ.get("TG_SECRET")
graph = "HHGOA_Fraud_Official"

# Use pyTigerGraph to get a valid token (handles Savanna auth correctly)
conn = tg.TigerGraphConnection(host=host, graphname=graph, gsqlSecret=secret)
token = conn.getToken(secret)[0]
print(f"Token acquired: {token[:20]}...")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
url = f"{host}/restpp/graph/{graph}"

print("Loading transaction IDs...")
df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv", usecols=["TransactionID"])
cases = pd.read_csv("C:/Users/malav/Downloads/closed_cases_history.csv")
case_ids = cases["first_fraud_txn_id"].dropna().astype(str).tolist()
all_ids = [str(x) for x in df["TransactionID"].tolist()] + case_ids

# Deduplicate
all_ids = list(dict.fromkeys(all_ids))
print(f"Total unique IDs to restore: {len(all_ids)}")

BATCH = 100
ok = 0
failed = 0

for i in range(0, len(all_ids), BATCH):
    batch = all_ids[i:i+BATCH]
    payload = {"vertices": {"O_Transaction": {vid: {} for vid in batch}}}
    for attempt in range(3):
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=30)
            if r.status_code == 200:
                ok += len(batch)
                if (i // BATCH) % 100 == 0:
                    print(f"  ...{i+len(batch)}/{len(all_ids)} OK")
                break
            else:
                print(f"  Chunk {i} attempt {attempt+1}: {r.status_code} {r.text[:120]}")
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  Chunk {i} attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    else:
        failed += len(batch)

print(f"\nDone! {ok} inserted, {failed} failed.")
