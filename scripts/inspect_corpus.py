#!/usr/bin/env python
"""
scripts/inspect_corpus.py — Inspect the EDGAR contracts jsonl.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
jsonl_path = ROOT / "data" / "raw" / "themis_edgar_contracts.jsonl"

if not jsonl_path.exists():
    sys.exit(f"File not found: {jsonl_path}")

docs = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]

for i, doc in enumerate(docs):
    print(f"Contract {i + 1}")
    print(f"Doc ID:       {doc.get('doc_id')}")
    print(f"Source:       {doc.get('source')}")
    print(f"Jurisdiction: {doc.get('jurisdiction')}")
    text = doc.get("text", "")
    preview = text[:500].replace("\n", " ")
    print(f"Text Preview: {preview}...")
    print("-" * 80)
