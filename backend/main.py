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
from langchain.tools import tool
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from dotenv import load_dotenv
load_dotenv()

# Import centralized configuration
from config import config as llm_config
import database

# For local development, read the port from config
backend_port = llm_config.backend_port

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
        self.metaclaw_client = None  # For MetaClaw client wrapper
        self.exit_stacks = []
        self.current_provider = None
        self.current_model = None
        self.current_mcp_urls = []
        self.current_temperature = None
        self.lock = asyncio.Lock()

state = AgentState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    try:
        await database.MongoDB.connect()
    except Exception as e:
        print(f"⚠️ Warning: MongoDB connection failed: {e}")
        # Continue startup even if MongoDB fails - feedback will be unavailable

    yield

    # Shutdown: Close MongoDB and MCP sessions
    print("\n--- SHUTTING DOWN: Closing connections... ---")
    try:
        await database.MongoDB.disconnect()
    except Exception as e:
        print(f"Error during MongoDB disconnect: {e}")

    for exit_stack in state.exit_stacks:
        try:
            await exit_stack.aclose()
        except Exception:
            pass
    state.exit_stacks = []
    print("All connections closed cleanly.")

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


# ------------------------------------------------------------------ #
# Shared Helper: Stream a LangGraph build run                          #
# ------------------------------------------------------------------ #

async def _stream_langgraph_build(requirements: str) -> AsyncGenerator[str, None]:
    """
    Stream LangGraph build run with full SSE event handling (messages/partial,
    messages/complete, metadata, error) and deduplication logic.
    Yields SSE-formatted strings.
    """
    lg_url = llm_config.langgraph_api_url

    if "localhost" in lg_url and os.path.exists("/.dockerenv"):
        lg_url = lg_url.replace("localhost", "host.docker.internal")

    print(f"Connecting to LangGraph at: {lg_url}")

    yield f"data: {json.dumps({'content': chr(10) + chr(10) + '> [SYSTEM]: Building MCP Server...' + chr(10) + chr(10)})}\n\n"

    try:
        from langgraph_sdk import get_client
        lg_client = get_client(url=lg_url)
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
                print(f"Metadata: {data}")
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


# ------------------------------------------------------------------ #
# Agent Factory                                                        #
# ------------------------------------------------------------------ #

@app.get("/health")
async def health_check():
    try:
        # Check if at least one provider is configured
        has_gemini = bool(llm_config.gemini_api_key)
        has_groq = bool(llm_config.groq_api_key)
        has_metaclaw = llm_config.metaclaw_enabled and bool(llm_config.metaclaw_api_key)

        if not (has_gemini or has_groq or has_metaclaw):
            return {
                "status": "unhealthy",
                "detail": "No API keys configured. Set GEMINI_API_KEY, GROQ_API_KEY, or METACLAW_ENABLED=true with METACLAW_API_KEY."
            }
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

        # Use centralized config for provider setup
        if provider == "gemini":
            api_key = llm_config.gemini_api_key
            if not api_key:
                raise Exception("GEMINI_API_KEY not found for Gemini provider.")
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_retries=2,
                api_key=api_key
            )
        elif provider == "groq":
            api_key = llm_config.groq_api_key
            if not api_key:
                raise Exception("GROQ_API_KEY not found for Groq provider.")
            llm = ChatGroq(
                model_name=model_name,
                temperature=temperature,
                api_key=api_key
            )
        elif provider == "metaclaw":
            # Use MetaClaw client wrapper
            from metaclaw_client import MetaClawClient, MetaClawDisabledError
            try:
                metaclaw_client = MetaClawClient(llm_config, model_name=model_name)
                # MetaClaw client returns its own streaming response, not a LangChain agent
                # Store the client in state for later use
                state.metaclaw_client = metaclaw_client
                state.agent = None  # Will be handled differently
                state.current_provider = provider
                state.current_model = model_name
                state.current_mcp_urls = mcp_urls.copy()
                state.current_temperature = temperature
                return metaclaw_client  # Return special marker
            except MetaClawDisabledError:
                raise Exception("MetaClaw is disabled in configuration")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    all_tools = []

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
# Gemini Executor for MCP Build                                        #
# ------------------------------------------------------------------ #

