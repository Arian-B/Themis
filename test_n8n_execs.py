import requests
import json
headers = {"X-N8N-API-KEY": "n8n_api_key_for_testing_12345"}
res = requests.get("http://localhost:5678/api/v1/executions?limit=1", headers=headers)
print(json.dumps(res.json(), indent=2))
