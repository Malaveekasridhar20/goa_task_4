# Actual Graph Inventory

This document reflects the exact native schema of the `Transaction_Fraud` graph in TigerGraph.

## 1. Vertices (0)

## 2. Edges (0)

## 3. Fraud Investigation Traversal Map

### Payment_Transaction → Card → related transactions
Signal: Identifies if the same card was used in other fraudulent or high-risk transactions. High velocity of transactions on one card in a short period suggests account takeover or card testing.

### Payment_Transaction → Merchant → Merchant_Category
Signal: Reveals if the transaction is directed at high-risk merchant categories (e.g., gambling, electronics) which are often targeted by fraudsters.

### Payment_Transaction → Card → Party → Device
Signal: Connects the transaction to the device used. If the device is new, unseen, or associated with multiple different parties/cards, it strongly suggests a fraudulent device or bot network.

### Payment_Transaction → Card → Party → IP
Signal: Connects the transaction to an IP address. Multiple transactions from different cards coming from the same IP (or high-risk IPs) signal coordinated fraud or account takeover.

### Payment_Transaction → Card → Party → Address → Zipcode → City → State
Signal: Provides the geographical location of the party. If the transaction occurs far from this established address (out-of-region), it signals potential card-present fraud or stolen details.

### Card → Community
Signal: Identifies if the card belongs to a densely connected community (via Louvain). High community size or connectivity serves as network context, but does not inherently prove fraud.

### Merchant → Community
Signal: Shows the merchant's cluster within the broader network. May highlight shared topologies, but requires further investigation to label as high-risk.

### Party → Community
Signal: Contextualizes the individual's network position. High PageRank or centrality indicates a highly connected node, not necessarily a mule.

### Card → Merchant
Signal: Analyzes the direct relationship frequency. A sudden spike in activity between a specific card and a specific merchant can indicate collusion or a targeted attack.

### Merchant → Merchant
Signal: Identifies related merchants (e.g., sharing terminals, owners, or transaction patterns). Useful for uncovering larger fraud rings masking as independent businesses.

