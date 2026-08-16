from langgraph.graph import StateGraph, START, END
from graph.state import ThemisState

def dummy_node(state: ThemisState):
    return {"risk_analysis_result": []}

builder = StateGraph(ThemisState)
builder.add_node("risk_analysis_agent", dummy_node)
builder.add_edge(START, "risk_analysis_agent")
builder.add_edge("risk_analysis_agent", END)
graph = builder.compile()

initial_state = {"contract_id": "test", "tenant_id": "tenant1", "session_id": "sess1", "raw_text": "text", "errors": []}
print("Initial state risk_analysis_result:", initial_state.get("risk_analysis_result"))
result = graph.invoke(initial_state)
print("Final state risk_analysis_result:", result.get("risk_analysis_result"))
