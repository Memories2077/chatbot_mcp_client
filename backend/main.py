import asyncio
import os
import json
import re
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from langchain_core.language_models import BaseLanguageModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from dotenv import load_dotenv
load_dotenv()

# For local development, read the port from .env and ensure it's a valid integer.
# This is ignored in Docker, which uses the 'command' from docker-compose.yml.
try:
    backend_port = int(os.getenv("NEXT_PUBLIC_BACKEND_PORT", "8000"))
except (ValueError, TypeError):
    backend_port = 8000

class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    provider: Optional[str] = "gemini"
    model: Optional[str] = "gemini-2.5-flash"
    temperature: Optional[float] = 0.0
    mcpServers: Optional[List[str]] = []

class AgentState:
    def __init__(self):
        self.agent = None
        self.exit_stacks = []
        self.current_provider = None
        self.current_model = None
        self.current_mcp_urls = []
        self.current_temperature = None
        self.lock = asyncio.Lock()

state = AgentState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    print("\n--- SHUTTING DOWN: Closing all MCP sessions... ---")
    for exit_stack in state.exit_stacks:
        try:
            await exit_stack.aclose()
        except Exception:
            pass
    state.exit_stacks = []
    print("All MCP sessions closed cleanly.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Shared Tool Definition (single source of truth)                      #
# ------------------------------------------------------------------ #

_create_mcp_server_tool_instance = None

def _create_mcp_server_tool():
    """Return the create_mcp_server tool, creating it once and caching it."""
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


# ------------------------------------------------------------------ #
# Shared Helper: Extract create_mcp_server tool call from a response  #
# ------------------------------------------------------------------ #

def _extract_create_mcp_tool_call(response) -> str | None:
    """
    Check a LangChain response message for a create_mcp_server tool call.
    Returns the requirements string if found, None otherwise.
    Handles both .tool_calls and .additional_kwargs['tool_calls'] formats.
    """
    tool_calls = []

    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_calls = response.tool_calls
    elif hasattr(response, "additional_kwargs"):
        raw = response.additional_kwargs.get("tool_calls", [])
        # Normalize provider-specific format: {function: {name, arguments}}
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
        return None  # No matching tool in additional_kwargs

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


# ------------------------------------------------------------------ #
# Shared Helper: Stream a LangGraph build run                          #
# ------------------------------------------------------------------ #

async def _stream_langgraph_build(requirements: str) -> AsyncGenerator[str, None]:
    """
    Stream LangGraph build run with full SSE event handling (messages/partial,
    messages/complete, metadata, error) and deduplication logic.
    Yields SSE-formatted strings.
    """
    lg_url = (
        os.getenv("NEXT_PUBLIC_LANGGRAPH_API_URL")
        or os.getenv("LANGGRAPH_API_URL")
        or "http://localhost:2024"
    )
    if "localhost" in lg_url and os.path.exists("/.dockerenv"):
        lg_url = lg_url.replace("localhost", "host.docker.internal")

    print(f"Connecting to LangGraph at: {lg_url}")

    # Yield a system message indicating build start
    yield f"data: {json.dumps({'content': chr(10) + chr(10) + '> [SYSTEM]: Building MCP Server...' + chr(10) + chr(10)})}\n\n"

    try:
        lg_client = get_client(url=lg_url)
        thread = await lg_client.threads.create()

        # Track partial streaming state per message ID
        partial_content_lengths = {}  # msg_id -> last length yielded
        streamed_ids = set()          # msg_ids that have been streamed via partial
        last_msg_id = ""

        async for lg_chunk in lg_client.runs.stream(
            thread["thread_id"],
            "agent",
            input={"messages": [{"role": "user", "content": requirements}]},
            stream_mode="messages"
        ):
            event_type = lg_chunk.event
            data = lg_chunk.data

            # Handle error events
            if event_type == "error":
                error_content = f"\n\n❌ LANGGRAPH ERROR:\n{json.dumps(data, indent=2)}\n\n"
                yield f"data: {json.dumps({'content': error_content})}\n\n"
                continue

            # Handle metadata events (optional: could be logged or ignored)
            if event_type == "metadata":
                # You can choose to yield metadata if needed, or just log
                print(f"Metadata: {data}")
                continue

            # Handle partial message chunks
            if event_type == "messages/partial" and isinstance(data, list):
                for msg_chunk in data:
                    msg_id = msg_chunk.get("id")
                    content = msg_chunk.get("content", "")
                    if msg_id and isinstance(content, str):
                        # New message? Reset state
                        if msg_id != last_msg_id:
                            if last_msg_id:
                                yield f"data: {json.dumps({'content': chr(10)})}\n\n"  # newline between messages
                            last_msg_id = msg_id
                            partial_content_lengths[msg_id] = 0

                        streamed_ids.add(msg_id)
                        last_len = partial_content_lengths.get(msg_id, 0)
                        if len(content) > last_len:
                            new_part = content[last_len:]
                            yield f"data: {json.dumps({'content': new_part})}\n\n"
                            partial_content_lengths[msg_id] = len(content)

            # Handle complete messages
            elif event_type == "messages/complete" and isinstance(data, list):
                for msg_chunk in data:
                    msg_id = msg_chunk.get("id")
                    content = msg_chunk.get("content", "")
                    if msg_id and isinstance(content, str):
                        if msg_id in streamed_ids:
                            # Already printed via partial, just add newline if needed
                            yield f"data: {json.dumps({'content': chr(10)})}\n\n"
                        else:
                            # Never streamed (e.g., tool result, system message) → print whole content
                            if content:
                                yield f"data: {json.dumps({'content': f'{chr(10)}{content}{chr(10)}'})}\n\n"
                        # Clean up tracking for this message
                        partial_content_lengths.pop(msg_id, None)
                        streamed_ids.discard(msg_id)
                        last_msg_id = ""

        print("--- LANGGRAPH BUILD COMPLETED ---")

    except Exception as lg_err:
        print(f"LangGraph Error: {lg_err}")
        err_msg = f"\n\n> [ERROR]: Cannot connect to LangGraph service: {str(lg_err)}\n\n"
        yield f"data: {json.dumps({'content': err_msg})}\n\n"

# ------------------------------------------------------------------ #
# MetaClaw Intent Detection Helpers                                    #
# ------------------------------------------------------------------ #

_TOOL_INTENT_KEYWORDS = [
    "create_mcp_server", "build an mcp server", "build a mcp server",
    "build mcp server", "create an mcp server", "create a mcp server",
    "create mcp server", "generate mcp server", "generate an mcp server",
    "i have initiated the build", "i'll build", "i will build",
    "i'll create", "i will create", "generating the mcp server",
    "starting the build", "start building", "let me build",
    "let me create", "tool_calls",
]


def _detect_tool_intent(response, content_text: str) -> dict | None:
    """
    Analyze MetaClaw's response to detect if it wants to call tools.
    Returns a dict with type and requirements if intent detected, None otherwise.
    First checks for structured tool_calls, then falls back to keyword matching.
    """
    # Check for structured tool call (covers .tool_calls and .additional_kwargs)
    requirements = _extract_create_mcp_tool_call(response)
    if requirements:
        return {"type": "create_mcp_server", "requirements": requirements}

    # Fallback: keyword scan of text content
    lower_content = content_text.lower()
    for keyword in _TOOL_INTENT_KEYWORDS:
        if keyword in lower_content:
            requirements = _extract_requirements_from_text(content_text)
            return {"type": "create_mcp_server", "requirements": requirements, "detected_from": "text"}

    return None


def _extract_requirements_from_text(text: str) -> str:
    """Extract MCP server requirements from MetaClaw's text response."""
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


# ------------------------------------------------------------------ #
# Agent Factory                                                        #
# ------------------------------------------------------------------ #

@app.get("/health")
async def health_check():
    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        if not gemini_key and not groq_key:
            return {"status": "unhealthy", "detail": "No API keys (GEMINI_API_KEY or GROQ_API_KEY) are set."}
        return {"status": "healthy", "service": "backend"}
    except Exception as e:
        return {"status": "unhealthy", "detail": str(e)}


async def get_or_create_agent(provider: str, model_name: str, mcp_urls: List[str], temperature: float):
    mcp_urls = [str(url) for url in mcp_urls if url]

    async with state.lock:
        if (state.agent and
            state.current_provider == provider and
            state.current_model == model_name and
            sorted(state.current_mcp_urls) == sorted(mcp_urls) and
            state.current_temperature == temperature):
            return state.agent

        print(f"\n--- CONFIG CHANGE DETECTED ---")
        print(f"Re-initializing agent for provider '{provider}' with model '{model_name}' (temperature = '{temperature}')...")

        for exit_stack in state.exit_stacks:
            try:
                await exit_stack.aclose()
            except Exception as e:
                print(f"Note: Could not cleanly close a session: {e}")
        state.exit_stacks = []
        state.agent = None

        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise Exception("GEMINI_API_KEY not found for Gemini provider.")
            llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature, max_retries=2, api_key=api_key)
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                raise Exception("GROQ_API_KEY not found for Groq provider.")
            llm = ChatGroq(model_name=model_name, temperature=temperature, api_key=api_key)
        elif provider == "metaclaw":
            api_key = os.getenv("METACLAW_API_KEY", "metaclaw")
            base_url = os.getenv("METACLAW_BASE_URL", "http://localhost:30000/v1")
            llm = ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key, base_url=base_url)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    all_tools = [_create_mcp_server_tool()]  # Use cached singleton

    if mcp_urls:
        sessions = []
        for url in mcp_urls:
            try:
                print(f"Attempting to connect to: {url}...")
                exit_stack = AsyncExitStack()
                streams = await asyncio.wait_for(
                    exit_stack.enter_async_context(streamable_http_client(url)),
                    timeout=10.0
                )
                read, write, _ = streams
                session = await exit_stack.enter_async_context(ClientSession(read, write))
                await asyncio.wait_for(session.initialize(), timeout=10.0)
                state.exit_stacks.append(exit_stack)
                sessions.append(session)
                print(f"Successfully connected: {url}")
            except Exception as e:
                print(f"Failed to connect to {url}: {e}")
                continue

        for session in sessions:
            try:
                tools = await load_mcp_tools(session)
                all_tools.extend(tools)
            except Exception as e:
                print(f"Failed to load tools: {e}")

    if all_tools:
        print('Using agents with tools...')
        state.agent = create_agent(llm, all_tools)
    else:
        print('No tools provided, using basic model...')
        state.agent = llm

    state.current_provider = provider
    state.current_model = model_name
    state.current_mcp_urls = mcp_urls.copy()
    state.current_temperature = temperature
    return state.agent


