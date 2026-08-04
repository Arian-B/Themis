"""
retrieval/loaders/us_corpus_loader.py — US-generic legal corpus seed loader.

Responsibility:
  Downloads and indexes a set of reference legal documents into the Qdrant
  platform corpus collection "platform_us_generic". This collection is shared
  (read-only) across all tenants and serves as the reference knowledge base
  for risk analysis of US-jurisdiction contracts.

Source documents (Phase 2 initial seed):
  1. UCC Article 2 (Uniform Commercial Code — goods contracts)
  2. CISG (UN Convention on Contracts for International Sale of Goods)
  3. ABA Model Contract Clauses (publicly available provisions)
  4. NVCA Model Legal Documents (venture/startup contracts — permissive license)
  5. EDGAR sample 10-K exhibit contracts (publicly filed, open access)

Processing pipeline:
  for each source document:
    1. Download / read from data/corpora/us/ (place files here manually)
    2. Convert to text via pdf_loader.load_pdf_to_documents()
    3. Tag metadata: {jurisdiction: "us_generic", source_title, source_type}
    4. Embed + upsert to Qdrant collection "platform_us_generic"

Usage:
  python -m retrieval.loaders.us_corpus_loader --data-dir data/corpora/us/

Note: Corpus loading is a one-time offline operation, NOT part of the
contract analysis hot path. Run once during platform setup.
"""

from __future__ import annotations

import argparse
from pathlib import Path

# TODO (Phase 2): Implement corpus loading:
#   1. Iterate PDFs in data_dir
#   2. Call pdf_loader.load_pdf_to_documents() for each
#   3. Add jurisdiction metadata
#   4. Call vector_store.add_documents() with collection "platform_us_generic"


def load_us_corpus(data_dir: Path) -> int:
    """
    Load all US-generic legal corpus documents from data_dir into Qdrant.

    Args:
        data_dir: Path to directory containing US legal reference PDFs.

    Returns:
        Number of chunks indexed.
    """
    raise NotImplementedError("Phase 2: us_corpus_loader.load_us_corpus() not implemented")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load US legal corpus into Qdrant")
    parser.add_argument("--data-dir", type=Path, default=Path("data/corpora/us"))
    args = parser.parse_args()
    count = load_us_corpus(args.data_dir)
    print(f"Indexed {count} chunks into platform_us_generic")
