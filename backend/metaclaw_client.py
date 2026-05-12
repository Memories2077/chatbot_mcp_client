"""
MetaClaw Client Wrapper

Encapsulates all MetaClaw-specific logic into a single, reusable client.
Handles two-stage routing: MetaClaw (intent detection) → Gemini (execution).
"""
import os
import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator, List, cast
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from config import LLMConfig
from shared import (
    create_mcp_server_tool,
    create_use_mcp_tools_tool,
    extract_create_mcp_tool_call,
    extract_use_mcp_tool_call,
    stream_langgraph_build,
    normalize_docker_urls_in_dict,
)

logger = logging.getLogger(__name__)


def sse_event(payload: Dict[str, Any]) -> str:
    """Format a typed SSE data payload."""
    return f"data: {json.dumps(payload)}\n\n"


def sse_content(content: str) -> str:
    """Emit a typed content event while preserving the legacy content field."""
    return sse_event({"type": "content", "content": content})


def sse_error(error: str) -> str:
    """Emit a typed error event while preserving the legacy error field."""
    return sse_event({"type": "error", "error": error})


def sse_done() -> str:
    """Emit typed done plus legacy [DONE] sentinel."""
    return f"data: {json.dumps({'type': 'done'})}\n\ndata: [DONE]\n\n"


class MetaClawError(Exception):
    """Base exception for MetaClaw client errors"""
    pass


class MetaClawDisabledError(MetaClawError):
    """Raised when MetaClaw is disabled in configuration"""
    pass


