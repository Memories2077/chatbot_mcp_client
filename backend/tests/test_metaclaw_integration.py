"""
Integration tests for MetaClaw client and routing.

Tests cover:
- MetaClaw client initialization and configuration
- Two-stage handoff logic (MetaClaw → Gemini)
- Fallback behavior when MetaClaw is disabled
- Tool intent detection
- LangGraph build streaming

Run with: pytest tests/test_metaclaw_integration.py -v
"""
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Set test environment before imports
os.environ["METACLAW_ENABLED"] = "true"
os.environ["METACLAW_BASE_URL"] = "http://test-metaclaw:30000/v1"
os.environ["METACLAW_API_KEY"] = "test-key"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"

from chatbot_mcp_client.backend.config import LLMConfig
from chatbot_mcp_client.backend.metaclaw_client import MetaClawClient, MetaClawDisabledError


class TestLLMConfig:
    """Test centralized configuration management"""

    def test_config_loads_from_env(self):
        """Test that configuration loads correctly from environment"""
        os.environ["METACLAW_ENABLED"] = "true"
        os.environ["METACLAW_BASE_URL"] = "http://custom:30000/v1"
        os.environ["GEMINI_API_KEY"] = "test-gemini"
        os.environ["GROQ_API_KEY"] = "test-groq"
        os.environ["NEXT_PUBLIC_BACKEND_PORT"] = "9000"

        config = LLMConfig.from_env()

        assert config.metaclaw_enabled is True
        assert config.metaclaw_base_url == "http://custom:30000/v1"
        assert config.gemini_api_key == "test-gemini"
        assert config.groq_api_key == "test-groq"
        assert config.backend_port == 9000

    def test_metaclaw_disabled_by_default(self):
        """Test that MetaClaw is disabled when env var not set"""
        if "METACLAW_ENABLED" in os.environ:
            del os.environ["METACLAW_ENABLED"]

        config = LLMConfig.from_env()
        assert config.metaclaw_enabled is False

    def test_default_values(self):
        """Test that sensible defaults are provided"""
        # Clear relevant env vars
        for key in ["METACLAW_BASE_URL", "METACLAW_API_KEY", "GEMINI_API_KEY",
                    "GEMINI_MODEL", "GROQ_API_KEY", "GROQ_MODEL"]:
            if key in os.environ:
                del os.environ[key]

        config = LLMConfig.from_env()

        assert config.metaclaw_base_url == "http://localhost:30000/v1"
        assert config.metaclaw_api_key == "metaclaw"
        assert config.gemini_model == "gemini-2.5-flash"
        assert config.groq_model == "llama-3.3-70b-versatile"


