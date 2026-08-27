import os, sys, traceback
sys.path.insert(0, r"d:\Coding\themis")
from dotenv import load_dotenv
load_dotenv(r"d:\Coding\themis\.env")
os.environ.setdefault("ENVIRONMENT", "development")

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.build import build_graph

conn = sqlite3.connect(".langgraph.db", check_same_thread=False, isolation_level=None)
checkpointer = SqliteSaver(conn)
checkpointer.setup()
graph = build_graph(checkpointer=checkpointer)

contract_id = "1668ffbb-e61a-4a81-8437-39a56466952e"
config = {"configurable": {"thread_id": contract_id}}
state = graph.get_state(config)

print("=== Pre-invoke state.next:", list(state.next))
print("=== Pre-invoke extraction clauses:", len((state.values.get("extraction_result") or {}).get("clauses", [])))
print("=== Pre-invoke jurisdiction:", state.values.get("jurisdiction_result"))

# Resume the graph - it will attempt to run risk_analysis_agent next
try:
    res = graph.invoke(None, config)
    print("=== INVOKE SUCCESS!")
    n_risk = len(res.get("risk_analysis_result") or [])
    n_ver = len(res.get("verification_result") or [])
    print(f"   risk_flags={n_risk} verification={n_ver}")
    print(f"   state.next after:", list(state.next))
except Exception as e:
    print(f"=== INVOKE FAILED! Exception: {type(e).__name__}: {e}")
    traceback.print_exc()
    # Re-fetch state after failure to see if anything got saved
    state2 = graph.get_state(config)
    print(f"   state.next after crash:", list(state2.next))
    tasks = list(state2.tasks)
    print(f"   tasks count: {len(tasks)}")
    for task in tasks:
        err = getattr(task, "error", None)
        state_attr = getattr(task, "state", None)
        print(f"     task name={task.name} state={state_attr} error?={err is not None}")
        if err:
            print(f"       ERROR: {err}")

conn.close()
