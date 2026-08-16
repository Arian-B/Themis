import os
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

def get_complex_reasoning_llm(temperature: float = 0, **kwargs) -> ChatOpenAI:
    """
    Returns an initialized LangChain ChatOpenAI-compatible instance for complex reasoning tasks.
    Provider is selected via COMPLEX_TIER_PROVIDER environment variable (default: "groq").
    """
    provider = os.getenv("COMPLEX_TIER_PROVIDER", "groq").strip().lower()

    if provider == "kimi":
        api_key = os.getenv("KIMI_API_KEY", "")
        base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
        model = "moonshot-v1-8k"
    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        # Ensure we use a strong currently-available Groq model:
        model = "llama-3.1-8b-instant" 
    else:
        logger.warning(f"Unknown COMPLEX_TIER_PROVIDER '{provider}', falling back to groq.")
        api_key = os.getenv("GROQ_API_KEY", "")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        model = "llama-3.1-8b-instant"

    if not api_key:
        logger.warning(f"No API key found for provider {provider}. (Expected KIMI_API_KEY or GROQ_API_KEY)")

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        **kwargs
    )
