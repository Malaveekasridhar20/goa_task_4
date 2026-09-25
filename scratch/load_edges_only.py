import os
import time
import requests
import json
import pandas as pd
from dotenv import load_dotenv
import pyTigerGraph as tg

load_dotenv()
conn = tg.TigerGraphConnection(
    host=os.environ.get('TG_HOST'),
    graphname='HHGOA_Fraud_Official',
    gsqlSecret=os.environ.get('TG_SECRET')
)
conn.apiToken = conn.getToken(os.environ.get('TG_SECRET'))[0]

print("Loading CSVs...")
df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
idf = pd.read_csv("C:/Users/malav/Downloads/identity.csv")

print("Merging relationships...")
df = pd.merge(df, idf, on='TransactionID', how='left')

df['TransactionID'] = df['TransactionID'].astype(str)
df['device_id'] = (df['DeviceType'].fillna('').astype(str) + "_" + 
                   df['DeviceInfo'].fillna('').astype(str))
df['region_id'] = (df['addr1'].fillna('').astype(str) + "_" + 
                   df['addr2'].fillna('').astype(str))
df = df.copy()

def chunked_upsert_edge(data, e_type, from_type, from_id, to_type, to_id, chunk_size=10000):
    if len(data) == 0: return
    data = data.copy()
    data[from_id] = data[from_id].astype(str)
    data[to_id] = data[to_id].astype(str)
    data = data[(data[from_id] != 'nan') & (data[to_id] != 'nan') & 
                (data[from_id] != '') & (data[to_id] != '')]
                
    # CRITICAL FIX: Only keep the two ID columns so pyTigerGraph doesn't interpret other columns as attributes!
    data = data[[from_id, to_id]]
    
    if len(data) == 0: return
    print(f"Upserting {len(data)} to {e_type} in chunks...")
    for i in range(0, len(data), chunk_size):
        chunk = data.iloc[i:i+chunk_size]
        try:
            conn.upsertEdgeDataFrame(chunk, from_type, e_type, to_type, from_id=from_id, to_id=to_id, attributes={})
            print(f"  ...edge chunk {i}-{i+len(chunk)} OK")
        except Exception as e:
            print(f"  Failed edge chunk {i} for {e_type}: {e}")

print("Upserting Edges...")
owns = df[['card1']].copy()
owns['customer_id'] = owns['card1']
chunked_upsert_edge(owns, "O_OWNS", "O_Customer", "customer_id", "O_Card", "card1")

made = df[['TransactionID', 'card1']].copy()
chunked_upsert_edge(made, "O_MADE", "O_Card", "card1", "O_Transaction", "TransactionID")

from_dev = df[['TransactionID', 'device_id']].copy()
from_dev = from_dev[(from_dev['device_id'] != '_') & (from_dev['device_id'] != 'nan_nan')]
chunked_upsert_edge(from_dev, "O_FROM_DEVICE", "O_Transaction", "TransactionID", "O_DeviceProfile", "device_id")

from_email = df[['TransactionID', 'P_emaildomain']].copy()
chunked_upsert_edge(from_email, "O_PURCHASER_EMAIL", "O_Transaction", "TransactionID", "O_EmailDomain", "P_emaildomain")

billed = df[['TransactionID', 'region_id']].copy()
billed = billed[(billed['region_id'] != '_') & (billed['region_id'] != 'nan_nan')]
chunked_upsert_edge(billed, "O_BILLED_IN", "O_Transaction", "TransactionID", "O_BillingRegion", "region_id")

cases2 = pd.read_csv("C:/Users/malav/Downloads/closed_cases_history.csv")
involved = pd.DataFrame({
    'from_id': cases2['first_fraud_txn_id'].astype(str),
    'to_id': cases2['case_id'].astype(str)
}).dropna()
chunked_upsert_edge(involved, "O_INVOLVED_IN", "O_Transaction", "from_id", "O_ClosedCase", "to_id")

print("Full dataset edge load complete!")
