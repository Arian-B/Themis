import os
import requests
from dotenv import load_dotenv

load_dotenv()

def print_result(service_name, success, details=""):
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} | {service_name:15} | {details}")

def test_groq():
    api_key = os.getenv("GROQ_API_KEY")
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        models = client.models.list()
        print_result("Groq", True, f"Found {len(models.data)} models")
    except Exception as e:
        print_result("Groq", False, str(e))

def test_qdrant():
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=url, api_key=api_key, timeout=10)
        collections = client.get_collections()
        print_result("Qdrant", True, f"Found {len(collections.collections)} collections")
    except Exception as e:
        print_result("Qdrant", False, str(e))

def test_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    try:
        # Check health using REST API directly instead of relying on supabase python package
        response = requests.get(f"{url}/rest/v1/", headers={"apikey": key, "Authorization": f"Bearer {key}"})
        if response.status_code == 200:
            print_result("Supabase", True, "Successfully authenticated with REST API")
        else:
            print_result("Supabase", False, f"Status Code: {response.status_code}")
    except Exception as e:
        print_result("Supabase", False, str(e))

def test_langfuse():
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST")
    try:
        from langfuse import Langfuse
        langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        if langfuse.auth_check():
            print_result("Langfuse", True, "Successfully authenticated")
        else:
            print_result("Langfuse", False, "Auth check returned False")
    except Exception as e:
        print_result("Langfuse", False, str(e))

def test_huggingface():
    token = os.getenv("HF_TOKEN")
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        user_info = api.whoami(token=token)
        print_result("HuggingFace", True, f"Authenticated as {user_info.get('name')}")
    except Exception as e:
        print_result("HuggingFace", False, str(e))

def test_kimi():
    api_key = os.getenv("KIMI_API_KEY")
    try:
        # Kimi (Moonshot) provides an OpenAI compatible API
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get("https://api.moonshot.ai/v1/models", headers=headers)
        if response.status_code == 200:
            models = response.json().get("data", [])
            print_result("Kimi", True, f"Found {len(models)} models")
        else:
            print_result("Kimi", False, f"Status Code: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print_result("Kimi", False, str(e))

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Testing .env credentials...")
    print("--------------------------------------------------")
    test_kimi()
    test_groq()
    test_qdrant()
    test_supabase()
    test_langfuse()
    test_huggingface()
    print("--------------------------------------------------")
