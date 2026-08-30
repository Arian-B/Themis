import os, sys
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

print("=== state.values truthy:", bool(state.values))
print("=== state.next (status logic key):", list(state.next))
if state.tasks:
    print(f"=== state.tasks ({len(state.tasks)} total):")
    for task in state.tasks:
        print(f"   name={task.name} status={task.status} id={task.id}")
        if getattr(task, "error", None):
            print(f"     error: {task.error}")
else:
    print("=== state.tasks: EMPTY")

vals = state.values
if not vals:
    print("state.values: EMPTY DICT/NONE")
    sys.exit(0)

keys = list(vals.keys())
print(f"=== VALUES keys ({len(keys)}): {keys}")

for k in keys:
    v = vals[k]
    if isinstance(v, list):
        n = len(v)
        print(f"\n[{k}] list len={n}")
        if n > 0:
            item0 = v[0]
            if isinstance(item0, dict):
                print(f"  first keys: {list(item0.keys())}")
                print(f"  first sample (truncated): {str(item0)[:300]}")
            else:
                s = str(item0)[:200]
                print(f"  first sample: {s}")
    elif isinstance(v, dict):
        subkeys = list(v.keys())
        print(f"\n[{k}] dict subkeys: {subkeys}")
        for sk in subkeys:
            sv = v[sk]
            if isinstance(sv, list):
                print(f"    {sk}: list len={len(sv)}")
            elif isinstance(sv, dict):
                print(f"    {sk}: subkeys={list(sv.keys())[:10]}")
            else:
                ss = str(sv)[:150]
                print(f"    {sk}: {ss}")
    else:
        s = str(v)[:250]
        print(f"\n[{k}] raw: {s}")

conn.close()
