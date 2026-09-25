import os
import json
import glob
import pyTigerGraph as tg
from dotenv import load_dotenv

load_dotenv()
conn = tg.TigerGraphConnection(
    host=os.environ.get('TG_HOST'),
    graphname='HHGOA_Fraud_Official',
    gsqlSecret=os.environ.get('TG_SECRET')
)
conn.apiToken = conn.getToken(os.environ.get('TG_SECRET'))[0]

print("1. O_Transaction count:", conn.getVertexCount("O_Transaction"))
print("2. O_Customer count:", conn.getVertexCount("O_Customer"))

with open("C:/Users/malav/Downloads/task_4 goa hh/cases/HHG-001.json") as f:
    c = json.load(f)
    print("3. HHG-001 final verdict:", c["case"]["verdict"])
    print("4. HHG-001 fraud_probability:", c["case"]["fraud_probability"])
    print("5. HHG-001 pattern:", c["case"]["pattern"])
    print("6. HHG-001 initial NBA:", [a["action"] for a in c["next_best_actions"]["initial"]])
    print("7. HHG-001 final NBA:", [a["action"] for a in c["final_nba"]["actions"]])
    print("8. HHG-001 evidence_requests:", len(c["evidence_requests"]))
    print("9. HHG-001 what_changed:", c["next_best_actions"]["what_changed"])
    print("10. HHG-001 SAR decision:", c["sar"]["file"], c["sar"]["reason"])
    print("11. HHG-001 graph_case_id:", c["case"]["graph_case_id"])

files = glob.glob("C:/Users/malav/Downloads/task_4 goa hh/cases/*.json")
modes = set()
mappings = set()
valid_schema = True
for f in files:
    with open(f) as fp:
        d = json.load(fp)
        modes.add(d.get("execution_mode"))
        if "mapping_method" in d:
            mappings.add(d.get("mapping_method"))
        if not all(k in d for k in ["case_id", "execution_mode", "case", "evidence_requests", "next_best_actions", "sar", "stop_reason", "tool_calls"]):
            valid_schema = False

print("12. All 20 contain schema:", valid_schema)
print("13. All 20 use OFFICIAL_BENCHMARK:", modes)
print("14. None use DEMO_MAPPING:", mappings)