def get_system_prompt(has_tools: bool, mcp_urls: List[str], last_turn_index: int):
    base = f"""You are a helpful and intelligent AI assistant. 
The conversation history is provided with [Turn Index] and [Timestamp] for each message. 
The current message is [Turn {last_turn_index}].

IMPORTANT: You are an autonomous builder assistant. If the user provides an API guide, technical documentation, or any requirements that could be used to build an MCP server, you MUST call the `create_mcp_server` tool immediately in the same turn. 
DO NOT ask 'Would you like me to build this?' or wait for confirmation—just start the build process automatically.

LANGUAGE: Always respond in the same language the user is using. If the user writes in Vietnamese, respond in Vietnamese. If in English, respond in English. Match their language automatically for every message.

AFTER TOOL EXECUTION — MANDATORY REPORTING RULES:
After every tool call, you MUST report the outcome in full detail. Follow this structure:
1. Tool name: State which tool was called and with what parameters.
2. Status: Clearly state SUCCESS or FAILURE.
3. Result: Show the ACTUAL output, data, or response returned by the tool — not a summary phrase like "completed successfully". If the tool returned structured data, present it clearly. If it returned an error, quote the exact error message.
4. Impact: Briefly explain what this result means for the user's request.

NEVER replace detailed results with vague phrases such as:
- "The operation was successful"
- "Done"
- "Task completed"
- "The tool ran successfully"
These phrases are FORBIDDEN as standalone responses after a tool call.

EXCEPTIONAL RULE FOR `create_mcp_server`: When building an MCP server, you do NOT need to report the tool result yourself. The system will handle the progress reporting. Just trigger the tool and stay silent.
"""

    if has_tools:
        tools_list = ", ".join(mcp_urls) if mcp_urls else "active sessions"
        return f"{base}\n\nCURRENT STATUS (Turn {last_turn_index}): MCP Tools are ENABLED. You have access to: {tools_list}. Use them if the user request requires real-time or external data."
    else:
        return f"{base}\n\nCURRENT STATUS (Turn {last_turn_index}): MCP Tools are DISABLED. No external tools or files are available in this turn. You MUST answer based ONLY on your internal knowledge. Do NOT attempt to use tools or mention that you might have them in the future unless the user adds them."


