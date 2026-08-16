"""
retrieval/qdrant_retriever.py — LangChain Retriever for Qdrant Cloud.

Embedding strategy:
  - Day 1 used OllamaEmbeddings(nomic-embed-text) → 768-dim vectors stored in Qdrant.
  - For retrieval we need the same embedding space. 
  - EMBEDDING_PROVIDER env var selects the backend:
      "ollama"  (default if Ollama Docker is running) → OllamaEmbeddings
      "local"   (fallback, no Docker needed)          → HuggingFaceEmbeddings with
                nomic-ai/nomic-embed-text-v1 via sentence-transformers (768-dim, matches corpus)
  - The local fallback is zero-cost and runs on CPU.
"""
import os
import logging
from typing import Optional

from langchain_core.retrievers import BaseRetriever
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


def _get_embeddings():
    """
    Return an embeddings instance. Tries Ollama first; falls back to
    sentence-transformers (local CPU, 768-dim, same space as Day 1 corpus).
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "ollama").strip().lower()
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    if provider == "ollama":
        # Try Ollama first; if it fails, fall back to local
        try:
            from langchain_ollama import OllamaEmbeddings
            emb = OllamaEmbeddings(model=embed_model, base_url=ollama_host)
            # Probe with a cheap call to detect connection failure early
            emb.embed_query("ping")
            logger.info("retrieval: using OllamaEmbeddings (%s @ %s)", embed_model, ollama_host)
            return emb
        except Exception as exc:
            logger.warning(
                "retrieval: Ollama unavailable (%s) — falling back to local sentence-transformers", exc
            )

    # Local CPU fallback — nomic-embed-text-v1 via sentence-transformers, 768-dim
    # This matches the 768-dim Cosine collections created by the Day 1 Dagster pipeline.
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings  # older compat

    local_model = os.getenv(
        "LOCAL_EMBED_MODEL",
        "nomic-ai/nomic-embed-text-v1",
    )
    logger.info("retrieval: using local HuggingFaceEmbeddings (%s)", local_model)
    return HuggingFaceEmbeddings(
        model_name=local_model,
        model_kwargs={"trust_remote_code": True},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_retriever(jurisdiction: str = "us_generic", k: int = 4) -> Optional[BaseRetriever]:
    """
    Returns a LangChain Retriever over the Qdrant Cloud collection
    corresponding to the given jurisdiction.
    """
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url or not qdrant_api_key:
        logger.error("Missing QDRANT_URL or QDRANT_API_KEY in environment.")
        return None

    collection_name = f"themis_{jurisdiction}"

    try:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        embeddings = _get_embeddings()

        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
            content_payload_key="text",   # Day 1 pipeline stored text under 'text', not 'page_content'
        )

        logger.info("retrieval: retriever initialized for collection '%s' (k=%d)", collection_name, k)
        return vector_store.as_retriever(search_kwargs={"k": k})

    except Exception as e:
        logger.error("Failed to initialize Qdrant retriever for %s: %s", collection_name, e)
        return None
