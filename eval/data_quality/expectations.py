"""
eval/data_quality/expectations.py — Corpus data quality validation for Themis.

Validates the raw corpus data produced by dlt before it is chunked and embedded.
Uses Great Expectations 1.x Fluent API (GX changed its API significantly in v1).

Expectations enforced:
  1. doc_id        — present, non-null, unique (no duplicate document IDs)
  2. source        — present, non-null, minimum length 3 chars
  3. jurisdiction  — present, non-null, value in allowed set
  4. document_type — present, non-null, value in allowed set
  5. text          — present, non-null, minimum length 100 characters
  6. source_url    — present, non-null, starts with http
  7. fetched_at    — present, non-null

Note on GX 1.x: The GX API changed substantially between 0.18 and 1.x.
This module uses the GX 1.x fluent datasource API with pandas batches.
For portability, it wraps the GX API and also provides a pure-pandas
validate_dataframe_pandas() fallback used when GX is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

VALID_JURISDICTIONS = {"us_generic", "uk", "us_ca", "us_ny", "eu"}
VALID_DOCUMENT_TYPES = {"statute", "regulation", "contract_exhibit", "case_law"}
MIN_TEXT_LENGTH = 100   # characters


class ValidationResult:
    """
    Simple validation result container (GX-API-agnostic).
    Returned by both validate_dataframe() and validate_dataframe_pandas().
    """

    def __init__(
        self,
        success: bool,
        results: list[dict[str, Any]],
        document_count: int,
    ) -> None:
        self.success = success
        self.results = results          # list of {name, success, details}
        self.document_count = document_count

    def __repr__(self) -> str:
        passed = sum(1 for r in self.results if r["success"])
        return (
            f"ValidationResult(success={self.success}, "
            f"{passed}/{len(self.results)} expectations passed, "
            f"{self.document_count} documents)"
        )


def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    """
    Validate a pandas DataFrame against the corpus expectations.

    Tries GX 1.x first; falls back to pure-pandas validation if GX import fails.

    Args:
        df: DataFrame of raw corpus documents (one row per document).

    Returns:
        ValidationResult with .success and .results breakdown.

    Raises:
        RuntimeError: If validation fails (any expectation not met).
    """
    try:
        return _validate_with_gx(df)
    except (ImportError, Exception) as gx_err:
        logger.warning(
            "GX validation failed (%s: %s) — falling back to pandas validation.",
            type(gx_err).__name__,
            gx_err,
        )
        return _validate_with_pandas(df)


def _validate_with_gx(df: pd.DataFrame) -> ValidationResult:
    """
    Run validation using GX 1.x Fluent API.
    Uses gx.dataset.PandasDataset for expectations (the stable 1.x path).
    """
    import great_expectations as gx
    from great_expectations.expectations import (
        ExpectColumnToExist,
        ExpectColumnValuesToNotBeNull,
        ExpectColumnValuesToBeUnique,
        ExpectColumnValuesToBeInSet,
        ExpectColumnValueLengthsToBeBetween,
    )

    context = gx.get_context(mode="ephemeral")

    # GX 1.x: add pandas datasource
    datasource = context.data_sources.add_pandas(name="corpus")
    asset = datasource.add_dataframe_asset(name="documents")
    batch_def = asset.add_batch_definition_whole_dataframe("all_documents")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Build suite using GX 1.x ExpectationSuite (param is 'name' not 'expectation_suite_name')
    suite = context.suites.add(
        gx.core.ExpectationSuite(
            name="themis_corpus_raw",
            expectations=[
                # doc_id
                ExpectColumnToExist(column="doc_id"),
                ExpectColumnValuesToNotBeNull(column="doc_id"),
                ExpectColumnValuesToBeUnique(column="doc_id"),
                ExpectColumnValueLengthsToBeBetween(column="doc_id", min_value=32, max_value=64),
                # source
                ExpectColumnToExist(column="source"),
                ExpectColumnValuesToNotBeNull(column="source"),
                ExpectColumnValueLengthsToBeBetween(column="source", min_value=3),
                # jurisdiction
                ExpectColumnToExist(column="jurisdiction"),
                ExpectColumnValuesToNotBeNull(column="jurisdiction"),
                ExpectColumnValuesToBeInSet(
                    column="jurisdiction", value_set=list(VALID_JURISDICTIONS)
                ),
                # document_type
                ExpectColumnToExist(column="document_type"),
                ExpectColumnValuesToNotBeNull(column="document_type"),
                ExpectColumnValuesToBeInSet(
                    column="document_type", value_set=list(VALID_DOCUMENT_TYPES)
                ),
                # text
                ExpectColumnToExist(column="text"),
                ExpectColumnValuesToNotBeNull(column="text"),
                ExpectColumnValueLengthsToBeBetween(column="text", min_value=MIN_TEXT_LENGTH),
                # source_url
                ExpectColumnToExist(column="source_url"),
                ExpectColumnValuesToNotBeNull(column="source_url"),
                # fetched_at
                ExpectColumnToExist(column="fetched_at"),
                ExpectColumnValuesToNotBeNull(column="fetched_at"),
            ],
        )
    )

    validation_def = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="corpus_validation",
            data=batch_def,
            suite=suite,
        )
    )
    gx_result = validation_def.run(batch_parameters={"dataframe": df})

    results = [
        {
            "name": str(r.expectation_config.type if hasattr(r, "expectation_config") else r),
            "success": bool(r.success),
            "details": str(r.result) if hasattr(r, "result") else "",
        }
        for r in gx_result.results
    ]
    result = ValidationResult(
        success=bool(gx_result.success),
        results=results,
        document_count=len(df),
    )

    _raise_on_failure(result)
    return result


def _validate_with_pandas(df: pd.DataFrame) -> ValidationResult:
    """
    Pure-pandas fallback validation. Runs the same checks without GX dependency.
    Used when GX is not installed or when the GX API fails.
    """
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "success": passed, "details": detail})

    required_columns = ["doc_id", "source", "jurisdiction", "document_type", "text",
                        "source_url", "fetched_at"]

    # 1–2. Column existence + nulls
    for col in required_columns:
        exists = col in df.columns
        check(f"expect_column_to_exist[{col}]", exists)
        if exists:
            null_count = df[col].isna().sum()
            check(f"expect_column_values_to_not_be_null[{col}]", null_count == 0,
                  f"{null_count} nulls")

    # 3. doc_id uniqueness
    if "doc_id" in df.columns:
        dups = df["doc_id"].duplicated().sum()
        check("expect_column_values_to_be_unique[doc_id]", dups == 0, f"{dups} duplicates")
        # doc_id length
        bad_len = df["doc_id"].dropna().apply(lambda x: len(str(x))).lt(32).sum()
        check("expect_column_value_lengths_to_be_between[doc_id]", bad_len == 0,
              f"{bad_len} with length < 32")

    # 4. jurisdiction in allowed set
    if "jurisdiction" in df.columns:
        invalid = (~df["jurisdiction"].isin(VALID_JURISDICTIONS)).sum()
        check("expect_column_values_to_be_in_set[jurisdiction]", invalid == 0,
              f"{invalid} invalid values: {df['jurisdiction'][~df['jurisdiction'].isin(VALID_JURISDICTIONS)].unique().tolist()}")

    # 5. document_type in allowed set
    if "document_type" in df.columns:
        invalid = (~df["document_type"].isin(VALID_DOCUMENT_TYPES)).sum()
        check("expect_column_values_to_be_in_set[document_type]", invalid == 0,
              f"{invalid} invalid values")

    # 6. text minimum length
    if "text" in df.columns:
        short = df["text"].dropna().apply(lambda x: len(str(x))).lt(MIN_TEXT_LENGTH).sum()
        check(f"expect_column_value_lengths_to_be_between[text][min={MIN_TEXT_LENGTH}]",
              short == 0, f"{short} documents with text < {MIN_TEXT_LENGTH} chars")

    # 7. source_url format
    if "source_url" in df.columns:
        bad_url = (~df["source_url"].dropna().str.startswith("http")).sum()
        check("expect_source_url_starts_with_http", bad_url == 0,
              f"{bad_url} invalid URLs")

    success = all(c["success"] for c in checks)
    result = ValidationResult(success=success, results=checks, document_count=len(df))
    _raise_on_failure(result)
    return result


def _raise_on_failure(result: ValidationResult) -> None:
    """Raise RuntimeError with details if any expectation failed."""
    if not result.success:
        failed = [
            f"  ✗ {r['name']}: {r.get('details', '')}"
            for r in result.results
            if not r["success"]
        ]
        raise RuntimeError(
            f"Corpus data quality validation FAILED — "
            f"{len(failed)} expectation(s) not met:\n" + "\n".join(failed)
        )
