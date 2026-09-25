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

# Use raw REST for transactions (too wide for PyTigerGraph upsertVertexDataFrame)
REST_URL = conn.restppUrl + '/graph/HHGOA_Fraud_Official'
HEADERS = {'Authorization': f'Bearer {conn.apiToken}', 'Content-Type': 'application/json'}

print("Loading CSVs...")
df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
idf = pd.read_csv("C:/Users/malav/Downloads/identity.csv")
cases = pd.read_csv("C:/Users/malav/Downloads/closed_cases_history.csv")

print("Merging relationships...")
df = pd.merge(df, idf, on='TransactionID', how='left')

df['TransactionID'] = df['TransactionID'].astype(str)
df['device_id'] = (df['DeviceType'].fillna('').astype(str) + "_" + 
                   df['DeviceInfo'].fillna('').astype(str))
df['region_id'] = (df['addr1'].fillna('').astype(str) + "_" + 
                   df['addr2'].fillna('').astype(str))
df = df.copy()

print(f"Full dataset size: {len(df)} transactions.")

# === Simple vertex helpers via PyTigerGraph ===
def chunked_upsert_vertex(data, v_type, v_id_col, chunk_size=10000):
    if len(data) == 0: return
    data = data.copy()
    for col in data.columns:
        data[col] = data[col].fillna('').astype(str)
    print(f"Upserting {len(data)} to {v_type} in chunks...")
    for i in range(0, len(data), chunk_size):
        chunk = data.iloc[i:i+chunk_size]
        try:
            conn.upsertVertexDataFrame(chunk, v_type, v_id=v_id_col)
            print(f"  ...chunk {i}-{i+len(chunk)} OK")
        except Exception as e:
            print(f"  Failed chunk {i} for {v_type}: {e}")

def chunked_upsert_edge(data, e_type, from_type, from_id, to_type, to_id, chunk_size=10000):
    if len(data) == 0: return
    data = data.copy()
    data[from_id] = data[from_id].astype(str)
    data[to_id] = data[to_id].astype(str)
    data = data[(data[from_id] != 'nan') & (data[to_id] != 'nan') & 
                (data[from_id] != '') & (data[to_id] != '')]
    if len(data) == 0: return
    print(f"Upserting {len(data)} to {e_type} in chunks...")
    for i in range(0, len(data), chunk_size):
        chunk = data.iloc[i:i+chunk_size]
        try:
            conn.upsertEdgeDataFrame(chunk, from_type, e_type, to_type, from_id=from_id, to_id=to_id)
            print(f"  ...edge chunk {i}-{i+len(chunk)} OK")
        except Exception as e:
            print(f"  Failed edge chunk {i} for {e_type}: {e}")

# === Raw REST upsert for wide transaction vertices ===
# TG schema O_Transaction has ~400 attrs, but transactions.csv only has ~40 cols.
# We only send columns that exist in the schema and the CSV.
SCHEMA_TXN_ATTRS = [
    "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6",
    "addr1", "addr2", "dist1", "dist2", "P_emaildomain", "R_emaildomain",
    "C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12","C13","C14",
    "D1","D2","D3","D4","D5","D6","D7","D8","D9","D10","D11","D12","D13","D14","D15",
    "M1","M2","M3","M4","M5","M6","M7","M8","M9",
    "DeviceType", "DeviceInfo"
]
# Also include identity cols that exist
IDENTITY_COLS = [c for c in idf.columns if c != 'TransactionID']

TXN_COLS_TO_SEND = ['TransactionID'] + [c for c in SCHEMA_TXN_ATTRS if c in df.columns] + \
                   [c for c in IDENTITY_COLS if c in df.columns and c not in SCHEMA_TXN_ATTRS]

# Numeric cols for proper typing
NUMERIC_TXN_COLS = ['TransactionAmt', 'dist1', 'dist2',
                    'C1','C2','C3','C4','C5','C6','C7','C8','C9','C10','C11','C12','C13','C14',
                    'D1','D2','D3','D4','D5','D6','D7','D8','D9','D10','D11','D12','D13','D14','D15']

