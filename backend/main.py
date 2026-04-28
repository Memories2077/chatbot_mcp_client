import asyncio
import os
import json
import re
import logging
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any, AsyncGenerator, Union

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
from shared import create_mcp_server_tool, stream_langgraph_build, extract_create_mcp_tool_call
from metaclaw_client import MetaClawClient

# For local development, read the port from config
backend_port = llm_config.backend_port

# Setup logging
logger = logging.getLogger(__name__)

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
        logger.warning(f"MongoDB connection failed: {e}")
        # Continue startup even if MongoDB fails - feedback will be unavailable

    yield

    # Shutdown: Close MongoDB and MCP sessions
    logger.info("Shutting down: Closing connections...")
    try:
        await database.MongoDB.disconnect()
    except Exception as e:
        logger.error(f"Error during MongoDB disconnect: {e}")

    for exit_stack in state.exit_stacks:
        try:
            await exit_stack.aclose()
        except Exception as e:
            logger.warning(f"Error closing exit stack during shutdown: {e}")
    state.exit_stacks = []
    logger.info("All connections closed cleanly.")

app = FastAPI(lifespan=lifespan)

# CORS configuration: allow only specific trusted origins
# Use ALLOWED_ORIGINS env var (comma-separated) or default to localhost:9002
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:9002").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Agent Factory                                                        #
# ------------------------------------------------------------------ #

def resolve_docker_url(url: str) -> str:
    """If running in Docker, resolve localhost to the internal container names."""
    if os.path.exists('/.dockerenv'):
        if "localhost:8080" in url or "127.0.0.1:8080" in url:
            return url.replace("localhost:8080", "docker-manager:8080").replace("127.0.0.1:8080", "docker-manager:8080")
        elif "localhost" in url or "127.0.0.1" in url:
            return url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
    return url


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


async def get_or_create_agent(
    provider: str,
    model_name: str,
    mcp_urls: Optional[List[str]],
    temperature: float
) -> Union[BaseLanguageModel, MetaClawClient]:
    # Normalize None to empty list
    if mcp_urls is None:
        mcp_urls = []
    # Map URLs properly for Docker environment
    mcp_urls = [resolve_docker_url(str(url)) for url in mcp_urls if url]

    async with state.lock:
        if (state.agent and
            state.current_provider == provider and
            state.current_model == model_name and
            sorted(state.current_mcp_urls) == sorted(mcp_urls) and
            state.current_temperature == temperature):
            return state.agent

        logger.info(f"Config change detected: Re-initializing agent for provider '{provider}' with model '{model_name}' (temperature = '{temperature}')")

        for exit_stack in state.exit_stacks:
            try:
                await exit_stack.aclose()
            except Exception as e:
                logger.debug(f"Note: Could not cleanly close a session: {e}")
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
    failed_urls: List[str] = []  # Track MCP connection failures

    if mcp_urls:
        sessions = []
        for url in mcp_urls:
            max_retries = llm_config.mcp_connection_retries
            connected = False
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempting to connect to MCP server: {url} (Attempt {attempt + 1}/{max_retries})...")
                    exit_stack = AsyncExitStack()
                    streams = await asyncio.wait_for(
                        exit_stack.enter_async_context(streamable_http_client(url)),
                        timeout=llm_config.mcp_connection_timeout
                    )
                    read, write, _ = streams
                    session = await exit_stack.enter_async_context(ClientSession(read, write))
                    await asyncio.wait_for(session.initialize(), timeout=llm_config.mcp_initialization_timeout)
                    state.exit_stacks.append(exit_stack)
                    sessions.append(session)
                    logger.info(f"Successfully connected to MCP server: {url}")
                    connected = True
                    break
                except Exception as e:
                    logger.error(f"Failed to connect to MCP server {url} (Attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(llm_config.mcp_retry_delay)

            if not connected:
                logger.error(f"All {max_retries} connection attempts failed for {url}")
                failed_urls.append(url)

        for session in sessions:
            try:
                tools = await load_mcp_tools(session)
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"Failed to load tools from MCP server: {e}")

    if all_tools:
        logger.info("Using agent with MCP tools")
        state.agent = create_agent(llm, all_tools)
    else:
        logger.info("No MCP tools provided, using basic model")
        state.agent = llm

    # Attach MCP failure information to agent for user warning
    if failed_urls:
        try:
            state.agent._mcp_failures = failed_urls
        except Exception as e:
            logger.debug(f"Could not attach _mcp_failures to agent: {e}")

    state.current_provider = provider
    state.current_model = model_name
    state.current_mcp_urls = mcp_urls.copy()
    state.current_temperature = temperature
    return state.agent


def get_system_prompt(
    has_mcp_tools: bool,
    has_create_mcp_server_tool: bool,
    mcp_urls: List[str],
    last_turn_index: int
) -> str:
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
"""

    if has_create_mcp_server_tool:
        base += """
