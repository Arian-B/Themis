"""
retrieval/vector_store.py — LangChain↔Qdrant abstraction layer.

Provides a per-tenant, per-jurisdiction vector store interface. All Qdrant
operations go through this module — no other code touches the Qdrant client directly.

Key design decisions:
  - Collection naming: "{tenant_id}_{jurisdiction}" (e.g., "acme_us_generic")
    This gives per-tenant isolation without running separate Qdrant instances.
  - Embedding model: abstracted via retrieval/embeddings.py — swap without changing this file.
  - Metadata filtering: every stored chunk carries {tenant_id, jurisdiction, clause_type,
    contract_id, chunk_index} — enables metadata-filtered similarity search.

Public API (to be implemented):
  - similarity_search(query, tenant_id, jurisdiction, k, clause_type_filter) → list[Document]
  - add_documents(docs, tenant_id, jurisdiction) → list[str] (chunk IDs)
  - delete_contract(contract_id, tenant_id) → int (chunks deleted)
  - collection_exists(tenant_id, jurisdiction) → bool
  - create_collection(tenant_id, jurisdiction) → None

Usage (from agents, via MCP tool):
    # Called indirectly via tools/mcp/retrieval_server.py search_corpus tool
    results = await store.similarity_search(
        query="limitation of liability cap",
        tenant_id="acme",
        jurisdiction="us_generic",
        k=5,
    )
"""

from __future__ import annotations

# TODO (Phase 2): Implement using:
#   from langchain_qdrant import QdrantVectorStore
#   from qdrant_client import QdrantClient
#   QdrantClient reads QDRANT_URL from environment

raise NotImplementedError("Phase 2: retrieval/vector_store.py not yet implemented")
