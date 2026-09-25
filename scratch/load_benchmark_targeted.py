"""
Targeted loader using PyTigerGraph upsertVertex — proven to work.
Loads 20 benchmark transactions + card-context transactions one-at-a-time.
"""
import os
import math
import time
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

NUMERIC_COLS = {
    # Only DOUBLE in TG schema
    'TransactionAmt',
    'C1','C2','C3','C4','C5','C6','C7','C8','C9','C10','C11','C12','C13','C14',
    'D1','D2','D3','D4','D5','D6','D7','D8','D9','D10','D11','D12','D13','D14','D15',
    'V1','V2','V3','V4','V5','V6','V7','V8','V9','V10',
    'V11','V12','V13','V14','V15','V16','V17','V18','V19','V20',
    'V21','V22','V23','V24','V25','V26','V27','V28','V29','V30',
    'id_01','id_02','id_03','id_04','id_05','id_06','id_07','id_08','id_09','id_10',
    'id_11','id_12','id_13','id_14','id_15','id_16','id_17','id_18','id_19','id_20',
    'id_21','id_22','id_23','id_24','id_25','id_26','id_27','id_28','id_29','id_30',
    'id_31','id_32','id_33','id_34','id_35','id_36','id_37','id_38',
}
# STRING cols in TG schema (dist1, dist2, addr1, addr2, card1-6, TransactionDT, M1-M9, DeviceType, DeviceInfo, etc.)
# Everything NOT in NUMERIC_COLS is treated as string.


# Columns that exist in TG schema
TG_SCHEMA_COLS = {
    'TransactionDT', 'TransactionAmt', 'ProductCD',
    'card1', 'card2', 'card3', 'card4', 'card5', 'card6',
    'addr1', 'addr2', 'dist1', 'dist2', 'P_emaildomain', 'R_emaildomain',
    'C1','C2','C3','C4','C5','C6','C7','C8','C9','C10','C11','C12','C13','C14',
    'D1','D2','D3','D4','D5','D6','D7','D8','D9','D10','D11','D12','D13','D14','D15',
    'M1','M2','M3','M4','M5','M6','M7','M8','M9',
    'DeviceType', 'DeviceInfo',
    'id_01','id_02','id_03','id_04','id_05','id_06','id_07','id_08','id_09','id_10',
    'id_11','id_12','id_13','id_14','id_15','id_16','id_17','id_18','id_19','id_20',
    'id_21','id_22','id_23','id_24','id_25','id_26','id_27','id_28','id_29','id_30',
    'id_31','id_32','id_33','id_34','id_35','id_36','id_37','id_38',
}

def safe_val(col, val):
    """Return a properly typed, JSON-safe value."""
    if col in NUMERIC_COLS:
        try:
            fv = float(val)
            return 0.0 if not math.isfinite(fv) else fv
        except (ValueError, TypeError):
            return 0.0
    else:
        if isinstance(val, float) and math.isnan(val):
            return ""
        return str(val) if val is not None else ""

def upsert_txn(row):
    vid = str(row['TransactionID'])
    attrs = {}
    for col in TG_SCHEMA_COLS:
        if col in row.index:
            attrs[col] = safe_val(col, row[col])
    try:
        conn.upsertVertex('O_Transaction', vid, attributes=attrs)
        return True
    except Exception as e:
        print(f"  TXN {vid} FAILED: {str(e)[:150]}")
        return False

def upsert_edge(from_type, from_id, e_type, to_type, to_id):
    try:
        conn.upsertEdge(from_type, str(from_id), e_type, to_type, str(to_id))
        return True
    except Exception as e:
        print(f"  Edge {e_type} {from_id}->{to_id} FAILED: {str(e)[:100]}")
        return False

print("Loading CSVs...")
cases = pd.read_csv("C:/Users/malav/Downloads/case_pack.csv")
df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
idf = pd.read_csv("C:/Users/malav/Downloads/identity.csv")
df = pd.merge(df, idf, on='TransactionID', how='left')
df['TransactionID'] = df['TransactionID'].astype(str)
df['device_id'] = df['DeviceType'].fillna('').astype(str) + "_" + df['DeviceInfo'].fillna('').astype(str)
df['region_id'] = df['addr1'].fillna('').astype(str) + "_" + df['addr2'].fillna('').astype(str)
df = df.copy()

benchmark_ids = set(cases['flagged_txn_id'].astype(str))
benchmark_df = df[df['TransactionID'].isin(benchmark_ids)].copy()
benchmark_cards = set(benchmark_df['card1'].dropna().astype(str))

# Card context: last 100 per card
context_df = df[df['card1'].astype(str).isin(benchmark_cards)].copy()
context_df = context_df.sort_values('TransactionDT', ascending=False).groupby('card1').head(100)
to_load = pd.concat([benchmark_df, context_df]).drop_duplicates(subset='TransactionID')

print(f"Total to load: {len(to_load)} ({len(benchmark_df)} benchmark + {len(to_load)-len(benchmark_df)} context)")

# === Upload transactions ===
ok = 0; failed = 0
for i, (_, row) in enumerate(to_load.iterrows()):
    if upsert_txn(row):
        ok += 1
    else:
        failed += 1
    if (i+1) % 10 == 0:
        print(f"  TXN progress: {i+1}/{len(to_load)} | {ok} ok, {failed} failed")

print(f"\nTransactions done: {ok} ok, {failed} failed")

# === Upload edges ===
print("\nUploading edges...")
ek = 0; ef = 0
for _, row in to_load.iterrows():
    tid = str(row['TransactionID'])
    card = str(row['card1']) if pd.notna(row.get('card1')) else None
    dev = row['device_id']
    email = str(row.get('P_emaildomain', '')) if pd.notna(row.get('P_emaildomain')) else None
    region = row['region_id']
    
    if card and card not in ('nan', ''):
        if upsert_edge("O_Card", card, "O_MADE", "O_Transaction", tid): ek += 1
        else: ef += 1
    if dev and dev not in ('_', 'nan_nan', ''):
        if upsert_edge("O_Transaction", tid, "O_FROM_DEVICE", "O_DeviceProfile", dev): ek += 1
        else: ef += 1
    if email and email not in ('nan', ''):
        if upsert_edge("O_Transaction", tid, "O_PURCHASER_EMAIL", "O_EmailDomain", email): ek += 1
        else: ef += 1
    if region and region not in ('_', 'nan_nan', ''):
        if upsert_edge("O_Transaction", tid, "O_BILLED_IN", "O_BillingRegion", region): ek += 1
        else: ef += 1

print(f"Edges done: {ek} ok, {ef} failed")

# === Final verification of all 20 benchmark TXNs ===
print("\n=== Verifying 20 benchmark transactions ===")
all_found = True
for _, row in cases.iterrows():
    tid = str(row['flagged_txn_id'])
    try:
        result = conn.getVerticesById('O_Transaction', [tid])
        found = len(result) > 0
        status = '✅ FOUND' if found else '❌ MISSING'
        if not found: all_found = False
        print(f"  {row['case_id']} TXN {tid}: {status}")
    except Exception as e:
        print(f"  {row['case_id']} TXN {tid}: ERROR - {e}")
        all_found = False

print(f"\n{'✅ ALL 20 BENCHMARK TRANSACTIONS VERIFIED' if all_found else '❌ SOME TRANSACTIONS MISSING'}")
print("Targeted load complete!")
