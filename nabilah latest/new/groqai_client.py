# ai_client.py
import os
from groq import Groq

_client = None  # singleton

# Groq AI API key (replace with your own api)
GROQ_API_KEY = "replace _here"

def get_ai_client():
    """
    Get Groq AI client
    """
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Please define it in environment variables."
        )

    _client = Groq(api_key=api_key)
    return _client


# Keep backward compatibility
def get_openai_client():
    """Deprecated: Use get_ai_client() instead"""
    return get_ai_client()