# ------------------------------------------------------------------ #
# MCP Metadata Endpoint                                                #
# ------------------------------------------------------------------ #

class McpMetadataRequest(BaseModel):
    url: str

@app.post("/mcp/metadata")
async def get_mcp_metadata(request: McpMetadataRequest):
    url = request.url
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        async with AsyncExitStack() as exit_stack:
            streams = await asyncio.wait_for(
                exit_stack.enter_async_context(streamable_http_client(url)),
                timeout=10.0
            )
            read, write, _ = streams
            session = await exit_stack.enter_async_context(ClientSession(read, write))
            init_result = await asyncio.wait_for(session.initialize(), timeout=10.0)
            server_name = init_result.serverInfo.name if hasattr(init_result, 'serverInfo') else "Unknown Server"
            return {"name": server_name, "url": url, "status": "connected"}
    except Exception as e:
        print(f"Failed to fetch metadata for {url}: {e}")
        return {
            "name": url.split('/')[-1] or "External Server",
            "url": url,
            "status": "error",
            "detail": str(e)
        }


# ------------------------------------------------------------------ #
# Chat Endpoint                                                        #
# ------------------------------------------------------------------ #
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        if request.provider == "metaclaw":
            return await _handle_metaclaw_request(request)

        agent = await get_or_create_agent(
            provider=request.provider,
            model_name=request.model,
            mcp_urls=request.mcpServers,
            temperature=request.temperature
        )

        has_tools = not isinstance(agent, BaseLanguageModel)
        last_turn_index = len(request.messages) - 1
        dynamic_prompt = get_system_prompt(has_tools, state.current_mcp_urls, last_turn_index)

        langchain_msgs = [SystemMessage(content=dynamic_prompt)]
        for msg in request.messages:
            if msg.role == "user":
                langchain_msgs.append(HumanMessage(content=msg.content))
            else:
                langchain_msgs.append(AIMessage(content=msg.content))

        async def stream_generator():
            try:
                # Gọi LLM/Agent bằng ainvoke (ổn định)
                if hasattr(agent, "ainvoke"):
                    if has_tools:
                        response = await agent.ainvoke({"messages": langchain_msgs})
                    else:
                        response = await agent.ainvoke(langchain_msgs)
                else:
                    raise Exception("Agent does not have ainvoke method")

                # Trích xuất nội dung cuối cùng và kiểm tra tool call
                final_content = ""
                if isinstance(response, dict) and "messages" in response:
                    last_msg = response["messages"][-1]
                    # Kiểm tra tool call create_mcp_server
                    requirements = _extract_create_mcp_tool_call(last_msg)
                    if requirements is not None:
                        print(f"--- TRIGGERING LANGGRAPH BUILD ---")
                        print(f"Requirements: {requirements[:100]}...")
                        async for sse in _stream_langgraph_build(requirements):
                            yield sse
                        yield "data: [DONE]\n\n"
                        return

                    # Lấy nội dung text
                    if hasattr(last_msg, "content"):
                        final_content = last_msg.content
                    else:
                        final_content = str(last_msg)
                elif hasattr(response, "content"):
                    final_content = response.content
                else:
                    final_content = str(response)

                # Làm sạch nội dung
                if not isinstance(final_content, str):
                    if isinstance(final_content, list):
                        final_content = "\n".join(
                            [str(b.get("text", b) if isinstance(b, dict) else b) for b in final_content]
                        )
                    else:
                        final_content = json.dumps(final_content, cls=CustomEncoder)
                final_content = re.sub(r'<think>.*?</think>', '', final_content, flags=re.DOTALL).strip()

                # Gửi toàn bộ nội dung trong một khối duy nhất
                yield f"data: {json.dumps({'content': final_content})}\n\n"

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(error_msg)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
            finally:
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
# MetaClaw Two-Stage Routing                                           #
# ------------------------------------------------------------------ #

