"""
retrieval/chunker.py — Legal-aware text chunker for the Themis corpus.

Splits raw document text into overlapping chunks suitable for embedding.
Designed specifically for legal text, which has strong section structure.

Strategy:
  1. Split on legal section separators first (§, numbered headings, PART/CHAPTER)
     to preserve clause boundaries as much as possible.
  2. Fall back to paragraph breaks, then sentences.
  3. Enforce a token budget (600 tokens target, 100-token overlap) using tiktoken
     with the cl100k_base encoding (a reasonable proxy for nomic-embed-text).
  4. Attach document-level metadata to every chunk for filtered retrieval.

Why 600 tokens?
  - nomic-embed-text has a 8192-token context window — 600 is well within limits.
  - Legal clauses are typically 200-800 words; 600 tokens (~450 words) captures
    most full clauses without splitting in the middle of a liability cap.
  - Overlap of 100 tokens ensures context continuity across retrieval boundaries.

Output schema (per chunk dict):
  chunk_id      : str   — SHA-256 of (doc_id + chunk_index)
  doc_id        : str   — parent document ID
  source        : str   — human-readable source name
  jurisdiction  : str   — jurisdiction code
  document_type : str   — document type
  title         : str   — parent document title
  text          : str   — chunk text
  chunk_index   : int   — 0-based position within document
  token_count   : int   — tiktoken count of this chunk
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Target chunk size and overlap in tokens
CHUNK_SIZE_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 100

# Legal section separators — sorted from most specific to most general
# RecursiveCharacterTextSplitter tries each in order until chunk is small enough
LEGAL_SEPARATORS = [
    # Section headers: "§ 2-201.", "Section 5.", "1. TITLE"
    r"\n(?=§ )",
    r"\n(?=Section \d)",
    r"\n(?=\d+\. [A-Z])",
    r"\n(?=Chapter \d)",
    r"\n(?=PART \d)",
    r"\n(?=Article \d)",
    # Numbered subsections: "(a)", "(1)", "(i)"
    r"\n(?=\([a-z]\) )",
    r"\n(?=\(\d+\) )",
    # Double newline (paragraph break)
    "\n\n",
    # Single newline
    "\n",
    # Fallback: space
    " ",
    "",
]


def _get_tokenizer():
    """Return a tiktoken tokenizer (cached — tiktoken caches internally)."""
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except ImportError as e:
        raise ImportError(
            "tiktoken is required for token-accurate chunking. "
            "Install with: pip install -e '.[pipeline]'"
        ) from e


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken cl100k_base encoding."""
    enc = _get_tokenizer()
    return len(enc.encode(text))


def _make_chunk_id(doc_id: str, chunk_index: int) -> str:
    """Deterministic chunk ID: SHA-256 of (doc_id + chunk_index)."""
    payload = f"{doc_id}::{chunk_index}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def chunk_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Chunk a single corpus document into overlapping token-bounded chunks.

    Args:
        document: A raw document dict matching the schema from sources.py.

    Returns:
        List of chunk dicts, each with all metadata fields and the chunk text.

    Raises:
        KeyError: If document is missing required fields (doc_id, text).
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore

    doc_id: str = document["doc_id"]
    text: str = document["text"]

    # Convert token budget to approximate character budget for LangChain's splitter.
    # Average English token is ~4 chars; legal text is slightly denser (~3.8 chars/token).
    # We use the tiktoken length_function so the split is token-accurate, not char-based.
    enc = _get_tokenizer()

    def _token_len(t: str) -> int:
        return len(enc.encode(t))

    splitter = RecursiveCharacterTextSplitter(
        separators=LEGAL_SEPARATORS,
        chunk_size=CHUNK_SIZE_TOKENS,
        chunk_overlap=CHUNK_OVERLAP_TOKENS,
        length_function=_token_len,
        is_separator_regex=True,
    )

    raw_chunks: list[str] = splitter.split_text(text)

    chunks: list[dict[str, Any]] = []
    for idx, chunk_text in enumerate(raw_chunks):
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue

        token_count = _token_len(chunk_text)
        chunks.append({
            "chunk_id": _make_chunk_id(doc_id, idx),
            "doc_id": doc_id,
            "source": document.get("source", ""),
            "jurisdiction": document.get("jurisdiction", ""),
            "document_type": document.get("document_type", ""),
            "title": document.get("title", ""),
            "text": chunk_text,
            "chunk_index": idx,
            "token_count": token_count,
        })

    logger.debug(
        "Chunked doc %s ('%s'): %d chars → %d chunks",
        doc_id,
        document.get("title", "")[:60],
        len(text),
        len(chunks),
    )
    return chunks


def chunk_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Chunk a list of corpus documents.

    Args:
        documents: List of raw document dicts.

    Returns:
        Flat list of all chunk dicts across all documents.
    """
    all_chunks: list[dict[str, Any]] = []
    for doc in documents:
        try:
            all_chunks.extend(chunk_document(doc))
        except Exception as e:
            logger.warning(
                "Failed to chunk document %s: %s — skipping.",
                doc.get("doc_id", "unknown"),
                e,
            )
    logger.info(
        "Chunked %d documents → %d total chunks (avg %.1f per doc)",
        len(documents),
        len(all_chunks),
        len(all_chunks) / max(len(documents), 1),
    )
    return all_chunks
