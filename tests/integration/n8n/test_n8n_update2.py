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

# Fetch
res = requests.get("http://localhost:5678/api/v1/workflows/iOCitbp5vyK7lS7p", headers=headers)
wf = res.json()

# Fix
for node in wf['nodes']:
    if node['name'] == 'HTTP Request':
        node['parameters']['requestMethod'] = 'POST'
        node['parameters']['options'] = {}
        node['parameters']['jsonParameters'] = True
        node['parameters']['options']['bodyContentType'] = 'json'

# I will just write to a file via Execute Command to be 100% sure, or just POST.
# Let's just fix the POST.

res2 = requests.put("http://localhost:5678/api/v1/workflows/iOCitbp5vyK7lS7p", headers=headers, json={"name": wf['name'], "nodes": wf['nodes'], "connections": wf['connections'], "settings": wf['settings']})
print("Update:", res2.status_code)
