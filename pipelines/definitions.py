"""
pipelines/definitions.py — Dagster Definitions object (the pipeline entry point).

This is the module Dagster loads when you run:
  dagster dev -m pipelines.definitions
  dagster asset materialize -m pipelines.definitions --select "corpus_ingestion/*"
  dagster job execute -m pipelines.definitions -j corpus_ingestion_job

Resources are bound to environment variables here. Dagster resolves them at
execution time from the running process's environment (which loads .env via
the startup command or direnv).

Schedules:
  corpus_ingestion_weekly — Re-runs full ingestion every Sunday at 02:00 UTC.
  This ensures new EDGAR filings and statute amendments are picked up weekly.
"""

from __future__ import annotations

import os

from dagster import (
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_modules,
)

from pipelines import assets as assets_module
from pipelines.resources import OllamaConfig, PipelineConfig, QdrantResource

# ─────────────────────────────────────────────────────────────────────────────
# Assets
# ─────────────────────────────────────────────────────────────────────────────

all_assets = load_assets_from_modules([assets_module])

# ─────────────────────────────────────────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────────────────────────────────────────

corpus_ingestion_job = define_asset_job(
    name="corpus_ingestion_job",
    selection=AssetSelection.groups("corpus_ingestion"),
    description=(
        "Full corpus ingestion pipeline: "
        "dlt ingest → GX validate → chunk+embed → Qdrant upsert."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# Schedules
# ─────────────────────────────────────────────────────────────────────────────

corpus_ingestion_weekly = ScheduleDefinition(
    name="corpus_ingestion_weekly",
    cron_schedule="0 2 * * 0",   # Sunday 02:00 UTC
    job=corpus_ingestion_job,
    execution_timezone="UTC",
)

# ─────────────────────────────────────────────────────────────────────────────
# Resources
# ─────────────────────────────────────────────────────────────────────────────

# dry_run=True when PIPELINE_DRY_RUN=1 (useful in CI without Ollama/Qdrant)
_dry_run = os.getenv("PIPELINE_DRY_RUN", "0") == "1"

resources = {
    "qdrant": QdrantResource(),
    "ollama": OllamaConfig(),
    "pipeline_config": PipelineConfig(dry_run=_dry_run),
}

# ─────────────────────────────────────────────────────────────────────────────
# Definitions (Dagster entry point)
# ─────────────────────────────────────────────────────────────────────────────

defs = Definitions(
    assets=all_assets,
    jobs=[corpus_ingestion_job],
    schedules=[corpus_ingestion_weekly],
    resources=resources,
)
