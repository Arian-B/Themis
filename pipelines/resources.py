"""
pipelines/resources.py — Dagster resources for the Themis corpus ingestion pipeline.

Resources are Dagster's dependency injection mechanism. They wrap external services
(Qdrant, Ollama) and inject configuration from environment variables at runtime,
keeping asset code free of environment-specific wiring.

Resources defined here:
  QdrantResource    — Qdrant Cloud client, configured from QDRANT_URL + QDRANT_API_KEY
  OllamaConfig      — Ollama connection config (host, model) + health check
  EnvConfig         — General environment config (paths, flags)

Usage in assets.py:
    @asset
    def load_to_qdrant(context: AssetExecutionContext, qdrant: QdrantResource, ...) -> None:
        client = qdrant.get_client()
"""

from __future__ import annotations

import os
from pathlib import Path

from dagster import ConfigurableResource, EnvVar


class QdrantResource(ConfigurableResource):
    """Qdrant Cloud client resource."""

    url: str = EnvVar("QDRANT_URL")
    api_key: str = EnvVar("QDRANT_API_KEY")

    def get_client(self) -> "qdrant_client.QdrantClient":
        """Return a configured QdrantClient."""
        from qdrant_client import QdrantClient
        return QdrantClient(url=self.url, api_key=self.api_key, timeout=60)


class OllamaConfig(ConfigurableResource):
    """Ollama connection configuration."""

    host: str = EnvVar("OLLAMA_HOST")
    embed_model: str = EnvVar("OLLAMA_EMBED_MODEL")

    def fetch_available_models(self) -> list[str]:
        """Fetch list of model names from Ollama /api/tags endpoint."""
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.host}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]

    def check_health(self) -> tuple[bool, list[str]]:
        """
        Return (is_healthy, available_models).
        is_healthy is True if Ollama is reachable and embed_model is available
        (matching base model name regardless of tag suffix).
        """
        try:
            models = self.fetch_available_models()
            target_base = self.embed_model.split(":")[0]
            is_available = any(
                m == self.embed_model or m.split(":")[0] == target_base
                for m in models
            )
            return is_available, models
        except Exception:
            return False, []



class PipelineConfig(ConfigurableResource):
    """General pipeline configuration."""

    raw_data_dir: str = str(Path(__file__).parents[1] / "data" / "raw")
    embed_batch_size: int = 32
    chunk_size_tokens: int = 600
    chunk_overlap_tokens: int = 100
    dry_run: bool = False  # If True, skip Qdrant upsert (for testing without Ollama)

    @property
    def raw_data_path(self) -> Path:
        return Path(self.raw_data_dir)
