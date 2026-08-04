"""
tools/mcp/retrieval_server.py — MCP server exposing retrieval tools to agent nodes.

Why MCP instead of LangChain @tool?
  MCP (Model Context Protocol) makes the tool layer protocol-standard and
  swappable. Agents call tools via the MCP client SDK, not via LangChain
  internals. This means:
    - The tool implementation can be replaced (e.g., swap Qdrant for Pinecone)
      without touching any agent code.
    - Tools are callable by any MCP-compatible client (LangGraph agents, Claude
      Desktop, n8n MCP nodes) — maximally portable.
    - Tool schemas are auto-generated from Python type hints → OpenAPI compatible.

Tools exposed by this server:
  1. search_corpus(query, tenant_id, jurisdiction, k, clause_type_filter?) → list[Chunk]
     Calls vector_store.similarity_search() with jurisdiction-routed collection.

  2. query_graph(cypher, tenant_id, params?) → list[dict]
     Executes a read-only Cypher query against Neo4j via graph_store.query_portfolio().
     Note: write access to Neo4j goes through kg_server.py, not this server.

Running this server:
  uvicorn tools.mcp.retrieval_server:app --port 8001
  Or via docker-compose (see service: mcp-retrieval)

MCP transport: stdio (for LangGraph tool-calling) or HTTP SSE (for n8n).
"""

from __future__ import annotations

# TODO (Phase 2): Implement using the MCP Python SDK (mcp package).
# Pattern:
#   from mcp.server import Server
#   from mcp.server.models import InitializationOptions
#   server = Server("themis-retrieval")
#
#   @server.list_tools()
#   async def list_tools() -> list[Tool]: ...
#
#   @server.call_tool()
#   async def call_tool(name, arguments) -> list[TextContent]: ...

raise NotImplementedError("Phase 2: retrieval_server MCP server not yet implemented")
