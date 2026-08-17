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

with open("d:/Coding/themis/automation/n8n_high_risk_webhook.json") as f:
    wf = json.load(f)

new_wf = {
    "name": "High Risk Flag Webhook (Fixed Host)",
    "nodes": wf['nodes'],
    "connections": wf['connections'],
    "settings": wf['settings']
}

res = requests.post("http://localhost:5678/api/v1/workflows", headers=headers, json=new_wf)
print(res.status_code)
data = res.json()
print("Workflow ID:", data['id'])

# Activate
res2 = requests.post(f"http://localhost:5678/api/v1/workflows/{data['id']}/activate", headers=headers)
print("Activate:", res2.status_code)

# Get the webhook URL
for node in data['nodes']:
    if node['type'] == 'n8n-nodes-base.webhook':
        print("Webhook path:", node['parameters']['path'])
