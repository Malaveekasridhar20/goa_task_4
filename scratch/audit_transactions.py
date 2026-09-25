import pandas as pd

print("Running integrity check...")

# Load transactions
df_txns = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
txn_ids = df_txns['TransactionID'].dropna().astype(str).tolist()

# Load closed cases
df_cases = pd.read_csv("C:/Users/malav/Downloads/closed_cases_history.csv")
case_txn_ids = df_cases['first_fraud_txn_id'].dropna().astype(str).tolist()

print(f"Total rows in transactions.csv: {len(df_txns)}")
print(f"Total rows in closed_cases_history.csv: {len(df_cases)}")

unique_txns = set(txn_ids)
unique_case_txns = set(case_txn_ids)

print(f"Unique TransactionIDs in transactions.csv: {len(unique_txns)}")
print(f"Duplicates in transactions.csv: {len(txn_ids) - len(unique_txns)}")

print(f"Unique TransactionIDs in closed_cases_history.csv: {len(unique_case_txns)}")
print(f"Duplicates in closed_cases_history.csv: {len(case_txn_ids) - len(unique_case_txns)}")

overlap = unique_txns.intersection(unique_case_txns)
print(f"Number of closed-case transactions that duplicate an existing official TransactionID: {len(overlap)}")

# TigerGraph expected total
print(f"Expected TigerGraph O_Transaction count: {len(unique_txns) + len(unique_case_txns) - len(overlap)}")
