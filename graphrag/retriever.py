import pandas as pd
import os

class GraphRAGRetriever:
    def __init__(self, cases_csv_path: str):
        self.cases_csv_path = cases_csv_path
        self.history_df = None
        
    def load_history(self):
        global _HISTORY_DF_CACHE
        if '_HISTORY_DF_CACHE' not in globals():
            try:
                _HISTORY_DF_CACHE = pd.read_csv(self.cases_csv_path)
            except Exception as e:
                print(f"GraphRAG Error: {e}")
                _HISTORY_DF_CACHE = pd.DataFrame()
        self.history_df = _HISTORY_DF_CACHE
                
    def load_policy(self):
        policy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "POLICY_MAPPING.md")
        try:
            with open(policy_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Policy Load Error: {e}")
            return ""

    def build_context(self, graph_evidence: list, context_keywords: list, limit: int = 3):
        """
        GraphRAG Context Builder.
        Combines semantic retrieval of historical cases and policy documents with exact TigerGraph evidence.
        """
        self.load_history()
        
        # A. TigerGraph Graph Evidence (passed in)
        context = {"graph_evidence": graph_evidence}
        
        # B & E. Policy Documents & Regulatory
        policy_text = self.load_policy()
        context["policy"] = policy_text
        context["regulatory"] = "Extracted from policy (e.g. SAR > $1000 thresholds)" if "Regulatory Reporting" in policy_text else "UNVERIFIED"
        
        # C. Fraud Patterns
        context["patterns"] = ["Card testing", "CNP", "CNP from new device", "Out-of-region", "Account takeover"]
        
        # D. Historical Cases (Semantic Retrieval)
        historical_cases = []
        if not self.history_df.empty:
            for _, row in self.history_df.iterrows():
                notes = str(row.get('analyst_notes', '')).lower()
                if any(k.lower() in notes for k in context_keywords):
                    historical_cases.append(row.to_dict())
                    if len(historical_cases) >= limit:
                        break
        
        context["historical_cases"] = historical_cases
        return context
