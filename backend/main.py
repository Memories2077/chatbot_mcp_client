import asyncio
import os
import json
import re
import logging
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any, AsyncGenerator, Union, cast

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
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

class McpMetadataRequest(BaseModel):
    url: str

class AgentState:
    def __init__(self):
        self.agent: Optional[Any] = None
        self.metaclaw_client: Optional[MetaClawClient] = None
        self.mcp_connections: Dict[str, Dict[str, Any]] = {} # URL -> {"stack": AsyncExitStack, "tools": List}
        self.exit_stacks: List[AsyncExitStack] = [] # Legacy field
        self.current_provider: Optional[str] = None
        self.current_model: Optional[str] = None
        self.current_mcp_urls: List[str] = []
        self.current_mcp_failures: List[str] = []
        self.current_temperature: Optional[float] = None
        self.lock = asyncio.Lock()

state = AgentState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    try:
        await database.MongoDB.connect()
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")

    yield

    # Shutdown: Close everything
    logger.info("Shutting down: Releasing all persistent MCP links...")
    for url, conn in state.mcp_connections.items():
        try:
            await conn["stack"].aclose()
        except Exception:
            pass
    
    await database.MongoDB.disconnect()
    logger.info("Shutdown complete.")

app = FastAPI(lifespan=lifespan)

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
# Helper Utilities                                                     #
# ------------------------------------------------------------------ #

def resolve_docker_url(url: str) -> str:
    """If running in Docker, resolve localhost to the internal container names."""
    if os.path.exists('/.dockerenv'):
        if "localhost:8080" in url or "127.0.0.1:8080" in url:
            return url.replace("localhost:8080", "docker-manager:8080").replace("127.0.0.1:8080", "docker-manager:8080")
        elif "localhost" in url or "127.0.0.1" in url:
            return url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
    return url


def sse_event(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"

def sse_content(content: str) -> str:
    return sse_event({"type": "content", "content": content})

def sse_error(error: str) -> str:
    return sse_event({"type": "error", "error": error})

def sse_status(message: str) -> str:
    return sse_event({"type": "status", "message": message})

def sse_done() -> str:
    return f"data: {json.dumps({'type': 'done'})}\n\ndata: [DONE]\n\n"

# ------------------------------------------------------------------ #
# Agent Factory (Keep-Alive Implementation)                            #
# ------------------------------------------------------------------ #

async def get_or_create_agent(
    provider: str,
    model_name: str,
    mcp_urls: Optional[List[str]],
    temperature: float
) -> Union[BaseLanguageModel, MetaClawClient]:
    if mcp_urls is None:
        mcp_urls = []
    
    # Normalize and filter URLs
    target_urls = [resolve_docker_url(str(url)) for url in mcp_urls if url]

    async with state.lock:
        # 1. Check if we can reuse the current agent
        urls_changed = sorted(state.current_mcp_urls) != sorted(target_urls)
        config_changed = (
            state.current_provider != provider or 
            state.current_model != model_name or 
            state.current_temperature != temperature
        )

        if state.agent and not config_changed and not urls_changed:
            return state.agent

        logger.info(f"Syncing agent: {provider} | {model_name} | URLs: {len(target_urls)}")

        # 2. Sync MCP Connections
        current_connected = set(state.mcp_connections.keys())
        target_set = set(target_urls)
        
        # Close obsolete
        for url in (current_connected - target_set):
            logger.info(f"Closing obsolete link: {url}")
            conn = state.mcp_connections.pop(url, {})
            if "stack" in conn:
                try: await conn["stack"].aclose()
                except Exception: pass
        
        # Connect new
        new_failures = []
        for url in (target_set - current_connected):
            max_retries = llm_config.mcp_connection_retries
            connected = False
            for attempt in range(max_retries):
                stack = AsyncExitStack()
                try:
                    logger.info(f"Connecting to {url} (Attempt {attempt+1})...")
                    async with asyncio.timeout(llm_config.mcp_connection_timeout + llm_config.mcp_initialization_timeout):
                        streams = await stack.enter_async_context(streamable_http_client(url))
                        read, write, _ = streams
                        session = await stack.enter_async_context(ClientSession(read, write))
                        await session.initialize()
                        tools = await load_mcp_tools(session)
                        
                        state.mcp_connections[url] = {"stack": stack, "tools": tools}
                        connected = True
                        logger.info(f"✅ Neural link established: {url}")
                        break
                except Exception as e:
                    await stack.aclose()
                    logger.warning(f"Connection failed to {url}: {e}")
                    if attempt < max_retries - 1: await asyncio.sleep(llm_config.mcp_retry_delay)
            
            if not connected:
                new_failures.append(url)

        # 3. Aggregate Tools
        all_mcp_tools = []
        for url in target_urls:
            if url in state.mcp_connections:
                all_mcp_tools.extend(state.mcp_connections[url]["tools"])

        # 4. Create Agent
        if provider == "metaclaw":
            from metaclaw_client import MetaClawClient
            agent = MetaClawClient(llm_config, model_name=model_name)
            agent.mcp_tools = all_mcp_tools
        elif provider == "gemini":
            llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature, api_key=llm_config.gemini_api_key)
            agent = create_agent(llm, all_mcp_tools) if all_mcp_tools else llm
        else: # groq
            llm = ChatGroq(model=model_name, temperature=temperature, api_key=llm_config.groq_api_key)
            agent = create_agent(llm, all_mcp_tools) if all_mcp_tools else llm

        # 5. Update state
        state.agent = agent
        state.current_provider = provider
        state.current_model = model_name
        state.current_mcp_urls = target_urls.copy()
        state.current_mcp_failures = new_failures
        state.current_temperature = temperature
        
        return agent

