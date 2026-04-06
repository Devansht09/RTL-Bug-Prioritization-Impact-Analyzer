import asyncio
import json
from backend.pipeline import run_pipeline

for ex in ["example 2", "example 3"]:
    print(f"--- {ex} ---")
    if ex == "example 2":
        v_path = f"Demo Dataset/example 2/Neural_Tensor_Core.v"
        j_path = f"Demo Dataset/example 2/detected_issues.json"
    else:
        v_path = f"Demo Dataset/example 3/PCIe_Gen5_Controller.v"
        j_path = f"Demo Dataset/example 3/detected_issues.json"
        
    with open(v_path) as f:
        v_code = f.read()
        
    with open(j_path) as f:
        ext_issues = json.load(f)
        
    res_dict = run_pipeline(v_code, ext_issues)
    res = res_dict['results']
    
    high = [r for r in res if r['severity_label'] == 'High']
    med  = [r for r in res if r['severity_label'] == 'Medium']
    low  = [r for r in res if r['severity_label'] == 'Low']
    
    print(f"High: {len(high)}, Med: {len(med)}, Low: {len(low)}")
    for i in high:
        print(f"HIGH: {i['bug_type']} on {i['signal']} (Rule: {i['rule_score']:.2f}, ML: {i['ml_score']:.2f}, Final: {i['final_score']:.2f}, Rank: {i.get('rank', 0)})")
