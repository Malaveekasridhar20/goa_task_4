# TigerGraph Dataset Audit

## Overview
This audit examines the current state of the live TigerGraph environment to determine if it possesses the official benchmark dataset schema and transactions.

## Findings
- **Current Graph Name:** `Transaction_Fraud`

### Vertex Types Found (18)
- `Phone`, `Email`, `Community`, `Address`, `IP`, `Device`, `City`, `Merchant`, `State`, `Full_Name`, `Zipcode`, `Payment_Transaction`, `Card`, `Merchant_Category`, `ID`, `Party`, `DOB`, `Concept`

### Edge Types Found (22)
- `Merchant_Merchant`, `Merchant_Receive_Transaction`, `Card_Send_Transaction`, `Card_Card`, `Merchant_Assigned`, `Is_SubCategory`, `Has_Interaction_With_Merchant`, `Has_Address`, `Is_Merchant`, `Party_Has_Card`, `Has_ID`, `Has_IP`, `Has_Device`, `Has_Phone`, `Has_Email`, `Has_Community`, `Assigned_To`, `Located_In`, `Has_DOB`, `Has_Full_Name`, `DESCRIBES`, `IS_CHILD_OF`

## Benchmark Transactions Check
A manual lookup was performed for all 20 official benchmark transactions (e.g., `3514030`, `3478782`, etc.) in the `Transaction_Fraud` graph under the `Payment_Transaction` vertex type.

**Result:** **0 out of 20 benchmark transactions exist in the current graph.**

## Conclusion
The current `Transaction_Fraud` graph does **NOT** contain the official dataset. It contains a completely different (likely outdated or demo) dataset. We must create a new graph `HHGOA_Fraud_Official` with a custom schema reflecting the exact supplied data in `case_pack.csv`, `transactions.csv`, `identity.csv`, and `closed_cases_history.csv` to process the OFFICIAL_BENCHMARK correctly.
