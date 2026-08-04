"""
retrieval/loaders/pdf_loader.py — PDF document loader and chunker.

Converts a raw PDF (bytes) into LangChain Document objects, ready for embedding
and storage in Qdrant.

Pipeline:
  1. pdfplumber: extracts text per-page (handles tables, columns better than pypdf)
  2. Presidio: PII redaction pass — replaces PII entities with [ENTITY_TYPE] tokens
  3. RecursiveCharacterTextSplitter: chunk with 512 tokens, 64-token overlap
     (tuned for legal text — longer chunks preserve clause context)
  4. Each chunk annotated with metadata: {page, chunk_index, contract_id, tenant_id}

Returns: list[Document] — standard LangChain Document with page_content + metadata

Note: This loader is called by ExtractionAgent AND by the corpus loaders.
The corpus loaders use the same chunking config for consistency.
"""

from __future__ import annotations

from langchain_core.documents import Document

# TODO (Phase 2): Implement using pdfplumber + Presidio + RecursiveCharacterTextSplitter


def load_pdf_to_documents(
    pdf_bytes: bytes,
    contract_id: str,
    tenant_id: str,
) -> list[Document]:
    """
    Convert PDF bytes to chunked LangChain Documents with metadata.

    Args:
        pdf_bytes: Raw PDF content.
        contract_id: UUID4 of the contract (for Qdrant metadata).
        tenant_id: Tenant identifier (for isolation metadata).

    Returns:
        List of Document objects ready for embedding + Qdrant upsert.
    """
    raise NotImplementedError("Phase 2: pdf_loader.load_pdf_to_documents() not implemented")
