import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
from graph.build import build_graph
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect(".langgraph.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
graph = build_graph(checkpointer)

config = {"configurable": {"thread_id": "ad79b056-4c97-457b-9e25-b71c5e18738e"}}
state = graph.get_state(config)
print("tenant_id:", state.values.get("tenant_id"))
