"""
retrieval/embeddings.py — LangChain Embeddings abstraction for agent use.

All embedding operations that go through LangChain (agent RAG queries, similarity
searches via LangChain's vector store interface) use this module.

For the data ingestion pipeline (chunking + upserting), see retrieval/embedder.py
which uses direct HTTP to Ollama and does NOT depend on LangChain.

Embedding model choices (set EMBEDDING_PROVIDER in .env):
  "ollama"  → nomic-embed-text via langchain-ollama (768-dim, local, free)
  "openai"  → text-embedding-3-small via langchain-openai (1536-dim, hosted)

Default: "ollama"

Usage (in agent retrieval / MCP retrieval server):
    from retrieval.embeddings import get_embeddings
    embeddings = get_embeddings()
    vector = await embeddings.aembed_query("limitation of liability clause")
"""

from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings


def get_embeddings() -> Embeddings:
    """
    Return the configured LangChain Embeddings implementation.
    Reads EMBEDDING_PROVIDER from environment (default: "ollama").

    Raises:
        ValueError: For unknown EMBEDDING_PROVIDER value.
        ImportError: If the required provider package is not installed.
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "ollama")

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings  # type: ignore[import]
        return OllamaEmbeddings(
            model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        )

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings  # type: ignore[import]
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            # OPENAI_API_KEY read automatically from environment
        )

    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER: {provider!r}. "
            "Valid options: 'ollama', 'openai'. Check your .env file."
        )
