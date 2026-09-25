# Dataset Analysis

## File Inventory
- **`README.md`**: Main instructions, task description, guidelines, policy rules, format requirements, and the 20 benchmark cases.
- **`TigerGraph Agentic Fraud Investigation HHGOA.docx`**: High-level problem statement and requirements (parallels README).
- **`transactions.csv` (590,742 rows)**: Contains core transaction data. Includes Vesta's original columns + `customer_id`, `ts`, `channel`, `risk_score`. No raw 'IsFraud' flag.
- **`identity.csv` (144,432 rows)**: Contains device and network identity info for online transactions. Joins to `transactions.csv` via `TransactionID`.
- **`closed_cases_history.csv` (5,565 rows)**: Past investigations (July to October) containing confirmed fraud and cleared alerts. Used as case memory.
- **`case_pack.csv` (20 rows)**: The 20 benchmark cases to be investigated by the agent (November and December).

## Schema & Column Descriptions

### Transactions (`transactions.csv`)
- **Primary Key**: `TransactionID`
- **Temporal/Financial**: `TransactionDT` (offset seconds), `ts` (real timestamp YYYY-MM-DD HH:MM:SS), `TransactionAmt`
- **Product/Channel**: `ProductCD` (W=in_person, C/H/R/S=online), `channel` (`in_person` or `online`)
- **Card/Customer**: `card1` - `card6` (network, type, issuer codes), `customer_id`
- **Location**: `addr1` (billing region), `addr2` (country, 87=home), `dist1`, `dist2`
- **Network**: `P_emaildomain`, `R_emaildomain`
- **Risk**: `risk_score` (0.0 to 1.0 from real-time model)
- **Vesta Features**: `C1`-`C14` (counts), `D1`-`D15` (time deltas), `M1`-`M9` (match flags), `V1`-`V339` (engineered features)

### Identity (`identity.csv`)
- **Primary Key**: `TransactionID` (Foreign Key to Transactions)
- **Device Identifiers**: `DeviceType` (mobile/desktop), `DeviceInfo` (e.g. `SAMSUNG SM-G935F Build/NRD90M`)
- **Network Identifiers**: `id_01` to `id_11` (ratings/counts)
- **Categorical**: `id_12` to `id_38` (e.g., `id_15`=New/Found device, `id_23`=proxy, `id_30`=OS, `id_31`=browser, `id_33`=screen)

### Closed Cases (`closed_cases_history.csv`)
- **Primary Key**: `case_id`
- **Entities**: `customer_id`, `card_id`
- **Temporal**: `opened_at`, `closed_at`
- **Investigation Details**: `outcome` (confirmed_fraud/cleared), `pattern` (fraud pattern type), `first_fraud_txn_id`, `txn_ids` (affected), `n_txns`, `exposure_usd`, `connected_card_ids`, `actions_taken`, `report_filed`
- **Narrative**: `analyst_notes`

### Case Pack (`case_pack.csv`)
- **Primary Key**: `case_id`
- **Trigger**: `opened_at`, `trigger_type` (risk_score, customer_report, analyst_request), `trigger_text`, `risk_score`
- **Entities**: `flagged_txn_id`, `card_id`, `customer_id`

## Relationships
- `Customer` (1) -> (M) `Card` (via `customer_id` & `card_id`)
- `Card` (1) -> (M) `Transaction` (via `card_id`)
- `Transaction` (1) -> (0..1) `DeviceProfile` (via `TransactionID` to `identity.csv`)
- `Transaction` (M) -> (1) `EmailDomain` (via `P_emaildomain` / `R_emaildomain`)
- `Transaction` (M) -> (1) `BillingRegion` (via `addr1`)
- `ClosedCase` (1) -> (M) `Transaction` (via `txn_ids`)
- `ClosedCase` (1) -> (M) `Card` (via `connected_card_ids` & `card_id`)

## Policy Structure & NBA
- **Actions**: ALLOW_TRANSACTION, DECLINE_TRANSACTION, MONITOR_CARD, MONITOR_CONNECTED_CARDS, WARN_CUSTOMER, VERIFY_WITH_CUSTOMER, STEP_UP_AUTH, BLOCK_CARD, BLOCK_ALL_CARDS, GENERATE_REPORT, CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST, CLOSE_NO_FRAUD.
- **Approval Routes**: `auto`, `L1` (team lead), `L2` (fraud manager).
- **Rules (R1-R10)**: Dictate step-up authentication, blocking limits, sharing of devices (R6), disputes (R7), and SAR filing thresholds.

## Fraud Patterns
1. `card_testing`: 3+ tiny online auths (<$5), then large purchase.
2. `card_not_present_fraud`: Unusual online use (amounts/products).
3. `card_not_present_new_device`: Above + new device (`id_15`=New).
4. `out_of_region_use`: Card-present in new `addr1` region.
5. `account_takeover`: Mixed-channel anomalies, credentials compromised.
6. `undocumented`: Fits none, coordinated abuse.
7. `none`: Legitimate.

## Implementation Mapping
1. **TigerGraph Schema**: Map entities to vertices (`Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `Case`) and build edges (`OWNS`, `MADE`, `FROM_DEVICE`, `BILLED_IN`, `NEXT`, `INVOLVES`).
2. **GraphRAG**: Vectorize `closed_cases_history.csv` analyst notes and policy rules for semantic search.
3. **Agent Workflow**: Given a trigger, fetch subgraph, retrieve similar cases, apply rules, determine uncertainty. Use simulated evidence requests when probability < 0.70 or required by policy.
4. **Output**: Generate 20 exact JSON files matching the structure specified in the README.