async def _execute_build_with_gemini(requirements: str, temperature: float) -> AsyncGenerator[str, None]:
    """
    Gemini executor: receives requirements from MetaClaw proxy,
    calls create_mcp_server tool, then streams the LangGraph build.
    Falls back to direct LangGraph trigger if Gemini skips the tool call.
    """
    gemini_system = """You are an autonomous MCP server builder assistant.
The system has already determined that an MCP server should be built based on the user's request.
Your job is to execute this decision by calling the create_mcp_server tool with the provided requirements.

DO NOT ask for permission or confirmation — just execute the build immediately.
DO NOT respond with text explanations — just trigger the tool and let the system handle progress reporting."""

    gemini_msgs = [
        SystemMessage(content=gemini_system),
        HumanMessage(content=f"Build an MCP server with the following requirements:\n\n{requirements}")
    ]

    try:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found.")

        gemini_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=temperature,
            max_retries=2,
            api_key=api_key
        ).bind_tools([_create_mcp_server_tool()])

        gemini_response = await gemini_llm.ainvoke(gemini_msgs)
        detected_requirements = _extract_create_mcp_tool_call(gemini_response)

        # Use Gemini's extracted requirements if available, else fall back to MetaClaw's
        build_requirements = detected_requirements if detected_requirements is not None else requirements
        print(f"[Gemini Executor] Triggering LangGraph build: {build_requirements[:100]}...")

        async for sse in _stream_langgraph_build(build_requirements):
            yield sse

    except Exception as e:
        err_msg = f"\n\n> [ERROR]: Gemini executor failed: {str(e)}\n\n"
        yield f"data: {json.dumps({'content': err_msg})}\n\n"


# ------------------------------------------------------------------ #
# Chat Endpoint                                                        #
# ------------------------------------------------------------------ #

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Determine the effective provider and model based on MetaClaw configuration
        effective_provider = request.provider
        effective_model = request.model

        if llm_config.is_metaclaw_enabled():
            print("[MetaClaw] MetaClaw enabled in config. Forcing provider to 'metaclaw'.")
            effective_provider = "metaclaw"
            effective_model = llm_config.metaclaw_model # Use metaclaw's configured model

        # Standard provider flow (Gemini, Groq, and MetaClaw via wrapper)
        agent = await get_or_create_agent(
            provider=effective_provider,
            model_name=effective_model,
            mcp_urls=request.mcpServers,
            temperature=request.temperature
        )

        # Handle MetaClaw client returned from get_or_create_agent
        from metaclaw_client import MetaClawClient
        if isinstance(agent, MetaClawClient):
            async def metaclaw_stream_from_state():
                try:
                    async for sse in agent.chat(
                        messages=[{"role": m.role, "content": m.content} for m in request.messages],
                        temperature=request.temperature,
                        langgraph_url=llm_config.langgraph_api_url
                    ):
                        yield sse
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    yield "data: [DONE]\n\n"
            return StreamingResponse(metaclaw_stream_from_state(), media_type="text/event-stream")

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
                if hasattr(agent, "ainvoke"):
                    if has_tools:
                        response = await agent.ainvoke({"messages": langchain_msgs})
                    else:
                        response = await agent.ainvoke(langchain_msgs)
                else:
                    raise Exception("Agent does not have ainvoke method")

                final_content = ""
                if isinstance(response, dict) and "messages" in response:
                    last_msg = response["messages"][-1]

                    # Safety net: catch if provider agent somehow calls create_mcp_server
                    requirements = _extract_create_mcp_tool_call(last_msg)
                    if requirements is not None:
                        print(f"[Chat] Safety net triggered — provider called create_mcp_server.")
                        async for sse in _execute_build_with_gemini(requirements, request.temperature):
                            yield sse
                        yield "data: [DONE]\n\n"
                        return

                    if hasattr(last_msg, "content"):
                        final_content = last_msg.content
                    else:
                        final_content = str(last_msg)
                elif hasattr(response, "content"):
                    final_content = response.content
                else:
                    final_content = str(response)

                if not isinstance(final_content, str):
                    if isinstance(final_content, list):
                        final_content = "\n".join(
                            [str(b.get("text", b) if isinstance(b, dict) else b) for b in final_content]
                        )
                    else:
                        final_content = json.dumps(final_content, cls=CustomEncoder)
                final_content = re.sub(r'<think>.*?</think>', '', final_content, flags=re.DOTALL).strip()

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