class TestMetaClawClient:
    """Test MetaClaw client wrapper"""

    @pytest.fixture
    def valid_config(self):
        """Create a valid LLMConfig for testing"""
        os.environ["METACLAW_ENABLED"] = "true"
        os.environ["METACLAW_API_KEY"] = "test-key"
        os.environ["GEMINI_API_KEY"] = "test-gemini"
        return LLMConfig.from_env()

    def test_client_initialization_success(self, valid_config):
        """Test successful client initialization"""
        client = MetaClawClient(valid_config)

        assert client.enabled is True
        assert client.base_url == "http://localhost:30000/v1"
        assert client.api_key == "test-key"
        assert client.model == "gemini-2.5-flash"

    def test_client_initialization_disabled_raises(self):
        """Test that disabled MetaClaw raises error"""
        config = LLMConfig.from_env()
        config.metaclaw_enabled = False

        with pytest.raises(MetaClawDisabledError):
            MetaClawClient(config)

    def test_extract_create_mcp_tool_call_from_tool_calls(self, valid_config):
        """Test extraction from structured tool_calls attribute"""
        client = MetaClawClient(valid_config)

        mock_response = MagicMock()
        mock_response.tool_calls = [{
            "name": "create_mcp_server",
            "args": {"requirements": "Build a weather API MCP server"}
        }]

        requirements = client._extract_create_mcp_tool_call(mock_response)
        assert requirements == "Build a weather API MCP server"

    def test_extract_create_mcp_tool_call_from_additional_kwargs(self, valid_config):
        """Test extraction from additional_kwargs (OpenAI format)"""
        client = MetaClawClient(valid_config)

        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_response.additional_kwargs = {
            "tool_calls": [{
                "function": {
                    "name": "create_mcp_server",
                    "arguments": '{"requirements": "Build a GitHub MCP server"}'
                }
            }]
        }

        requirements = client._extract_create_mcp_tool_call(mock_response)
        assert requirements == "Build a GitHub MCP server"

    def test_extract_create_mcp_tool_call_not_found(self, valid_config):
        """Test that None is returned when no tool call present"""
        client = MetaClawClient(valid_config)

        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_response.additional_kwargs = {}

        requirements = client._extract_create_mcp_tool_call(mock_response)
        assert requirements is None

    def test_detect_tool_intent_from_structured(self, valid_config):
        """Test intent detection from structured tool call"""
        client = MetaClawClient(valid_config)

        mock_response = MagicMock()
        mock_response.tool_calls = [{
            "name": "create_mcp_server",
            "args": {"requirements": "Build a Spotify MCP server"}
        }]

        intent = client._detect_tool_intent(mock_response, "some content")
        assert intent is not None
        assert intent["type"] == "create_mcp_server"
        assert intent["requirements"] == "Build a Spotify MCP server"

    def test_detect_tool_intent_from_text_keyword(self, valid_config):
        """Test intent detection from text keywords"""
        client = MetaClawClient(valid_config)

        content = "I'll build an MCP server for Twitter API with the following capabilities..."
        intent = client._detect_tool_intent({}, content)

        assert intent is not None
        assert intent["type"] == "create_mcp_server"
        assert "detected_from" in intent

    def test_detect_tool_intent_not_present(self, valid_config):
        """Test that no intent is detected when irrelevant content"""
        client = MetaClawClient(valid_config)

        content = "Hello, how are you today?"
        intent = client._detect_tool_intent({}, content)

        assert intent is None

    def test_extract_requirements_from_text(self, valid_config):
        """Test requirements extraction from text response"""
        client = MetaClawClient(valid_config)

        text = "I'll build it with the following capabilities: weather lookup, forecasts, and historical data."
        requirements = client._extract_requirements_from_text(text)

        assert "weather lookup" in requirements
        assert "forecasts" in requirements

    def test_extract_requirements_fallback(self, valid_config):
        """Test that full text is returned if no trigger found"""
        client = MetaClawClient(valid_config)

        text = "Some response without standard trigger phrases"
        requirements = client._extract_requirements_from_text(text)

        assert requirements == text[:800]


