"""
eval/data_quality/run_checks.py — Entry point for running GX corpus validation.

Reads all raw JSON Lines files from data/raw/, combines them into a DataFrame,
and runs the corpus expectations suite. Can be run standalone or called by Dagster.

Usage:
    python -m eval.data_quality.run_checks

Exit codes:
    0 — all expectations passed
    1 — one or more expectations failed (details printed to stderr)
    2 — data/raw/ not found or no documents loaded (pipeline hasn't run yet)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path(__file__).parents[2] / "data" / "raw"


def load_raw_documents() -> "list[dict]":
    """
    Load all raw corpus JSON Lines files from data/raw/.

    dlt writes files in the pattern:
        data/raw/<dataset_name>/documents.jsonl   (or .jsonl.gz)
        data/raw/<dataset_name>/<table_name>/<uuid>.jsonl

    We recursively glob for *.jsonl files and combine all records.
    """
    docs: list[dict] = []
    if not RAW_DATA_DIR.exists():
        return docs

    for jsonl_file in RAW_DATA_DIR.rglob("*.jsonl"):
        with jsonl_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        docs.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning("Skipping malformed line in %s: %s", jsonl_file, e)

    return docs


def run_validation(documents: list[dict] | None = None) -> bool:
    """
    Run GX validation against the corpus documents.

    Args:
        documents: Optional pre-loaded list of document dicts.
                   If None, loads from data/raw/ automatically.

    Returns:
        True if all expectations passed, False otherwise.

    Raises:
        RuntimeError: Propagated from GX if validation fails and raise_on_failure=True.
    """
    import pandas as pd

    from eval.data_quality.expectations import validate_dataframe

    if documents is None:
        documents = load_raw_documents()

    if not documents:
        raise ValueError(
            f"No documents found in {RAW_DATA_DIR}. "
            "Run the dlt ingestion pipeline first: "
            "python -m retrieval.corpus.pipeline"
        )

    df = pd.DataFrame(documents)
    logger.info(
        "Validating %d documents (%d unique doc_ids)",
        len(df),
        df["doc_id"].nunique() if "doc_id" in df.columns else 0,
    )

    try:
        result = validate_dataframe(df)
        n_expectations = len(result.results)
        logger.info("Validation PASSED: %d/%d expectations met.", n_expectations, n_expectations)
        return True
    except RuntimeError as e:
        logger.error("Validation FAILED:\n%s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    success = run_validation()
    sys.exit(0 if success else 1)
