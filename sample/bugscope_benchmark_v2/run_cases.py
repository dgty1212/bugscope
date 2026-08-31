#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL="http://127.0.0.1:8000"
def req(method,path,payload=None):
    body=None; headers={}
    if payload is not None:
        body=json.dumps(payload).encode("utf-8"); headers["Content-Type"]="application/json"
    r=urllib.request.Request(BASE_URL+path,data=body,headers=headers,method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            text=resp.read().decode("utf-8"); return json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        text=e.read().decode("utf-8",errors="replace"); raise RuntimeError(f"{method} {path} failed: {e.code}\n{text}") from e
def main():
    if len(sys.argv)<2: raise SystemExit("Usage: python run_cases.py <PROJECT_ID> [vector|hybrid]")
    pid=int(sys.argv[1]); mode=sys.argv[2] if len(sys.argv)>=3 else "hybrid"
    if mode not in {"vector","hybrid"}: raise SystemExit("mode must be vector or hybrid")
    cases=json.loads((Path(__file__).resolve().parent/"cases.json").read_text(encoding="utf-8")); ids=[]
    for i,c in enumerate(cases,1):
        print(f"[{i}/{len(cases)}] {c['difficulty'].upper()} - {c['title']}")
        a=req("POST",f"/projects/{pid}/analyze",{"error_log":c["error_log"],"situation":c["situation"],"top_k":5,"retrieval_mode":mode})
        did=a["debug_case_id"]; ids.append(did)
        req("PATCH",f"/projects/{pid}/debug-cases/{did}",{"actual_cause":c["actual_cause"],"expected_file":c["expected_file"],"expected_symbol":c["expected_symbol"],"resolved":True,"user_score":5.0})
    print("\nRetrieval evaluation\n")
    ev=req("POST",f"/projects/{pid}/evaluations/retrieval",{"limit":100})
    print(json.dumps(ev,ensure_ascii=False,indent=2)); print("\nCreated debug_case_ids:",ids)
if __name__=="__main__": main()
