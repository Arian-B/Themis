import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
import requests
res = requests.get("http://localhost:8000/api/v1/contracts/ad79b056-4c97-457b-9e25-b71c5e18738e/results", headers={"Authorization": "Bearer test-token-tenant-999"})
print(res.status_code)
print(res.json())
