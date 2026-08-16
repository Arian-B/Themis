import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

# Ensure utils is in path so we can import llm_provider
sys.path.append(str(ROOT))
from utils.llm_provider import get_complex_reasoning_llm

def test_llm_auth(provider_override: str = None):
    if provider_override:
        os.environ["COMPLEX_TIER_PROVIDER"] = provider_override
        
    provider = os.getenv("COMPLEX_TIER_PROVIDER", "groq").strip().lower()
    print(f"[*] Testing LLM Auth with provider: {provider.upper()}")
    
    try:
        # Note: timeout and max_retries might not be directly supported by all kwargs without warnings,
        # but we'll try to pass standard ones.
        llm = get_complex_reasoning_llm(temperature=0, max_retries=1, timeout=10)
        
        # Display some info about what we loaded
        print(f"[*] Model: {llm.model_name}")
        print(f"[*] Base URL: {llm.openai_api_base}")
        api_key = llm.openai_api_key.get_secret_value() if hasattr(llm.openai_api_key, "get_secret_value") else str(llm.openai_api_key)
        if not api_key:
            print("[-] FAIL: API key is missing or empty.")
            sys.exit(1)
            
        print(f"[*] Key prefix: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else ''}")
        
        print("\n[*] Sending ping to LLM...")
        response = llm.invoke("Please output 'OK' if you can read this.")
        print("\n[+] SUCCESS: LLM Authentication passed!")
        print(f"    Response: {response.content}")
        
    except Exception as e:
        print("\n[-] FAIL: LLM Authentication failed!")
        print(f"    Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test LLM Authentication")
    parser.add_argument("--provider", type=str, choices=["groq", "kimi"], help="Override provider (e.g., groq, kimi)")
    args = parser.parse_args()
    
    test_llm_auth(provider_override=args.provider)
