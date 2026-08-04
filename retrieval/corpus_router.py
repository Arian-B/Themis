"""
retrieval/corpus_router.py — Maps jurisdiction identifiers to Qdrant collection names.

This is the pluggable jurisdiction extension point. Adding a new jurisdiction
requires only:
  1. Adding the jurisdiction to schemas/jurisdiction.py Jurisdiction enum
  2. Adding an entry to JURISDICTION_MAP below
  3. Running the corresponding corpus loader in retrieval/loaders/

No changes needed in any agent code.

Design:
  - Collection name pattern: "{tenant_id}_{jurisdiction_key}"
  - Legal corpus (platform-wide) collections: "platform_{jurisdiction_key}"
    (shared across all tenants, read-only)
  - Per-contract collections for tenant-uploaded reference docs use tenant_id prefix.

Note on Qdrant collection strategy:
  Option A (current): one collection per (tenant, jurisdiction)
    → Simpler; metadata filters only needed for contract_id within collection
  Option B (alternative): one collection per tenant, jurisdiction as metadata filter
    → Fewer collections but slower filtered search at scale
  Option A is recommended for < 1000 tenants. Revisit at scale.
"""

from __future__ import annotations

from schemas.jurisdiction import Jurisdiction

JURISDICTION_MAP: dict[str, str] = {
    Jurisdiction.US_GENERIC: "us_generic",
    Jurisdiction.UK: "uk",
    # Future: Jurisdiction.EU_GDPR: "eu_gdpr",
    # Future: Jurisdiction.CA_PIPEDA: "ca_pipeda",
}

PLATFORM_CORPUS_PREFIX = "platform"


def get_corpus_collection(tenant_id: str, jurisdiction: str) -> str:
    """
    Return the Qdrant collection name for a given tenant + jurisdiction.
    Falls back to the platform-level corpus if tenant has no private collection.

    Args:
        tenant_id: The tenant's unique identifier.
        jurisdiction: A Jurisdiction enum value (e.g., "us_generic").

    Returns:
        Qdrant collection name string.
    """
    # TODO (Phase 2): Check if tenant-specific collection exists in Qdrant.
    # If yes, return f"{tenant_id}_{jurisdiction}".
    # If no, fall back to platform corpus: f"{PLATFORM_CORPUS_PREFIX}_{jurisdiction}".
    raise NotImplementedError("Phase 2: corpus_router.get_corpus_collection() not implemented")


def get_platform_corpus_collection(jurisdiction: str) -> str:
    """Return the platform-level (shared) corpus collection name for a jurisdiction."""
    mapped = JURISDICTION_MAP.get(jurisdiction, "us_generic")
    return f"{PLATFORM_CORPUS_PREFIX}_{mapped}"
