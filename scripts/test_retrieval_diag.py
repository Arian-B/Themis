"""
Diagnose what Qdrant is actually returning for a test query.
Prints raw doc content, metadata, and all available attributes.
"""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')

from retrieval.qdrant_retriever import get_retriever

retriever = get_retriever(jurisdiction='us_generic', k=3)
docs = retriever.invoke("The contract excludes liability for consequential damages.")

print(f"Retrieved {len(docs)} documents\n")
for i, doc in enumerate(docs):
    print(f"--- doc[{i}] ---")
    print(f"  type:         {type(doc)}")
    print(f"  id attr:      {getattr(doc, 'id', 'NO_ID_ATTR')}")
    print(f"  metadata:     {doc.metadata}")
    content = doc.page_content
    print(f"  page_content len: {len(content)}")
    print(f"  page_content preview: {repr(content[:300])}")
    print()
