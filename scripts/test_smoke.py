import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')

# Test 1: graph imports
try:
    from graph.build import build_graph
    print('[1] graph imports OK')
except Exception as e:
    print(f'[1] graph import FAILED: {e}')
    sys.exit(1)

# Test 2: embedding dimensions
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    emb = HuggingFaceEmbeddings(
        model_name='nomic-ai/nomic-embed-text-v1',
        model_kwargs={'trust_remote_code': True},
        encode_kwargs={'normalize_embeddings': True},
    )
    v = emb.embed_query('test legal clause')
    dim = len(v)
    status = 'MATCH' if dim == 768 else 'MISMATCH'
    print(f'[2] embedding dim={dim} (need 768) -> {status}')
except Exception as e:
    print(f'[2] embedding FAILED: {e}')
    sys.exit(1)
