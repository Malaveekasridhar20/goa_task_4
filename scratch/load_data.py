import os
import sys
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
try:
    import pyTigerGraph as tg
except ImportError:
    print("pyTigerGraph not installed")
    sys.exit(1)

host = os.environ.get("TG_HOST")
graph = "HHGOA_Fraud_Official"
user = os.environ.get("TG_USERNAME", "tigergraph")
pw = os.environ.get("TG_PASSWORD", "tigergraph")
secret = os.environ.get("TG_SECRET")

try:
    if secret:
        conn = tg.TigerGraphConnection(host=host, graphname=graph, gsqlSecret=secret)
        conn.apiToken = conn.getToken(secret)[0]
    else:
        conn = tg.TigerGraphConnection(host=host, graphname=graph, username=user, password=pw)
        conn.apiToken = conn.getToken(conn.createSecret())
except Exception as e:
    print(f"Error connecting: {e}")
    sys.exit(1)

base_path = "C:/Users/malav/Downloads"
print("Loading CSVs into Pandas...")
txns = pd.read_csv(f"{base_path}/transactions.csv")
# To speed up and reduce memory, we will only take a subset of columns if needed, but we promised to load all mapped ones.
# Actually pyTigerGraph's upsertVertexDataFrame is very fast.

ident = pd.read_csv(f"{base_path}/identity.csv")
cases = pd.read_csv(f"{base_path}/closed_cases_history.csv")

# Clean NA values
txns = txns.fillna('')
ident = ident.fillna('')
cases = cases.fillna('')

# We need to explicitly cast columns that the schema expects as DOUBLE or STRING
def to_numeric(series):
    return pd.to_numeric(series, errors='coerce').fillna(0.0)

for c in txns.columns:
    if c in ['TransactionAmt', 'risk_score'] or c.startswith('C') or c.startswith('D') or c.startswith('V') or c.startswith('id_'):
        txns[c] = to_numeric(txns[c])
    else:
        txns[c] = txns[c].astype(str)

for c in ident.columns:
    if c in ['TransactionAmt', 'risk_score'] or c.startswith('C') or c.startswith('D') or c.startswith('V') or c.startswith('id_'):
        ident[c] = to_numeric(ident[c])
    else:
        ident[c] = ident[c].astype(str)
        
for c in cases.columns:
    cases[c] = cases[c].astype(str)

print("Merging identities into transactions...")
df = pd.merge(txns, ident, on="TransactionID", how="left")
df = df.fillna('')
# After merge, the identity numeric columns that were NaN become empty string if not careful.
# Let's ensure numeric columns are properly typed in the merged dataframe too.
for c in df.columns:
    if c in ['TransactionAmt', 'risk_score'] or c.startswith('C') or c.startswith('D') or c.startswith('V') or c.startswith('id_'):
        df[c] = to_numeric(df[c])
    else:
        df[c] = df[c].astype(str)

df['TransactionID'] = df['TransactionID'].astype(str)

print("Preparing O_Customer...")
customers = pd.DataFrame({'id': df['customer_id'].unique()})
customers = customers[customers['id'] != '']

print("Preparing O_Card...")
cards = df[['card1', 'card2', 'card3', 'card4', 'card5', 'card6']].drop_duplicates().copy()
for c in ['card1', 'card2', 'card3', 'card4', 'card5', 'card6']:
    cards[c] = cards[c].astype(str)
cards['id'] = cards['card1'].astype(str)
cards = cards[cards['id'] != '']

print("Preparing O_DeviceProfile...")
devices = df[['DeviceType', 'DeviceInfo']].drop_duplicates().copy()
devices['DeviceType'] = devices['DeviceType'].astype(str)
devices['DeviceInfo'] = devices['DeviceInfo'].astype(str)
devices['id'] = devices['DeviceType'].astype(str) + "_" + devices['DeviceInfo'].astype(str)
devices = devices[devices['id'] != '_']
df['device_id'] = df['DeviceType'].astype(str) + "_" + df['DeviceInfo'].astype(str)

print("Preparing O_EmailDomain...")
emails_p = df[['P_emaildomain']].rename(columns={'P_emaildomain': 'id'})
emails_r = df[['R_emaildomain']].rename(columns={'R_emaildomain': 'id'})
emails = pd.concat([emails_p, emails_r]).drop_duplicates()
emails = emails[emails['id'] != '']

print("Preparing O_BillingRegion...")
regions = df[['addr1', 'addr2']].drop_duplicates().copy()
regions['addr1'] = regions['addr1'].astype(str)
regions['addr2'] = regions['addr2'].astype(str)
regions['id'] = regions['addr1'] + "_" + regions['addr2']
regions = regions[regions['id'] != '_']
df['region_id'] = df['addr1'].astype(str) + "_" + df['addr2'].astype(str)

# Fix fragmentation
df = df.copy()

def batch_upsert(conn, data, vertex_type, v_id, attrs={}, batch_size=500):
    for i in range(0, len(data), batch_size):
        batch = data.iloc[i:i+batch_size]
        for attempt in range(3):
            try:
                conn.upsertVertexDataFrame(batch, vertex_type, v_id=v_id, attributes=attrs)
                print(f"  ... {min(i+batch_size, len(data))} / {len(data)}", flush=True)
                break
            except Exception as e:
                print(f"Retry {attempt+1}/3 failed for {vertex_type} batch {i}: {e}", flush=True)
                import time
                time.sleep(2)

