import os
import json
import requests
from dotenv import load_dotenv

load_dotenv('.env')

with open('automation/n8n_high_risk_webhook.json', 'r') as f:
    workflow_data = json.load(f)

workflow_data["settings"] = {}
workflow_data.pop("active", None)

n8n_api_key = os.environ.get('N8N_API_KEY')
headers = {
    'X-N8N-API-KEY': n8n_api_key,
    'Content-Type': 'application/json'
}

resp = requests.post('http://localhost:5678/api/v1/workflows', headers=headers, json=workflow_data)
print(resp.status_code, resp.text)
if resp.status_code == 200:
    wf_id = resp.json().get('id')
    # Activate
    resp = requests.post(f'http://localhost:5678/api/v1/workflows/{wf_id}/activate', headers=headers)
    print("Activated:", resp.status_code, resp.text)
