"""
retrieval/loaders/uk_corpus_loader.py — UK legal corpus seed loader.

Responsibility:
  Seeds the "platform_uk" Qdrant collection with reference UK legal documents
  for use by agents operating on UK-jurisdiction contracts.

Source documents (Phase 2 initial seed):
  1. Sale of Goods Act 1979 (key provisions — publicly available)
  2. Consumer Rights Act 2015 (B2B-relevant sections)
  3. Unfair Contract Terms Act 1977 (UCTA — critical for limitation clauses)
  4. ICO Model Contract Clauses (UK GDPR data processing agreements)
  5. Law Society of England & Wales standard commercial clauses (public docs)
  6. Companies Act 2006 excerpts (director duties, material contracts)

Key difference from US corpus:
  UK contracts flagged as HIGH risk for limitation of liability clauses must
  be cross-referenced against UCTA 1977 — clauses may be void regardless of
  what they say. The corpus must include UCTA so the Risk Analysis Agent can
  surface this.

Processing pipeline:
  Identical to us_corpus_loader.py — see that module for details.
  Metadata tag: {jurisdiction: "uk", source_title, source_type}

Usage:
  python -m retrieval.loaders.uk_corpus_loader --data-dir data/corpora/uk/
"""

from __future__ import annotations

import argparse
from pathlib import Path

# TODO (Phase 2): Implement — mirror us_corpus_loader.py with UK sources.


def load_uk_corpus(data_dir: Path) -> int:
    """
    Load all UK legal corpus documents from data_dir into Qdrant.

    Args:
        data_dir: Path to directory containing UK legal reference PDFs.

    Returns:
        Number of chunks indexed.
    """
    raise NotImplementedError("Phase 2: uk_corpus_loader.load_uk_corpus() not implemented")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load UK legal corpus into Qdrant")
    parser.add_argument("--data-dir", type=Path, default=Path("data/corpora/uk"))
    args = parser.parse_args()
    count = load_uk_corpus(args.data_dir)
    print(f"Indexed {count} chunks into platform_uk")
