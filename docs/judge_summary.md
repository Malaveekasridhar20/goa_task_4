# Judge Summary: TigerGraph Agentic Fraud Investigator

## Overview
We built an autonomous Fraud Investigation AI Agent that utilizes TigerGraph as an active memory and investigation engine. Instead of relying on a black-box LLM to hallucinate probabilities, our agent extracts highly structural graph features to produce deterministic, evidence-weighted fraud scores mapped to a strict Next-Best-Action policy engine.

## Problem & Solution
- **Problem**: Fraud analysts spend hours manually querying databases to piece together transaction context, device histories, and past cases.
- **Solution**: An AI orchestrator natively integrated with TigerGraph (via MCP and REST APIs) that actively queries the graph, detects CNP (Card Not Present) patterns, evaluates uncertainty, recommends policy-driven actions, and automatically writes the verdict back to TigerGraph to inform future investigations.
- **Why TigerGraph?**: Relational databases cannot efficiently traverse the N-deep hops (Transaction → Device → Other Transactions → Closed Cases) required to detect sophisticated fraud rings in real-time. TigerGraph handles these deep traversals instantaneously.

## Core Features & Workflow
1. **Agentic Workflow**: The agent is not a simple linear script. It dynamically requests graph context for the transaction, card, device, and historical connections.
2. **Evidence Provenance & GraphRAG**: Historical case memory is accessed via GraphRAG (vector search on `O_ClosedCase`). The system features a strict self-reference isolation layer, ensuring the current transaction cannot act as its own historical evidence.
3. **Evidence-Weighted Fraud Probability**: The system uses a strict mathematical scoring engine (e.g. Base 0.5 + 0.35 Verified CNP + 0.15 New Device = 1.00). It does *not* invent probabilities.
4. **Uncertainty Handling**: Partial evidence dynamically flags cases as `HIGH` or `MEDIUM` uncertainty, preventing premature card blocking and triggering "step-up authentication" instead.
5. **Next-Best-Action (NBA) Policy Engine**: Deterministic rules govern exactly what action is taken based on the fraud score and financial exposure (e.g., >$2500 triggers L2 Analyst Escalation).
6. **SAR Logic (Suspicious Activity Report)**: SARs are exclusively filed when policy limits are exceeded (e.g. exposure > $1000) or undocumented coordinated activity is detected.
7. **Graph Write-Back (Case Memory)**: The ultimate result of every case is written back to TigerGraph natively (`O_ClosedCase` connected to `O_Transaction`).

## 20-Case Official Benchmark Statistics
The system was evaluated against the official 20-case IEEE fraud dataset.

- **Total Cases Processed**: 20/20 completed
- **Graph Writes Verified**: 20/20 verified in TigerGraph
- **Fraud Verdicts**: 15 cases (High probability, Block Card)
- **Uncertain Verdicts**: 5 cases (Insufficient evidence, Verify with Customer)
- **SARs Filed**: 1 case (HHG-010 exceeded $1000 threshold)
