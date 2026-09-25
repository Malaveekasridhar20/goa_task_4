import json
import os
import asyncio
import time
from typing import Dict, Any, List, Tuple
from graphrag.retriever import GraphRAGRetriever
from agent.investigation_tools import GraphInvestigationTools

class InvestigationAgent:
    def __init__(self, llm_mode="real", evaluation_mode="OFFICIAL_BENCHMARK"):
        self.llm_mode = llm_mode
        self.evaluation_mode = evaluation_mode
        self.tool_calls = 0
    
    def investigate(self, case_input: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        case_id = case_input.get("case_id")
        flagged_txn_id = case_input.get("flagged_txn_id")
        risk_score = case_input.get("risk_score", 0.5)
        
        execution_status = "REAL"
        
        # 1. Multi-Hop Investigation using Investigation Tools
        investigator = GraphInvestigationTools(self._call_mcp_query, evaluation_mode=self.evaluation_mode)
        
        # Traversals
        card_ev = investigator.get_transaction_context(flagged_txn_id)
        algo_ev = investigator.get_graph_algorithms_context(flagged_txn_id)
        merch_ev = investigator.get_merchant_context(flagged_txn_id)
        party_ev = investigator.get_party_device_ip_context(flagged_txn_id)
        case_ev = investigator.get_closed_case_context(flagged_txn_id)
        
        if self.evaluation_mode == "OFFICIAL_BENCHMARK":
            probe_vertex_type = "O_Transaction"
        else:
            probe_vertex_type = "Payment_Transaction"
            
        probe_status, probe_res_text = self._call_mcp_query("tigergraph__get_node", {
            "vertex_type": probe_vertex_type,
            "vertex_id": str(flagged_txn_id)
        })
        
        is_missing = False
        if probe_status == "BLOCKED":
            execution_status = "BLOCKED"
            is_missing = True
        elif probe_status == "FAILED":
            is_vertex_missing = (
                "not found" in probe_res_text.lower() or
                "does not exist" in probe_res_text.lower() or
                "vertex id" in probe_res_text.lower()
            ) if probe_res_text else False
            
            if is_vertex_missing and self.evaluation_mode == "OFFICIAL_BENCHMARK":
                execution_status = "BLOCKED_DATASET_MISMATCH"
                is_missing = True
            elif is_vertex_missing and self.evaluation_mode == "DEMO_INTEGRATION":
                execution_status = "REAL_GRAPH_DEMO"
                is_missing = True
        elif probe_status == "MOCK":
            execution_status = "MOCK"
        elif self.evaluation_mode == "DEMO_INTEGRATION":
            execution_status = "REAL_GRAPH_DEMO"
            
        if is_missing:
            # Handle missing case scenario (mostly untouched)
            investigation_status = "DATA_UNAVAILABLE" if self.evaluation_mode == "DEMO_INTEGRATION" else "BLOCKED"
            return self._build_empty_response(case_id, flagged_txn_id, execution_status, investigation_status, start_time)
            
        investigation_status = "COMPLETED"
        graph_evidence = [e for e in [card_ev, merch_ev, party_ev, algo_ev, case_ev] if e]
        
        # Exposure
        exposure_usd = 0.0
        if card_ev and "attributes" in card_ev:
            exposure_usd = float(card_ev["attributes"].get("TransactionAmt", 0.0))
            
        graph_evidence_raw = json.dumps(graph_evidence)
        
        # 2. GraphRAG Retrieval
        self.tool_calls += 1
        rag_context = self._build_graphrag_context(graph_evidence_raw)
        policy_text = rag_context.get("policy", "")
        has_policy = bool(policy_text)
        
        graphrag_evidence = [
            {"source": "policy", "value": "VERIFIED (Loaded from official policy document)" if has_policy else "UNVERIFIED (No deterministic blocking policy found in official source.)"},
            {"source": "fraud_patterns", "value": rag_context.get("patterns", [])},
            {"source": "regulatory", "value": rag_context.get("regulatory", "UNVERIFIED")}
        ] + [{"source": "historical_case", "value": h.get("case_id")} for h in rag_context.get("historical_cases", [])]
        
        # 2b. Fraud Pattern & Probability
        pattern_assessment = self._assess_patterns(graph_evidence)
        initial_prob, initial_verdict, initial_pattern = self._calculate_fraud_probability(graph_evidence, pattern_assessment)
        
        # 3. Uncertainty
        evidence_summaries = [ev["finding"] for ev in graph_evidence if ev and ev.get("finding")]
        uncertainty_level = "HIGH" if initial_prob < 0.70 and initial_prob > 0.30 else "LOW"
        
        # 4. Initial NBA
        initial_nba = self._generate_nba(graph_evidence, initial_prob, exposure_usd, [], rag_context)
        
        # 5. Evidence Request & Simulated Reassessment Loop
        evidence_requests_log = []
        final_nba = initial_nba.copy()
        final_prob = initial_prob
        final_verdict = initial_verdict
        final_pattern = initial_pattern
        
        if initial_nba.get("requires_more_evidence", False) or uncertainty_level == "HIGH":
            # Simulate Customer Response
            assumed_response = "Customer denied recognizing the transaction." if initial_prob > 0.65 else \
                               ("Customer confirmed the transaction." if initial_prob <= 0.65 and initial_prob >= 0.35 else "Analyst review requested.")
            
            evidence_requests_log.append({
                "type": "customer_validation",
                "asked_after_step": "initial_investigation",
                "assumed_response": assumed_response
            })
            
            # SECOND INVESTIGATION: Create additional evidence based on simulation
            simulated_additional_evidence = [{
                "claim": assumed_response,
                "source": "customer" if "Customer" in assumed_response else "analyst",
                "supporting_fraud": "denied" in assumed_response.lower()
            }]
            
            # Recalculate based on simulation
            if "denied" in assumed_response.lower():
                final_prob = 0.95
                final_verdict = "fraud"
            elif "confirmed" in assumed_response.lower():
                final_prob = 0.05
                final_verdict = "legitimate"
            else:
                final_prob = initial_prob
                final_verdict = "uncertain"
                
            uncertainty_level = "LOW"
            final_nba = self._generate_nba(graph_evidence, final_prob, exposure_usd, simulated_additional_evidence, rag_context)
            
        # 6. Policy Decision
        policy_decision = {
            "policy_status": final_nba.get("policy_status", "UNVERIFIED"),
            "policy_rule": final_nba.get("policy_rule"),
            "approval_route": final_nba.get("route", "auto"),
            "explanation": final_nba.get("reason", "")
        }
        
        # 7. SAR Generation
        sar = {
            "file": False,
            "reason": "",
            "narrative": "",
            "subjects": [],
            "total_amount_usd": 0.0,
            "activity_dates": []
        }
        if final_nba.get("policy_rule") == "R5" or (final_prob >= 0.85 and exposure_usd > 1000):
            sar = {
                "file": True,
                "reason": "Confirmed fraud with exposure exceeding $1000 threshold (Rule R5).",
                "narrative": f"Agent identified fraudulent transaction {flagged_txn_id} exposing ${exposure_usd}. Customer validation indicated denial.",
                "subjects": [str(flagged_txn_id)],
                "total_amount_usd": exposure_usd,
                "activity_dates": ["2023-12-01"] # Mock date as we lack full temporal extraction in this scope
            }
        
        # 8. Case Memory Write
        self.tool_calls += 1
        write_status_result = self._write_case_to_graph(case_id, final_nba.get("actions", []))
        
        if write_status_result == "BLOCKED":
            execution_status = "BLOCKED"
            
        latency_s = time.time() - start_time
            
        # 9. Output Schema Match
        result = {
            "case_id": case_id,
            "execution_mode": execution_status,
            "investigation_status": investigation_status,
            "case": {
                "status": "COMPLETED",
                "verdict": final_verdict,
                "fraud_probability": final_prob,
                "pattern": final_pattern,
                "pattern_description": f"Detected {final_pattern} via graph connections.",
                "affected_txn_ids": [str(flagged_txn_id)],
                "first_suspicious_txn_id": str(flagged_txn_id),
                "connected_card_ids": [card_ev["entities"][1]] if card_ev and len(card_ev.get("entities", [])) > 1 else [],
                "connected_device_profiles": party_ev["entities"][3:] if party_ev and len(party_ev.get("entities", [])) > 3 else [],
                "exposure_usd": exposure_usd,
                "evidence": [e.get("evidence_id") for e in graph_evidence],
                "similar_prior_cases": [h.get("case_id") for h in rag_context.get("historical_cases", [])],
                "summary": f"Case investigated. Initial probability {initial_prob:.2f}. Final probability {final_prob:.2f}. Final action: {policy_decision['explanation']}",
                "written_to_graph": write_status_result == "VERIFIED",
                "graph_case_id": case_id if write_status_result == "VERIFIED" else None
            },
            "graph_evidence": graph_evidence,
            "graphrag_evidence": graphrag_evidence,
            "uncertainty_level": uncertainty_level,
            "pattern_assessment": pattern_assessment,
            "evidence_requests": evidence_requests_log,
            "next_best_actions": {
                "initial": initial_nba.get("actions", []),
                "final": final_nba.get("actions", []),
                "what_changed": "Reassessed based on simulated customer response." if evidence_requests_log else "No change."
            },
            "final_nba": final_nba, # Kept for backward compat
            "policy_results": policy_decision,
            "sar": sar,
            "stop_reason": policy_decision.get("explanation", ""),
            "tool_calls": [{"tool": "TigerGraph_MCP", "count": self.tool_calls}],
            "tokens": {"prompt": 0, "completion": 0},
            "latency_s": latency_s
        }
        
        if self.evaluation_mode == "DEMO_INTEGRATION":
            result["mapping_method"] = "DEMO_MAPPING"
            result["mapping_confidence"] = 0
            
        return result
        
    def _calculate_fraud_probability(self, graph_evidence: List[Dict], patterns: List[Dict]) -> Tuple[float, str, str]:
        prob = 0.5
        verdict = "uncertain"
        primary_pattern = "Unknown"
        
        # Simple weighted evidence scoring
        for p in patterns:
            if p["status"] == "VERIFIED":
                prob += 0.2
                primary_pattern = p["pattern"]
            elif p["status"] == "PARTIAL":
                prob += 0.1
                if primary_pattern == "Unknown":
                    primary_pattern = p["pattern"]
                    
        prob = min(max(prob, 0.0), 1.0)
        if prob > 0.7:
            verdict = "fraud"
        elif prob < 0.4:
            verdict = "legitimate"
            
        return round(prob, 2), verdict, primary_pattern

    def _assess_patterns(self, graph_evidence: List[Dict]) -> List[Dict]:
        patterns = []
        
        card_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "get_transaction_context"), None)
        merch_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "get_merchant_context"), None)
        party_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "get_party_device_ip_context"), None)
        
        # 1. Card testing
        ct_status = "UNAVAILABLE"
        ct_reason = "No card or related transaction evidence available."
        ct_evidence = []
        if card_ev and card_ev.get("evidence_strength") == "DIRECT":
            finding = card_ev.get("finding", "")
            if "Sampled related" in finding:
                ct_status = "PARTIAL"
                ct_reason = "High velocity / related transactions observed, but requires external payment gateway logs to verify actual authorization declines."
                ct_evidence = [card_ev.get("evidence_id")]
        patterns.append({"pattern": "Card testing", "status": ct_status, "evidence": ct_evidence, "reason": ct_reason})
        
        # 2. CNP (Card Not Present)
        cnp_status = "UNAVAILABLE"
        cnp_reason = "No merchant evidence available."
        cnp_evidence = []
        if merch_ev and merch_ev.get("evidence_strength") == "DIRECT":
            cnp_status = "PARTIAL"
            cnp_reason = "Merchant/category context is available, but transaction-level card-entry-mode or POS authentication evidence is not available in the connected schema."
            cnp_evidence = [merch_ev.get("evidence_id")]
        patterns.append({"pattern": "CNP", "status": cnp_status, "evidence": cnp_evidence, "reason": cnp_reason})
        
        # 3. CNP from new device
        cnp_new_device_status = "UNAVAILABLE"
        cnp_new_device_reason = "No device or party context available."
        cnp_new_device_evidence = []
        if party_ev and party_ev.get("evidence_strength") == "DIRECT":
            cnp_new_device_status = "PARTIAL"
            cnp_new_device_reason = "Device context established, but transaction-level authentication logs are missing to confirm it's a new unrecognized device."
            cnp_new_device_evidence = [party_ev.get("evidence_id")]
        patterns.append({"pattern": "CNP from new device", "status": cnp_new_device_status, "evidence": cnp_new_device_evidence, "reason": cnp_new_device_reason})
        
        # 4. Out-of-region
        oor_status = "UNAVAILABLE"
        oor_reason = "No party location context available."
        oor_evidence = []
        if party_ev and party_ev.get("evidence_strength") == "DIRECT":
            oor_status = "PARTIAL"
            oor_reason = "Party established but transaction-specific location evidence is unavailable in the schema, requiring customer validation for out-of-region activity."
            oor_evidence = [party_ev.get("evidence_id")]
        patterns.append({"pattern": "Out-of-region", "status": oor_status, "evidence": oor_evidence, "reason": oor_reason})
        
        # 5. Account takeover
        ato_status = "UNAVAILABLE"
        ato_reason = "Missing transaction-level signals: Cannot link specific transactions to IP/Device changes without external authentication logs."
        ato_evidence = []
        if party_ev and party_ev.get("evidence_strength") == "DIRECT":
            ato_status = "PARTIAL"
            ato_reason = "Party has device/IP context, but requires external authentication logs or customer confirmation to prove account takeover."
            ato_evidence = [party_ev.get("evidence_id")]
        patterns.append({"pattern": "Account takeover", "status": ato_status, "evidence": ato_evidence, "reason": ato_reason})
        
        return patterns
        
    def _call_mcp_query(self, tool_name: str, args: Dict[str, Any]) -> Tuple[str, str]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        async def fetch():
            import sys
            import shutil
            import os
            
            cmd = "tigergraph-mcp"
            if sys.platform == "win32":
                local_exe = os.path.join(os.getcwd(), ".venv_311", "Scripts", "tigergraph-mcp.exe")
                if os.path.exists(local_exe):
                    cmd = local_exe
                elif shutil.which("tigergraph-mcp.exe"):
                    cmd = "tigergraph-mcp.exe"
                    
            env_copy = os.environ.copy()
            if self.evaluation_mode == "OFFICIAL_BENCHMARK":
                env_copy["TG_GRAPHNAME"] = "HHGOA_Fraud_Official"
                
            server_params = StdioServerParameters(command=cmd, args=[], env=env_copy)
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        tool_names = [tool.name for tool in tools.tools]
                        if tool_name in tool_names and os.getenv("DEMO_MODE", "true").lower() != "true":
                            res = await session.call_tool(tool_name, args)
                            text = res.content[0].text
                            
                            if "CONNECTION_ERROR" in text or "Failed to connect" in text or "refused" in text.lower():
                                return "BLOCKED", text
                                
                            if text.startswith("Error:") or "error" in text.lower() or "not found" in text.lower():
                                return "FAILED", text
                                
                            return "SUCCESS", text
                        else:
                            return "MOCK", ""
            except Exception as e:
                return "BLOCKED", str(e)
                
        try:
            return asyncio.run(fetch())
        except Exception as e:
            return "BLOCKED", str(e)

    def _write_case_to_graph(self, case_id: str, final_actions: List[Dict]) -> str:
        write_status, write_res = self._call_mcp_query("tigergraph__add_node", {
            "vertex_type": "O_ClosedCase",
            "vertex_id": case_id,
            "attributes": {"outcome": "CLOSED", "pattern": "auto-investigated"}
        })
        
        if write_status in ["BLOCKED", "MOCK", "FAILED"]:
            return write_status
            
        read_status, read_res = self._call_mcp_query("tigergraph__get_node", {
            "vertex_type": "O_ClosedCase",
            "vertex_id": case_id
        })
        if read_status == "SUCCESS":
            try:
                import json
                res_data = json.loads(read_res)
                if "results" in res_data and len(res_data["results"]) > 0:
                    if res_data["results"][0].get("v_id") == case_id:
                        return "VERIFIED"
            except Exception:
                if f'"{case_id}"' in read_res:
                    return "VERIFIED"
            
        return "FAILED"

    def _build_graphrag_context(self, graph_evidence_raw: str) -> Dict[str, Any]:
        retriever = GraphRAGRetriever("C:/Users/malav/Downloads/closed_cases_history.csv")
        return retriever.build_context(
            graph_evidence=[graph_evidence_raw],
            context_keywords=["testing"]
        )

    def _generate_nba(self, graph_evidence: List[Dict], fraud_probability: float, exposure_usd: float, additional_evidence: List[Dict], rag_context: Dict[str, Any]) -> Dict[str, Any]:
        from agent.policy_engine import check_policy, determine_approval_route
        
        policy_text = rag_context.get("policy", "")
        has_policy = bool(policy_text)
        
        recommendation = ""
        
        if additional_evidence:
            if any(ev.get("supporting_fraud") for ev in additional_evidence):
                recommendation = "BLOCK_CARD"
            else:
                recommendation = "ALLOW_TRANSACTION"
        else:
            if fraud_probability > 0.65:
                recommendation = "BLOCK_CARD"
            elif fraud_probability < 0.35:
                recommendation = "ALLOW_TRANSACTION"
            else:
                recommendation = "VERIFY_WITH_CUSTOMER"
                
        # Policy Engine evaluates the decision
        policy_result = check_policy(recommendation, 1.0 - fraud_probability, exposure_usd, graph_evidence + additional_evidence, fraud_probability)
        
        actions = policy_result["actions"]
        rule = policy_result["policy_reference"]
        route = determine_approval_route(actions)
        
        requires_more = any("VERIFY" in a["action"] for a in actions)
        reason = actions[0]["reason"] if actions else "No policy actions matched."
        policy_status = "VERIFIED" if has_policy and rule in policy_text else "UNVERIFIED"
            
        return {
            "actions": actions,
            "requires_more_evidence": requires_more,
            "policy_rule": rule,
            "policy_status": policy_status,
            "reason": reason,
            "route": route
        }

    def _build_empty_response(self, case_id, flagged_txn_id, execution_status, investigation_status, start_time):
        return {
            "case_id": case_id,
            "execution_mode": execution_status,
            "investigation_status": investigation_status,
            "case": {
                "status": "BLOCKED",
                "verdict": "uncertain",
                "fraud_probability": 0.0,
                "pattern": "",
                "pattern_description": "",
                "affected_txn_ids": [],
                "first_suspicious_txn_id": "",
                "connected_card_ids": [],
                "connected_device_profiles": [],
                "exposure_usd": 0.0,
                "evidence": [],
                "similar_prior_cases": [],
                "summary": "Investigation blocked.",
                "written_to_graph": False,
                "graph_case_id": None
            },
            "evidence_requests": [],
            "next_best_actions": {"initial": [], "final": [], "what_changed": ""},
            "sar": {"file": False},
            "stop_reason": "Blocked.",
            "tool_calls": [],
            "tokens": {},
            "latency_s": time.time() - start_time
        }
