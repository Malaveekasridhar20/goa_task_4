import os
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

print("Loading transactions...")
df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
idf = pd.read_csv("C:/Users/malav/Downloads/identity.csv")
cases = pd.read_csv("C:/Users/malav/Downloads/closed_cases_history.csv")

df = pd.merge(df, idf, on='TransactionID', how='left')
df['TransactionID'] = df['TransactionID'].astype(str)

def to_numeric(series):
    return pd.to_numeric(series, errors='coerce').fillna(0.0)

STRING_COLS = {'DeviceType', 'DeviceInfo', 'ProductCD', 'card4', 'card6',
               'P_emaildomain', 'R_emaildomain', 'M1', 'M2', 'M3', 'M4',
               'M5', 'M6', 'M7', 'M8', 'M9'}

for c in df.columns:
    if c in STRING_COLS:
        df[c] = df[c].fillna('').astype(str)
    elif c in ['TransactionAmt', 'risk_score'] or c.startswith('C') or c.startswith('D') or c.startswith('V') or c.startswith('id_'):
        df[c] = to_numeric(df[c])
    else:
        df[c] = df[c].fillna('').astype(str)

schema = conn.getSchema(force=True)
v_type = [v for v in schema['VertexTypes'] if v['Name'] == 'O_Transaction'][0]
allowed_attrs = [a['AttributeName'] for a in v_type['Attributes']]
valid_txn_attrs = {k: k for k in df.columns if k in allowed_attrs}

print(f"Upserting {len(df)} transactions in chunks...")
chunk_size = 1000
for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i+chunk_size]
    try:
        conn.upsertVertexDataFrame(chunk, "O_Transaction", v_id="TransactionID", attributes=valid_txn_attrs)
        print(f"  ...chunk {i}-{i+len(chunk)} OK")
    except Exception as e:
        print(f"  Failed chunk {i}: {e}")

print("Upserting historical case transactions (just the IDs to re-establish them)...")
cases_txns = pd.DataFrame({'TransactionID': cases['first_fraud_txn_id'].dropna().astype(str)})
try:
    conn.upsertVertexDataFrame(cases_txns, "O_Transaction", v_id="TransactionID", attributes={})
    print("  ...historical transactions OK")
except Exception as e:
    print(f"  Failed historical txns: {e}")

print("Restoration complete.")
