import requests
import os
from dotenv import load_dotenv

load_dotenv("d:/Coding/themis/.env")
api_key = os.getenv("N8N_API_KEY")

headers = {
    "X-N8N-API-KEY": api_key,
    "accept": "application/json"
}

res = requests.get("http://localhost:5678/api/v1/workflows", headers=headers)
print(res.status_code)
print(res.json())