EXCEPTIONAL RULE FOR `create_mcp_server`: When building an MCP server, you do NOT need to report the tool result yourself. The system will handle the progress reporting. Just trigger the tool and stay silent.
"""

    if has_mcp_tools:
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
    original_url = request.url
    if not original_url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    url = resolve_docker_url(original_url)
    try:
        async with AsyncExitStack() as exit_stack:
            streams = await asyncio.wait_for(
                exit_stack.enter_async_context(streamable_http_client(url)),
                timeout=llm_config.mcp_connection_timeout
            )
            read, write, _ = streams
            session = await exit_stack.enter_async_context(ClientSession(read, write))
            init_result = await asyncio.wait_for(session.initialize(), timeout=llm_config.mcp_initialization_timeout)
            server_name = init_result.serverInfo.name if hasattr(init_result, 'serverInfo') else "Unknown Server"
            return {"name": server_name, "url": original_url, "status": "connected"}
    except Exception as e:
        # Catch all exceptions including TaskGroup errors from anyio
        logger.error(f"Failed to fetch metadata for {url}: {e}", exc_info=True)
        return {
            "name": original_url.split('/')[-1] or "External Server",
            "url": original_url,
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
        ).bind_tools([create_mcp_server_tool()])

        gemini_response = await gemini_llm.ainvoke(gemini_msgs)
        detected_requirements = extract_create_mcp_tool_call(gemini_response)

        # Use Gemini's extracted requirements if available, else fall back to MetaClaw's
        build_requirements = detected_requirements if detected_requirements is not None else requirements
        logger.info(f"[Gemini Executor] Triggering LangGraph build: {build_requirements[:100]}...")

        async for sse in stream_langgraph_build(build_requirements, llm_config.langgraph_api_url):
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
            logger.info("[MetaClaw] MetaClaw enabled in config. Forcing provider to 'metaclaw'.")
            effective_provider = "metaclaw"
            effective_model = llm_config.metaclaw_model  # Use metaclaw's configured model

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
                        langgraph_url=llm_config.langgraph_api_url,
                        mcp_urls=request.mcpServers
                    ):
                        # Check for control event to use standard agent
                        try:
                            # Only parse data lines; skip empty lines and other SSE events
                            if sse.strip().startswith("data:"):
                                data = json.loads(sse.removeprefix("data: ").strip())
                                if isinstance(data, dict) and data.get("__use_standard_agent__") is True:
                                    logger.info("[MetaClaw] Control event received: routing to standard agent with MCP tools")
                                    # Stream from standard agent instead
                                    async for std_sse in _stream_standard_agent_response(
                                        request=request,
                                        messages=[{"role": m.role, "content": m.content} for m in request.messages],
                                        mcp_urls=request.mcpServers,
                                        temperature=request.temperature,
                                        state=state
                                    ):
                                        yield std_sse
                                    return
                        except (json.JSONDecodeError, KeyError, IndexError):
                            # Not a control event, pass through
                            pass
                        yield sse
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    yield "data: [DONE]\n\n"
            return StreamingResponse(metaclaw_stream_from_state(), media_type="text/event-stream")

        # Standard agent flow (Gemini, Groq) - use helper
        return StreamingResponse(
            _stream_standard_agent_response(
                request=request,
                messages=[{"role": m.role, "content": m.content} for m in request.messages],
                mcp_urls=request.mcpServers,
                temperature=request.temperature,
                state=state,
                agent=agent  # Pass the pre-created agent to avoid double creation
            ),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Error in MCP server connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function for standard agent streaming
async def _stream_standard_agent_response(
    request: ChatRequest,
    messages: List[Dict[str, Any]],
    mcp_urls: Optional[List[str]],
    temperature: float,
    state: AgentState,
    agent: Optional[Union[BaseLanguageModel, MetaClawClient]] = None
) -> AsyncGenerator[str, None]:
    """Stream response from standard agent (Gemini/Groq) with MCP tools."""
    try:
        # Get or create agent with MCP connections handled by factory
        if agent is None:
            agent = await get_or_create_agent(
                provider=request.provider,
                model_name=request.model,
                mcp_urls=mcp_urls or [],
                temperature=temperature
            )
    except Exception as e:
        logger.error(f"[Chat] Agent creation error: {e}")
        yield f"data: {json.dumps({'error': f'Failed to create agent: {str(e)}'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Detect MetaClaw client explicitly (shouldn't happen in standard flow, but safe)
    from metaclaw_client import MetaClawClient
    if isinstance(agent, MetaClawClient):
        has_tools = False
    else:
        has_tools = hasattr(agent, 'tools') and bool(agent.tools)

    # Emit warning if MCP servers were requested but failed to connect
    if mcp_urls and hasattr(agent, '_mcp_failures'):
        failures = getattr(agent, '_mcp_failures', [])
        if failures:
            warning_msg = f"> [WARNING]: Failed to connect to MCP servers: {', '.join(failures)}. Proceeding without tool support.\n\n"
            yield f"data: {json.dumps({'content': warning_msg})}\n\n"
            # Remove attribute to avoid duplicate warnings if agent is reused
            try:
                delattr(agent, '_mcp_failures')
            except Exception as e:
                logger.debug(f"Could not delete _mcp_failures attribute: {e}")

    last_turn_index = len(messages) - 1
    # Use the passed mcp_urls parameter, not state.current_mcp_urls
    dynamic_prompt = get_system_prompt(has_mcp_tools=has_tools, has_create_mcp_server_tool=False, mcp_urls=mcp_urls or [], last_turn_index=last_turn_index)

    langchain_msgs = [SystemMessage(content=dynamic_prompt)]
    for msg in messages:
        if msg.get("role") == "user":
            langchain_msgs.append(HumanMessage(content=msg.get("content", "")))
        else:
            langchain_msgs.append(AIMessage(content=msg.get("content", "")))

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
            requirements = extract_create_mcp_tool_call(last_msg)
            if requirements is not None:
                logger.warning(f"[Chat] Safety net triggered — provider called create_mcp_server.")
                async for sse in _execute_build_with_gemini(requirements, temperature):
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
        logger.error(error_msg)
        yield f"data: {json.dumps({'error': error_msg})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


