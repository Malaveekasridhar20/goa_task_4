import uuid
import json

class GraphInvestigationTools:
    def __init__(self, mcp_caller, max_hops=2, max_related=10, evaluation_mode="DEMO_INTEGRATION"):
        self.mcp_caller = mcp_caller
        self.max_hops = max_hops
        self.max_related = max_related
        self.evaluation_mode = evaluation_mode
        self.evidence_ledger = []
        
    def v(self, type_name):
        if self.evaluation_mode == "OFFICIAL_BENCHMARK":
            mapping = {
                "Payment_Transaction": "O_Transaction",
                "Card": "O_Card",
                "Merchant": "O_BillingRegion", # Official uses BillingRegion as proxy for merchant context or just EmailDomain
                "Merchant_Category": "O_EmailDomain",
                "Party": "O_Customer",
                "Device": "O_DeviceProfile",
                "IP": "O_DeviceProfile" # We map IP to device profile
            }
            return mapping.get(type_name, type_name)
        return type_name
        
    def e(self, type_name):
        if self.evaluation_mode == "OFFICIAL_BENCHMARK":
            mapping = {
                "Card_Send_Transaction": "O_MADE_REVERSE",
                "reverse_Card_Send_Transaction": "O_MADE",
                "Merchant_Receive_Transaction": "O_BILLED_IN_REVERSE",
                "Merchant_Assigned": "O_PURCHASER_EMAIL",
                "Party_Has_Card": "O_OWNS_REVERSE",
                "Has_Device": "O_FROM_DEVICE",
                "Has_IP": "O_FROM_DEVICE"
            }
            return mapping.get(type_name, type_name)
        return type_name

    def _clean_json(self, text):
        import re
        # Find json block
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback to finding the first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text.strip()

    def _add_evidence(self, query_name, traversal, entities, attributes, finding, strength, source="TigerGraph_MCP"):
        evidence = {
            "evidence_id": f"EV-{uuid.uuid4().hex[:8].upper()}",
            "source": source,
            "query": query_name,
            "traversal": traversal,
            "entities": entities,
            "attributes": attributes,
            "finding": finding,
            "evidence_strength": strength
        }
        self.evidence_ledger.append(evidence)
        return evidence

    def get_transaction_context(self, txn_id):
        """A. Transaction -> Card -> related Transactions"""
        # 1. Get Transaction
        status, txn_res = self.mcp_caller("tigergraph__get_node", {
            "vertex_type": self.v("Payment_Transaction"),
            "vertex_id": str(txn_id)
        })
        if status != "SUCCESS":
            return self._add_evidence("get_transaction_context", self.v("Payment_Transaction"), [txn_id], {}, "Transaction not found", "UNAVAILABLE")
        
        try:
            txn_data = json.loads(self._clean_json(txn_res)).get("data", {})
        except Exception:
            txn_data = {}
            
        txn_attrs = txn_data.get("attributes", {})
        
        # 2. Get Card linked to Transaction
        status, edge_res = self.mcp_caller("tigergraph__get_node_edges", {
            "vertex_type": self.v("Payment_Transaction"),
            "vertex_id": str(txn_id)
        })
        
        print(f"DEBUG get_node_edges status: {status}, res: {edge_res[:200]}...")
        
        try:
            edges = json.loads(self._clean_json(edge_res)).get("data", {}).get("edges", [])
            print(f"DEBUG PARSED EDGES: {edges}")
        except Exception as e:
            print(f"DEBUG PARSE ERROR: {e}")
            edges = []
            
        card_id = None
        for edge in edges:
            if edge.get("e_type") == self.e("Card_Send_Transaction") or edge.get("e_type") == self.e("reverse_Card_Send_Transaction") or edge.get("to_type") == self.v("Card"):
                card_id = edge.get("to_id")
            elif edge.get("from_type") == self.v("Card"):
                card_id = edge.get("from_id")
                
        if not card_id:
            return self._add_evidence(
                "get_transaction_context", 
                f"{self.v('Payment_Transaction')} -> {self.v('Card')}", 
                [txn_id], 
                txn_attrs, 
                "No Card found for transaction", 
                "INDIRECT"
            )
            
        # 3. Get Card details
        status, card_res = self.mcp_caller("tigergraph__get_node", {
            "vertex_type": self.v("Card"),
            "vertex_id": str(card_id)
        })
        try:
            card_data = json.loads(self._clean_json(card_res)).get("data", {})
        except:
            card_data = {}
            
        # 4. Get related transactions from Card
        status, rel_txn_res = self.mcp_caller("tigergraph__get_node_edges", {
            "vertex_type": self.v("Card"),
            "vertex_id": str(card_id)
        })
        try:
            rel_txns = json.loads(self._clean_json(rel_txn_res)).get("data", {}).get("edges", [])
        except:
            rel_txns = []
            
        rel_txn_ids = [e.get("to_id") for e in rel_txns if e.get("to_type") == self.v("Payment_Transaction") and e.get("to_id") != txn_id]
        if not rel_txn_ids:
            rel_txn_ids = [e.get("from_id") for e in rel_txns if e.get("from_type") == self.v("Payment_Transaction") and e.get("from_id") != txn_id]
        
        # 4.5 Fallback to CSV for precise history and current txn details (due to missing graph mapping)
        import pandas as pd
        try:
            df = pd.read_csv("C:/Users/malav/Downloads/transactions.csv")
            curr_txn = df[df["TransactionID"] == int(txn_id)]
            if not curr_txn.empty:
                txn_attrs["TransactionAmt"] = float(curr_txn["TransactionAmt"].values[0])
                txn_attrs["TransactionDT"] = str(curr_txn["TransactionDT"].values[0])
                txn_attrs["ProductCD"] = str(curr_txn["ProductCD"].values[0])
            
            rel_df = df[df["TransactionID"].isin([int(x) for x in rel_txn_ids])].sort_values("TransactionDT")
            history = [{"id": str(r["TransactionID"]), "amt": float(r["TransactionAmt"]), "ts": str(r["TransactionDT"]), "channel": str(r["ProductCD"])} for _, r in rel_df.iterrows()]
        except Exception as e:
            history = []
            print(f"DEBUG CSV Error: {e}")

        rel_txn_ids = rel_txn_ids[:self.max_related]
        
        finding = f"Transaction {txn_id} (Amt: {txn_attrs.get('TransactionAmt', 0)}, TS: {txn_attrs.get('TransactionDT', '')}, Channel: {txn_attrs.get('ProductCD', '')}) was made by Card {card_id}, which has {len(rel_txns)} total transactions. History: {history}"
        return self._add_evidence(
            "get_transaction_context",
            "Payment_Transaction -> Card -> Payment_Transaction",
            [txn_id, card_id] + rel_txn_ids,
            {"txn_amount": txn_attrs.get("TransactionAmt", 0), "card_pagerank": card_data.get("attributes", {}).get("pagerank")},
            finding,
            "DIRECT" if len(rel_txns) > 0 else "INDIRECT"
        )
        
    def get_merchant_context(self, txn_id):
        """B. Transaction -> Merchant -> Merchant Category"""
        status, edge_res = self.mcp_caller("tigergraph__get_node_edges", {
            "vertex_type": self.v("Payment_Transaction"),
            "vertex_id": str(txn_id)
        })
        try:
            edges = json.loads(self._clean_json(edge_res)).get("data", {}).get("edges", [])
        except:
            edges = []
            
        merchant_id = None
        for edge in edges:
            if self.v("Merchant") in edge.get("to_type", "") or edge.get("to_type", "") == self.v("Merchant"):
                merchant_id = edge.get("to_id")
                
        if not merchant_id:
            return self._add_evidence("get_merchant_context", f"{self.v('Payment_Transaction')} -> {self.v('Merchant')}", [txn_id], {}, "No Merchant found", "UNAVAILABLE")
            
        status, m_edges_res = self.mcp_caller("tigergraph__get_node_edges", {
            "vertex_type": self.v("Merchant"),
            "vertex_id": merchant_id
        })
        try:
            m_edges = json.loads(self._clean_json(m_edges_res)).get("data", {}).get("edges", [])
        except:
            m_edges = []
            
        categories = [e.get("to_id") for e in m_edges if "Category" in e.get("to_type", "")]
        
        return self._add_evidence(
            "get_merchant_context",
            "Payment_Transaction -> Merchant -> Merchant_Category",
            [txn_id, merchant_id] + categories,
            {},
            f"Transaction at Merchant {merchant_id}, Categories: {categories}",
            "DIRECT"
        )
        
    def get_graph_algorithms_context(self, txn_id):
        """Executes a dynamic Graph Algorithm via Interpreted GSQL to calculate Card Transaction Velocity."""
        
        graph_name = "HHGOA_Fraud_Official" if self.evaluation_mode == "OFFICIAL_BENCHMARK" else "Transaction_Fraud"
        vt = self.v("Payment_Transaction")
        vc = self.v("Card")
        et = self.e("Card_Send_Transaction")
        
        query = f'''INTERPRET QUERY () FOR GRAPH {graph_name} SYNTAX V2 {{
          SumAccum<INT> @txn_count;
          SumAccum<DOUBLE> @total_amount;
          MaxAccum<DOUBLE> @max_amount;
          
          Start = {{{vt}.*}};
          Txn = SELECT t FROM Start:t WHERE t.id == "{txn_id}";
          
          Cards = SELECT c FROM Txn:t -({et}:e)- {vc}:c;
          
          AllTxns = SELECT t FROM Cards:c -({et}:e)- {vt}:t
                    ACCUM c.@txn_count += 1, 
                          c.@total_amount += t.amount,
                          c.@max_amount += t.amount;
                          
          PRINT Cards[Cards.@txn_count as velocity_count, Cards.@total_amount as velocity_amount, Cards.@max_amount as max_amount];
        }}'''
        
        status, res = self.mcp_caller("tigergraph__run_query", {"query_text": query})
        
        if status != "SUCCESS":
            return self._add_evidence(
                "Card Transaction Velocity (Local Neighborhood Sub-graph Aggregation)",
                "Payment_Transaction -> Card -> Payment_Transaction",
                [str(txn_id)],
                {},
                "Graph algorithm execution failed or data is unavailable.",
                "UNAVAILABLE",
                source="TigerGraph_GraphAlgorithm"
            )
            
        try:
            res_data = json.loads(self._clean_json(res))
            # Handle standard REST format or MCP returned format
            if "data" in res_data:
                res_content = res_data["data"]
            else:
                res_content = res_data
                
            results = res_content.get("result", [])
            cards_list = results[0].get("Cards", []) if results else []
            
            if not cards_list:
                raise ValueError("No algorithm results returned.")
                
            attrs = cards_list[0].get("attributes", {})
            v_count = attrs.get("velocity_count", 0)
            v_amount = attrs.get("velocity_amount", 0.0)
            v_max = attrs.get("max_amount", 0.0)
            
            finding = f"The graph algorithm executed a neighborhood velocity analysis and identified {v_count} connected transactions with a total aggregated value of ${v_amount:,.2f}."
            
            return self._add_evidence(
                "Card Transaction Velocity (Local Neighborhood Sub-graph Aggregation)",
                "Payment_Transaction -> Card -> Payment_Transaction",
                [str(txn_id)],
                {"velocity_count": v_count, "velocity_amount": v_amount, "max_amount": v_max},
                finding,
                "DIRECT",
                source="TigerGraph_GraphAlgorithm"
            )
        except Exception as e:
            return self._add_evidence(
                "Card Transaction Velocity (Local Neighborhood Sub-graph Aggregation)",
                "Payment_Transaction -> Card -> Payment_Transaction",
                [str(txn_id)],
                {},
                "Graph algorithm execution failed or data is unavailable.",
                "UNAVAILABLE",
                source="TigerGraph_GraphAlgorithm"
            )

    def get_party_device_ip_context(self, txn_id):
        """C & D: Transaction -> Card -> Party -> Device/IP"""
        # We need the card first.
        card_ev = self.get_transaction_context(txn_id)
        entities = card_ev.get("entities", [])
        if len(entities) < 2:
            return self._add_evidence("get_party_device_ip_context", f"Transaction->{self.v('Card')}->{self.v('Party')}", [txn_id], {}, "Cannot traverse, no Card found.", "UNAVAILABLE")
            
        card_id = entities[1] # the second entity is Card
        
        status, p_edges_res = self.mcp_caller("tigergraph__get_node_edges", {
            "vertex_type": self.v("Card"),
            "vertex_id": str(card_id),
        })
        try:
            p_edges = json.loads(self._clean_json(p_edges_res)).get("data", {}).get("edges", [])
        except:
            p_edges = []
            
        party_id = None
        for e in p_edges:
            if e.get("from_type") == self.v("Party"):
                party_id = e.get("from_id")
            elif e.get("to_type") == self.v("Party"):
                party_id = e.get("to_id")
                
        if not party_id:
            return self._add_evidence("get_party_device_ip_context", f"{self.v('Card')} -> {self.v('Party')}", [card_id], {}, "No Party linked to Card", "INDIRECT")
            
        # Get Devices, IPs
        if self.evaluation_mode == "OFFICIAL_BENCHMARK":
            status, txn_edges_res = self.mcp_caller("tigergraph__get_node_edges", {
                "vertex_type": self.v("Payment_Transaction"),
                "vertex_id": str(txn_id)
            })
            try:
                txn_edges = json.loads(self._clean_json(txn_edges_res)).get("data", {}).get("edges", [])
            except:
                txn_edges = []
            devices = [e.get("to_id") for e in txn_edges if e.get("to_type") == self.v("Device")]
            ips = []
        else:
            status, party_edges_res = self.mcp_caller("tigergraph__get_node_edges", {
                "vertex_type": self.v("Party"),
                "vertex_id": party_id
            })
            try:
                party_edges = json.loads(self._clean_json(party_edges_res)).get("data", {}).get("edges", [])
            except:
                party_edges = []
                
            devices = [e.get("to_id") for e in party_edges if e.get("to_type") == self.v("Device")]
            ips = [e.get("to_id") for e in party_edges if e.get("to_type") == self.v("IP")]
        
        return self._add_evidence(
            "get_party_device_ip_context",
            "Transaction -> Card -> Party -> Device/IP",
            [txn_id, card_id, party_id] + devices + ips,
            {},
            f"Party {party_id} has Devices: {devices}, IPs: {ips}",
            "DIRECT"
        )
        
    def get_closed_case_context(self, txn_id):
        """E: Transaction -> ClosedCase"""
        if self.evaluation_mode == "OFFICIAL_BENCHMARK":
            status, edges_res = self.mcp_caller("tigergraph__get_node_edges", {
                "vertex_type": self.v("Payment_Transaction"),
                "vertex_id": str(txn_id)
            })
            try:
                edges = json.loads(self._clean_json(edges_res)).get("data", {}).get("edges", [])
            except:
                edges = []
                
            cases = [e.get("to_id") for e in edges if e.get("to_type") == "O_ClosedCase" or e.get("from_type") == "O_ClosedCase"]
            if not cases:
                # check reverse edge explicitly
                cases = [e.get("from_id") for e in edges if e.get("from_type") == "O_ClosedCase"]
                if not cases:
                    cases = [e.get("to_id") for e in edges if e.get("e_type") == "O_INVOLVED_IN_REVERSE" or e.get("e_type") == "O_INVOLVED_IN"]
            
            if cases:
                return self._add_evidence(
                    "get_closed_case_context",
                    f"{self.v('Payment_Transaction')} <- O_INVOLVED_IN - O_ClosedCase",
                    [txn_id] + cases,
                    {},
                    f"Transaction {txn_id} is linked to historical closed cases: {cases}",
                    "DIRECT"
                )
        return None
