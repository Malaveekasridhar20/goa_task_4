import os
import json
import glob

def summarize():
    cases_dir = "C:/Users/malav/Downloads/task_4 goa hh/cases"
    files = glob.glob(os.path.join(cases_dir, "*.json"))
    
    total = len(files)
    real = 0
    blocked = 0
    failed = 0
    verified_write = 0
    mock = 0
    missing_evidence = 0
    exceptions = 0
    
    for f in files:
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
                
            mode = data.get("execution_mode", "")
            if mode == "REAL":
                real += 1
            elif mode == "BLOCKED":
                blocked += 1
            elif mode == "MOCK":
                mock += 1
                
            write_status = data.get("case", {}).get("written_to_graph", False)
            if write_status:
                verified_write += 1
            else:
                failed += 1
                
            # If evidence_requests log exists, it means simulation occurred
            if len(data.get("evidence_requests", [])) == 0:
                missing_evidence += 1
                
        except Exception as e:
            exceptions += 1
            
    print("--- 20-CASE SUMMARY ---")
    print(f"Number actually executed: {total}")
    print(f"Number REAL: {real}")
    print(f"Number BLOCKED: {blocked}")
    print(f"Number FAILED (write): {failed}")
    print(f"Number with VERIFIED case-memory write: {verified_write}")
    print(f"Number with MOCK/DEMO execution: {mock}")
    print(f"Number with missing evidence (empty): {missing_evidence}")
    print(f"Number with exceptions: {exceptions}")
    print("-----------------------")

if __name__ == "__main__":
    summarize()
