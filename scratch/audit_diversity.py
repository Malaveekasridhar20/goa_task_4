import os
import json
import glob
import re

def audit():
    cases_dir = "cases_demo"
    files = sorted(glob.glob(os.path.join(cases_dir, "*.json")))
    
    print("=== DIVERSITY AUDIT ===\n")
    
    for f in files:
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
            
        case_id = data.get("case_id")
        txn_id = data.get("flagged_txn_id")
        
        # Extract graph evidence
        graph_ev = data.get("graph_evidence", [])
        
        linked_card = "None"
        merchant = "None"
        categories = "None"
        v_count = 0
        v_amount = 0.0
        max_amount = 0.0
        
        for ev in graph_ev:
            if not ev: continue
            
            # extract merchant
            if ev.get("query") == "get_merchant_context":
                finding = ev.get("finding", "")
                # e.g., "Transaction at Merchant fraud_Kuhic LLC, Categories: ['shopping_net']"
                m_match = re.search(r"Merchant (.*?), Categories: (\[.*\])", finding)
                if m_match:
                    merchant = m_match.group(1)
                    categories = m_match.group(2)
                    
            # extract card
            if ev.get("query") == "get_transaction_context":
                finding = ev.get("finding", "")
                c_match = re.search(r"made by Card (.*?),", finding)
                if c_match:
                    linked_card = c_match.group(1)
                    
            # extract algorithm
            if ev.get("source") == "TigerGraph_GraphAlgorithm":
                attrs = ev.get("attributes", {})
                v_count = attrs.get("velocity_count", 0)
                v_amount = attrs.get("velocity_amount", 0.0)
                max_amount = attrs.get("max_amount", 0.0)
                
        patterns = {p.get("pattern"): p.get("status") for p in data.get("pattern_assessment", [])}
        uncertainty = data.get("uncertainty", {}).get("level")
        nba = data.get("final_nba", {}).get("actions", [{}])[0].get("action", "NONE")
        
        print(f"[{case_id}] Txn: {txn_id} | Card: {linked_card} | Merch: {merchant} {categories}")
        print(f"    Algo: {v_count} txns, ${v_amount:.2f} total, ${max_amount:.2f} max")
        print(f"    Patterns: {patterns}")
        print(f"    Uncertainty: {uncertainty} | NBA: {nba}\n")

if __name__ == "__main__":
    audit()