def rest_upsert_transactions(chunk_size=500):
    """Upload transactions using raw REST API with small chunks to avoid SSL EOF."""
    txn_df = df[TXN_COLS_TO_SEND].copy()
    
    # Type-cast
    for col in NUMERIC_TXN_COLS:
        if col in txn_df.columns:
            txn_df[col] = pd.to_numeric(txn_df[col], errors='coerce').fillna(0.0)
    
    string_cols = [c for c in txn_df.columns if c not in NUMERIC_TXN_COLS + ['TransactionID']]
    for col in string_cols:
        txn_df[col] = txn_df[col].fillna('').astype(str)
    
    total = len(txn_df)
    print(f"Upserting {total} O_Transaction via REST in {chunk_size}-row chunks...")
    success_count = 0
    error_count = 0
    
    for i in range(0, total, chunk_size):
        chunk = txn_df.iloc[i:i+chunk_size]
        vertices = {}
        for _, row in chunk.iterrows():
            vid = row['TransactionID']
            if not vid or vid == 'nan': continue
            attrs = {}
            for col in TXN_COLS_TO_SEND:
                if col == 'TransactionID': continue
                if col in row:
                    val = row[col]
                    if col in NUMERIC_TXN_COLS:
                        attrs[col] = {"value": float(val)}
                    else:
                        attrs[col] = {"value": str(val)}
            vertices[vid] = attrs
        
        if not vertices: continue
        
        payload = {"vertices": {"O_Transaction": vertices}}
        retries = 3
        for attempt in range(retries):
            try:
                r = requests.post(REST_URL, headers=HEADERS, json=payload, timeout=30)
                if r.status_code == 200:
                    success_count += len(vertices)
                    break
                else:
                    print(f"  REST error chunk {i}: {r.status_code} {r.text[:200]}")
                    break
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    error_count += len(vertices)
                    print(f"  Failed chunk {i} after {retries} retries: {e}")
        
        if (i // chunk_size) % 100 == 0:
            print(f"  Progress: {i}/{total} ({success_count} ok, {error_count} err)")
    
    print(f"Transactions upload done: {success_count} ok, {error_count} failed")

# === Run upsets ===
customers = pd.DataFrame({"id": df["card1"].unique()}).query("id != '' and id != 'nan'")
cards = df[['card1']].drop_duplicates().copy()
cards['id'] = cards['card1']
cards = cards[['id']].query("id != '' and id != 'nan'")

devices = df[['DeviceType', 'DeviceInfo']].drop_duplicates().copy()
devices['id'] = devices['DeviceType'].fillna('').astype(str) + "_" + devices['DeviceInfo'].fillna('').astype(str)
devices = devices[['id']]
devices = devices[(devices['id'] != '_') & (devices['id'] != 'nan_nan') & (devices['id'] != '')]

emails = pd.DataFrame({"id": df["P_emaildomain"].unique()})
emails = emails[emails['id'].notna() & (emails['id'] != '') & (emails['id'] != 'nan')]

regions = pd.DataFrame({"id": df["region_id"].unique()})
regions = regions[(regions['id'] != '_') & (regions['id'] != 'nan_nan') & (regions['id'] != '')]

chunked_upsert_vertex(customers, "O_Customer", "id")
chunked_upsert_vertex(cards, "O_Card", "id")
chunked_upsert_vertex(devices, "O_DeviceProfile", "id")
chunked_upsert_vertex(emails, "O_EmailDomain", "id")
chunked_upsert_vertex(regions, "O_BillingRegion", "id")

print("Upserting Closed Cases...")
cases_slim = cases[['case_id', 'customer_id', 'card_id', 'outcome', 'pattern',
                     'first_fraud_txn_id', 'opened_at', 'closed_at']].copy()
for col in cases_slim.columns:
    cases_slim[col] = cases_slim[col].fillna('').astype(str)
try:
    conn.upsertVertexDataFrame(cases_slim, "O_ClosedCase", v_id="case_id",
                               attributes={c: c for c in cases_slim.columns if c != 'case_id'})
    print(f"  Closed Cases OK: {len(cases_slim)}")
except Exception as e:
    print(f"  Failed Closed Cases: {e}")

print("Upserting Transactions (REST, small chunks)...")
rest_upsert_transactions(chunk_size=500)

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

print("Full dataset load complete!")
