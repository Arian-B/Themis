import requests
n8n_url = "http://localhost:5678/webhook/cb6f1a7d-6359-4579-85ca-089ee400f3f1"
res = requests.post(n8n_url, json={"test": True})
print("Status:", res.status_code)
print("Response:", res.text)
