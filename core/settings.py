"""Configuration settings for CrewAI system."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""

    # API Keys for LLMs (used in main.py)
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    deepseek_api_key: str = Field(default="", env="DEEPSEEK_API_KEY")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")

    # LLM Configuration (used in main.py)
    llm_model: str = Field(default="llama-3-2-3b-instruct-q4-k-m", description="Default LLM model")
    llm_base_url: str = Field(default="http://localhost:5020", description="Llama.cpp server base URL")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="LLM temperature")
    llm_max_tokens: int = Field(default=4000, ge=1, le=16000, description="Max tokens per response")

    # MCP Configuration (used in main.py)
    mcp_servers: list[str] = Field(
        default_factory=lambda: [
            "github", "notion", "figma", "wordpress", "gmail",
            "brave-search", "bright", "perplexity", "crawl4ai", "playwright"
        ],
        description="Available MCP servers"
    )

    # API Configuration (used in llm_driven_api_tool.py)
    apidog_timeout: int = Field(default=30, ge=1, le=120, description="API timeout in seconds")

    # LLM API Integration Settings (used in llm_driven_api_tool.py)
    llm_api_enabled: bool = Field(default=True, description="LLM-gesteuerte API-Tools aktivieren")
    llm_api_security_level: str = Field(default="strict", description="Sicherheitslevel für LLM-API-Calls")
    llm_api_rate_limit: int = Field(default=100, description="Max API-Calls pro Stunde pro API")
    llm_api_cache_enabled: bool = Field(default=True, description="API Response Caching aktivieren")
    llm_api_audit_log: bool = Field(default=True, description="API-Call Auditing aktivieren")

    # OpenAPI LLM Settings (used in llm_router.py)
    openapi_llm_model: str = Field(default="Llama-3.2-3B-Instruct-Q4_K_M.gguf", description="LLM für OpenAPI Interpretation")
    openapi_llm_temperature: float = Field(default=0.1, description="Temperature für präzise API-Interpretation")
    openapi_llm_max_tokens: int = Field(default=1000, description="Max Tokens für LLM-Response")

    # Tyk Integration Settings (used in universal_nango_api_tool.py)
    tyk_base_url: str = Field(default="http://localhost:8080", description="Tyk Gateway URL")

    # API Policies - Neue SEKTION (aus Transfer-Doc)
    api_policies: dict = Field(default_factory=lambda: {
        "oauth2": {
            "automatic_refresh": True,
            "refresh_buffer_seconds": 300,
            "max_tokens_per_api": 10
        },
        "api_key": {
            "manual_validation": True,
            "rotation_days": 90,
            "exposure_detection": True
        }
    }, description="API-spezifische Policies")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()