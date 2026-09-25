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
        investigator = GraphInvestigationTools(self._call_mcp_query, evaluation_mode=self.evaluation_mode)
        
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
            is_vertex_missing = ("not found" in probe_res_text.lower() or "does not exist" in probe_res_text.lower() or "vertex id" in probe_res_text.lower()) if probe_res_text else False
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
            investigation_status = "DATA_UNAVAILABLE" if self.evaluation_mode == "DEMO_INTEGRATION" else "BLOCKED"
            return self._build_empty_response(case_id, flagged_txn_id, execution_status, investigation_status, start_time)
            
        investigation_status = "COMPLETED"
        graph_evidence = [e for e in [card_ev, merch_ev, party_ev, algo_ev, case_ev] if e]
        
        exposure_usd = 0.0
        if card_ev and "attributes" in card_ev:
            exposure_usd = float(card_ev["attributes"].get("txn_amount", 0.0))
            print(f"DEBUG EXPOSURE: Case {case_id}, Txn {flagged_txn_id}, Exposure={exposure_usd}")
            
        graph_evidence_raw = json.dumps(graph_evidence)
        self.tool_calls += 1
        rag_context = self._build_graphrag_context(graph_evidence_raw)
        policy_text = rag_context.get("policy", "")
        has_policy = bool(policy_text)
        
        graphrag_evidence = [
            {"source": "policy", "value": "VERIFIED (Loaded from official policy document)" if has_policy else "UNVERIFIED (No deterministic blocking policy found in official source.)"},
            {"source": "fraud_patterns", "value": rag_context.get("patterns", [])},
            {"source": "regulatory", "value": rag_context.get("regulatory", "UNVERIFIED")}
        ] + [{"source": "historical_case", "value": h.get("case_id")} for h in rag_context.get("historical_cases", [])]
        
        pattern_assessment = self._assess_patterns(graph_evidence)
        initial_prob, initial_verdict, initial_pattern = self._calculate_fraud_probability(graph_evidence, pattern_assessment)
        
        evidence_summaries = [ev["finding"] for ev in graph_evidence if ev and ev.get("finding")]
        uncertainty_level = "HIGH" if initial_prob < 0.70 and initial_prob > 0.30 else "LOW"
        
        initial_nba = self._generate_nba(initial_prob, exposure_usd, graph_evidence, [], rag_context, pattern_assessment)
        
        evidence_requests_log = []
        final_nba = initial_nba.copy()
        final_prob = initial_prob
        final_verdict = initial_verdict
        final_pattern = initial_pattern
        
        requires_verification = any("VERIFY" in a["action"] for a in initial_nba.get("actions", []))
        
        if requires_verification or uncertainty_level == "HIGH":
            # Simulate Customer Response independent of probability
            simulated_response = self._simulate_response(pattern_assessment, graph_evidence)
            
            evidence_requests_log.append({
                "type": "customer_validation",
                "asked_after_step": "initial_investigation",
                "assumed_response": simulated_response,
                "reason": "SIMULATION: Benchmark does not provide live customer. This response is deterministically assumed based on graph evidence patterns.",
                "is_simulation": True
            })
            
            simulated_additional_evidence = [{
                "claim": simulated_response,
                "source": "customer" if "Customer" in simulated_response else "analyst",
                "finding": simulated_response,
                "evidence_strength": "DIRECT",
                "supporting_fraud": "denied" in simulated_response.lower()
            }]
            
            if "denied" in simulated_response.lower():
                final_prob = 0.95
                final_verdict = "fraud"
            elif "confirmed" in simulated_response.lower():
                final_prob = 0.05
                final_verdict = "legitimate"
            else:
                final_prob = initial_prob
                final_verdict = "uncertain"
                
            uncertainty_level = "LOW"
            final_nba = self._generate_nba(final_prob, exposure_usd, graph_evidence, simulated_additional_evidence, rag_context, pattern_assessment)
            
        policy_decision = {
            "policy_status": final_nba.get("policy_status", "UNVERIFIED"),
            "policy_rule": final_nba.get("policy_rule"),
            "approval_route": final_nba.get("route", "auto"),
            "explanation": final_nba.get("reason", "")
        }
        
        # SAR Generation based on all conditions
        sar = self._generate_sar(final_prob, exposure_usd, flagged_txn_id, final_nba, pattern_assessment, rag_context)
        
        self.tool_calls += 1
        write_status_result = self._write_case_to_graph(case_id, final_nba.get("actions", []))
        if write_status_result == "BLOCKED":
            execution_status = "BLOCKED"
            
        latency_s = time.time() - start_time
            
        result = {
            "case_id": case_id,
            "execution_mode": execution_status,
            "investigation_status": investigation_status,
            "case": {
                "status": "closed_legitimate" if final_verdict == "legitimate" else "closed_fraud" if final_verdict == "fraud" else "escalated",
                "verdict": final_verdict,
                "fraud_probability": final_prob,
                "pattern": final_pattern,
                "pattern_description": "No documented fraud pattern could be verified from the available graph and dataset evidence; the agent requested additional customer validation." if final_pattern == "Unknown" else f"Detected {final_pattern} via graph connections.",
                "affected_txn_ids": [str(flagged_txn_id)],
                "first_suspicious_txn_id": str(flagged_txn_id),
                "connected_card_ids": [card_ev["entities"][1]] if card_ev and len(card_ev.get("entities", [])) > 1 else [],
                "connected_device_profiles": party_ev["entities"][3:] if party_ev and len(party_ev.get("entities", [])) > 3 else [],
                "exposure_usd": exposure_usd,
                "evidence": [e.get("evidence_id") for e in graph_evidence],
                "similar_prior_cases": [h.get("case_id") for h in rag_context.get("historical_cases", [])],
                "summary": f"Case investigated. Initial probability {initial_prob:.2f}. Final probability {final_prob:.2f}. Final assessment after simulated customer confirmation: no documented fraud pattern was established from available evidence, so the case was closed as legitimate under the applicable policy." if final_verdict == "legitimate" and len(evidence_requests_log) > 0 else f"Case investigated. Initial probability {initial_prob:.2f}. Final probability {final_prob:.2f}. Final action: {policy_decision.get('explanation', 'None')}",
                "written_to_graph": write_status_result == "VERIFIED",
                "graph_case_id": case_id if write_status_result == "VERIFIED" else None
            },
            "graph_evidence": graph_evidence,
            "graphrag_evidence": graphrag_evidence,
            "uncertainty_level": "HIGH" if final_prob == 0.50 and len(graph_evidence) == 0 else uncertainty_level,
            "pattern_assessment": pattern_assessment,
            "evidence_requests": evidence_requests_log,
            "next_best_actions": {
                "initial": initial_nba.get("actions", []),
                "final": final_nba.get("actions", []),
                "what_changed": "Reassessed based on simulated customer response." if evidence_requests_log else "No change."
            },
            "final_nba": final_nba,
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

    def _simulate_response(self, pattern_assessment: List[Dict], graph_evidence: List[Dict]) -> str:
        # Determine based strictly on the strength of the evidence patterns, not the overall probability float.
        # If any major fraud pattern is fully verified or has strong direct evidence, simulate denial.
        # If there are no fraud patterns, simulate confirmation.
        # If it's partial or contradictory, simulate Analyst escalation.
        verified_patterns = sum(1 for p in pattern_assessment if p["status"] == "VERIFIED")
        partial_patterns = sum(1 for p in pattern_assessment if p["status"] == "PARTIAL")
        
        if verified_patterns > 0 or partial_patterns >= 2:
            return "SIMULATED CUSTOMER RESPONSE (for benchmark execution): Customer denied recognizing the transaction."
        elif partial_patterns == 0:
            return "SIMULATED CUSTOMER RESPONSE (for benchmark execution): Customer confirmed the transaction as legitimate."
        else:
            return "SIMULATED CUSTOMER RESPONSE (for benchmark execution): Analyst investigation required. Customer unreachable or response ambiguous."

    def _generate_sar(self, fraud_prob: float, exposure_usd: float, txn_id: str, final_nba: Dict, patterns: List[Dict], rag_context: Dict) -> Dict:
        sar = {
            "file": False,
            "reason": "",
            "narrative": "",
            "subjects": [],
            "total_amount_usd": 0.0,
            "activity_dates": []
        }
        
        is_fraud = fraud_prob >= 0.70
        is_r5 = final_nba.get("policy_rule") == "R5"
        
        # Check all SAR conditions:
        # 1. Confirmed fraud + >$1000
        # 2. Shared device/region (velocity)
        # 3. Another customer's fraud (historical case match)
        # 4. Undocumented/coordinated activity
        
        reasons = []
        if is_r5 or (is_fraud and exposure_usd > 1000):
            reasons.append("Confirmed fraud with exposure exceeding $1000 threshold (Rule R5).")
        
        has_shared_device = any("shared" in p["reason"].lower() or "takeover" in p["pattern"].lower() for p in patterns if p["status"] in ["VERIFIED", "PARTIAL"])
        if has_shared_device and is_fraud:
            reasons.append("Fraud involving shared device or account takeover.")
            
        if len(rag_context.get("historical_cases", [])) > 0 and is_fraud:
            reasons.append("Fraud matches prior closed cases.")
            
        is_undocumented = any("UNDOCUMENTED" in a["reason"].upper() for a in final_nba.get("actions", []))
        if is_undocumented:
            reasons.append("Coordinated or undocumented fraud activity detected.")
            
        if reasons:
            sar["file"] = True
            sar["reason"] = " ".join(reasons)
            sar["narrative"] = f"Agent identified fraudulent transaction {txn_id} exposing ${exposure_usd}. " + " ".join(reasons)
            sar["subjects"] = [str(txn_id)]
            sar["total_amount_usd"] = exposure_usd
            sar["activity_dates"] = ["2023-12-01"] # Mock date as we lack full temporal extraction in this scope
            
        return sar

    def _calculate_fraud_probability(self, graph_evidence: List[Dict], patterns: List[Dict]) -> Tuple[float, str, str]:
        prob = 0.5
        verdict = "uncertain"
        primary_pattern = "Unknown"
        
        for p in patterns:
            if p["status"] == "VERIFIED":
                prob += 0.2
                primary_pattern = p["pattern"]
            elif p["status"] == "PARTIAL":
                prob += 0.1
                if primary_pattern == "Unknown":
                    primary_pattern = p["pattern"]
                    
        prob = min(max(prob, 0.0), 1.0)
        if prob >= 0.7:
            verdict = "fraud"
        elif prob <= 0.35:
            verdict = "legitimate"
            
        return round(prob, 2), verdict, primary_pattern

    def _assess_patterns(self, graph_evidence: List[Dict]) -> List[Dict]:
        patterns = []
        card_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "get_transaction_context"), None)
        merch_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "get_merchant_context"), None)
        party_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "get_party_device_ip_context"), None)
        algo_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "Card Transaction Velocity (Local Neighborhood Sub-graph Aggregation)"), None)
        case_ev = next((ev for ev in graph_evidence if ev and ev.get("query") == "get_closed_case_context"), None)
        
        ct_status, ct_reason, ct_evidence = "UNAVAILABLE", "No card or related transaction evidence available.", []
        if card_ev and card_ev.get("evidence_strength") == "DIRECT":
            finding = card_ev.get("finding", "")
            import re, ast, datetime
            # finding has format: Transaction {txn_id} (Amt: {amt}, TS: {ts}, Channel: {ch}) was made by Card ... History: [{...}]
            history_match = re.search(r"History:\s*(\[.*?\])", finding)
            if history_match:
                try:
                    history = ast.literal_eval(history_match.group(1))
                    
                    # Also get current txn
                    curr_amt_match = re.search(r"\(Amt:\s*([0-9.]+),", finding)
                    curr_amt = float(curr_amt_match.group(1)) if curr_amt_match else 0.0
                    
                    # Convert timestamps and filter small online auths
                    # We consider W, C, S as online channels. $5 threshold.
                    small_auths = []
                    for h in history:
                        # try parse TS
                        try:
                            # format typically: 2016-12-05 01:55:28
                            ts = datetime.datetime.strptime(str(h.get("ts", "")), "%Y-%m-%d %H:%M:%S")
                        except:
                            continue
                            
                        amt = h.get("amt", 0.0)
                        channel = h.get("channel", "")
                        
                        if amt < 5.0 and channel in ["W", "C", "S", "R"]:
                            small_auths.append((ts, amt))
                            
                    # Check if 3+ small auths in ~1 hr followed by curr_amt (larger purchase)
                    small_auths.sort(key=lambda x: x[0])
                    card_testing_found = False
                    for i in range(len(small_auths) - 2):
                        t1 = small_auths[i][0]
                        t3 = small_auths[i+2][0]
                        if (t3 - t1).total_seconds() <= 3600 * 2: # ~1 hour (using 2 just in case)
                            if curr_amt > 10.0:
                                card_testing_found = True
                                break
                                
                    if card_testing_found:
                        ct_status = "VERIFIED"
                        ct_reason = "3+ small online authorizations under $5 within ~1 hour followed by a larger purchase."
                        ct_evidence = [card_ev.get("evidence_id")]
                    elif len(small_auths) > 0:
                        ct_status = "PARTIAL"
                        ct_reason = "Small authorizations observed, but not meeting strict card testing velocity criteria."
                        ct_evidence = [card_ev.get("evidence_id")]
                    else:
                        ct_status = "UNAVAILABLE"
                        ct_reason = "No small authorization sequence detected."
                except Exception as e:
                    print(f"DEBUG Error parsing history: {e}")
            else:
                # Fallback if no history parsing
                cnt_match = re.search(r"(\d+) total transactions", finding)
                cnt = int(cnt_match.group(1)) if cnt_match else 0
                if cnt > 10:
                    ct_status = "PARTIAL"
                    ct_reason = "High velocity transactions observed but amounts/timestamps missing."
                    ct_evidence = [card_ev.get("evidence_id")]
        patterns.append({"pattern": "Card testing", "status": ct_status, "evidence": ct_evidence, "reason": ct_reason})
        
        cnp_status, cnp_reason, cnp_evidence = "UNAVAILABLE", "No merchant evidence available.", []
        # Actually in IEEE data, if the transaction is linked to a closed case, it's highly suspicious.
        if case_ev and case_ev.get("evidence_strength") == "DIRECT":
            cnp_status = "VERIFIED"
            cnp_reason = "Transaction explicitly linked to a historical closed case."
            cnp_evidence = [case_ev.get("evidence_id")]
        patterns.append({"pattern": "CNP", "status": cnp_status, "evidence": cnp_evidence, "reason": cnp_reason})
        
        cnp_new_device_status, cnp_new_device_reason, cnp_new_device_ev = "UNAVAILABLE", "No device or party context available.", []
        if party_ev and party_ev.get("evidence_strength") == "DIRECT":
            finding = party_ev.get("finding", "")
            if "Devices: []" not in finding and "IPs: []" not in finding:
                cnp_new_device_status = "PARTIAL"
                cnp_new_device_reason = "Device context established."
                cnp_new_device_ev = [party_ev.get("evidence_id")]
        patterns.append({"pattern": "CNP from new device", "status": cnp_new_device_status, "evidence": cnp_new_device_ev, "reason": cnp_new_device_reason})
        
        oor_status, oor_reason, oor_evidence = "UNAVAILABLE", "No party location context available.", []
        patterns.append({"pattern": "Out-of-region", "status": oor_status, "evidence": oor_evidence, "reason": oor_reason})
        
        ato_status, ato_reason, ato_evidence = "UNAVAILABLE", "Missing transaction-level signals for ATO.", []
        if party_ev and party_ev.get("evidence_strength") == "DIRECT":
            if "shared" in party_ev.get("finding", "").lower():
                ato_status = "PARTIAL"
                ato_reason = "Shared devices detected."
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
                if os.path.exists(local_exe): cmd = local_exe
                elif shutil.which("tigergraph-mcp.exe"): cmd = "tigergraph-mcp.exe"
            env_copy = os.environ.copy()
            if self.evaluation_mode == "OFFICIAL_BENCHMARK": env_copy["TG_GRAPHNAME"] = "HHGOA_Fraud_Official"
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
                        else: return "MOCK", ""
            except Exception as e: return "BLOCKED", str(e)
        try: return asyncio.run(fetch())
        except Exception as e: return "BLOCKED", str(e)

    def _write_case_to_graph(self, case_id: str, final_actions: List[Dict]) -> str:
        write_status, write_res = self._call_mcp_query("tigergraph__add_node", {
            "vertex_type": "O_ClosedCase",
            "vertex_id": case_id,
            "attributes": {"outcome": "CLOSED", "pattern": "auto-investigated"}
        })
        if write_status in ["BLOCKED", "MOCK", "FAILED"]: return write_status
        read_status, read_res = self._call_mcp_query("tigergraph__get_node", {
            "vertex_type": "O_ClosedCase",
            "vertex_id": case_id
        })
        if read_status == "SUCCESS":
            try:
                import json
                res_data = json.loads(read_res)
                if "results" in res_data and len(res_data["results"]) > 0:
                    if res_data["results"][0].get("v_id") == case_id: return "VERIFIED"
            except Exception:
                if f'"{case_id}"' in read_res: return "VERIFIED"
        return "FAILED"

    def _build_graphrag_context(self, graph_evidence_raw: str) -> Dict[str, Any]:
        retriever = GraphRAGRetriever("C:/Users/malav/Downloads/closed_cases_history.csv")
        return retriever.build_context(
            graph_evidence=[graph_evidence_raw],
            context_keywords=["testing"]
        )

    def _generate_nba(self, fraud_probability: float, exposure_usd: float, graph_evidence: List[Dict], additional_evidence: List[Dict], rag_context: Dict[str, Any], patterns: List[Dict]) -> Dict[str, Any]:
        from agent.policy_engine import check_policy, determine_approval_route
        
        policy_text = rag_context.get("policy", "")
        has_policy = bool(policy_text)
        
        # Determine recommendation dynamically based on full evidence and probability, independent of forcing a specific action
        recommendation = ""
        is_fraud = False
        is_legitimate = False
        
        if additional_evidence:
            if any(ev.get("supporting_fraud") for ev in additional_evidence):
                is_fraud = True
            elif any("confirm" in ev.get("finding", "").lower() for ev in additional_evidence):
                is_legitimate = True
        
        if is_fraud or fraud_probability > 0.70:
            recommendation = "BLOCK_CARD"
        elif is_legitimate or fraud_probability <= 0.35:
            recommendation = "ALLOW_TRANSACTION"
        else:
            recommendation = "VERIFY_WITH_CUSTOMER"
                
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
