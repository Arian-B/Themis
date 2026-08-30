import requests
import os
import json
from dotenv import load_dotenv

load_dotenv("d:/Coding/themis/.env")
api_key = os.getenv("N8N_API_KEY")

headers = {
    "X-N8N-API-KEY": api_key,
    "accept": "application/json"
}

res = requests.get("http://localhost:5678/api/v1/executions/8?includeData=true", headers=headers)
print(json.dumps(res.json(), indent=2))
