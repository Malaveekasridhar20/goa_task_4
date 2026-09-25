# TigerGraph Agentic Fraud Investigation System

## Problem
Fraud investigation relies on slow, manual gathering of disconnected data across siloed systems. Analysts lack real-time graph insights and an automated assistant to handle routine evidence gathering and policy-based action generation.

## Solution
An autonomous AI Agent that receives fraud alerts, queries a TigerGraph database via the Model Context Protocol (MCP), performs GraphRAG on historical cases, synthesizes evidence, handles uncertainty loops (requesting more evidence when required), and recommends actions via a strict Next-Best-Action (NBA) Policy Engine.

## Architecture
- **TigerGraph & GSQL**: Primary source of truth for graph topologies, cards, devices, and transactions.
- **TigerGraph MCP Server**: A native JSON-RPC Model Context Protocol server that exposes graph tools via standard I/O (stdio).
- **Agent Orchestrator**: Manages investigation workflow, acts as the MCP Client, dynamically discovers tools, and parses results.
- **GraphRAG**: Vector search across past closed cases (`analyst_notes`) to find identical patterns.
- **Policy & NBA Engine**: Deterministic rules checking risk limits, exposure thresholds, and generating the appropriate action and approval routes (`auto`, `L1`, `L2`).

## Running Locally
1. Clone the repository.
2. Ensure you have python installed. Create a virtual environment and install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in credentials.
4. Run `python tigergraph/loading/load_data.py` to upsert datasets into TigerGraph.
5. Start the frontend: `streamlit run ui/app.py`.

## Running Benchmark Cases
Execute `python evaluation/run_all_cases.py` to process the `case_pack.csv` and generate JSON outputs in the `/cases/` directory.

## Demo Instructions
Launch the Streamlit UI. Select `DEMO_MODE=true` in your `.env` to run the agent in a simulated environment if TigerGraph credentials are missing. Use the "Case Detail" page to step through an automated investigation for any of the 20 benchmark cases.