async def _handle_metaclaw_request(request: ChatRequest):
    """
    Two-stage routing for MetaClaw:
    1. Invoke MetaClaw (with tool bound) to get its raw response.
    2. If tool intent detected → hand off to Gemini for execution.
       Otherwise → stream MetaClaw's text response directly.
    """
    last_turn_index = len(request.messages) - 1

    metaclaw_system = f"""You are a helpful and intelligent AI assistant with deep knowledge of APIs, MCP servers, and tool building.
The conversation history is provided with [Turn Index] and [Timestamp] for each message.
The current message is [Turn {last_turn_index}].

IMPORTANT: If the user provides an API guide, technical documentation, or any requirements that could be used to build an MCP server, you should clearly state that you will build it and describe what tools and capabilities the server will have.

LANGUAGE: Always respond in the same language the user is using. If the user writes in Vietnamese, respond in Vietnamese. If in English, respond in English. Match their language automatically for every message.
"""

    metaclaw_msgs = [SystemMessage(content=metaclaw_system)]
    for msg in request.messages:
        if msg.role == "user":
            metaclaw_msgs.append(HumanMessage(content=msg.content))
        else:
            metaclaw_msgs.append(AIMessage(content=msg.content))

    try:
        api_key = os.getenv("METACLAW_API_KEY", "metaclaw")
        base_url = os.getenv("METACLAW_BASE_URL", "http://localhost:30000/v1")
        metaclaw_llm = ChatOpenAI(
            model=request.model,
            temperature=request.temperature,
            api_key=api_key,
            base_url=base_url
        ).bind_tools([_create_mcp_server_tool()])

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

        intent = _detect_tool_intent(metaclaw_response, content_text)

        if intent:
            print(f"[MetaClaw] Tool intent detected: {intent['type']}")
            print(f"[MetaClaw] Requirements: {intent.get('requirements', '')[:200]}...")
            return await _execute_with_gemini(intent, request, content_text)
        else:
            print("[MetaClaw] No tool intent, streaming directly")
            async def direct_stream():
                try:
                    yield f"data: {json.dumps({'content': content_text})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                finally:
                    yield "data: [DONE]\n\n"
            return StreamingResponse(direct_stream(), media_type="text/event-stream")

    except Exception as e:
        error_msg = str(e)
        print(f"[MetaClaw] Error: {error_msg}")
        async def error_stream():
            yield f"data: {json.dumps({'error': f'MetaClaw error: {error_msg}'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")


