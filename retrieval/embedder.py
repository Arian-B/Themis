"""
retrieval/embedder.py — Batched text embedding via Ollama nomic-embed-text.

Calls the Ollama embeddings API directly (not via LangChain) so the embedding
step can be used in isolation (e.g., during corpus ingestion) without the full
LangChain stack in memory.

API used: POST http://localhost:11434/api/embed
  Input:  {"model": "nomic-embed-text", "input": ["text1", "text2", ...]}
  Output: {"embeddings": [[0.1, 0.2, ...], ...], "model": "...", ...}

nomic-embed-text produces 768-dimensional vectors.
The Qdrant collection is created with size=768, distance=COSINE.

Why direct HTTP instead of langchain-ollama?
  - No LangChain dependency in the data pipeline (keeps pipeline deps minimal)
  - Explicit control over batch size, timeout, and retry logic
  - Easier to swap to OpenAI-compatible embeddings if Ollama is unavailable
    (just point OLLAMA_HOST to a different endpoint)

Environment variables (from .env):
  OLLAMA_HOST       — default "http://localhost:11434"
  OLLAMA_EMBED_MODEL — default "nomic-embed-text"
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# nomic-embed-text output dimensionality
EMBEDDING_DIM = 768

# Batch size: Ollama processes all inputs in one HTTP call, so we cap at 32
# to avoid OOM on the local container and stay within HTTP timeout.
EMBED_BATCH_SIZE = 32

_EMBED_TIMEOUT = 120.0   # seconds per batch request
_RETRY_DELAY   = 2.0     # seconds between retries
_MAX_RETRIES   = 3


def _get_ollama_config() -> tuple[str, str]:
    """Return (ollama_host, embed_model) from environment."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    return host, model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings using Ollama nomic-embed-text.

    Sends texts in batches of EMBED_BATCH_SIZE. Retries up to _MAX_RETRIES
    times on transient HTTP errors before raising.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (one per input text), each of length EMBEDDING_DIM.

    Raises:
        httpx.HTTPError: If Ollama returns a non-2xx status after retries.
        ConnectionError: If Ollama is not reachable.
        ValueError: If the response is malformed or embedding count mismatches.
    """
    if not texts:
        return []

    host, model = _get_ollama_config()
    url = f"{host}/api/embed"
    all_embeddings: list[list[float]] = []

    logger.info(
        "Embedding %d texts via Ollama (%s) in batches of %d",
        len(texts),
        model,
        EMBED_BATCH_SIZE,
    )

    for batch_start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[batch_start : batch_start + EMBED_BATCH_SIZE]
        batch_embeddings = _embed_batch_with_retry(url, model, batch)
        all_embeddings.extend(batch_embeddings)
        logger.debug(
            "Embedded batch %d–%d (%d vectors)",
            batch_start,
            batch_start + len(batch),
            len(batch_embeddings),
        )

    if len(all_embeddings) != len(texts):
        raise ValueError(
            f"Embedding count mismatch: requested {len(texts)}, "
            f"got {len(all_embeddings)}"
        )

    return all_embeddings


def _embed_batch_with_retry(
    url: str,
    model: str,
    batch: list[str],
) -> list[list[float]]:
    """Send one batch to Ollama with retry logic."""
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            return _embed_batch(url, model, batch)
        except (httpx.HTTPError, ConnectionError, ValueError) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    "Embedding attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    _RETRY_DELAY,
                )
                time.sleep(_RETRY_DELAY)
            else:
                logger.error("All %d embedding attempts failed.", _MAX_RETRIES)

    raise RuntimeError(
        f"Failed to embed batch after {_MAX_RETRIES} attempts"
    ) from last_exc


def _embed_batch(url: str, model: str, batch: list[str]) -> list[list[float]]:
    """Send one embedding request to Ollama and parse the response."""
    try:
        with httpx.Client(timeout=_EMBED_TIMEOUT) as client:
            response = client.post(
                url,
                json={"model": model, "input": batch},
            )
            response.raise_for_status()
    except httpx.ConnectError as e:
        raise ConnectionError(
            f"Cannot connect to Ollama at {url}. "
            "Ensure Ollama is running: docker compose up ollama -d"
        ) from e

    data: dict[str, Any] = response.json()

    # Ollama /api/embed returns: {"model": "...", "embeddings": [[...], ...]}
    embeddings = data.get("embeddings")
    if not embeddings:
        raise ValueError(
            f"Ollama response missing 'embeddings' key. Got: {list(data.keys())}"
        )
    if len(embeddings) != len(batch):
        raise ValueError(
            f"Batch size mismatch: sent {len(batch)} texts, "
            f"received {len(embeddings)} embeddings"
        )

    return embeddings


def embed_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add an 'embedding' field to each chunk dict.

    Args:
        chunks: List of chunk dicts (from retrieval/chunker.py).

    Returns:
        Same chunks with 'embedding': list[float] added.
        The original list is NOT mutated — a new list of dicts is returned.
    """
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    return [
        {**chunk, "embedding": embedding}
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]


def check_ollama_health() -> bool:
    """
    Ping Ollama to verify it is running and nomic-embed-text is available.

    Returns:
        True if healthy, False otherwise (does not raise).
    """
    host, model = _get_ollama_config()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{host}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            if model not in models:
                logger.warning(
                    "Ollama is running but model '%s' not found. "
                    "Pull it: docker compose exec ollama ollama pull %s",
                    model,
                    model,
                )
                return False
            return True
    except Exception as exc:
        logger.warning("Ollama health check failed: %s", exc)
        return False
