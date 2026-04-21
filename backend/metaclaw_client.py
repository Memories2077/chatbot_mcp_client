"""
MetaClaw Client Wrapper

Encapsulates all MetaClaw-specific logic into a single, reusable client.
Handles two-stage routing: MetaClaw (intent detection) → Gemini (execution).
"""
import os
import json
from typing import Optional, Dict, Any, AsyncGenerator
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool

from .config import LLMConfig


# Global cache for the core tool instance
_create_mcp_server_tool_instance = None


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

        if not self.enabled:
            raise MetaClawDisabledError("MetaClaw is disabled in configuration")

    def _create_mcp_server_tool(self):
        """Create the create_mcp_server tool (singleton pattern)"""
        # Use module-level caching to avoid redefining tool
        global _create_mcp_server_tool_instance
        if _create_mcp_server_tool_instance is None:
            @tool
            async def create_mcp_server(requirements: str) -> str:
                """
                Builds a custom MCP server. Call this tool IMMEDIATELY as soon as the user provides
                technical requirements, API documentation, or a guide that implies they want a tool
                or server built.
                Do NOT ask for permission or confirmation first—assume the user wants you to generate
                the server based on their input.
                Args:
                    requirements: Detailed description of the MCP server functionality and tools needed.
                """
                return f"GENERATE_MCP_SERVER_TRIGGERED:{requirements}"
            _create_mcp_server_tool_instance = create_mcp_server
        return _create_mcp_server_tool_instance

    def _extract_create_mcp_tool_call(self, response) -> Optional[str]:
        """
        Extract create_mcp_server tool call from MetaClaw response.
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

    def _detect_tool_intent(self, response, content_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze MetaClaw's response to detect if it wants to call tools.
        Returns dict with type and requirements if intent detected, None otherwise.
        """
        # Check for structured tool call first
        requirements = self._extract_create_mcp_tool_call(response)
        if requirements:
            return {"type": "create_mcp_server", "requirements": requirements}

        # Fallback: keyword scan
        keywords = [
            "create_mcp_server", "build an mcp server", "build a mcp server",
            "build mcp server", "create an mcp server", "create a mcp server",
            "generate mcp server", "i have initiated the build", "i'll build",
            "i will build", "i'll create", "i will create", "generating the mcp server",
            "starting the build", "start building", "let me build", "let me create",
        ]
        lower_content = content_text.lower()
        for keyword in keywords:
            if keyword in lower_content:
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

    async def _get_metaclaw_llm(self, temperature: float) -> BaseLanguageModel:
        """Initialize MetaClaw LLM with create_mcp_server tool bound"""
        base_url = self.base_url
        if "localhost" in base_url and os.path.exists("/.dockerenv"):
            base_url = base_url.replace("localhost", "host.docker.internal")

        return ChatOpenAI(
            model=self.model,
            temperature=temperature,
            api_key=self.api_key,
            base_url=base_url,
            max_retries=2,
        ).bind_tools([self._create_mcp_server_tool()])

    async def _get_gemini_executor(self, temperature: float) -> BaseLanguageModel:
        """Initialize Gemini executor for tool execution"""
        gemini_key = self.config.gemini_api_key
        if not gemini_key:
            raise MetaClawError("GEMINI_API_KEY not set for MetaClaw executor")

        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=temperature,
            max_retries=2,
            api_key=gemini_key,
        ).bind_tools([self._create_mcp_server_tool()])

    async def _stream_langgraph_build(self, requirements: str, langgraph_url: str) -> AsyncGenerator[str, None]:
        """Stream LangGraph build progress (SSE format)"""
        # Normalize URL for Docker
        if "localhost" in langgraph_url and os.path.exists("/.dockerenv"):
            langgraph_url = langgraph_url.replace("localhost", "host.docker.internal")

        yield f"data: {json.dumps({'content': chr(10) + chr(10) + '> [SYSTEM]: Building MCP Server...' + chr(10) + chr(10)})}\n\n"

        try:
            from langgraph_sdk import get_client
            lg_client = get_client(url=langgraph_url)
            thread = await lg_client.threads.create()

            partial_content_lengths = {}
            streamed_ids = set()
            last_msg_id = ""

            async for lg_chunk in lg_client.runs.stream(
                thread["thread_id"],
                "agent",
                input={"messages": [{"role": "user", "content": requirements}]},
                stream_mode="messages"
            ):
                event_type = lg_chunk.event
                data = lg_chunk.data

                if event_type == "error":
                    error_content = f"\n\n❌ LANGGRAPH ERROR:\n{json.dumps(data, indent=2)}\n\n"
                    yield f"data: {json.dumps({'content': error_content})}\n\n"
                    continue

                if event_type == "metadata":
                    continue

                if event_type == "messages/partial" and isinstance(data, list):
                    for msg_chunk in data:
                        msg_id = msg_chunk.get("id")
                        content = msg_chunk.get("content", "")
                        if msg_id and isinstance(content, str):
                            if msg_id != last_msg_id:
                                if last_msg_id:
                                    yield f"data: {json.dumps({'content': chr(10)})}\n\n"
                                last_msg_id = msg_id
                                partial_content_lengths[msg_id] = 0

                            streamed_ids.add(msg_id)
                            last_len = partial_content_lengths.get(msg_id, 0)
                            if len(content) > last_len:
                                new_part = content[last_len:]
                                yield f"data: {json.dumps({'content': new_part})}\n\n"
                                partial_content_lengths[msg_id] = len(content)

                elif event_type == "messages/complete" and isinstance(data, list):
                    for msg_chunk in data:
                        msg_id = msg_chunk.get("id")
                        content = msg_chunk.get("content", "")
                        if msg_id and isinstance(content, str):
                            if msg_id in streamed_ids:
                                yield f"data: {json.dumps({'content': chr(10)})}\n\n"
                            else:
                                if content:
                                    yield f"data: {json.dumps({'content': f'{chr(10)}{content}{chr(10)}'})}\n\n"
                            partial_content_lengths.pop(msg_id, None)
                            streamed_ids.discard(msg_id)
                            last_msg_id = ""

            print("--- LANGGRAPH BUILD COMPLETED ---")

        except Exception as lg_err:
            print(f"LangGraph Error: {lg_err}")
            err_msg = f"\n\n> [ERROR]: Cannot connect to LangGraph service: {str(lg_err)}\n\n"
            yield f"data: {json.dumps({'content': err_msg})}\n\n"

    async def chat(
        self,
        messages: list,
        temperature: float,
        langgraph_url: str
    ) -> AsyncGenerator[str, None]:
        """
        Process chat request through MetaClaw with two-stage handoff.

        Args:
            messages: List of message dicts with role and content
            temperature: LLM temperature setting
            langgraph_url: URL for LangGraph build service

        Yields:
            SSE-formatted strings for streaming response
        """
        # Prepare MetaClaw messages
        last_turn_index = len(messages) - 1
        metaclaw_system = f"""You are a helpful and intelligent AI assistant with deep knowledge of APIs, MCP servers, and tool building.
The conversation history is provided with [Turn Index] and [Timestamp] for each message.
The current message is [Turn {last_turn_index}].

IMPORTANT: If the user provides an API guide, technical documentation, or any requirements that could be used to build an MCP server, you should clearly state that you will build it and describe what tools and capabilities the server will have.

LANGUAGE: Always respond in the same language the user is using. If the user writes in Vietnamese, respond in Vietnamese. If in English, respond in English. Match their language automatically for every message.
"""

        metaclaw_msgs = [SystemMessage(content=metaclaw_system)]
        for msg in messages:
            if msg.get("role") == "user":
                metaclaw_msgs.append(HumanMessage(content=msg.get("content", "")))
            else:
                metaclaw_msgs.append(AIMessage(content=msg.get("content", "")))

        try:
            # Stage 1: Invoke MetaClaw
            metaclaw_llm = await self._get_metaclaw_llm(temperature)
            metaclaw_response = await metaclaw_llm.ainvoke(metaclaw_msgs)

            content_text = ""
            if hasattr(metaclaw_response, "content"):
                content_text = metaclaw_response.content or ""
            elif isinstance(metaclaw_response, dict):
                content_text = metaclaw_response.get("content", "")
            else:
                content_text = str(metaclaw_response)

            print(f"[MetaClaw] Response length: {len(content_text)} chars")
            print(f"[MetaClaw] Response preview: {content_text[:300]}...")

            # Check for tool intent
            intent = self._detect_tool_intent(metaclaw_response, content_text)

            if intent:
                print(f"[MetaClaw] Tool intent detected: {intent['type']}")
                print(f"[MetaClaw] Requirements: {intent.get('requirements', '')[:200]}...")
                yield await self._execute_with_gemini(intent, messages, content_text, temperature, langgraph_url)
            else:
                print("[MetaClaw] No tool intent, streaming directly")
                yield f"data: {json.dumps({'content': content_text})}\n\n"
                yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = str(e)
            print(f"[MetaClaw] Error: {error_msg}")
            yield f"data: {json.dumps({'error': f'MetaClaw error: {error_msg}'})}\n\n"
            yield "data: [DONE]\n\n"

    async def _execute_with_gemini(
        self,
        intent: Dict[str, Any],
        original_messages: list,
        metaclaw_context: str,
        temperature: float,
        langgraph_url: str
    ) -> str:
        """
        Hand off to Gemini for tool execution.
        Returns the full SSE response as a string.
        """
        requirements = intent.get("requirements", "")

        gemini_system = f"""You are an autonomous MCP server builder assistant.
MetaClaw (the decision-making brain) has already analyzed the user's request and decided that an MCP server should be built.
Your job is to execute this decision by calling the create_mcp_server tool with the appropriate requirements.

DO NOT ask for permission or confirmation — just execute the build immediately.
DO NOT respond with text explanations — just trigger the tool and let the system handle progress reporting.

Requirements from MetaClaw's analysis:
{requirements}
"""

        gemini_msgs = [SystemMessage(content=gemini_system)]
        for msg in original_messages:
            if msg.get("role") == "user":
                gemini_msgs.append(HumanMessage(content=msg.get("content", "")))
            else:
                gemini_msgs.append(AIMessage(content=msg.get("content", "")))
        if metaclaw_context:
            gemini_msgs.append(AIMessage(content=f"[MetaClaw Analysis]: {metaclaw_context[:500]}"))

        print(f"[Gemini] Executing with {len(gemini_msgs)} messages, requirements: {requirements[:100]}...")

        try:
            gemini_agent = await self._get_gemini_executor(temperature)
        except Exception as e:
            error_msg = str(e)
            return f"data: {json.dumps({'content': f'\\n\\n> [ERROR]: Cannot create Gemini executor: {error_msg}\\n\\n'})}\n\ndata: [DONE]\n\n"

        # Collect all SSE events into a single string
        sse_parts = []
        try:
            gemini_response = await gemini_agent.ainvoke(gemini_msgs)
            print(f"[Gemini] Response type: {type(gemini_response)}")

            detected_requirements = self._extract_create_mcp_tool_call(gemini_response)

            if detected_requirements is not None:
                build_requirements = detected_requirements or requirements
                print(f"[Gemini] TRIGGERING LANGGRAPH BUILD: {build_requirements[:100]}...")
            else:
                print(f"[Gemini] No tool call found, triggering LangGraph directly with MetaClaw requirements")
                build_requirements = requirements

            # Stream LangGraph build
            async for sse in self._stream_langgraph_build(build_requirements, langgraph_url):
                sse_parts.append(sse)

        except Exception as e:
            sse_parts.append(f"data: {json.dumps({'error': str(e)})}\n\n")
        finally:
            sse_parts.append("data: [DONE]\n\n")

        return "".join(sse_parts)
