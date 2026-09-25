import json
import glob
import os

files = sorted(glob.glob('cases/HHG-*.json'))

for f in files:
    with open(f) as fh:
        d = json.load(fh)
    
    cid = d.get('case_id')
    mode = d.get('execution_mode')
    status = d.get('investigation_status')
    verdict = d.get('verdict')
    prob = d.get('fraud_probability')
    
    # Best matching pattern
    patterns = d.get('pattern_assessment', [])
    pattern_name = None
    if patterns:
        for p in patterns:
            if p.get('status') == 'VERIFIED':
                pattern_name = p.get('pattern')
                break
        if not pattern_name and patterns:
            pattern_name = patterns[0].get('pattern')
            
    affected = d.get('affected_txn_ids', [])
    exposure = d.get('exposure_usd')
    ev_count = len(d.get('graph_evidence', []))
    
    ev_reqs = d.get('evidence_requests', [])
    
    # The schema might just have final_nba, let's see if initial_nba exists
    nba = d.get('final_nba', {})
    
    print(f"--- {cid} ---")
    print(f"mode: {mode}")
    print(f"status: {status}")
    print(f"verdict: {verdict}")
    print(f"fraud_prob: {prob}")
    print(f"pattern: {pattern_name}")
    print(f"affected_txns: {affected}")
    print(f"exposure: {exposure}")
    print(f"evidence_count: {ev_count}")
    print(f"evidence_requests: {json.dumps(ev_reqs)}")
    print(f"final_nba: {json.dumps(nba)}")
    print(f"sar_file: {d.get('sar', {}).get('file')}")
    print(f"graph_case_id: {d.get('graph_case_id')}")
    print()

