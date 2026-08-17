import os
import requests
import json
from dotenv import load_dotenv
load_dotenv(".env")
headers = {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}
res = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
print(json.dumps(res.json(), indent=2))
