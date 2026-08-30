import requests
import os
from dotenv import load_dotenv

load_dotenv("d:/Coding/themis/.env")
api_key = os.getenv("N8N_API_KEY")

headers = {
    "X-N8N-API-KEY": api_key,
    "accept": "application/json"
}

# Deactivate the old one
res = requests.post("http://localhost:5678/api/v1/workflows/KCaV713Eofpy00Ia/deactivate", headers=headers)
print("Deactivate old:", res.status_code)

# Activate the new one
res2 = requests.post("http://localhost:5678/api/v1/workflows/iOCitbp5vyK7lS7p/activate", headers=headers)
print("Activate new:", res2.status_code)
