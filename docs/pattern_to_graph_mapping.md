# Pattern to Graph Mapping

This document maps the five official fraud patterns to the actual retrieved `Transaction_Fraud` schema, applying strict evidence constraints.

---

### Pattern 1: Card testing
- **Required signals from README**: High-velocity, small-amount transactions, or a burst of declined transactions on a single card across multiple merchants, often indicating the card is being tested for validity.
- **Available graph evidence**: Card transaction statistics (e.g., `cnt_repeated_card`, `com_cd_txn_cnt`, `cd_com_size`), transaction `amount`, and `is_fraud` flags. We can see the history of transactions for a card.
- **Exact graph traversal**: `Payment_Transaction` → `Card_Send_Transaction` (reverse) → `Card` → `Card_Send_Transaction` → `Payment_Transaction`
- **Evidence strength**: INDIRECTLY_SUPPORTED (INDIRECT)
- **Missing transaction-level signals**: The graph schema lacks failed transaction codes, PIN/CVV failures, or exact POS error responses.
- **Additional evidence required**: External payment gateway logs to verify if a burst of transactions resulted in authorization declines.
- **What the agent may conclude**: The agent may conclude there is high velocity or a burst of small transactions associated with the card.
- **What the agent MUST NOT conclude**: The agent MUST NOT conclude definitively that it is "Card Testing" based purely on volume without gateway failure logs, nor should it hallucinate decline reasons.

---

### Pattern 2: CNP (Card Not Present)
- **Required signals from README**: Transactions occurring without the physical card present, typically online or over the phone.
- **Available graph evidence**: `Merchant_Category` (e.g., if a merchant is classified strictly as an online retailer).
- **Exact graph traversal**: `Payment_Transaction` → `Merchant_Receive_Transaction` → `Merchant` → `Merchant_Assigned` → `Merchant_Category`
- **Evidence strength**: INDIRECTLY_SUPPORTED (INDIRECT)
- **Missing transaction-level signals**: The graph schema lacks an explicit POS entry mode (e.g., chip, swipe, manual entry) or 3D-Secure authentication status on the `Payment_Transaction`.
- **Additional evidence required**: External authorization logs or receipt data containing the POS entry mode.
- **What the agent may conclude**: The agent may conclude the merchant is an online merchant or belongs to a specific category.
- **What the agent MUST NOT conclude**: The agent MUST NOT definitively conclude the transaction was CNP merely because the merchant category is "online retail" or similar. Merchant category is supporting context, not definitive CNP evidence.

---

### Pattern 3: CNP from new device
- **Required signals from README**: A Card Not Present transaction originating from a device never previously associated with the cardholder.
- **Available graph evidence**: The schema provides `Party` → `Has_Device` → `Device`.
- **Exact graph traversal**: `Payment_Transaction` → `Card_Send_Transaction` (reverse) → `Card` → `Party_Has_Card` (reverse) → `Party` → `Has_Device` → `Device`
- **Evidence strength**: NOT_AVAILABLE_FROM_GRAPH (UNAVAILABLE)
- **Missing transaction-level signals**: There is no `Payment_Transaction` → `Device` relationship in the extracted schema. We cannot automatically prove that a particular transaction was performed from a particular device.
- **Additional evidence required**: External web/mobile application session logs tying the specific `Payment_Transaction` ID to a specific Device ID.
- **What the agent may conclude**: The agent may conclude that a Party has a set of known devices.
- **What the agent MUST NOT conclude**: The agent MUST NOT conclude that a missing `Has_Device` relationship proves a new device was used for the transaction, nor can it attribute a transaction to a specific device solely from the graph.

---

### Pattern 4: Out-of-region
- **Required signals from README**: A transaction occurring in a geographic location significantly distant from the cardholder's known or established location.
- **Available graph evidence**: The Party's established location is available.
- **Exact graph traversal**: `Party` → `Has_Address` → `Address` → `Assigned_To` → `Zipcode` → `Assigned_To` → `City` → `Assigned_To` → `State`
- **Evidence strength**: REQUIRES_EXTERNAL_EVIDENCE (INDIRECT)
- **Missing transaction-level signals**: `Payment_Transaction` has `city_pop` but no demonstrated `city` attribute or `Located_In` edge. Transaction-level geographic location is missing.
- **Additional evidence required**: Validated dataset field, external IP geolocation, or merchant POS location data to establish the transaction's actual location.
- **What the agent may conclude**: The agent may conclude the Party's established location based on their address.
- **What the agent MUST NOT conclude**: The agent MUST NOT invent a `Payment_Transaction.city` attribute, and MUST NOT claim out-of-region fraud unless another validated external dataset establishes the transaction's location.

---

### Pattern 5: Account takeover
- **Required signals from README**: Unauthorized access to a party's account, followed by fraudulent actions, often indicated by sudden changes in credentials (IP, email, phone) or highly anomalous behavior.
- **Available graph evidence**: The schema links the Party to various identifiers (`Has_IP`, `Has_Device`, `Has_Email`, `Has_Phone`).
- **Exact graph traversal**: `Payment_Transaction` → `Card` (reverse) → `Party` → `IP`/`Device`/`Email`/`Phone`
- **Evidence strength**: NOT_AVAILABLE_FROM_GRAPH (UNAVAILABLE)
- **Missing transaction-level signals**: There is no direct link between a `Payment_Transaction` and the specific `IP`, `Email`, or `Phone` used during that transaction. 
- **Additional evidence required**: External authentication logs (login events, MFA failures, password changes) mapping the transaction time to a specific session/IP/Device.
- **What the agent may conclude**: The agent may conclude that a Party has multiple IPs or Devices, and if any of those global vertices have an `is_blocked` flag.
- **What the agent MUST NOT conclude**: The agent MUST NOT claim that a specific transaction originated from a specific IP/device unless external data explicitly supports that transaction-level association.

---

### Contextual Graph Metrics
**Community Analytics**
- **Available Evidence**: `Card`/`Party`/`Merchant` → `Community`. The schema has attributes like `pagerank`, `c_size`, `c_id`.
- **Constraint**: Do not call a community "fraudulent" merely because it exists, has high size, PageRank, or connectivity. Treat community metrics as contextual/network evidence only.
