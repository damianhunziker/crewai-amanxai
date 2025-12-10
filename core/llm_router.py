# core/llm_router.py
from crewai import LLM
from .settings import settings

def get_llm_for_api_interpretation() -> LLM:
    """Gibt LLM-Instanz für OpenAPI Interpretation zurück"""
    return LLM(
        model=settings.openapi_llm_model,
        base_url=settings.llm_base_url,
        temperature=settings.openapi_llm_temperature,
        max_tokens=settings.openapi_llm_max_tokens
    )