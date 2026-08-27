import os, sys
sys.path.insert(0, r"d:\Coding\themis")
from dotenv import load_dotenv
load_dotenv(r"d:\Coding\themis\.env")
os.environ.setdefault("ENVIRONMENT", "development")

from api.main import app
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string("checkpoints.sqlite")
config = {"configurable": {"thread_id": "1668ffbb-e61a-4a81-8437-39a56466952e"}}

state = memory.get(config)
print("=== State exists:", state is not None)
if state:
    print("=== Next in tasks list:")
    for task in state.tasks:
        print(" ", task.name, task.status)
    vals = state.values
    keys = list(vals.keys()) if vals else []
    print("=== State keys present:", keys)
    # print each key with truncated summary
    for k in keys:
        v = vals[k]
        if isinstance(v, list):
            print(f"  {k}: len={len(v)}, first sample:")
            if v:
                sample = v[0]
                s = str(sample)[:200]
                print(f"     {s}")
        elif isinstance(v, dict):
            subkeys = list(v.keys())
            print(f"  {k}: subkeys={subkeys}")
            for sk in subkeys:
                sv = v[sk]
                if isinstance(sv, list):
                    print(f"     {sk}: len={len(sv)}")
                else:
                    ss = str(sv)[:150]
                    print(f"     {sk}: {ss}")
        else:
            s = str(v)[:200]
            print(f"  {k}: {s}")
else:
    print("State is None for this thread_id")
