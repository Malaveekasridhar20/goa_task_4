import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import pandas as pd
from dotenv import load_dotenv
from agent.graph_agent import InvestigationAgent

load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["official", "demo"], required=True, help="Evaluation mode")
    args = parser.parse_args()
    
    if args.mode == "official":
        print("Evaluating all 20 cases in OFFICIAL_BENCHMARK mode...")
        df_path = "C:/Users/malav/Downloads/case_pack.csv"
        evaluation_mode = "OFFICIAL_BENCHMARK"
    else:
        print("Evaluating all 20 cases in DEMO_INTEGRATION mode...")
        df_path = "evaluation/case_pack_mapped.csv"
        evaluation_mode = "DEMO_INTEGRATION"
        
    tg_host = os.environ.get("TG_HOST")
    demo_mode = os.environ.get("DEMO_MODE", "true").lower() == "true"
    
    if not demo_mode and (not tg_host or "localhost" in tg_host):
        print("BLOCKED: Cannot run authentic evaluation because real TG_HOST is missing, and DEMO_MODE is false.")
        sys.exit(1)
        
    if not os.path.exists(df_path):
        print(f"ERROR: Dataset not found at {df_path}")
        sys.exit(1)
        
    df = pd.read_csv(df_path)
    agent = InvestigationAgent(llm_mode="real", evaluation_mode=evaluation_mode)
    
    out_dir = "cases" if args.mode == "official" else f"cases_{args.mode}"
    os.makedirs(out_dir, exist_ok=True)
    
    for _, row in df.iterrows():
        print(f"Investigating case {row['case_id']}...")
        case_input = row.to_dict()
        result = agent.investigate(case_input)
        
        with open(f"{out_dir}/{row['case_id']}.json", "w") as f:
            json.dump(result, f, indent=2)
            
    print(f"Evaluated {len(df)} cases. Outputs saved to {out_dir} directory.")

if __name__ == "__main__":
    main()
