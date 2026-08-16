import os
import json
from dotenv import load_dotenv
load_dotenv()
from utils.mcp_client import call_mcp_tool

def get_mcp_script(name: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tools", "mcp", name))

def test_retrieval_server_search():
    script = get_mcp_script("retrieval_server.py")
    res = call_mcp_tool(script, "search_corpus", {"query": "warranty", "jurisdiction": "us_generic", "k": 1})
    data = json.loads(res)
    assert isinstance(data, list)

def test_retrieval_server_contract_clauses():
    script = get_mcp_script("retrieval_server.py")
    res = call_mcp_tool(script, "get_contract_clauses", {"contract_id": "fake_id"})
    data = json.loads(res)
    assert "error" in data or "clauses" in data

def test_jurisdiction_router():
    script = get_mcp_script("jurisdiction_router_server.py")
    text = "This agreement shall be governed by the laws of the State of New York."
    res = call_mcp_tool(script, "classify_jurisdiction", {"text": text})
    data = json.loads(res)
    assert isinstance(data, dict)

def test_regulatory_update_server():
    script = get_mcp_script("regulatory_update_server.py")
    res = call_mcp_tool(script, "get_tracked_sources", {"jurisdiction": "uk"})
    data = json.loads(res)
    assert isinstance(data, list)
    assert any("FCA" in item for item in data)