print("Upserting Vertices...", flush=True)

print(f"Upserting {len(customers)} Customers...", flush=True)
batch_upsert(conn, customers, "O_Customer", "id", {})

print(f"Upserting {len(cards)} Cards...", flush=True)
batch_upsert(conn, cards, "O_Card", "id", {"card1":"card1", "card2":"card2", "card3":"card3", "card4":"card4", "card5":"card5", "card6":"card6"})

print(f"Upserting {len(devices)} Devices...", flush=True)
batch_upsert(conn, devices, "O_DeviceProfile", "id", {"DeviceType":"DeviceType", "DeviceInfo":"DeviceInfo"})

print(f"Upserting {len(emails)} Emails...", flush=True)
batch_upsert(conn, emails, "O_EmailDomain", "id", {})

print(f"Upserting {len(regions)} Regions...", flush=True)
batch_upsert(conn, regions, "O_BillingRegion", "id", {"addr1":"addr1", "addr2":"addr2"})

print(f"Upserting {len(cases)} Closed Cases...", flush=True)
case_attrs = {c: c for c in cases.columns if c != 'case_id'}
batch_upsert(conn, cases, "O_ClosedCase", "case_id", case_attrs)

print(f"Upserting {len(df)} Transactions...", flush=True)
schema = conn.getSchema(force=True)
v_type = [v for v in schema['VertexTypes'] if v['Name'] == 'O_Transaction'][0]
allowed_attrs = [a['AttributeName'] for a in v_type['Attributes']]
valid_txn_attrs = {k: k for k in df.columns if k in allowed_attrs}

batch_upsert(conn, df, "O_Transaction", "TransactionID", valid_txn_attrs)

print("Preparing Edges...", flush=True)
# OWNS (Customer -> Card)
owns = df[['customer_id', 'card1']].drop_duplicates().rename(columns={'customer_id': 'from_id', 'card1': 'to_id'})
owns = owns[(owns['from_id'] != '') & (owns['to_id'] != '')]
conn.upsertEdgeDataFrame(owns, "O_Customer", "O_OWNS", "O_Card", from_id="from_id", to_id="to_id", attributes={})

# MADE (Card -> Transaction)
made = df[['card1', 'TransactionID']].rename(columns={'card1': 'from_id', 'TransactionID': 'to_id'})
made = made[(made['from_id'] != '') & (made['to_id'] != '')]
conn.upsertEdgeDataFrame(made, "O_Card", "O_MADE", "O_Transaction", from_id="from_id", to_id="to_id", attributes={})

# FROM_DEVICE (Transaction -> Device)
from_device = df[['TransactionID', 'device_id']].rename(columns={'TransactionID': 'from_id', 'device_id': 'to_id'})
from_device = from_device[(from_device['from_id'] != '') & (from_device['to_id'] != '_')]
conn.upsertEdgeDataFrame(from_device, "O_Transaction", "O_FROM_DEVICE", "O_DeviceProfile", from_id="from_id", to_id="to_id", attributes={})

# PURCHASER_EMAIL (Transaction -> Email)
from_p_email = df[['TransactionID', 'P_emaildomain']].rename(columns={'TransactionID': 'from_id', 'P_emaildomain': 'to_id'})
from_p_email = from_p_email[(from_p_email['from_id'] != '') & (from_p_email['to_id'] != '')]
conn.upsertEdgeDataFrame(from_p_email, "O_Transaction", "O_PURCHASER_EMAIL", "O_EmailDomain", from_id="from_id", to_id="to_id", attributes={})

# BILLED_IN (Transaction -> Region)
from_region = df[['TransactionID', 'region_id']].rename(columns={'TransactionID': 'from_id', 'region_id': 'to_id'})
from_region = from_region[(from_region['from_id'] != '') & (from_region['to_id'] != '_')]
conn.upsertEdgeDataFrame(from_region, "O_Transaction", "O_BILLED_IN", "O_BillingRegion", from_id="from_id", to_id="to_id", attributes={})

# NEXT (Transaction -> Transaction)
# Sort by customer, then time. 
print("Linking NEXT transactions...")
df_sorted = df.sort_values(['customer_id', 'TransactionDT'])
df_sorted['next_txn'] = df_sorted.groupby('customer_id')['TransactionID'].shift(-1)
next_txns = df_sorted[['TransactionID', 'next_txn']].dropna().rename(columns={'TransactionID': 'from_id', 'next_txn': 'to_id'})
next_txns['to_id'] = next_txns['to_id'].astype(str).str.split('.').str[0]
conn.upsertEdgeDataFrame(next_txns, "O_Transaction", "O_NEXT", "O_Transaction", from_id="from_id", to_id="to_id", attributes={})

# INVOLVES (ClosedCase -> Transaction)
print("Linking cases...")
case_inv = []
for idx, row in cases.iterrows():
    case_id = row['case_id']
    txn_ids = str(row['txn_ids']).split('|')
    for tid in txn_ids:
        tid = tid.strip()
        if tid:
            case_inv.append({'from_id': case_id, 'to_id': tid})
case_inv_df = pd.DataFrame(case_inv)
if len(case_inv_df) > 0:
    conn.upsertEdgeDataFrame(case_inv_df, "O_ClosedCase", "O_INVOLVES", "O_Transaction", from_id="from_id", to_id="to_id", attributes={})

print("Data load complete!")
