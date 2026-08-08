"""
pipelines/assets.py — Dagster asset definitions for the Themis corpus ingestion pipeline.

Pipeline graph (asset dependency order):
  1. ingest_corpus          — dlt: fetch all sources → data/raw/*.jsonl
  2. validate_corpus        — GX: check data quality of raw files
  3. chunk_and_embed_corpus — Chunker + Ollama: produce embedded chunks per jurisdiction
  4. load_corpus_to_qdrant  — Qdrant: upsert chunks into themis_us_generic + themis_uk

All four assets are in the "corpus_ingestion" group and can be materialized together:
  dagster asset materialize -m pipelines.definitions --select "corpus_ingestion/*"

Or run the single job that wraps all four:
  dagster job execute -m pipelines.definitions -j corpus_ingestion_job
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from dagster import (
    MetadataValue,
    asset,
)

from pipelines.resources import OllamaConfig, PipelineConfig, QdrantResource

logger = logging.getLogger(__name__)

_GROUP = "corpus_ingestion"


# ─────────────────────────────────────────────────────────────────────────────
# Asset 1: Ingest corpus
# ─────────────────────────────────────────────────────────────────────────────

@asset(
    group_name=_GROUP,
    description="Run dlt pipeline to ingest US statutes, UK statutes, and EDGAR contracts into data/raw/.",
)
def ingest_corpus(
    context,
    pipeline_config: PipelineConfig,
) -> list[dict[str, Any]]:
    """
    Run all three dlt sources and return a flat list of raw document dicts.
    Also writes JSON Lines files to data/raw/ for downstream inspection and GX validation.
    """
    from retrieval.corpus.sources import (
        edgar_exhibits_source,
        uk_statutes_source,
        us_statutes_source,
    )

    all_docs: list[dict[str, Any]] = []
    sources = [
        ("themis_us_statutes", us_statutes_source),
        ("themis_uk_statutes", uk_statutes_source),
        ("themis_edgar_contracts", edgar_exhibits_source),
    ]

    raw_dir = pipeline_config.raw_data_path
    raw_dir.mkdir(parents=True, exist_ok=True)

    for dataset_name, source_fn in sources:
        context.log.info("Running source: %s", dataset_name)
        source_obj = source_fn()
        docs: list[dict[str, Any]] = []

        try:
            for resource in source_obj.resources.values():
                for record in resource:
                    if isinstance(record, dict):
                        docs.append(record)
                    elif isinstance(record, list):
                        docs.extend(record)
        except AttributeError:
            for record in source_obj:
                if isinstance(record, dict):
                    docs.append(record)

        output_path = raw_dir / f"{dataset_name}.jsonl"
        with output_path.open("w") as f:
            for doc in docs:
                f.write(json.dumps(doc) + "\n")

        context.log.info("Source %s: %d documents → %s", dataset_name, len(docs), output_path)
        all_docs.extend(docs)

    context.add_output_metadata({
        "total_documents": MetadataValue.int(len(all_docs)),
        "raw_dir": MetadataValue.path(str(raw_dir)),
        "sources": MetadataValue.json([s[0] for s in sources]),
    })
    return all_docs


# ─────────────────────────────────────────────────────────────────────────────
# Asset 2: Validate corpus
# ─────────────────────────────────────────────────────────────────────────────

@asset(
    group_name=_GROUP,
    description="Run Great Expectations suite to validate raw corpus documents.",
)
def validate_corpus(
    context,
    ingest_corpus: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Validate the raw corpus documents with GX.
    Raises RuntimeError (fails this asset + all downstream) if any expectation fails.
    Returns the same document list unchanged if validation passes.
    """
    import pandas as pd
    from eval.data_quality.expectations import validate_dataframe

    df = pd.DataFrame(ingest_corpus)
    context.log.info(
        "Validating %d documents (%d unique doc_ids)",
        len(df),
        df["doc_id"].nunique() if "doc_id" in df.columns else 0,
    )

    result = validate_dataframe(df)
    n_ok = sum(1 for r in result.results if r["success"])
    n_total = len(result.results)

    context.add_output_metadata({
        "expectations_passed": MetadataValue.int(n_ok),
        "expectations_total": MetadataValue.int(n_total),
        "documents_validated": MetadataValue.int(len(df)),
        "validation_success": MetadataValue.bool(result.success),
    })
    context.log.info("GX validation PASSED: %d/%d expectations met.", n_ok, n_total)
    return ingest_corpus


