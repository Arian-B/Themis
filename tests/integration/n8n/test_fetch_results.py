import requests
import json
headers = {"Authorization": "Bearer test-token-tenant-123"}
res = requests.get("http://127.0.0.1:8000/api/v1/contracts/e7decf46-a98c-4655-998e-fcf2b54f731e/results", headers=headers)
print(json.dumps(res.json(), indent=2))
