import os
import pyTigerGraph as tg
from dotenv import load_dotenv

load_dotenv()
conn = tg.TigerGraphConnection(
    host=os.environ.get('TG_HOST'),
    graphname='HHGOA_Fraud_Official',
    gsqlSecret=os.environ.get('TG_SECRET')
)
conn.apiToken = conn.getToken(os.environ.get('TG_SECRET'))[0]

print("1. O_Transaction =", conn.getVertexCount("O_Transaction"))
print("2. O_MADE =", conn.getEdgeCount("O_MADE"))
print("3. O_INVOLVED_IN =", conn.getEdgeCount("O_INVOLVED_IN"))

benchmark_ids = [
    "3514030", "3478782", "3530164", "3583227", "3523199",
    "3476682", "3514948", "3558054", "3581141", "3506725",
    "3583368", "3553342", "3526826", "3478561", "3464869",
    "3534820", "3450629", "3491361", "3503878", "3509359"
]

print("\n4. Verifying Benchmark IDs:")
missing = 0
for bid in benchmark_ids:
    try:
        res = conn.getVerticesById("O_Transaction", [bid])
        if len(res) == 0:
            missing += 1
            print(f"MISSING: {bid}")
    except:
        missing += 1
        print(f"MISSING (err): {bid}")

if missing == 0:
    print("ALL 20 BENCHMARK IDs EXIST")

print("\n5. Verifying HHG-001 (3514030) Edges:")
try:
    edges = conn.getEdges("O_Transaction", "3514030")
    types = set([e['e_type'] for e in edges])
    print(f"HHG-001 edge types found: {types}")
except Exception as e:
    print(f"Failed to fetch HHG-001 edges: {e}")

print("\n6. Verifying 'nan':")
try:
    res = conn.getVerticesById("O_Transaction", ["nan"])
    if len(res) > 0:
        print("'nan' vertex EXISTS! (FAIL)")
    else:
        print("'nan' vertex does NOT exist. (PASS)")
except Exception as e:
    # 601 error means not found, which is a PASS
    if '601' in str(e):
        print("'nan' vertex does NOT exist (601 error). (PASS)")
    else:
        print(f"'nan' check error: {e}")

print("\n7. Other Edge Counts:")
for e_type in ["O_FROM_DEVICE", "O_BILLED_IN", "O_PURCHASER_EMAIL", "O_OWNS", "O_NEXT", "O_ON_CARD", "O_CONNECTED_TO"]:
    print(f"{e_type}: {conn.getEdgeCount(e_type)}")

print("\nDONE.")