# ------------------------------------------------------------------ #
# API Endpoints                                                        #
# ------------------------------------------------------------------ #

@app.get("/health")
async def health_check():
    return {"status": "healthy", "metaclaw": llm_config.is_metaclaw_enabled()}

@app.post("/mcp/metadata")
async def get_mcp_metadata(request: McpMetadataRequest):
    url = resolve_docker_url(request.url)
    if url in state.mcp_connections:
        return {"name": "Connected Server", "url": request.url, "status": "connected"}

    try:
        stack = AsyncExitStack()
        async with asyncio.timeout(15):
            streams = await stack.enter_async_context(streamable_http_client(url))
            session = await stack.enter_async_context(ClientSession(streams[0], streams[1]))
            init = await session.initialize()
            tools = await load_mcp_tools(session)
            
            async with state.lock:
                state.mcp_connections[url] = {"stack": stack, "tools": tools}
                if url not in state.current_mcp_urls:
                    state.current_mcp_urls.append(url)
            
            return {"name": init.serverInfo.name, "url": request.url, "status": "connected"}
    except Exception as e:
        logger.error(f"Probe failed for {url}: {e}")
        return {"name": "Error", "url": request.url, "status": "error", "detail": str(e)}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        prov = "metaclaw" if llm_config.is_metaclaw_enabled() else (request.provider or "gemini")
        model = llm_config.metaclaw_model if prov == "metaclaw" else (request.model or "gemini-2.5-flash")
        
        agent = await get_or_create_agent(prov, model, request.mcpServers, request.temperature or 0.0)

        if isinstance(agent, MetaClawClient):
            async def metaclaw_stream():
                async for sse in agent.chat(
                    messages=[{"role": m.role, "content": m.content} for m in request.messages],
                    temperature=request.temperature or 0.0,
                    langgraph_url=llm_config.langgraph_api_url,
                    mcp_urls=request.mcpServers
                ):
                    if "__use_standard_agent__" in sse:
                        # Handoff logic (simplified for brevity)
                        async for std_sse in _stream_standard_agent_response(request, [{"role": m.role, "content": m.content} for m in request.messages], request.mcpServers, request.temperature or 0.0, state):
                            yield std_sse
                        return
                    yield sse
            return StreamingResponse(metaclaw_stream(), media_type="text/event-stream")

        return StreamingResponse(_stream_standard_agent_response(request, [{"role": m.role, "content": m.content} for m in request.messages], request.mcpServers, request.temperature or 0.0, state, agent), media_type="text/event-stream")

    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))

