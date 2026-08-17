import requests
import os
import json
from dotenv import load_dotenv

load_dotenv("d:/Coding/themis/.env")
api_key = os.getenv("N8N_API_KEY")

headers = {
    "X-N8N-API-KEY": api_key,
    "accept": "application/json",
    "content-type": "application/json"
}

# Get workflow
res = requests.get("http://localhost:5678/api/v1/workflows/KCaV713Eofpy00Ia", headers=headers)
wf = res.json()

# Modify node 2
for node in wf['nodes']:
    if node['name'] == 'HTTP Request':
        node['parameters']['url'] = 'http://host.docker.internal:8001/log'

# Update
res2 = requests.put("http://localhost:5678/api/v1/workflows/KCaV713Eofpy00Ia", headers=headers, json=wf)
print(res2.status_code)
print(res2.json())
