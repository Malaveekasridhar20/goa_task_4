import os
import json
import pyTigerGraph as tg
from dotenv import load_dotenv

load_dotenv()
conn = tg.TigerGraphConnection(
    host=os.environ.get('TG_HOST'),
    graphname='HHGOA_Fraud_Official',
    gsqlSecret=os.environ.get('TG_SECRET')
)
conn.apiToken = conn.getToken(os.environ.get('TG_SECRET'))[0]

print("1. Verifying 'nan' vertex...")
try:
    v = conn.getVerticesById("O_Transaction", ["nan"])
    print("nan vertex details:", v)
except Exception as e:
    print("Error fetching nan vertex:", e)
    v = []

print("\n2. Verifying 'nan' edges...")
try:
    edges = conn.getEdges("O_Transaction", "nan")
    print(f"Edges for nan: {len(edges)} found.")
except Exception as e:
    print("Error fetching nan edges:", e)

benchmark_ids = [
    "3514030", "3478782", "3530164", "3583227", "3523199",
    "3476682", "3514948", "3558054", "3581141", "3506725",
    "3583368", "3553342", "3526826", "3478561", "3464869",
    "3534820", "3450629", "3491361", "3503878", "3509359"
]

print("\n3. Confirming not referenced by benchmark...")
if "nan" not in benchmark_ids:
    print("'nan' is NOT in the 20 official benchmark IDs.")

if len(v) > 0:
    print("\n4. Removing 'nan' vertex...")
    res = conn.delVerticesById("O_Transaction", ["nan"])
    print("Delete result:", res)
else:
    print("\n4. 'nan' vertex not found! Skipping delete.")

print("\n5. Re-querying O_Transaction count...")
count = conn.getVertexCount("O_Transaction")
print(f"Total O_Transaction count: {count}")
assert count == 595407, f"Expected 595407, got {count}"

print("\n6. Verifying all 20 benchmark IDs exist...")
for bid in benchmark_ids:
    check = conn.getVerticesById("O_Transaction", [bid])
    if len(check) == 0:
        print(f"MISSING: {bid}")
    else:
        print(f"FOUND: {bid}")
