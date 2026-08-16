"""
Inspect raw Qdrant point payloads to find where text is stored.
"""
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')

from qdrant_client import QdrantClient

client = QdrantClient(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY'),
)

# Scroll first 3 points to see raw payload structure
points, _ = client.scroll(
    collection_name='themis_us_generic',
    limit=3,
    with_payload=True,
    with_vectors=False,
)

print(f"Collection: themis_us_generic — {len(points)} points retrieved\n")
for i, pt in enumerate(points):
    print(f"--- point[{i}] id={pt.id} ---")
    print(f"  payload keys: {list(pt.payload.keys())}")
    for k, v in pt.payload.items():
        val_preview = str(v)[:300] if v else repr(v)
        print(f"  [{k}]: {val_preview}")
    print()
