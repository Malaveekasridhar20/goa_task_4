import pandas as pd
import json

base_path = "C:/Users/malav/Downloads"

try:
    case_pack = pd.read_csv(f"{base_path}/case_pack.csv")
    transactions = pd.read_csv(f"{base_path}/transactions.csv")
    identity = pd.read_csv(f"{base_path}/identity.csv")
    closed_cases = pd.read_csv(f"{base_path}/closed_cases_history.csv")

    txn_ids = set(transactions['TransactionID'].astype(str))
    identity_ids = set(identity['TransactionID'].astype(str))

    benchmark_ids = [
        "3514030", "3478782", "3530164", "3583227", "3523199",
        "3476682", "3514948", "3558054", "3581141", "3506725",
        "3583368", "3553342", "3526826", "3478561", "3464869",
        "3534820", "3450629", "3491361", "3503878", "3509359"
    ]

    report = {
        "transaction_count": len(transactions),
        "identity_count": len(identity),
        "closed_case_count": len(closed_cases),
        "benchmark_cases": []
    }

    for b_id in benchmark_ids:
        report["benchmark_cases"].append({
            "id": b_id,
            "in_transactions": b_id in txn_ids,
            "in_identity": b_id in identity_ids
        })

    with open("scratch/audit_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Audit data dumped to scratch/audit_report.json")
    print(f"Transactions cols: {list(transactions.columns)[:10]}...")
    print(f"Identity cols: {list(identity.columns)[:10]}...")
    print(f"Closed Cases cols: {list(closed_cases.columns)[:10]}...")
except Exception as e:
    print(f"Error: {e}")
