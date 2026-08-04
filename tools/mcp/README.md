# Themis MCP Tool Contracts

This directory contains MCP (Model Context Protocol) servers that expose tools
to Themis agent nodes and external clients.

## Servers

| Server | Port | Tools |
|---|---|---|
| `retrieval_server.py` | 8001 | `search_corpus`, `query_graph` |
| `kg_server.py` | 8002 | `write_entity`, `write_relationship`, `query_portfolio`, `get_obligations_due` |
| `monitoring_server.py` | 8003 | `fetch_regulation`, `diff_against_contract`, `list_tracked_regulations` |

## Why MCP instead of LangChain @tool?

1. **Protocol-standard**: Any MCP-compatible client can call these tools —
   LangGraph agents, Claude Desktop, n8n MCP nodes, future clients.
2. **Swappable implementation**: Swap Qdrant for Pinecone by changing
   `retrieval_server.py` internals — agent code is untouched.
3. **Separate deployment**: Each MCP server is independently deployable,
   scalable, and testable.
4. **Auto-generated schemas**: Tool input/output schemas are derived from
   Python type hints — always in sync with implementation.

## Transport

- **stdio**: Used when agents call tools via LangGraph's tool-calling mechanism.
- **HTTP SSE**: Used when n8n or external systems call tools over the network.

## Running locally

```bash
# Start all MCP servers (added to docker-compose in Phase 2)
uvicorn tools.mcp.retrieval_server:app --port 8001
uvicorn tools.mcp.kg_server:app --port 8002
uvicorn tools.mcp.monitoring_server:app --port 8003
```
