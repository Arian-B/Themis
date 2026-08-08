"""
scripts/run_pipeline.py — Convenience runner for the corpus ingestion pipeline.

Runs the Dagster corpus_ingestion_job directly from Python without needing
the full Dagster CLI. Useful for:
  - Quick local testing without starting dagster-webserver
  - CI dry-run (set PIPELINE_DRY_RUN=1 to skip Ollama/Qdrant calls)
  - Debugging individual assets

Usage:
  # Full run (requires Ollama running + QDRANT_URL set):
  python scripts/run_pipeline.py

  # Dry run (validates code path without Ollama/Qdrant):
  PIPELINE_DRY_RUN=1 python scripts/run_pipeline.py

  # Validate only (ingest + GX check, skip embedding):
  PIPELINE_DRY_RUN=1 python scripts/run_pipeline.py --validate-only

  # Via Dagster CLI (alternative):
  dagster job execute -m pipelines.definitions -j corpus_ingestion_job
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).parents[1]))

# Load .env before importing Dagster (resources read env vars at import time)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Themis corpus ingestion pipeline")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run ingest + GX validation only (skip embedding and Qdrant load)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Ollama embedding and Qdrant upsert (overrides PIPELINE_DRY_RUN env var)",
    )
    args = parser.parse_args()

    if args.dry_run or args.validate_only:
        os.environ["PIPELINE_DRY_RUN"] = "1"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    from dagster import DagsterInstance, materialize
    from pipelines.assets import (
        chunk_and_embed_corpus,
        ingest_corpus,
        load_corpus_to_qdrant,
        validate_corpus,
    )
    from pipelines.resources import OllamaConfig, PipelineConfig, QdrantResource

    resources = {
        "qdrant": QdrantResource(),
        "ollama": OllamaConfig(),
        "pipeline_config": PipelineConfig(dry_run=os.getenv("PIPELINE_DRY_RUN") == "1"),
    }

    assets_to_run = [ingest_corpus, validate_corpus]
    if not args.validate_only:
        assets_to_run += [chunk_and_embed_corpus, load_corpus_to_qdrant]

    instance = DagsterInstance.local_temp()

    logger.info("Starting corpus ingestion pipeline...")
    result = materialize(
        assets=assets_to_run,
        resources=resources,
        instance=instance,
    )

    if result.success:
        logger.info("Pipeline completed successfully.")
        for event in result.all_node_events:
            if hasattr(event, "event_type_value") and "ASSET_MATERIALIZATION" in str(event.event_type_value):
                logger.info("  ✓ %s", event.asset_key)
    else:
        logger.error("Pipeline FAILED. Check logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