async def _execute_with_gemini(intent: dict, request: ChatRequest, metaclaw_context: str):
    """
    Hand off to Gemini (LLM with tools bound, NOT a full ReAct agent).
    Gemini calls create_mcp_server → we detect it and stream the LangGraph build.
    Falls back to direct LangGraph trigger if Gemini skips the tool call.
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
    for msg in request.messages:
        if msg.role == "user":
            gemini_msgs.append(HumanMessage(content=msg.content))
        else:
            gemini_msgs.append(AIMessage(content=msg.content))
    if metaclaw_context:
        gemini_msgs.append(AIMessage(content=f"[MetaClaw Analysis]: {metaclaw_context[:500]}"))

    print(f"[Gemini] Executing with {len(gemini_msgs)} messages, requirements: {requirements[:100]}...")

    try:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found for Gemini executor.")
        gemini_agent = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=request.temperature,
            max_retries=2,
            api_key=api_key
        ).bind_tools([_create_mcp_server_tool()])
    except Exception as e:
        error_msg = str(e)
        async def fallback_stream():
            yield f"data: {json.dumps({'content': f'\\n\\n> [ERROR]: Cannot create Gemini executor: {error_msg}\\n\\n'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(fallback_stream(), media_type="text/event-stream")

    async def gemini_stream():
        try:
            gemini_response = await gemini_agent.ainvoke(gemini_msgs)
            print(f"[Gemini] Response type: {type(gemini_response)}")

            detected_requirements = _extract_create_mcp_tool_call(gemini_response)

            if detected_requirements is not None:
                # Use Gemini's extracted requirements (may be more specific than MetaClaw's)
                build_requirements = detected_requirements or requirements
                print(f"[Gemini] TRIGGERING LANGGRAPH BUILD: {build_requirements[:100]}...")
            else:
                # Gemini skipped the tool call — use MetaClaw's requirements directly
                print(f"[Gemini] No tool call found, triggering LangGraph directly with MetaClaw requirements")
                build_requirements = requirements

            async for sse in _stream_langgraph_build(build_requirements):
                yield sse

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(gemini_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=backend_port)