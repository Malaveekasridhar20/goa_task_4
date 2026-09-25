import pandas as pd
import os

def gen_schema():
    base_path = "C:/Users/malav/Downloads"
    transactions = pd.read_csv(f"{base_path}/transactions.csv", nrows=1)
    identity = pd.read_csv(f"{base_path}/identity.csv", nrows=1)
    closed = pd.read_csv(f"{base_path}/closed_cases_history.csv", nrows=1)
    
    txn_cols = list(transactions.columns)
    id_cols = list(identity.columns)
    case_cols = list(closed.columns)
    
    # We want to declare types. We can default most to STRING, except for obvious numeric.
    # However, to be safe with TigerGraph, treating everything as STRING or DOUBLE is easiest.
    # We will use STRING for all IDs, categories, and DOUBLE for amounts/scores.
    
    def map_type(col):
        if col in ['DeviceType', 'DeviceInfo']:
            return "STRING"
        if col in ['TransactionAmt', 'risk_score'] or col.startswith('C') or col.startswith('D') or col.startswith('V') or col.startswith('id_'):
            return "DOUBLE"
        return "STRING"
    
    txn_attrs = []
    for c in txn_cols:
        if c == 'TransactionID': continue
        t = map_type(c)
        txn_attrs.append(f"{c} {t}")
        
    id_attrs = []
    for c in id_cols:
        if c == 'TransactionID': continue
        t = map_type(c)
        id_attrs.append(f"{c} {t}")
        
    case_attrs = []
    for c in case_cols:
        if c == 'case_id': continue
        case_attrs.append(f"{c} STRING")
        
    gsql = f"""USE GLOBAL

# CREATE VERTICES
CREATE VERTEX O_Customer (PRIMARY_ID id STRING) WITH PRIMARY_ID_AS_ATTRIBUTE="true"
CREATE VERTEX O_Card (PRIMARY_ID id STRING, card1 STRING, card2 STRING, card3 STRING, card4 STRING, card5 STRING, card6 STRING) WITH PRIMARY_ID_AS_ATTRIBUTE="true"
CREATE VERTEX O_DeviceProfile (PRIMARY_ID id STRING, DeviceType STRING, DeviceInfo STRING) WITH PRIMARY_ID_AS_ATTRIBUTE="true"
CREATE VERTEX O_EmailDomain (PRIMARY_ID id STRING) WITH PRIMARY_ID_AS_ATTRIBUTE="true"
CREATE VERTEX O_BillingRegion (PRIMARY_ID id STRING, addr1 STRING, addr2 STRING) WITH PRIMARY_ID_AS_ATTRIBUTE="true"

CREATE VERTEX O_Transaction (
    PRIMARY_ID id STRING,
    {', '.join(txn_attrs)},
    {', '.join(id_attrs)}
) WITH PRIMARY_ID_AS_ATTRIBUTE="true"

CREATE VERTEX O_ClosedCase (
    PRIMARY_ID id STRING,
    {', '.join(case_attrs)}
) WITH PRIMARY_ID_AS_ATTRIBUTE="true"

# CREATE EDGES
CREATE DIRECTED EDGE O_OWNS (FROM O_Customer, TO O_Card) WITH REVERSE_EDGE="O_OWNS_REVERSE"
CREATE DIRECTED EDGE O_MADE (FROM O_Card, TO O_Transaction) WITH REVERSE_EDGE="O_MADE_REVERSE"
CREATE DIRECTED EDGE O_FROM_DEVICE (FROM O_Transaction, TO O_DeviceProfile) WITH REVERSE_EDGE="O_FROM_DEVICE_REVERSE"
CREATE DIRECTED EDGE O_PURCHASER_EMAIL (FROM O_Transaction, TO O_EmailDomain) WITH REVERSE_EDGE="O_PURCHASER_EMAIL_REVERSE"
CREATE DIRECTED EDGE O_BILLED_IN (FROM O_Transaction, TO O_BillingRegion) WITH REVERSE_EDGE="O_BILLED_IN_REVERSE"
CREATE DIRECTED EDGE O_NEXT (FROM O_Transaction, TO O_Transaction) WITH REVERSE_EDGE="O_PREVIOUS"
CREATE DIRECTED EDGE O_INVOLVES (FROM O_ClosedCase, TO O_Transaction) WITH REVERSE_EDGE="O_INVOLVED_IN"
CREATE DIRECTED EDGE O_ON_CARD (FROM O_ClosedCase, TO O_Card) WITH REVERSE_EDGE="O_CASE_ON_CARD"
CREATE DIRECTED EDGE O_CONNECTED_TO (FROM O_ClosedCase, TO O_Card) WITH REVERSE_EDGE="O_CASE_CONNECTED_TO"

# CREATE GRAPH
CREATE GRAPH HHGOA_Fraud_Official (*)
"""
    
    os.makedirs("tigergraph", exist_ok=True)
    with open("tigergraph/schema_official.gsql", "w") as f:
        f.write(gsql)
    print("Generated tigergraph/schema_official.gsql")

if __name__ == "__main__":
    gen_schema()
