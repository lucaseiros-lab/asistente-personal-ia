from functools import lru_cache

from google import genai

from app.core.config import settings


@lru_cache
def get_ai_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)
