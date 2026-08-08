"""
retrieval/vector_store.py — Qdrant vector store abstraction for Themis.

All Qdrant operations go through this module. No other code imports qdrant-client
directly — this is the single place where collection names, vector config, and
payload filtering are defined.

Collection naming strategy:
  Corpus collections (created by the ingestion pipeline):
    "themis_{jurisdiction}"  →  e.g. "themis_us_generic", "themis_uk"
    These contain the pre-embedded legal corpus (statutes, templates, EDGAR).

  Tenant contract collections (created on first contract upload):
    "{tenant_id}_{jurisdiction}"  →  e.g. "acme_corp_us_generic"
    These contain chunks of a specific tenant's uploaded contracts.

Vector config:
  size     = 768   (nomic-embed-text output dimensionality)
  distance = COSINE

Payload fields stored per point:
  chunk_id, doc_id, source, jurisdiction, document_type, title,
  text, chunk_index, token_count   (+ tenant_id for tenant collections)

Environment variables (from .env):
  QDRANT_URL     — Qdrant Cloud cluster URL
  QDRANT_API_KEY — Qdrant Cloud API key
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# nomic-embed-text dimensionality — must match embedder.py
VECTOR_SIZE = 768

# Corpus jurisdiction → collection name
JURISDICTION_TO_COLLECTION: dict[str, str] = {
    "us_generic": "themis_us_generic",
    "uk":         "themis_uk",
    "us_ca":      "themis_us_ca",
    "eu":         "themis_eu",
}


def _get_client() -> "qdrant_client.QdrantClient":
    """Return a configured Qdrant client from environment variables."""
    try:
        from qdrant_client import QdrantClient
    except ImportError as e:
        raise ImportError(
            "qdrant-client is required. Install with: pip install -e '.[pipeline]'"
        ) from e

    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")

    if not url or not api_key:
        missing = []
        if not url:
            missing.append("QDRANT_URL")
        if not api_key:
            missing.append("QDRANT_API_KEY")
        raise EnvironmentError(
            f"Qdrant Cloud credentials missing: {', '.join(missing)}. "
            "Qdrant Cloud is used exclusively — set QDRANT_URL and QDRANT_API_KEY in your .env file."
        )

    return QdrantClient(url=url, api_key=api_key, timeout=60)



def collection_name_for_jurisdiction(jurisdiction: str) -> str:
    """Return the Qdrant collection name for a given jurisdiction code."""
    return JURISDICTION_TO_COLLECTION.get(jurisdiction, f"themis_{jurisdiction}")


def corpus_collection_name(tenant_id: str, jurisdiction: str) -> str:
    """
    Return the collection name for a tenant's contract collection.
    Corpus (shared) collections use 'themis_' prefix; tenant collections use tenant_id.
    """
    return f"{tenant_id}_{jurisdiction}"


def ensure_corpus_collection(
    jurisdiction: str,
    client: "qdrant_client.QdrantClient | None" = None,
) -> str:
    """
    Ensure the corpus collection for a jurisdiction exists in Qdrant.
    Creates it if it doesn't exist. Idempotent.

    Args:
        jurisdiction: e.g. "us_generic", "uk"
        client:       Optional pre-built client (useful in tests)

    Returns:
        The collection name that was created or confirmed to exist.
    """
    from qdrant_client.models import Distance, VectorParams

    client = client or _get_client()
    name = collection_name_for_jurisdiction(jurisdiction)

    existing = {c.name for c in client.get_collections().collections}
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s (dim=%d)", name, VECTOR_SIZE)
    else:
        logger.debug("Qdrant collection already exists: %s", name)

    return name


def upsert_chunks(
    chunks: list[dict[str, Any]],
    jurisdiction: str,
    batch_size: int = 100,
    client: "qdrant_client.QdrantClient | None" = None,
) -> int:
    """
    Upsert embedded chunks into the Qdrant corpus collection for a jurisdiction.

    Each chunk dict must have an 'embedding' field (added by embedder.embed_chunks).
    The chunk_id is used as the Qdrant point ID (truncated to 32 hex chars → UUID-like).

    Args:
        chunks:     List of chunk dicts with 'embedding' field.
        jurisdiction: e.g. "us_generic" or "uk"
        batch_size: Number of points per upsert call.
        client:     Optional pre-built client.

    Returns:
        Total number of points upserted.

    Raises:
        ValueError: If any chunk is missing the 'embedding' field.
        EnvironmentError: If QDRANT_URL is not set.
    """
    from qdrant_client.models import PointStruct

    if not chunks:
        logger.info("upsert_chunks called with empty chunk list — nothing to do.")
        return 0

    # Validate all chunks have embeddings before starting upsert
    missing = [c.get("chunk_id", "?") for c in chunks if "embedding" not in c]
    if missing:
        raise ValueError(
            f"{len(missing)} chunks are missing 'embedding' field. "
            "Run embedder.embed_chunks() before upsert_chunks(). "
            f"First missing: {missing[0]}"
        )

    client = client or _get_client()
    collection = ensure_corpus_collection(jurisdiction, client)
    total = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        points = [
            PointStruct(
                id=_chunk_id_to_int(chunk["chunk_id"]),
                vector=chunk["embedding"],
                payload={
                    "chunk_id":     chunk["chunk_id"],
                    "doc_id":       chunk["doc_id"],
                    "source":       chunk.get("source", ""),
                    "jurisdiction": chunk.get("jurisdiction", jurisdiction),
                    "document_type": chunk.get("document_type", ""),
                    "title":        chunk.get("title", ""),
                    "text":         chunk["text"],
                    "chunk_index":  chunk.get("chunk_index", 0),
                    "token_count":  chunk.get("token_count", 0),
                },
            )
            for chunk in batch
        ]
        client.upsert(collection_name=collection, points=points)
        total += len(points)
        logger.debug(
            "Upserted batch %d–%d to '%s' (%d points total)",
            i,
            i + len(batch),
            collection,
            total,
        )

    logger.info(
        "Upserted %d chunks into collection '%s'",
        total,
        collection,
    )
    return total


def similarity_search(
    query_vector: list[float],
    jurisdiction: str,
    k: int = 5,
    document_type_filter: str | None = None,
    client: "qdrant_client.QdrantClient | None" = None,
) -> list[dict[str, Any]]:
    """
    Search the corpus collection for nearest neighbours to a query vector.

    Args:
        query_vector:        Embedded query text (same model as corpus embeddings).
        jurisdiction:        e.g. "us_generic" — determines which collection to search.
        k:                   Number of results to return.
        document_type_filter: Optional — restrict to "statute", "contract_exhibit", etc.
        client:              Optional pre-built client.

    Returns:
        List of payload dicts from the nearest-neighbour points, ordered by score.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = client or _get_client()
    collection = collection_name_for_jurisdiction(jurisdiction)

    query_filter = None
    if document_type_filter:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_type",
                    match=MatchValue(value=document_type_filter),
                )
            ]
        )

    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=k,
        query_filter=query_filter,
        with_payload=True,
    )

    return [
        {**hit.payload, "_score": hit.score}
        for hit in results
    ]


def collection_stats(
    jurisdiction: str,
    client: "qdrant_client.QdrantClient | None" = None,
) -> dict[str, Any]:
    """Return collection info dict for monitoring / health checks."""
    client = client or _get_client()
    name = collection_name_for_jurisdiction(jurisdiction)
    info = client.get_collection(name)
    return {
        "collection": name,
        "vectors_count": info.vectors_count,
        "points_count": info.points_count,
        "status": str(info.status),
    }


def _chunk_id_to_int(chunk_id: str) -> int:
    """
    Convert a 32-char hex chunk_id to an integer for use as Qdrant point ID.

    Qdrant accepts either UUID strings or unsigned 64-bit integers as point IDs.
    We use the first 16 hex chars (64 bits) of the SHA-256 chunk_id.
    Collision probability for 14 documents × ~20 chunks = 280 points is negligible.
    """
    return int(chunk_id[:16], 16)
