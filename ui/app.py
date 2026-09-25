import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import json
import os
import glob
from datetime import datetime

st.set_page_config(page_title="TigerGraph Fraud Analyst Command Center", layout="wide")

st.markdown("""
    <style>
    .big-font {
        font-size:24px !important;
        font-weight: bold;
    }
    .risk-high {
        color: #ff4b4b;
        font-weight: bold;
    }
    .risk-med {
        color: #ffa500;
        font-weight: bold;
    }
    .risk-low {
        color: #008000;
        font-weight: bold;
    }
    .card-style {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Fraud Analyst Command Center")

# Dataset Mode Selection
st.sidebar.title("Configuration")
dataset_mode = st.sidebar.radio("Dataset Mode", ["DEMO_INTEGRATION", "OFFICIAL_BENCHMARK"])

if dataset_mode == "DEMO_INTEGRATION":
    st.info("**DEMO_INTEGRATION — Live TigerGraph**  \n*Not official benchmark accuracy*")
    cases_dir = r"c:\Users\malav\Downloads\task_4 goa hh\cases_demo"
else:
    cases_dir = r"c:\Users\malav\Downloads\task_4 goa hh\cases"

# Load cases from JSON
case_files = glob.glob(os.path.join(cases_dir, "*.json"))

cases = []
for cf in case_files:
    try:
        with open(cf, 'r') as f:
            cases.append(json.load(f))
    except:
        pass

if not cases:
    st.warning("No cases found. Run the Benchmark Evaluator first.")
    st.stop()

def get_display_status(c_data):
    if c_data.get('execution_mode') == "BLOCKED_DATASET_MISMATCH":
        return "INVESTIGATION_BLOCKED"
    final_action = (c_data.get('final_nba', {}).get('actions') or [{}])[0].get('action', 'N/A')
    if final_action == "REQUESTED_NOT_AVAILABLE":
        return "EVIDENCE_REQUESTED"
    return c_data.get('investigation_status')

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Active Investigations", "Case Detail", "Graph View"])

if page == "Dashboard":
    st.header("Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Cases", len(cases))
    
    blocked = len([c for c in cases if (c.get('final_nba', {}).get('actions') or [{}])[0].get('action') == 'BLOCK_CARD'])
    allowed = len([c for c in cases if (c.get('final_nba', {}).get('actions') or [{}])[0].get('action') == 'ALLOW_TRANSACTION'])
    needs_verif = len([c for c in cases if (c.get('final_nba', {}).get('actions') or [{}])[0].get('action') == 'REQUESTED_NOT_AVAILABLE'])
    
    col2.metric("Blocked Cards", blocked)
    col3.metric("Allowed Txns", allowed)
    col4.metric("Needs Verification", needs_verif)
    
    avg_evidence = sum(len([ev for ev in c.get('graph_evidence', []) if "Transaction not found" not in ev.get('finding', '')]) for c in cases) / len(cases) if cases else 0
    col5.metric("Avg Substantive Graph Evidence / Case", f"{avg_evidence:.1f}")

    st.subheader("Recent Alerts")
    df = pd.DataFrame([{
        "Case ID": c.get('case_id'),
        "Txn ID": c.get('flagged_txn_id') or c.get('case', {}).get('first_suspicious_txn_id'),
        "Status": get_display_status(c),
        "NBA / Decision State": (c.get('final_nba', {}).get('actions') or [{}])[0].get('action', 'N/A'),
        "Execution Mode": c.get('execution_mode')
    } for c in cases])
    st.dataframe(df, use_container_width=True)

elif page == "Case Detail":
    selected_case = st.sidebar.selectbox("Select Case", [c['case_id'] for c in cases])
    c = next((x for x in cases if x['case_id'] == selected_case), None)
    
    if c:
        txn_id = c.get('flagged_txn_id') or c.get('case', {}).get('first_suspicious_txn_id') or (c.get('case', {}).get('affected_txn_ids') or ["N/A"])[0]
        st.header(f"Case {selected_case} (Txn: {txn_id})")
        
        final_action = (c.get('final_nba', {}).get('actions') or [{}])[0].get('action', 'N/A')
        risk_class = "risk-high" if final_action == 'BLOCK_CARD' else "risk-low" if final_action == 'ALLOW_TRANSACTION' else "risk-med"
        
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**NBA / Decision State:** <span class='{risk_class}'>{final_action}</span>", unsafe_allow_html=True)
        display_status = get_display_status(c)
        col2.markdown(f"**Status:** {display_status}")
        col3.markdown(f"**Execution Mode:** {c.get('execution_mode')}")

        if c.get('execution_mode') in ['REAL', 'OFFICIAL_BENCHMARK']:
            st.subheader("Official Benchmark Results")
            case_info = c.get('case', {})
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Verdict", case_info.get('verdict', 'N/A'))
            col_b.metric("Fraud Probability", case_info.get('fraud_probability', 'N/A'))
            col_c.metric("Pattern", case_info.get('pattern', 'N/A'))
            
            sar = c.get('sar', {})
            st.markdown(f"**SAR Required:** {sar.get('file', False)}")
            st.markdown(f"**SAR Reason:** {sar.get('reason', 'N/A')}")
            st.markdown(f"**Graph Case Memory ID:** `{case_info.get('graph_case_id', 'N/A')}`")
            st.markdown(f"**Stop Reason:** {c.get('stop_reason', 'N/A')}")

        is_official = c.get('execution_mode') in ['REAL', 'OFFICIAL_BENCHMARK']
        
        st.subheader("Uncertainty & Summary")
        if is_official:
            unc_reason = c.get('case', {}).get('summary', 'N/A')
            st.info(unc_reason)
        else:
            unc_reason = c.get('uncertainty', {}).get('reason', 'N/A')
            unc_reason = unc_reason.replace("without verified policy or customer confirmation", "without customer confirmation")
            st.info(unc_reason)
        
        
        col_ev, col_nba = st.columns(2)
        with col_ev:
            if is_official:
                st.subheader("Official Case Evidence & Summary")
                case_data = c.get('case', {})
                st.markdown(f"**Case Summary:** {case_data.get('summary', 'Not available in official benchmark output')}")
                st.markdown(f"**Connected Cards:** {', '.join(case_data.get('connected_card_ids', [])) or 'None'}")
                dev_list = case_data.get('connected_device_profiles', [])
                st.markdown(f"**Connected Devices:** {', '.join(dev_list) if dev_list else 'Not available in official benchmark output'}")
                st.markdown(f"**Evidence Keys:** {', '.join(case_data.get('evidence', [])) or 'None'}")
                st.markdown(f"**Similar Cases:** {', '.join(case_data.get('similar_prior_cases', [])) or 'None'}")
            else:
                st.subheader("Graph Evidence")
                import re
                for ev in c.get('graph_evidence', []):
                    finding_clean = ev.get('finding', '').replace('\\n', '\n')
                    finding_clean = re.sub(r'was made by Card (\d+), which has (\d+) total transactions', r'was associated with Card \1, with a graph community size of \2', finding_clean)
                    finding_clean = re.sub(r'identified (\d+) connected transactions', r'Connected transaction neighborhood: \1', finding_clean)
                    st.markdown(f"- **{ev.get('traversal', 'Node')}**: {finding_clean}")
                
                if c.get('additional_evidence'):
                    st.subheader("Additional Evidence")
                    for ev in c.get('additional_evidence', []):
                        st.markdown(f"- **{ev.get('source')}**: {ev.get('claim')}")

            st.subheader("Fraud Pattern Assessment")
            pattern_list = ['Card testing', 'CNP', 'CNP from new device', 'Out-of-region', 'Account takeover']
            p_assessments = {p.get('pattern'): p for p in c.get('pattern_assessment', [])}
            
            for p_name in pattern_list:
                p_data = p_assessments.get(p_name, {})
                status = p_data.get('status', 'N/A')
                reason = p_data.get('reason', 'N/A')
                ev_list = p_data.get('evidence', [])
                
                status_color = "#008000" if status == "VERIFIED" else "#ff4b4b" if status == "UNAVAILABLE" else "#ffa500"
                st.markdown(f"**{p_name}**: <span style='color:{status_color}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)
                st.markdown(f"*Reason:* {reason}")
                if ev_list:
                    st.markdown(f"*Evidence IDs:* {', '.join(ev_list)}")
                st.write("")

            st.subheader("GraphRAG & Policy Evidence")
            for rag_ev in c.get('graphrag_evidence', []):
                source = rag_ev.get('source', 'Unknown')
                value = rag_ev.get('value', 'N/A')
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                value_clean = str(value).replace('\\n', '\n')
                st.markdown(f"- **{source.replace('_', ' ').title()}**: {value_clean}")
            
            if is_official:
                policy_res = c.get('policy_results', {})
                if policy_res:
                    st.markdown(f"- **Policy Rule**: {policy_res.get('policy_rule', 'N/A')}")
                    st.markdown(f"- **Policy Status**: {policy_res.get('policy_status', 'N/A')}")
                    st.markdown(f"- **Approval Route**: {policy_res.get('approval_route', 'N/A')}")
                else:
                    st.markdown("- **Policy Rule**: Not available in official benchmark output")
                    st.markdown("- **Policy Status**: Not available in official benchmark output")
            else:
                policy_dec = c.get('policy_decision', {})
                p_rule = policy_dec.get('policy_rule', 'N/A')
                p_status = policy_dec.get('policy_status', 'UNVERIFIED')
                st.markdown(f"- **Policy Rule**: {p_rule}")
                st.markdown(f"- **Policy Status**: {p_status}")

        with col_nba:
            st.subheader("Next Best Action")
            st.markdown("**Initial Recommendation:**")
            
            if is_official:
                initial_action = (c.get('next_best_actions', {}).get('initial') or [{}])[0].get('action', 'N/A')
                initial_reason = (c.get('next_best_actions', {}).get('initial') or [{}])[0].get('reason', 'N/A')
            else:
                initial_action = (c.get('initial_nba', {}).get('actions') or [{}])[0].get('action', 'N/A')
                initial_reason = c.get('initial_nba', {}).get('reason', 'N/A')
                if "insufficient" in initial_reason.lower() and "policy rules" in initial_reason.lower():
                    initial_reason = "Available graph evidence is insufficient to establish customer authorization, therefore customer validation is required before taking a final action."
            
            st.markdown(f"- `{initial_action}`")
            st.markdown(f"  *Reason: {initial_reason}*")
            
            st.markdown("---")
            if is_official:
                ev_reqs = c.get('evidence_requests', [])
                req_type = ev_reqs[0].get('type') if ev_reqs else None
                req_reason = ev_reqs[0].get('reason') if ev_reqs else None
            else:
                ev_reqs = None
                req_type = (c.get('evidence_request') or {}).get('type')
                req_reason = (c.get('evidence_request') or {}).get('reason')
                
            if is_official and not ev_reqs:
                pass # Hide section completely
            else:
                if c.get('execution_mode') == 'BLOCKED_DATASET_MISMATCH':
                    st.subheader("ADDITIONAL EVIDENCE")
                else:
                    st.subheader("REQUEST ADDITIONAL EVIDENCE")
                
                if req_type:
                    st.markdown(f"**Evidence type:** {req_type}")
                    st.markdown(f"**Reason:** {req_reason}")
                else:
                    st.markdown("**Evidence type:** None available")
                
            if c.get('execution_mode') == 'BLOCKED_DATASET_MISMATCH':
                st.info("Customer validation unavailable because the benchmark transaction is not present in the connected TigerGraph dataset.")
                display_action = "N/A"
                display_reason = initial_reason
                mem_status = c.get('case_memory_write_status', 'N/A')
            elif is_official and not ev_reqs:
                display_action = (c.get('final_nba', {}).get('actions') or [{}])[0].get('action', 'N/A')
                display_reason = c.get('final_nba', {}).get('reason', 'N/A')
            else:
                st.info("Demo Interaction: Select a simulated customer response to see how the Agent recalculates the NBA.")
                sim_response = st.radio("[Simulated Customer Response]", ["No response", "Customer confirmed", "Customer denied"])
                
                if sim_response == "No response":
                    display_action = "REQUESTED_NOT_AVAILABLE"
                    display_reason = initial_reason
                    mem_status = c.get('case_memory_write_status', 'N/A')
                else:
                    from agent.graph_agent import InvestigationAgent
                    agent = InvestigationAgent(evaluation_mode="DEMO_INTEGRATION")
                    c_input = c.copy()
                    c_input["additional_evidence"] = "Customer confirmed" if sim_response == "Customer confirmed" else "Customer denied"
                    
                    with st.spinner("Agent re-evaluating evidence..."):
                        updated_c = agent.investigate(c_input)
                    
                    display_action = (updated_c.get('final_nba', {}).get('actions') or [{}])[0].get('action', 'N/A')
                    display_reason = updated_c.get('final_nba', {}).get('reason', 'N/A')
                    mem_status = updated_c.get('case_memory_write_status', 'N/A')
                
            st.markdown("### UPDATED CASE")
            st.markdown(f"**NBA / Decision State:** `{display_action}`")
            if "insufficient" in display_reason.lower() and "policy rules" in display_reason.lower() and not is_official:
                display_reason = "Available graph evidence is insufficient to establish customer authorization, therefore customer validation is required before taking a final action."
            st.markdown(f"**Reason:** *{display_reason}*")
            
            if is_official:
                pol_status = c.get('policy_results', {}).get('policy_status')
                if pol_status:
                    st.markdown("**Policy Decision:**")
                    st.markdown(f"- Status: {pol_status}")
            else:
                st.markdown("**Policy Decision:**")
                st.markdown(f"- Status: {c.get('policy_decision', {}).get('policy_status')}")
            
            st.markdown("**Case Memory:**")
            if is_official:
                is_written = c.get('case', {}).get('written_to_graph')
                if is_written:
                    st.markdown("- Write Status: VERIFIED")
                    st.markdown(f"- Graph Case ID: {c.get('case', {}).get('graph_case_id', 'N/A')}")
                else:
                    st.markdown("- Write Status: Not written")
            else:
                st.markdown(f"- Write Status: `{mem_status}`")
elif page == "Active Investigations":
    st.header("Active Investigations")
    
    table_data = []
    for case_data in cases:
        final_nba = (case_data.get('final_nba', {}).get('actions') or [{}])[0].get('action', 'N/A')
        display_nba = "Awaiting Customer Verification" if final_nba == "REQUESTED_NOT_AVAILABLE" else final_nba
        txn_id = case_data.get('flagged_txn_id') or case_data.get('case', {}).get('first_suspicious_txn_id')
        
        table_data.append({
            "Case ID": case_data.get('case_id'),
            "Transaction ID": txn_id,
            "Investigation Status": get_display_status(case_data),
            "Uncertainty": case_data.get('uncertainty', {}).get('level', 'N/A') if 'uncertainty' in case_data else 'N/A',
            "Pattern Assessment": case_data.get('case', {}).get('pattern', 'N/A') if case_data.get('execution_mode') in ['REAL', 'OFFICIAL_BENCHMARK'] else (case_data.get('pattern_assessment', [{}])[0].get('status', 'N/A') if case_data.get('pattern_assessment') else 'N/A'),
            "Evidence Count": 0 if case_data.get('execution_mode') == "BLOCKED_DATASET_MISMATCH" else len(case_data.get('graph_evidence', [])),
            "Evidence Request": len(case_data.get('evidence_requests', [])),
            "NBA / Decision State": display_nba,
            "Execution Mode": case_data.get('execution_mode')
        })
        
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)
    
    selected_investigation = st.selectbox("Open Case Detail", [""] + [c['case_id'] for c in cases])
    if selected_investigation:
        st.info(f"Navigate to the 'Case Detail' tab and select **{selected_investigation}** to view full details.")
            
elif page == "Graph View":
    st.header("Graph Investigation")
    selected_case = st.selectbox("Load Case Context", [c['case_id'] for c in cases])
    c = next((x for x in cases if x['case_id'] == selected_case), None)
    
    if c:
        st.subheader(f"Graph Evidence for {selected_case}")
        
        if c.get('execution_mode') == 'BLOCKED_DATASET_MISMATCH':
            st.warning("No graph relationships available")
            st.info("The benchmark transaction is not present in the connected TigerGraph dataset. No graph traversal or relationship evidence was available for this case.")
            
        nodes_dict = {}
        edges_list = []
        
        txn_id = c.get('flagged_txn_id') or c.get('case', {}).get('first_suspicious_txn_id')
        if txn_id:
            nodes_dict[txn_id] = {"id": txn_id, "label": f"TXN {txn_id}", "color": "#FFA500", "shape": "star", "size": 30, "font": {"size": 14}}
        
        import re
        for ev in c.get('graph_evidence', []):
            finding = ev.get('finding', '')
            
            card_match = re.search(r"Card (\d+)", finding)
            if card_match:
                card_id = card_match.group(1)
                nodes_dict[card_id] = {"id": card_id, "label": f"CARD {card_id}", "color": "#FB7E81", "shape": "box"}
                edges_list.append({"from": txn_id, "to": card_id, "label": "made by"})
                
                related_match = re.search(r"related: \[(.*?)\]", finding)
                if related_match:
                    related_ids = [x.strip(" '\"") for x in related_match.group(1).split(",")]
                    for rid in related_ids:
                        if rid != txn_id:
                            nodes_dict[rid] = {"id": rid, "label": f"TXN {rid}", "color": "#D2E5FF", "shape": "box"}
                            edges_list.append({"from": card_id, "to": rid, "label": "made"})
            
            merch_match = re.search(r"Merchant ([\w\s\-,]+),", finding)
            if merch_match:
                merch_id = merch_match.group(1).strip()
                nodes_dict[merch_id] = {"id": merch_id, "label": f"MERCHANT {merch_id}", "color": "#7BE141", "shape": "box"}
                edges_list.append({"from": txn_id, "to": merch_id, "label": "at merchant"})
                
                cat_match = re.search(r"Categories: \[(.*?)\]", finding)
                if cat_match:
                    cat_ids = [x.strip(" '\"") for x in cat_match.group(1).split(",")]
                    for cid in cat_ids:
                        nodes_dict[cid] = {"id": cid, "label": f"CATEGORY {cid}", "color": "#FFC0CB", "shape": "ellipse"}
                        edges_list.append({"from": merch_id, "to": cid, "label": "in category"})
                        
        nodes_json = json.dumps(list(nodes_dict.values()))
        edges_json = json.dumps(edges_list)
        
        html_code = f'''
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <div id="mynetwork" style="width: 100%; height: 600px; border: 1px solid #444; border-radius: 5px; background-color: #2b2b2b;"></div>
        <script type="text/javascript">
          var nodes = new vis.DataSet({nodes_json});
          var edges = new vis.DataSet({edges_json});
          var container = document.getElementById('mynetwork');
          var data = {{nodes: nodes, edges: edges}};
          var options = {{
            nodes: {{ font: {{ color: '#ffffff' }} }},
            edges: {{ font: {{ color: '#aaaaaa', align: 'middle' }}, arrows: 'to' }},
            physics: {{ stabilization: true, barnesHut: {{ springLength: 200 }} }}
          }};
          var network = new vis.Network(container, data, options);
          network.once('stabilizationIterationsDone', function() {{
              network.fit();
              var focusId = '{txn_id}';
              if (nodes.get(focusId)) {{
                  network.focus(focusId, {{scale: 1.2, animation: true}});
              }}
          }});
        </script>
        '''
        import streamlit.components.v1 as components
        
        st.markdown("""
        **Graph Legend:**
        - 🌟 **Orange Star**: Investigated Transaction
        - 🟦 **Light Blue Box**: Related Transaction
        - 🟥 **Red Box**: Card
        - 🟩 **Green Box**: Merchant
        - ⭕ **Pink Circle**: Merchant Category
        """)
        
        components.html(html_code, height=620)
