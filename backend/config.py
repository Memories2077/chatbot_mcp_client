"""
Centralized Configuration Management

Single source of truth for all LLM provider configurations.
Eliminates scattered os.getenv() calls throughout the codebase.
"""
import os
from dataclasses import dataclass
from typing import List


@dataclass
class LLMConfig:
    """ Unified configuration for all LLM providers """
    # Primary provider selection
    default_provider: str
    gemini_api_key: str
    gemini_model: str
    groq_api_key: str
    groq_model: str

    # MetaClaw proxy configuration
    metaclaw_enabled: bool
    metaclaw_base_url: str
    metaclaw_api_key: str
    metaclaw_model: str

    # General settings
    default_temperature: float
    default_timeout_ms: int

    # Backend settings
    backend_port: int
    langgraph_api_url: str

    # MCP settings
    mcp_connection_timeout: float
    mcp_initialization_timeout: float

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables"""
        # Backend port with validation
        try:
            backend_port = int(os.getenv("NEXT_PUBLIC_BACKEND_PORT", "8000"))
        except (ValueError, TypeError):
            backend_port = 8000

        # LangGraph API URL with Docker fallback
        langgraph_url = (
            os.getenv("NEXT_PUBLIC_LANGGRAPH_API_URL")
            or os.getenv("LANGGRAPH_API_URL")
            or "http://localhost:2024"
        )

        return cls(
            # Primary provider
            default_provider=os.getenv("LLM_PROVIDER", "gemini"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),

            # MetaClaw proxy
            metaclaw_enabled=os.getenv("METACLAW_ENABLED", "false").lower() == "true",
            metaclaw_base_url=os.getenv("METACLAW_BASE_URL", "http://localhost:30000/v1"),
            metaclaw_api_key=os.getenv("METACLAW_API_KEY", "metaclaw"),
            metaclaw_model=os.getenv("METACLAW_MODEL", "gemini-2.5-flash"),

            # General settings
            default_temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            default_timeout_ms=int(os.getenv("LLM_TIMEOUT_MS", "300000")),

            # Backend settings
            backend_port=backend_port,
            langgraph_api_url=langgraph_url,

            # MCP settings
            mcp_connection_timeout=float(os.getenv("MCP_CONNECTION_TIMEOUT", "10.0")),
            mcp_initialization_timeout=float(os.getenv("MCP_INIT_TIMEOUT", "10.0")),
        )

    def get_llm_provider(self, provider_override: str = None) -> str:
        """Get the effective provider to use"""
        if provider_override:
            return provider_override
        return self.default_provider

    def is_metaclaw_enabled(self) -> bool:
        """Check if MetaClaw proxy routing is enabled"""
        return self.metaclaw_enabled

    def get_metaclaw_config(self) -> dict:
        """Get MetaClaw-specific configuration"""
        return {
            "base_url": self.metaclaw_base_url,
            "api_key": self.metaclaw_api_key,
            "model": self.metaclaw_model,
            "enabled": self.metaclaw_enabled,
        }


# Global configuration instance (loaded once at module import)
config = LLMConfig.from_env()
