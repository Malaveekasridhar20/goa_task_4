# Demo Guide

This guide explains how to present the TigerGraph Agentic Fraud Investigation System for the 3-5 minute Hackathon Demo.

## Step 1: Preparation
- Ensure `python evaluation/run_all_cases.py` has been executed so the `/cases/` directory is populated with 20 JSON artifacts.
- Run the UI via `streamlit run ui/app.py`.

## Step 2: The Command Center (0:00 - 1:00)
- **Visuals**: Show the main dashboard.
- **Talking Points**: Explain how the dashboard aggregates investigations. Point out the metrics: Total Cases, Confirmed Fraud, and SARs Filed. Emphasize that the agent has completely pre-processed these cases.

## Step 3: Deep Dive into a Case (1:00 - 3:00)
- Navigate to the **Case Detail** tab and select `HHG-017`.
- **Explain the workflow**: The agent triggered on a risk score, used MCP to query TigerGraph for the 2-hop transaction context, and used GraphRAG to find similar cases.
- **Uncertainty Loop**: Highlight that the agent initially did not have enough evidence to block the card (following Policy R1). It simulated a "VERIFY_WITH_CUSTOMER" step, received a denial, and subsequently updated its confidence.
- **Next Best Action**: Show the "Initial" vs "Final" NBA side-by-side, demonstrating how the agent dynamically changes decisions as evidence flows in. Note the correct approval routes (`L1`, `L2`, `auto`).

## Step 4: Explainability & Graph (3:00 - 4:00)
- Highlight the **Suspicious Activity Report (SAR)**. Show how the agent autonomously generated the narrative for the regulator without manual intervention.
- Navigate to the **Graph View** tab to show the (simulated/rendered) TigerGraph schema and topological traversal of the fraud ring.

## Step 5: Wrap Up
- Reiterate the core engineering principles: TigerGraph for deterministic graph facts, GraphRAG for historical context, and the Agent for reasoning, synthesis, and policy adherence.