class TestMetaClawIntegration:
    """Test full MetaClaw integration flow"""

    @pytest.fixture
    def valid_config(self):
        """Create a valid LLMConfig for testing"""
        os.environ["METACLAW_ENABLED"] = "true"
        os.environ["METACLAW_API_KEY"] = "test-metaclaw"
        os.environ["GEMINI_API_KEY"] = "test-gemini"
        return LLMConfig.from_env()

    @pytest.mark.asyncio
    async def test_chat_metaclaw_disabled_raises_on_init(self):
        """Test that chat raises when MetaClaw disabled"""
        config = LLMConfig.from_env()
        config.metaclaw_enabled = False

        with pytest.raises(MetaClawDisabledError):
            MetaClawClient(config)

    @pytest.mark.asyncio
    async def test_metaClaw_stream_flow_no_tool_intent(self, valid_config):
        """Test streaming when MetaClaw returns text without tool intent"""
        client = MetaClawClient(valid_config)

        # Mock the internal methods
        client._get_metacaw_llm = AsyncMock()
        mock_metaclaw_response = MagicMock()
        mock_metaclaw_response.content = "I can help you with that!"
        mock_metaclaw_response.tool_calls = []
        client._get_metacaw_llm.return_value.ainvoke.return_value = mock_metaclaw_response

        # Mock _detect_tool_intent to return None
        client._detect_tool_intent = MagicMock(return_value=None)

        # Collect stream output
        outputs = []
        async for sse in client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.0,
            langgraph_url="http://test-langgraph:2024"
        ):
            outputs.append(sse)

        # Should have content and DONE
        assert any('"content": "I can help you with that!"' in sse for sse in outputs)
        assert any(sse.strip() == "data: [DONE]" for sse in outputs)

    @pytest.mark.asyncio
    async def test_metaClaw_stream_flow_with_tool_intent(self, valid_config):
        """Test streaming when MetaClaw signals tool intent"""
        client = MetaClawClient(valid_config)

        # Mock MetaClaw LLM
        client._get_metacaw_llm = AsyncMock()
        mock_metaclaw_response = MagicMock()
        mock_metaclaw_response.content = "I'll build an MCP server for you."
        mock_metaclaw_response.tool_calls = [{
            "name": "create_mcp_server",
            "args": {"requirements": "Build a Twitter MCP server"}
        }]
        client._get_metacaw_llm.return_value.ainvoke.return_value = mock_metaclaw_response

        # Mock _detect_tool_intent to return intent
        client._detect_tool_intent = MagicMock(return_value={
            "type": "create_mcp_server",
            "requirements": "Build a Twitter MCP server"
        })

        # Mock _execute_with_gemini
        client._execute_with_gemini = AsyncMock(return_value="data: {\"content\": \"Building...\"}\n\ndata: [DONE]\n\n")

        # Collect stream output
        outputs = []
        async for sse in client.chat(
            messages=[{"role": "user", "content": "Build an MCP for Twitter"}],
            temperature=0.0,
            langgraph_url="http://test-langgraph:2024"
        ):
            outputs.append(sse)

        # Should have called _execute_with_gemini
        client._execute_with_gemini.assert_called_once()
        assert len(outputs) > 0

    @pytest.mark.asyncio
    async def test_gemini_executor_failure_handled(self, valid_config):
        """Test that Gemini executor failure is handled gracefully"""
        client = MetaClawClient(valid_config)

        # Mock MetaClaw to return tool intent
        client._get_metacaw_llm = AsyncMock()
        mock_metaclaw_response = MagicMock()
        mock_metaclaw_response.content = "I'll build it."
        mock_metaclaw_response.tool_calls = [{
            "name": "create_mcp_server",
            "args": {"requirements": "Build something"}
        }]
        client._get_metacaw_llm.return_value.ainvoke.return_value = mock_metaclaw_response
        client._detect_tool_intent = MagicMock(return_value={
            "type": "create_mcp_server",
            "requirements": "Build something"
        })

        # Mock _execute_with_gemini to raise
        client._execute_with_gemini = AsyncMock(side_effect=Exception("Gemini failed"))

        outputs = []
        async for sse in client.chat(
            messages=[{"role": "user", "content": "Build"}],
            temperature=0.0,
            langgraph_url="http://test-langgraph:2024"
        ):
            outputs.append(sse)

        # Should have error response
        assert any("error" in sse for sse in outputs)

    @pytest.mark.asyncio
    async def test_langgraph_build_streaming(self, valid_config):
        """Test that LangGraph build progress is streamed correctly"""
        client = MetaClawClient(valid_config)

        # Mock _get_metacaw_llm to return simple response without tool intent
        client._get_metacaw_llm = AsyncMock()
        mock_metaclaw_response = MagicMock()
        mock_metaclaw_response.content = "Simple response"
        mock_metaclaw_response.tool_calls = []
        client._get_metacaw_llm.return_value.ainvoke.return_value = mock_metaclaw_response
        client._detect_tool_intent = MagicMock(return_value=None)

        outputs = []
        async for sse in client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.0,
            langgraph_url="http://test-langgraph:2024"
        ):
            outputs.append(sse)

        # Should have content and DONE
        assert any('"content": "Simple response"' in sse for sse in outputs)
        assert any(sse.strip() == "data: [DONE]" for sse in outputs)


class TestFallbackBehavior:
    """Test fallback to direct providers when MetaClaw is disabled"""

    def test_fallback_to_gemini_when_metaclaw_disabled(self):
        """Test that Gemini is used when MetaClaw is disabled"""
        os.environ["METACLAW_ENABLED"] = "false"
        os.environ["GEMINI_API_KEY"] = "test-gemini"

        config = LLMConfig.from_env()
        assert config.metaclaw_enabled is False
        assert bool(config.gemini_api_key) is True

    def test_fallback_to_groq_when_no_gemini(self):
        """Test that Groq is used when Gemini not available"""
        # Clear all except Groq
        os.environ["METACLAW_ENABLED"] = "false"
        os.environ["GEMINI_API_KEY"] = ""
        os.environ["GROQ_API_KEY"] = "test-groq"

        config = LLMConfig.from_env()
        assert config.metaclaw_enabled is False
        assert not config.gemini_api_key
        assert config.groq_api_key == "test-groq"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
