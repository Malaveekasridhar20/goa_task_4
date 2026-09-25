import os
import requests
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
REST_URL = f"{os.environ.get('TG_HOST', 'http://127.0.0.1')}:9000/graph/HHGOA_Fraud_Official"
if not REST_URL.startswith("http"):
    REST_URL = "https://" + REST_URL
HEADERS = {"Authorization": f"Bearer {os.environ.get('TG_SECRET')}"}

print("Loading CSVs...")
df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
idf = pd.read_csv("C:/Users/malav/Downloads/identity.csv")
df = pd.merge(df, idf, on='TransactionID', how='left')

df['TransactionID'] = df['TransactionID'].astype(str)
df['device_id'] = (df['DeviceType'].fillna('').astype(str) + "_" + 
                   df['DeviceInfo'].fillna('').astype(str))
df['region_id'] = (df['addr1'].fillna('').astype(str) + "_" + 
                   df['addr2'].fillna('').astype(str))

def rest_upsert_edge(data, e_type, from_type, from_id_col, to_type, to_id_col, chunk_size=5000):
    if len(data) == 0: return
    data = data.copy()
    data[from_id_col] = data[from_id_col].astype(str)
    data[to_id_col] = data[to_id_col].astype(str)
    data = data[(data[from_id_col] != 'nan') & (data[to_id_col] != 'nan') & 
                (data[from_id_col] != '') & (data[to_id_col] != '')]
    
    total = len(data)
    print(f"Upserting {total} edges to {e_type} via REST...")
    
    for i in range(0, total, chunk_size):
        chunk = data.iloc[i:i+chunk_size]
        
        # Build REST payload
        edges = {}
        for _, row in chunk.iterrows():
            fid = row[from_id_col]
            tid = row[to_id_col]
            
            if fid not in edges:
                edges[fid] = {e_type: {to_type: {}}}
            
            edges[fid][e_type][to_type][tid] = {}

        payload = {"edges": {from_type: edges}}
        
        try:
            r = requests.post(REST_URL, headers=HEADERS, json=payload, timeout=30)
            if r.status_code == 200:
                print(f"  ...chunk {i}-{i+len(chunk)} OK")
            else:
                print(f"  Failed chunk {i}: {r.status_code} {r.text[:100]}")
        except Exception as e:
            print(f"  Failed chunk {i} with exception: {e}")

print("Upserting Edges via REST...")
owns = df[['card1']].copy()
owns['customer_id'] = owns['card1']
rest_upsert_edge(owns, "O_OWNS", "O_Customer", "customer_id", "O_Card", "card1")

made = df[['TransactionID', 'card1']].copy()
rest_upsert_edge(made, "O_MADE", "O_Card", "card1", "O_Transaction", "TransactionID")

from_dev = df[['TransactionID', 'device_id']].copy()
from_dev = from_dev[(from_dev['device_id'] != '_') & (from_dev['device_id'] != 'nan_nan')]
rest_upsert_edge(from_dev, "O_FROM_DEVICE", "O_Transaction", "TransactionID", "O_DeviceProfile", "device_id")

from_email = df[['TransactionID', 'P_emaildomain']].copy()
rest_upsert_edge(from_email, "O_PURCHASER_EMAIL", "O_Transaction", "TransactionID", "O_EmailDomain", "P_emaildomain")

billed = df[['TransactionID', 'region_id']].copy()
billed = billed[(billed['region_id'] != '_') & (billed['region_id'] != 'nan_nan')]
rest_upsert_edge(billed, "O_BILLED_IN", "O_Transaction", "TransactionID", "O_BillingRegion", "region_id")

cases2 = pd.read_csv("C:/Users/malav/Downloads/closed_cases_history.csv")
involved = pd.DataFrame({
    'from_id': cases2['first_fraud_txn_id'].astype(str),
    'to_id': cases2['case_id'].astype(str)
}).dropna()
rest_upsert_edge(involved, "O_INVOLVED_IN", "O_Transaction", "from_id", "O_ClosedCase", "to_id")

print("Full dataset REST edge load complete!")
