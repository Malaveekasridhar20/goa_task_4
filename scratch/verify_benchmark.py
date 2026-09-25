import os
import pyTigerGraph as tg
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
conn = tg.TigerGraphConnection(
    host=os.environ.get('TG_HOST'),
    graphname='HHGOA_Fraud_Official',
    gsqlSecret=os.environ.get('TG_SECRET')
)

cases = pd.read_csv('C:/Users/malav/Downloads/case_pack.csv')
all_found = True
for _, row in cases.iterrows():
    tid = str(row['flagged_txn_id'])
    result = conn.getVerticesById('O_Transaction', [tid])
    found = len(result) > 0
    if not found:
        all_found = False
    status = 'FOUND' if found else 'MISSING'
    print(f"  {row['case_id']} TXN {tid}: {status}")

print()
print('ALL 20 FOUND:', all_found)
print('O_Transaction total:', conn.getVertexCount('O_Transaction'))
print('O_ClosedCase total:', conn.getVertexCount('O_ClosedCase'))
print('O_Customer total:', conn.getVertexCount('O_Customer'))
print('O_Card total:', conn.getVertexCount('O_Card'))
