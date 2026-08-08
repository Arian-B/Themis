"""
retrieval/corpus/pipeline.py — dlt pipeline wiring for the Themis legal corpus.

Runs all three sources (US statutes, UK statutes, EDGAR contracts) and writes
raw document records to `data/raw/` as JSON Lines files. dlt handles:
  - Incremental state (skips already-loaded docs on re-run via primary_key merge)
  - Schema inference and enforcement
  - Filesystem destination write

Usage:
    python -m retrieval.corpus.pipeline          # standalone run
    # Or via Dagster: pipelines/assets.py asset "ingest_corpus"

Output files:
    data/raw/themis_us_statutes/documents.jsonl
    data/raw/themis_uk_statutes/documents.jsonl
    data/raw/themis_edgar_contracts/documents.jsonl

Each line is a JSON object matching the Document schema in sources.py.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import dlt

from retrieval.corpus.sources import (
    edgar_exhibits_source,
    uk_statutes_source,
    us_statutes_source,
)

logger = logging.getLogger(__name__)

# Where dlt writes raw output files
RAW_DATA_DIR = Path(__file__).parents[2] / "data" / "raw"


def build_pipeline(pipeline_name: str, dataset_name: str) -> dlt.Pipeline:
    """Create a dlt filesystem pipeline targeting data/raw/."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=dlt.destinations.filesystem(str(RAW_DATA_DIR)),
        dataset_name=dataset_name,
        export_schema_path="data/dlt_state",
    )


def run_ingestion() -> dict[str, int]:
    """
    Run all three corpus sources and load to the filesystem destination.

    Returns:
        dict mapping dataset_name → number of documents loaded.
    """
    results: dict[str, int] = {}

    sources = [
        ("themis_us_statutes_pipeline", "themis_us_statutes", us_statutes_source()),
        ("themis_uk_statutes_pipeline", "themis_uk_statutes", uk_statutes_source()),
        ("themis_edgar_pipeline", "themis_edgar_contracts", edgar_exhibits_source()),
    ]

    for pipeline_name, dataset_name, source in sources:
        logger.info("Running dlt pipeline: %s", pipeline_name)
        pipeline = build_pipeline(pipeline_name, dataset_name)
        load_info = pipeline.run(source)

        if load_info.has_failed_jobs:
            failed = [str(j) for j in load_info.failed_jobs]
            logger.error("Pipeline %s had failed jobs: %s", pipeline_name, failed)
            raise RuntimeError(f"dlt pipeline {pipeline_name} failed: {failed}")

        # Count documents from load info metrics
        doc_count = sum(
            m.items_count
            for job in load_info.load_packages
            for m in job.jobs.get("completed_jobs", [])
            if hasattr(m, "items_count")
        ) or -1  # -1 = unknown (dlt doesn't always expose item count)

        results[dataset_name] = doc_count
        logger.info("Pipeline %s complete. Docs loaded: %s", pipeline_name, doc_count)

    return results


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Allow overriding DAGSTER_HOME for local runs
    if dagster_home := os.getenv("DAGSTER_HOME"):
        logger.info("DAGSTER_HOME: %s", dagster_home)

    results = run_ingestion()
    print("Ingestion complete:")
    for name, count in results.items():
        print(f"  {name}: {count} records")
    sys.exit(0)
