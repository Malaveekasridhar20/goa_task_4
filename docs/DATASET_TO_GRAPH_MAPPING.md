# Dataset to Graph Mapping

This document maps the official task datasets to the Graph schema implemented in this project to ensure no relationships were hallucinated or invented.

## Dataset Analysis

### 1. `transactions.csv`
- **Columns**: `TransactionID`, `isFraud`, `TransactionDT`, `TransactionAmt`, `ProductCD`, `card1`, `card2`, `card3`, `card4`, `card5`, `card6`, `addr1`, `addr2`, `dist1`, `dist2`, `P_emaildomain`, `R_emaildomain`, `customer_id`, `ts`, `channel`, `risk_score`

### 2. `identity.csv`
- **Columns**: `TransactionID`, `id_01` to `id_38`, `DeviceType`, `DeviceInfo`

---

## Vertices

| Graph Vertex | Dataset Source | Source Column(s) | Reason / Justification |
| :--- | :--- | :--- | :--- |
| **Customer** | `transactions.csv` | `customer_id` | Unique identifier for a human customer initiating the transaction. |
| **Card** | `transactions.csv` | `card1` to `card6` | `card1-6` represent features of the payment card (issuer, type, network). |
| **Transaction** | `transactions.csv` | `TransactionID`, `TransactionAmt`, `ProductCD`, `channel`, `risk_score`, `ts` | The core event representing a transfer of funds. |
| **DeviceProfile** | `identity.csv` | `DeviceInfo`, `DeviceType`, `id_30` (os), `id_31` (browser) | The identity dataset explicitly provides device characteristics linked to `TransactionID`. |
| **EmailDomain** | `transactions.csv` | `P_emaildomain`, `R_emaildomain` | Purchaser and recipient email domains. Grouping by domain helps find fraud rings. |
| **BillingRegion** | `transactions.csv` | `addr1`, `addr2` | Explicit columns representing billing region and country. |
| **ClosedCase** | `closed_cases_history.csv` | `case_id`, `opened_at`, `closed_at`, `outcome` | Historical cases stored for GraphRAG and semantic retrieval. |

## Edges

| Edge | From Vertex | To Vertex | Source Column(s) / Justification |
| :--- | :--- | :--- | :--- |
| **OWNS** | Customer | Card | Deduced via a customer using a specific card1-6 combination. |
| **MADE** | Card | Transaction | Deduced from the transaction record containing the card features. |
| **FROM_DEVICE** | Transaction | DeviceProfile | `identity.csv` strictly maps `TransactionID` to `DeviceInfo`. |
| **PURCHASER_EMAIL** | Transaction | EmailDomain | `P_emaildomain` column in `transactions.csv`. |
| **RECIPIENT_EMAIL** | Transaction | EmailDomain | `R_emaildomain` column in `transactions.csv`. |
| **BILLED_IN** | Transaction | BillingRegion | `addr1` and `addr2` columns in `transactions.csv`. |
| **INVOLVES** | ClosedCase | Transaction | Implicit; cases investigate specific flagged transactions. |
