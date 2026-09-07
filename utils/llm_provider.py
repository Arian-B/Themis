import os
import logging
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

def get_complex_reasoning_llm(temperature: float = 0, **kwargs):
    """
    Returns an initialized LangChain ChatOpenAI-compatible instance for complex reasoning tasks.
    Provider is selected via COMPLEX_TIER_PROVIDER environment variable (default: "ollama" for local-first).
    """
    provider = os.getenv("COMPLEX_TIER_PROVIDER", "ollama").strip().lower()

    if provider == "kimi":
        api_key = os.getenv("KIMI_API_KEY", "")
        base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
        model = "moonshot-v1-8k"
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            **kwargs
        )
    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        model = "openai/gpt-oss-120b"
        if not api_key:
            logger.warning("No GROQ_API_KEY found, falling back to Ollama")
            provider = "ollama"
        else:
            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                **kwargs
            )
    elif provider == "ollama":
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_CLASSIFY_MODEL", "llama3.1:8b")
        logger.info(f"Using Ollama for complex reasoning: {model} at {ollama_host}")
        return ChatOllama(
            base_url=ollama_host,
            model=model,
            temperature=temperature,
            **kwargs
        )
    else:
        logger.warning(f"Unknown COMPLEX_TIER_PROVIDER '{provider}', falling back to Ollama.")
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_CLASSIFY_MODEL", "llama3.1:8b")
        return ChatOllama(
            base_url=ollama_host,
            model=model,
            temperature=temperature,
            **kwargs
        )