async def _stream_standard_agent_response(request, messages, mcp_urls, temp, state, agent=None):
    if agent is None:
        agent = await get_or_create_agent(request.provider or "gemini", request.model or "gemini-2.5-flash", mcp_urls, temp)
    
    # Check for tools in the agent object
    has_tools = hasattr(agent, "tools") or (isinstance(agent, MetaClawClient) and bool(mcp_urls))
    
    prompt = get_system_prompt(has_tools, False, mcp_urls or [], len(messages)-1)
    langchain_msgs = [SystemMessage(content=prompt)]
    for m in messages:
        langchain_msgs.append(HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]))

    try:
        # Use astream for real-time response generation
        full_content = ""
        async for chunk in agent.astream({"messages": langchain_msgs}):
            content_chunk = ""
            
            # 1. Handle LangGraph-style state updates (e.g., {'agent': {...}, 'model': {...}})
            if isinstance(chunk, dict):
                # Try to find messages in any of the top-level keys
                for key in ["messages", "agent", "model"]:
                    val = chunk.get(key)
                    if val:
                        if isinstance(val, dict) and "messages" in val:
                            msg = val["messages"][-1]
                        elif isinstance(val, list) and len(val) > 0:
                            msg = val[-1]
                        else:
                            msg = val
                        
                        if hasattr(msg, "content"):
                            content_chunk = msg.content
                            break

            # 2. Handle direct Message objects or fallback
            if not content_chunk:
                if hasattr(chunk, "content"):
                    content_chunk = chunk.content
                elif isinstance(chunk, str):
                    content_chunk = chunk

            # 3. Handle complex content formats (list of dicts like [{'type': 'text', 'text': '...'}])
            if isinstance(content_chunk, list):
                parts = []
                for part in content_chunk:
                    if isinstance(part, dict):
                        parts.append(part.get("text", ""))
                    else:
                        parts.append(str(part))
                content_chunk = "".join(parts)

            if content_chunk:
                # Ensure it's a string
                safe_chunk = str(content_chunk)
                
                # Stream the clean chunk
                yield sse_content(safe_chunk)
                full_content += safe_chunk

        logger.info(f"Stream completed. Total length: {len(full_content)} chars")
    except Exception as e:
        yield sse_error(str(e))
    finally:
        yield sse_done()

# (Remaining standard routes like /mcp/servers, feedback, etc. should be below)
@app.get("/mcp/servers")
async def list_mcp_servers():
    try:
        response = await asyncio.to_thread(requests.get, f"{llm_config.mcp_gen_base_url}/api/mcp/servers", timeout=5)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

class McpFeedbackRequest(BaseModel):
    type: str
    userId: Optional[str] = None
    comment: Optional[str] = None

@app.post("/mcp/{server_id}/feedback")
async def submit_mcp_feedback(server_id: str, request: McpFeedbackRequest):
    try:
        response = await asyncio.to_thread(requests.post, f"{llm_config.mcp_gen_base_url}/api/mcp/{server_id}/feedback", json=request.dict(exclude_none=True), timeout=5)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

def get_system_prompt(has_mcp_tools, has_create_mcp_server_tool, mcp_urls, last_turn_index):
    base = f"You are a helpful AI assistant. [Turn {last_turn_index}]. Respond in the same language as the user."
    if has_mcp_tools:
        return f"{base}\nMCP Tools are ENABLED ({', '.join(mcp_urls)}). Use them if needed."
    return f"{base}\nMCP Tools are DISABLED. Answer from internal knowledge only."