# ─────────────────────────────────────────────────────────────────────────────
# Asset 3: Chunk and embed corpus
# ─────────────────────────────────────────────────────────────────────────────

@asset(
    group_name=_GROUP,
    description="Chunk documents into 600-token segments, embed with Ollama nomic-embed-text.",
)
def chunk_and_embed_corpus(
    context,
    validate_corpus: list[dict[str, Any]],
    ollama: OllamaConfig,
    pipeline_config: PipelineConfig,
) -> dict[str, list[dict[str, Any]]]:
    """
    Chunk and embed all validated documents.
    Returns a dict keyed by jurisdiction → list of embedded chunk dicts.
    """
    from retrieval.chunker import chunk_documents
    from retrieval.embedder import embed_chunks

    if pipeline_config.dry_run:
        context.log.warning("DRY RUN: skipping actual embedding. Returning empty chunks.")
        return {}

    if not ollama.check_health():
        raise RuntimeError(
            f"Ollama is not reachable at {ollama.host} or model '{ollama.embed_model}' "
            "is not available.\n"
            "  docker compose up ollama -d\n"
            "  docker compose exec ollama ollama pull nomic-embed-text"
        )

    context.log.info("Chunking %d documents...", len(validate_corpus))
    all_chunks = chunk_documents(validate_corpus)
    context.log.info("Produced %d chunks total.", len(all_chunks))

    context.log.info("Embedding %d chunks via Ollama (%s)...", len(all_chunks), ollama.embed_model)
    embedded_chunks = embed_chunks(all_chunks)

    by_jurisdiction: dict[str, list[dict[str, Any]]] = {}
    for chunk in embedded_chunks:
        j = chunk.get("jurisdiction", "us_generic")
        by_jurisdiction.setdefault(j, []).append(chunk)

    context.add_output_metadata({
        "total_chunks": MetadataValue.int(len(embedded_chunks)),
        "jurisdictions": MetadataValue.json(list(by_jurisdiction.keys())),
        "chunks_per_jurisdiction": MetadataValue.json({
            j: len(c) for j, c in by_jurisdiction.items()
        }),
        "embedding_dim": MetadataValue.int(
            len(embedded_chunks[0]["embedding"]) if embedded_chunks else 0
        ),
    })
    return by_jurisdiction


# ─────────────────────────────────────────────────────────────────────────────
# Asset 4: Load to Qdrant
# ─────────────────────────────────────────────────────────────────────────────

@asset(
    group_name=_GROUP,
    description="Upsert embedded chunks into Qdrant Cloud (one collection per jurisdiction).",
)
def load_corpus_to_qdrant(
    context,
    chunk_and_embed_corpus: dict[str, list[dict[str, Any]]],
    qdrant: QdrantResource,
    pipeline_config: PipelineConfig,
) -> dict[str, int]:
    """
    Upsert all embedded chunks into Qdrant.
    Creates one collection per jurisdiction. Returns {jurisdiction: points_upserted}.
    """
    from retrieval.vector_store import ensure_corpus_collection, upsert_chunks

    if pipeline_config.dry_run:
        context.log.warning("DRY RUN: skipping Qdrant upsert.")
        return {}

    if not chunk_and_embed_corpus:
        context.log.warning("No chunks to load.")
        return {}

    client = qdrant.get_client()
    results: dict[str, int] = {}

    for jurisdiction, chunks in chunk_and_embed_corpus.items():
        context.log.info("Upserting %d chunks for '%s'...", len(chunks), jurisdiction)
        ensure_corpus_collection(jurisdiction, client=client)
        n = upsert_chunks(chunks, jurisdiction, client=client)
        results[jurisdiction] = n
        context.log.info("Upserted %d points into 'themis_%s'.", n, jurisdiction)

    total = sum(results.values())
    context.add_output_metadata({
        "total_points_upserted": MetadataValue.int(total),
        "collections": MetadataValue.json(results),
    })
    return results
