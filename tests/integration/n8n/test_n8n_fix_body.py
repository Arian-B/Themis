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

res = requests.get("http://localhost:5678/api/v1/workflows/iOCitbp5vyK7lS7p", headers=headers)
wf = res.json()

for node in wf['nodes']:
    if node['name'] == 'HTTP Request':
        node['parameters']['jsonBody'] = '={{.body}}'

update_payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": wf["settings"]
}

res2 = requests.put("http://localhost:5678/api/v1/workflows/iOCitbp5vyK7lS7p", headers=headers, json=update_payload)
print(res2.status_code)
print(res2.json())
