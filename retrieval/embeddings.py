"""
retrieval/embeddings.py — Embedding model abstraction.

All embedding operations go through this module. Switching between local
(Ollama nomic-embed-text) and hosted (OpenAI text-embedding-3-small) requires
only changing the EMBEDDING_PROVIDER env var — no code changes.

Embedding model choices:
  - "ollama"  → nomic-embed-text (768-dim, runs locally, free, good for legal text)
  - "openai"  → text-embedding-3-small (1536-dim, hosted, higher quality)
  Default: "ollama" for local dev; "openai" for production.

Usage:
    embeddings = get_embeddings()  # reads EMBEDDING_PROVIDER from env
    vector = await embeddings.aembed_query("limitation of liability cap")
"""

from __future__ import annotations

import os
from langchain_core.embeddings import Embeddings


def get_embeddings() -> Embeddings:
    """
    Factory: returns the configured LangChain embeddings implementation.
    Reads EMBEDDING_PROVIDER from environment (default: "ollama").
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "ollama")

    if provider == "ollama":
        # TODO (Phase 2): from langchain_ollama import OllamaEmbeddings
        # return OllamaEmbeddings(model="nomic-embed-text", base_url=os.getenv("OLLAMA_URL"))
        raise NotImplementedError("Phase 2: Ollama embeddings not yet configured")

    elif provider == "openai":
        # TODO (Phase 2): from langchain_openai import OpenAIEmbeddings
        # return OpenAIEmbeddings(model="text-embedding-3-small")
        raise NotImplementedError("Phase 2: OpenAI embeddings not yet configured")

    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider!r}. Use 'ollama' or 'openai'.")