class MetaClawClient:
    """
    MetaClaw client with two-stage handoff capability.

    Stage 1: Send user request to MetaClaw with create_mcp_server tool bound
    Stage 2: If MetaClaw signals tool intent, hand off to Gemini for execution
             Otherwise, stream MetaClaw's text response directly
    """

    def __init__(self, config: LLMConfig, model_name: Optional[str] = None):
        """
        Initialize MetaClaw client.

        Args:
            config: LLMConfig instance with MetaClaw settings
            model_name: Optional override for the MetaClaw model

        Raises:
            MetaClawDisabledError: If MetaClaw is not enabled in config
        """
        self.config = config
        self.enabled = config.metaclaw_enabled
        self.base_url = config.metaclaw_base_url
        self.api_key = config.metaclaw_api_key
        self.model = model_name if model_name else config.metaclaw_model
        self.mcp_tools: List[Any] = [] # Storage for tools metadata

        if not self.enabled:
            raise MetaClawDisabledError("MetaClaw is disabled in configuration")

    def _get_mcp_tools_description(self) -> str:
        """Helper to format MCP tools metadata for the prompt."""
        if not self.mcp_tools:
            return "No external MCP tools are currently connected."
        
        descriptions = []
        for tool in self.mcp_tools:
            name = getattr(tool, "name", "unknown")
            desc = getattr(tool, "description", "no description")
            descriptions.append(f"- {name}: {desc}")
            
        return "The following external MCP tools are AVAILABLE via the `use_mcp_tools` handoff:\n" + "\n".join(descriptions)

    def _extract_create_mcp_tool_call(self, response: Any) -> Optional[str]:
        """
        Extract create_mcp_server tool call from response.
        Returns requirements string if found, None otherwise.
        """
        tool_calls = []

        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = response.tool_calls
        elif hasattr(response, "additional_kwargs"):
            raw = response.additional_kwargs.get("tool_calls", [])
            for tc in raw:
                func = tc.get("function", {}) if isinstance(tc, dict) else {}
                name = func.get("name", "")
                if name == "create_mcp_server":
                    args_raw = func.get("arguments", "{}")
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    except Exception:
                        args = {}
                    return args.get("requirements", "") if isinstance(args, dict) else ""
            return None

        for tc in tool_calls:
            tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            if tc_name == "create_mcp_server":
                tc_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                if isinstance(tc_args, str):
                    try:
                        tc_args = json.loads(tc_args)
                    except Exception:
                        tc_args = {}
                return tc_args.get("requirements", "") if isinstance(tc_args, dict) else ""

        return None

    def _extract_use_mcp_tool_call(self, response: Any) -> bool:
        """Check if response contains a use_mcp_tools tool call."""
        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = response.tool_calls
        elif hasattr(response, "additional_kwargs"):
            raw = response.additional_kwargs.get("tool_calls", [])
            for tc in raw:
                func = tc.get("function", {}) if isinstance(tc, dict) else {}
                name = func.get("name", "")
                if name == "use_mcp_tools":
                    return True
            return False
        for tc in tool_calls:
            tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            if tc_name == "use_mcp_tools":
                return True
        return False

    def _detect_tool_intent(self, response, content_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze MetaClaw's response to detect if it wants to call tools.
        Returns dict with type and requirements if intent detected, None otherwise.
        """
        # Check for structured tool call first using instance method
        requirements = self._extract_create_mcp_tool_call(response)
        if requirements is not None:
            return {"type": "create_mcp_server", "requirements": requirements}

        # Check for use_mcp_tools tool call
        if self._extract_use_mcp_tool_call(response):
            return {"type": "use_mcp_tools"}

        # Fallback: keyword scan
        keywords = [
            "create_mcp_server", "build an mcp server", "build a mcp server",
            "build mcp server", "create an mcp server", "create a mcp server",
            "generate mcp server", "i have initiated the build", "i'll build",
            "i will build", "i'll create", "i will create", "generating the mcp server",
            "starting the build", "start building", "let me build", "let me create",
            "use_mcp_tools", "handoff to mcp", "using mcp tools",
        ]
        lower_content = content_text.lower()
        for keyword in keywords:
            if keyword in lower_content:
                # If it mentions using existing tools, trigger handoff
                if "use" in keyword or "handoff" in keyword:
                     return {"type": "use_mcp_tools"}
                
                requirements = self._extract_requirements_from_text(content_text)
                return {"type": "create_mcp_server", "requirements": requirements, "detected_from": "text"}

        return None

    def _extract_requirements_from_text(self, text: str) -> str:
        """Extract MCP server requirements from MetaClaw's text response"""
        triggers = [
            "with the following capabilities:", "includes:",
            "the server will include:", "capabilities:",
            "the following tools:", "tools:",
        ]
        for trigger in triggers:
            idx = text.lower().find(trigger.lower())
            if idx != -1:
                extracted = text[idx + len(trigger):].strip()
                return extracted[:500] if extracted else text[:500]
        return text[:800]

    async def _get_metaclaw_llm(self, temperature: float, session_done: bool = False) -> Any:
        """Initialize MetaClaw LLM with create_mcp_server tool bound"""
        base_url = self.base_url
        if "localhost" in base_url and os.path.exists("/.dockerenv"):
            base_url = base_url.replace("localhost", "host.docker.internal")

        # Prepare custom headers for session_done (MetaClaw-specific, not standard OpenAI API)
        headers = {"X-Session-Done": "true"} if session_done else None

        logger.info(f"Initializing MetaClaw LLM: model={self.model}, base_url={base_url}")

        return ChatOpenAI(
            model=self.model,
            temperature=temperature,
            api_key=self.api_key,  # type: ignore
            base_url=base_url,
            max_retries=2,
            default_headers=headers,
            top_p=self.config.metaclaw_top_p,
            max_completion_tokens=self.config.metaclaw_max_tokens,
        ).bind_tools([create_mcp_server_tool(), create_use_mcp_tools_tool()])

    async def _get_gemini_executor(self, temperature: float):
        """Initialize Gemini executor for tool execution"""
        gemini_key = self.config.gemini_api_key
        if not gemini_key:
            raise MetaClawError("GEMINI_API_KEY not set for MetaClaw executor")

        logger.info("Initializing Gemini executor: model=gemini-2.5-flash")

        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=temperature,
            max_retries=2,
            api_key=gemini_key,  # type: ignore
        ).bind_tools([create_mcp_server_tool()])

    async def _get_fallback_llm(self, temperature: float):
        """
        Initialize the fallback LLM (Gemini or Groq) for casual chat.
        Prioritizes Gemini if configured, otherwise Groq.
        """
        # Respect llm_config.default_provider first
        if self.config.default_provider == "gemini" and self.config.gemini_api_key:
            logger.info(f"Using Gemini as fallback: model={self.config.gemini_model}")
            return ChatGoogleGenerativeAI(
                model=self.config.gemini_model,
                temperature=temperature,
                max_retries=2,
                api_key=self.config.gemini_api_key,  # type: ignore
            )
        elif self.config.default_provider == "groq" and self.config.groq_api_key:
            logger.info(f"Using Groq as fallback: model={self.config.groq_model}")
            return cast(Any, ChatGroq)(
                model=self.config.groq_model,
                temperature=temperature,
                api_key=self.config.groq_api_key,
            )
        else:
            # Fallback to any available key if default_provider not explicitly set or keys missing
            if self.config.gemini_api_key:
                logger.info("[MetaClawClient] Using Gemini for fallback (default provider not explicitly set or invalid).")
                return ChatGoogleGenerativeAI(
                    model=self.config.gemini_model,
                    temperature=temperature,
                    max_retries=2,
                    api_key=self.config.gemini_api_key,  # type: ignore
                )
            elif self.config.groq_api_key:
                logger.info("[MetaClawClient] Using Groq for fallback (default provider not explicitly set or invalid).")
                return cast(Any, ChatGroq)(
                    model=self.config.groq_model,
                    temperature=temperature,
                    api_key=self.config.groq_api_key,
                )
            else:
                raise MetaClawError("No fallback LLM provider configured (GEMINI_API_KEY or GROQ_API_KEY missing.)")

    async def chat(
        self,
        messages: list,
        temperature: float,
        langgraph_url: str,
        mcp_urls: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process chat request through MetaClaw with two-stage handoff.
        MetaClaw acts as a pure Intent Router.
        """
        # Prepare MetaClaw messages
        last_turn_index = len(messages) - 1
        
        # Pure Router System Prompt
        metaclaw_system = f"""You are the Ethereal Intelligence Intent Router.
Your SOLE purpose is to route the user's request to the correct handler.

ROUTING RULES:
1. CREATE: If the user provides documentation/API requirements or asks to BUILD/GENERATE/CREATE a new MCP server, call `create_mcp_server`.
2. HANDOFF: If the user's request involves TOOLS in any way (using them, asking what they are, asking about their parameters, or inquiring about their capabilities), you MUST call `use_mcp_tools` immediately. 
   IMPORTANT: You do NOT have access to tool documentation or schemas. Only the execution agent does.
3. CHAT: If the request is purely social (greetings, general questions, philosophy) and requires NO tools or data, respond directly.

CONNECTED MCP SERVERS: {", ".join(mcp_urls) if mcp_urls else "None"}.

STRATEGY: When in doubt, call `use_mcp_tools`. It is always better to hand off than to provide an incomplete answer about tools you cannot see.

LANGUAGE: Always respond in the same language as the user.
"""

        from langchain_core.messages import BaseMessage
        metaclaw_msgs: list[BaseMessage] = [SystemMessage(content=metaclaw_system)]
        for msg in messages:
            if msg.get("role") == "user":
                metaclaw_msgs.append(HumanMessage(content=msg.get("content", "")))
            else:
                metaclaw_msgs.append(AIMessage(content=msg.get("content", "")))

        try:
            # Stage 1: Invoke MetaClaw with session_done=True to trigger memory ingestion
            metaclaw_llm = await self._get_metaclaw_llm(temperature, session_done=True)
            metaclaw_response = await metaclaw_llm.ainvoke(metaclaw_msgs)

            raw_content = getattr(cast(Any, metaclaw_response), "content", None)
            if raw_content is None and isinstance(metaclaw_response, dict):
                raw_content = metaclaw_response.get("content", "")
            content_text = str(raw_content) if raw_content is not None else str(metaclaw_response)

            logger.info(f"[MetaClaw] Response length: {len(content_text)} chars")
            logger.debug(f"[MetaClaw] Response preview: {content_text[:300]}...")

            # Check for tool intent
            intent = self._detect_tool_intent(metaclaw_response, content_text)

            if intent:
                logger.info(f"[MetaClaw] Tool intent detected: {intent['type']}")
                if intent["type"] == "create_mcp_server":
                    logger.info(f"[MetaClaw] Requirements: {intent.get('requirements', '')[:200]}...")
                    async for sse in self._execute_with_gemini(intent, messages, content_text, temperature, langgraph_url):
                        yield sse
                elif intent["type"] == "use_mcp_tools":
                    logger.info("[MetaClaw] Signaling main to use standard agent with MCP tools.")
                    # Send control event to main to switch to standard agent flow
                    yield f"data: {json.dumps({'__use_standard_agent__': True})}\n\n"
                    return
            else:
                logger.info(f"[MetaClaw] No tool intent. Feeding MetaClaw's memory-enriched context to fallback provider ({self.config.default_provider}).")

                # Get the fallback LLM for casual chat
                fallback_llm = await self._get_fallback_llm(temperature)

                # Prepare messages for the fallback LLM
                # Use a general system prompt for fallback
                fallback_system_prompt = f"""You are a helpful and intelligent AI assistant.
The conversation history is provided with [Turn Index] and [Timestamp] for each message.
The current message is [Turn {last_turn_index}].

MetaClaw (the intent router) has processed the previous messages and its internal memory,
and has provided the following additional context/response which you should incorporate
into your reply, but do NOT directly quote it unless necessary.
This context is to guide your response and ensure continuity with MetaClaw's memory system.

MetaClaw's Context: {content_text}

LANGUAGE: Always respond in the same language the user is using. If the user writes in Vietnamese, respond in Vietnamese. If in English, respond in English. Match their language automatically for every message.
"""
                from langchain_core.messages import BaseMessage
                fallback_messages: list[BaseMessage] = [SystemMessage(content=fallback_system_prompt)]
                for msg in messages:
                    if msg.get("role") == "user":
                        fallback_messages.append(HumanMessage(content=msg.get("content", "")))
                    else:
                        fallback_messages.append(AIMessage(content=msg.get("content", "")))

                # Stream response from the fallback LLM
                async for chunk in fallback_llm.astream(fallback_messages):
                    content = getattr(cast(Any, chunk), "content", None)
                    if content is None and isinstance(chunk, dict):
                        content = chunk.get("content")
                    if content:
                        yield sse_content(str(content))
                yield sse_done()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[MetaClaw] Error: {error_msg}")
            yield sse_error(f"MetaClaw error: {error_msg}")
            yield sse_done()

    async def _execute_with_gemini(
        self,
        intent: Dict[str, Any],
        original_messages: list,
        metaclaw_context: str,
        temperature: float,
        langgraph_url: str
    ) -> AsyncGenerator[str, None]:
        """
        Hands off to Gemini for tool execution.
        Yields SSE chunks directly from the LangGraph build stream.
        """
        import logging

        logger = logging.getLogger(__name__)
        requirements = intent.get("requirements", "")

        try:
            gemini_agent = await self._get_gemini_executor(temperature)
        except Exception as e:
            error_msg = str(e)
            yield sse_content(f"\n\n> [ERROR]: Cannot create Gemini executor: {error_msg}\n\n")
            yield sse_done()
            return

        try:
            # Build Gemini messages inline
            gemini_system = f"""You are an autonomous MCP server builder assistant.
MetaClaw (the decision-making brain) has already analyzed the user's request and decided that an MCP server should be built.
Your job is to execute this decision by calling the create_mcp_server tool with the appropriate requirements.

DO NOT ask for permission or confirmation — just execute the build immediately.
DO NOT respond with text explanations — just trigger the tool and let the system handle progress reporting.

Requirements from MetaClaw's analysis:
{requirements}
"""
            from langchain_core.messages import BaseMessage
            gemini_msgs: list[BaseMessage] = [SystemMessage(content=gemini_system)]
            for msg in original_messages:
                if msg.get("role") == "user":
                    gemini_msgs.append(HumanMessage(content=msg.get("content", "")))
                else:
                    gemini_msgs.append(AIMessage(content=msg.get("content", "")))
            if metaclaw_context:
                gemini_msgs.append(AIMessage(content=f"[MetaClaw Analysis]: {metaclaw_context[:500]}"))

            logger.info(f"[Gemini] Executing with {len(gemini_msgs)} messages, requirements: {requirements[:100]}...")

            gemini_response = await gemini_agent.ainvoke(gemini_msgs)
            logger.info(f"[Gemini] Response type: {type(gemini_response)}")

            detected_requirements = self._extract_create_mcp_tool_call(gemini_response)

            if detected_requirements is not None:
                build_requirements = detected_requirements or requirements
                logger.info(f"[Gemini] TRIGGERING LANGGRAPH BUILD: {build_requirements[:100]}...")
            else:
                logger.info(f"[Gemini] No tool call found, triggering LangGraph directly with MetaClaw requirements")
                build_requirements = requirements

            # Stream LangGraph build - yield chunks directly
            async for sse_chunk in stream_langgraph_build(build_requirements, langgraph_url):
                yield sse_chunk
            yield f"data: {json.dumps({'type': 'mcp_build_complete', 'status': 'running', 'message': 'MCP Server built successfully!'})}\n\n"
            yield sse_done()

        except Exception as e:
            logger.exception("Error during Gemini execution")
            yield sse_error(str(e))
            yield sse_done()
