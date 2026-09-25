import os
import sys
import pandas as pd
from dotenv import load_dotenv
import pyTigerGraph as tg
import time

load_dotenv()
host = os.environ.get("TG_HOST")
graph = "HHGOA_Fraud_Official"
secret = os.environ.get("TG_SECRET")

try:
    conn = tg.TigerGraphConnection(host=host, graphname=graph, gsqlSecret=secret)
    conn.apiToken = conn.getToken(secret)[0]
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

benchmark_ids = [
    "3514030", "3478782", "3530164", "3583227", "3523199",
    "3476682", "3514948", "3558054", "3581141", "3506725",
    "3583368", "3553342", "3526826", "3478561", "3464869",
    "3534820", "3450629", "3491361", "3503878", "3509359"
]

print("Loading CSVs...")
df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
idf = pd.read_csv("C:/Users/malav/Downloads/identity.csv")
cases = pd.read_csv("C:/Users/malav/Downloads/closed_cases_history.csv")

print("Filtering relationships for subset...")
df = pd.merge(df, idf, on='TransactionID', how='left')
df = df.fillna('')

def to_numeric(series):
    return pd.to_numeric(series, errors='coerce').fillna(0.0)

for c in df.columns:
    if c in ['TransactionAmt', 'risk_score'] or c.startswith('C') or c.startswith('D') or c.startswith('V') or c.startswith('id_'):
        df[c] = to_numeric(df[c])
    else:
        df[c] = df[c].astype(str)

df['TransactionID'] = df['TransactionID'].astype(str)
df['device_id'] = df['DeviceType'].astype(str) + "_" + df['DeviceInfo'].astype(str)
df['region_id'] = df['addr1'].astype(str) + "_" + df['addr2'].astype(str)

df = df[df['TransactionID'].astype(str).isin(benchmark_ids)]
print(f"Reduced dataset to {len(df)} transactions for graph context!")

df = df.copy()

customers = pd.DataFrame({"id": df["card1"].unique()})
cards = df[['card1', 'card2', 'card3', 'card4', 'card5', 'card6']].drop_duplicates().copy()
cards['id'] = cards['card1']

devices = df[['DeviceType', 'DeviceInfo']].drop_duplicates().copy()
devices['id'] = devices['DeviceType'].astype(str) + "_" + devices['DeviceInfo'].astype(str)

emails = pd.DataFrame({"id": pd.concat([df['P_emaildomain'], df['R_emaildomain']]).unique()})
emails = emails[emails['id'] != '']

regions = df[['addr1', 'addr2']].drop_duplicates().copy()
regions['id'] = regions['addr1'].astype(str) + "_" + regions['addr2'].astype(str)
regions = regions[regions['id'] != '_']

def do_upsert(data, vertex_type, v_id, attrs={}):
    if len(data) == 0: return
    print(f"Upserting {len(data)} to {vertex_type}")
    try:
        conn.upsertVertexDataFrame(data, vertex_type, v_id=v_id, attributes=attrs)
    except Exception as e:
        print(f"Failed {vertex_type}: {e}")

do_upsert(customers, "O_Customer", "id", {})
do_upsert(cards, "O_Card", "id", {"card1":"card1", "card2":"card2", "card3":"card3", "card4":"card4", "card5":"card5", "card6":"card6"})
do_upsert(devices, "O_DeviceProfile", "id", {"DeviceType":"DeviceType", "DeviceInfo":"DeviceInfo"})
do_upsert(emails, "O_EmailDomain", "id", {})
do_upsert(regions, "O_BillingRegion", "id", {"addr1":"addr1", "addr2":"addr2"})

print("Upserting Closed Cases...")
cases = cases.fillna('').astype(str)
case_attrs = {c: c for c in cases.columns if c != 'case_id'}
conn.upsertVertexDataFrame(cases, "O_ClosedCase", v_id="case_id", attributes=case_attrs)

print("Upserting Transactions...")
schema = conn.getSchema(force=True)
v_type = [v for v in schema['VertexTypes'] if v['Name'] == 'O_Transaction'][0]
allowed_attrs = [a['AttributeName'] for a in v_type['Attributes']]
valid_txn_attrs = {k: k for k in df.columns if k in allowed_attrs}

do_upsert(df, "O_Transaction", "TransactionID", valid_txn_attrs)

print("Preparing Edges...")
def do_upsert_edge(data, edge_type, from_type, from_id, to_type, to_id, attrs={}):
    if len(data) == 0: return
    print(f"Upserting {len(data)} to {edge_type}")
    try:
        conn.upsertEdgeDataFrame(data, from_type, edge_type, to_type, from_id=from_id, to_id=to_id, attributes=attrs)
    except Exception as e:
        print(f"Failed {edge_type}: {e}")

owns = df[['customer_id', 'card1']].drop_duplicates().rename(columns={'customer_id': 'from_id', 'card1': 'to_id'})
owns = owns[(owns['from_id'] != '') & (owns['to_id'] != '')]
do_upsert_edge(owns, "O_OWNS", "O_Customer", "from_id", "O_Card", "to_id")

made = df[['card1', 'TransactionID']].drop_duplicates().rename(columns={'card1': 'from_id', 'TransactionID': 'to_id'})
made = made[(made['from_id'] != '') & (made['to_id'] != '')]
do_upsert_edge(made, "O_MADE", "O_Card", "from_id", "O_Transaction", "to_id")

from_dev = df[['TransactionID', 'device_id']].drop_duplicates().rename(columns={'TransactionID': 'from_id', 'device_id': 'to_id'})
from_dev = from_dev[(from_dev['from_id'] != '') & (from_dev['to_id'] != '')]
do_upsert_edge(from_dev, "O_FROM_DEVICE", "O_Transaction", "from_id", "O_DeviceProfile", "to_id")

purchaser = df[['TransactionID', 'P_emaildomain']].drop_duplicates().rename(columns={'TransactionID': 'from_id', 'P_emaildomain': 'to_id'})
purchaser = purchaser[(purchaser['from_id'] != '') & (purchaser['to_id'] != '')]
do_upsert_edge(purchaser, "O_PURCHASER_EMAIL", "O_Transaction", "from_id", "O_EmailDomain", "to_id")

billed = df[['TransactionID', 'region_id']].drop_duplicates().rename(columns={'TransactionID': 'from_id', 'region_id': 'to_id'})
billed = billed[(billed['from_id'] != '') & (billed['to_id'] != '')]
do_upsert_edge(billed, "O_BILLED_IN", "O_Transaction", "from_id", "O_BillingRegion", "to_id")

involved = pd.DataFrame({
    'from_id': cases['first_fraud_txn_id'],
    'to_id': cases['case_id']
}).dropna()
do_upsert_edge(involved, "O_INVOLVED_IN", "O_Transaction", "from_id", "O_ClosedCase", "to_id")

print("Subset data load complete!")
