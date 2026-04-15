import asyncio
import os
import json
import re
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any

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

# Global state to keep track of the current agent and its config
class AgentState:
    def __init__(self):
        self.agent = None
        self.exit_stacks = []
        self.current_provider = None
        self.current_model = None
        self.current_mcp_urls = []
        self.current_temperature = None
        self.lock = asyncio.Lock() # Add lock to prevent race conditions

state = AgentState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    # Shutdown
    print("\n--- SHUTTING DOWN: Closing all MCP sessions... ---")
    for exit_stack in state.exit_stacks:
        try:
            await exit_stack.aclose()
        except Exception as e:
            pass # suppress error
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

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/K8s"""
    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        if not gemini_key and not groq_key:
            return {"status": "unhealthy", "detail": "No API keys (GEMINI_API_KEY or GROQ_API_KEY) are set."}
        return {"status": "healthy", "service": "backend"}
    except Exception as e:
        return {"status": "unhealthy", "detail": str(e)}

async def get_or_create_agent(provider: str, model_name: str, mcp_urls: List[str], temperature: float):
    # Ensure mcp_urls is a clean list of strings
    mcp_urls = [str(url) for url in mcp_urls if url]
    
    async with state.lock:
        # Check if we can reuse the existing agent
        if (state.agent and
            state.current_provider == provider and
            state.current_model == model_name and 
            sorted(state.current_mcp_urls) == sorted(mcp_urls) and
            state.current_temperature == temperature):
            return state.agent

        print(f"\n--- CONFIG CHANGE DETECTED ---")
        print(f"Re-initializing agent for provider '{provider}' with model '{model_name}' (temperature = '{temperature}')...")
        
        # Close the sessions progressively
        for exit_stack in state.exit_stacks:
            try:
                await exit_stack.aclose()
            except Exception as e:
                print(f"Note: Could not cleanly close a session: {e}")
        state.exit_stacks = []
        state.agent = None
        
        llm = None
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise Exception("GEMINI_API_KEY not found for Gemini provider.")
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_retries=2,
                api_key=api_key
            )
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                raise Exception("GROQ_API_KEY not found for Groq provider.")
            llm = ChatGroq(
                model_name=model_name,
                temperature=temperature,
                api_key=api_key
            )
        elif provider == "metaclaw":
            api_key = os.getenv("METACLAW_API_KEY", "metaclaw")
            base_url = os.getenv("METACLAW_BASE_URL", "http://localhost:30000/v1")
            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    # --- LangGraph Tool Definition ---
    @tool
    async def create_mcp_server(requirements: str) -> str:
        """
        Builds a custom MCP server. Call this tool IMMEDIATELY as soon as the user provides technical requirements, 
        API documentation, or a guide that implies they want a tool or server built. 
        Do NOT ask for permission or confirmation first—assume the user wants you to generate the server based on their input.
        Args:
            requirements: Detailed description of the MCP server functionality and tools needed.
        """
        # This is a marker tool. The actual streaming logic will be handled 
        # in the chat_endpoint when it detects this tool call.
        return f"GENERATE_MCP_SERVER_TRIGGERED:{requirements}"

    all_tools = [create_mcp_server]
    
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

class McpMetadataRequest(BaseModel):
    url: str

# ------------------------------------------------------------------ #
# MetaClaw → Gemini Handoff Helpers                                    #
# ------------------------------------------------------------------ #

# Keywords that indicate MetaClaw wants to execute tools / build something
_TOOL_INTENT_KEYWORDS = [
    "create_mcp_server",
    "build an mcp server",
    "build a mcp server",
    "build mcp server",
    "create an mcp server",
    "create a mcp server",
    "create mcp server",
    "generate mcp server",
    "generate an mcp server",
    "i have initiated the build",
    "i'll build",
    "i will build",
    "i'll create",
    "i will create",
    "generating the mcp server",
    "starting the build",
    "start building",
    "let me build",
    "let me create",
    "tool_calls",  # structured tool calls in response
]


def _detect_tool_intent(response, content_text: str) -> dict | None:
    """
    Analyze MetaClaw's response to detect if it wants to call tools.
    Returns the tool call info if intent detected, None otherwise.
    """
    # Check for structured tool_calls in the response message
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            if tc_name == "create_mcp_server":
                tc_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                if isinstance(tc_args, str):
                    try:
                        tc_args = json.loads(tc_args)
                    except Exception:
                        tc_args = {}
                requirements = tc_args.get("requirements", "") if isinstance(tc_args, dict) else ""
                if requirements:
                    return {"type": "create_mcp_server", "requirements": requirements}

    # Check for tool_calls in additional_kwargs (provider-specific format)
    if hasattr(response, "additional_kwargs") and response.additional_kwargs:
        tool_calls = response.additional_kwargs.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {}) if isinstance(tc, dict) else {}
            tc_name = func.get("name", "") if isinstance(func, dict) else ""
            if tc_name == "create_mcp_server":
                args_raw = func.get("arguments", "{}")
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw)
                    except Exception:
                        args = {}
                else:
                    args = args_raw
                requirements = args.get("requirements", "") if isinstance(args, dict) else ""
                if requirements:
                    return {"type": "create_mcp_server", "requirements": requirements}

    # Check text content for keyword patterns
    lower_content = content_text.lower()
    for keyword in _TOOL_INTENT_KEYWORDS:
        if keyword in lower_content:
            # Try to extract requirements from the text
            # Look for patterns like "with the following capabilities:", "includes:", etc.
            requirements = _extract_requirements_from_text(content_text)
            return {"type": "create_mcp_server", "requirements": requirements, "detected_from": "text"}

    return None


def _extract_requirements_from_text(text: str) -> str:
    """
    Extract MCP server requirements from MetaClaw's text response.
    Tries to find structured descriptions after trigger phrases.
    """
    # Try to find content after common trigger phrases
    triggers = [
        "with the following capabilities:",
        "includes:",
        "the server will include:",
        "capabilities:",
        "the following tools:",
        "tools:",
    ]
    for trigger in triggers:
        idx = text.lower().find(trigger.lower())
        if idx != -1:
            # Take everything after the trigger, up to ~500 chars
            extracted = text[idx + len(trigger):].strip()
            return extracted[:500] if extracted else text[:500]

    # Fallback: return the full text (let Gemini figure it out)
    return text[:800]


async def _create_gemini_executor(mcp_urls: list[str], temperature: float):
    """
    Create a Gemini LLM with tools BOUND (NOT a ReAct agent).
    We return the raw llm_with_tools so the backend can intercept tool_calls
    before they are consumed by an agent loop.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise Exception("GEMINI_API_KEY not found for Gemini executor.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=temperature,
        max_retries=2,
        api_key=api_key
    )

    all_tools = [_create_mcp_server_tool()]

    print(f'[Handoff] Creating Gemini executor with {len(all_tools)} tools...')
    # Return LLM with tools bound — NOT a full ReAct agent.
    # This keeps tool_calls visible in the AIMessage for manual handling.
    return llm.bind_tools(all_tools)


# We need a module-level reference to the create_mcp_server tool for the handoff
_create_mcp_server_tool_instance = None

def _create_mcp_server_tool():
    """Return the create_mcp_server tool (creates if needed)."""
    global _create_mcp_server_tool_instance
    if _create_mcp_server_tool_instance is None:
        @tool
        async def create_mcp_server(requirements: str) -> str:
            """
            Builds a custom MCP server. Call this tool IMMEDIATELY as soon as the user provides technical requirements,
            API documentation, or a guide that implies they want a tool or server built.
            Do NOT ask for permission or confirmation first—assume the user wants you to generate the server based on their input.
            Args:
                requirements: Detailed description of the MCP server functionality and tools needed.
            """
            return f"GENERATE_MCP_SERVER_TRIGGERED:{requirements}"
        _create_mcp_server_tool_instance = create_mcp_server
    return _create_mcp_server_tool_instance

@app.post("/mcp/metadata")
async def get_mcp_metadata(request: McpMetadataRequest):
    """Connect to an MCP server and fetch its metadata (name, etc.)"""
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
            
            # The initialize() call returns the server's metadata
            init_result = await asyncio.wait_for(session.initialize(), timeout=10.0)
            
            # Extract server name from the initialization result
            server_name = init_result.serverInfo.name if hasattr(init_result, 'serverInfo') else "Unknown Server"
            
            return {
                "name": server_name,
                "url": url,
                "status": "connected"
            }
    except Exception as e:
        print(f"Failed to fetch metadata for {url}: {e}")
        # Return a fallback name if connection fails but URL is valid format
        return {
            "name": url.split('/')[-1] or "External Server",
            "url": url,
            "status": "error",
            "detail": str(e)
        }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # === TWO-STAGE ROUTING FOR METACLAW ===
        # When using MetaClaw, first get its response, then decide:
        # - If MetaClaw wants to call tools → hand off to Gemini for execution
        # - If MetaClaw is just chatting → stream MetaClaw's response directly
        if request.provider == "metaclaw":
            return await _handle_metaclaw_request(request)

        # === ORIGINAL FLOW FOR GEMINI/GROQ ===
        agent = await get_or_create_agent(
            provider=request.provider,
            model_name=request.model,
            mcp_urls=request.mcpServers,
            temperature=request.temperature
        )

        has_status_info = False
        last_turn_index = len(request.messages) - 1
        dynamic_prompt = get_system_prompt(not isinstance(agent, BaseLanguageModel), state.current_mcp_urls, last_turn_index)

        langchain_msgs = [SystemMessage(content=dynamic_prompt)]
        for msg in request.messages:
            if msg.role == "user":
                langchain_msgs.append(HumanMessage(content=msg.content))
            else:
                langchain_msgs.append(AIMessage(content=msg.content))

        async def stream_generator():
            try:
                # 1. First pass: Handle LLM response (could be text or tool call)

                # Check if it's an agent or a model
                if hasattr(agent, "astream"):
                    # We use astream to catch both content and potential tool calls
                    async for chunk in agent.astream(langchain_msgs if isinstance(agent, BaseLanguageModel) else {"messages": langchain_msgs}):

                        # Case A: Pure content chunk
                        if hasattr(chunk, "content") and chunk.content:
                            yield f"data: {json.dumps({'content': chunk.content})}\n\n"

                        # Case B: Agent state chunk (for LangGraph agents)
                        elif isinstance(chunk, dict) and "messages" in chunk:
                            msg = chunk["messages"][-1]
                            if hasattr(msg, "content") and msg.content:
                                yield f"data: {json.dumps({'content': msg.content})}\n\n"

                            # Check for tool calls in ANY chunk format (Message or Dict)
                            tool_calls = []
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                tool_calls = msg.tool_calls
                            elif hasattr(msg, "additional_kwargs") and "tool_calls" in msg.additional_kwargs:
                                # Handle direct provider tool calls if not parsed by LC yet
                                tool_calls = msg.additional_kwargs["tool_calls"]

                            if tool_calls:
                                for tc in tool_calls:
                                    # Normalize tool call name (some providers might wrap it)
                                    tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                                    if tc_name == "create_mcp_server":
                                        tc_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                                        # args might be a JSON string from some providers
                                        if isinstance(tc_args, str):
                                            try:
                                                tc_args = json.loads(tc_args)
                                            except:
                                                pass

                                        requirements = tc_args.get("requirements", "") if isinstance(tc_args, dict) else ""

                                        print(f"--- TRIGGERING LANGGRAPH BUILD ---")
                                        print(f"Requirements: {requirements[:100]}...")

                                        system_msg = f"\n\n> [SYSTEM]: Building MCP Server with requirements: {requirements[:200]}...\n\n"
                                        yield f"data: {json.dumps({'content': system_msg})}\n\n"

                                        # Use correct Env Var from Docker Compose
                                        lg_url = os.getenv("NEXT_PUBLIC_LANGGRAPH_API_URL") or os.getenv("LANGGRAPH_API_URL") or "http://localhost:2024"

                                        # Handle localhost inside Docker
                                        if "localhost" in lg_url and os.path.exists("/.dockerenv"):
                                            lg_url = lg_url.replace("localhost", "host.docker.internal")

                                        print(f"Connecting to LangGraph at: {lg_url}")

                                        try:
                                            lg_client = get_client(url=lg_url)
                                            # Create thread and run
                                            thread = await lg_client.threads.create()

                                            # Convert LangChain messages to LangGraph SDK format
                                            lg_history = []
                                            for m in langchain_msgs:
                                                role = "user" if m.type == "human" else "assistant" if m.type == "ai" else "system"
                                                lg_history.append({"role": role, "content": m.content})

                                            async for lg_chunk in lg_client.runs.stream(
                                                thread["thread_id"],
                                                "agent", # ASSISTANT_ID
                                                input={"messages": lg_history},
                                                stream_mode="messages"
                                            ):
                                                if lg_chunk.event == "messages/partial" and isinstance(lg_chunk.data, list):
                                                    content = lg_chunk.data[0].get("content", "")
                                                    if content:
                                                        yield f"data: {json.dumps({'content': content})}\n\n"

                                            print("--- LANGGRAPH BUILD COMPLETED ---")
                                            # Terminate this stream immediately to prevent local agent from hallucinating
                                            return
                                        except Exception as lg_err:
                                            print(f"LangGraph Error: {lg_err}")
                                            yield f"data: {json.dumps({'content': f'\n\n> [ERROR]: Cannot connect to LangGraph service: {str(lg_err)}\n\n'})}\n\n"
                                            return

                else:
                    # Fallback for non-streamable agents
                    response = await agent.ainvoke(langchain_msgs if isinstance(agent, BaseLanguageModel) else {"messages": langchain_msgs})
                    content = response.content if hasattr(response, "content") else str(response)
                    yield f"data: {json.dumps({'content': content})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_metaclaw_request(request: ChatRequest):
    """
    Two-stage routing for MetaClaw:
    1. Send to MetaClaw to get its "thinking" response
    2. Analyze for tool-call intent:
       - If detected → hand off to Gemini (with tools) for execution
       - If not → stream MetaClaw's response directly to user
    """
    last_turn_index = len(request.messages) - 1

    # Build LangChain messages for MetaClaw
    # Use a system prompt that encourages MetaClaw to think about what to do
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

    # Stage 1: Get MetaClaw's raw response (invoke the LLM directly, NOT the agent loop)
    # This is critical: we need to see the raw tool_calls before the agent loop consumes them.
    try:
        api_key = os.getenv("METACLAW_API_KEY", "metaclaw")
        base_url = os.getenv("METACLAW_BASE_URL", "http://localhost:30000/v1")
        metaclaw_llm = ChatOpenAI(
            model=request.model,
            temperature=request.temperature,
            api_key=api_key,
            base_url=base_url
        )

        # Bind the create_mcp_server tool so MetaClaw can signal intent via tool_calls
        metaclaw_llm_with_tools = metaclaw_llm.bind_tools([_create_mcp_server_tool()])

        # Invoke the raw LLM — this returns the AIMessage with tool_calls intact
        metaclaw_response = await metaclaw_llm_with_tools.ainvoke(metaclaw_msgs)

        # Extract content from response
        content_text = ""
        if hasattr(metaclaw_response, "content"):
            content_text = metaclaw_response.content or ""
        elif isinstance(metaclaw_response, dict):
            content_text = metaclaw_response.get("content", "")
        else:
            content_text = str(metaclaw_response)

        print(f"[MetaClaw] Response length: {len(content_text)} chars")
        print(f"[MetaClaw] Response preview: {content_text[:300]}...")
        # Log tool_calls for debugging
        if hasattr(metaclaw_response, 'tool_calls') and metaclaw_response.tool_calls:
            print(f"[MetaClaw] tool_calls detected: {metaclaw_response.tool_calls}")
        if hasattr(metaclaw_response, 'additional_kwargs') and metaclaw_response.additional_kwargs.get('tool_calls'):
            print(f"[MetaClaw] additional_kwargs tool_calls: {metaclaw_response.additional_kwargs['tool_calls']}")

        # Stage 2: Detect tool-call intent
        intent = _detect_tool_intent(metaclaw_response, content_text)

        if intent:
            print(f"[MetaClaw] Tool intent detected: {intent['type']}")
            print(f"[MetaClaw] Requirements: {intent.get('requirements', '')[:200]}...")
            # Hand off to Gemini for execution
            return await _execute_with_gemini(intent, request, content_text)
        else:
            # No tool intent — stream MetaClaw's response directly
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
    Hand off to Gemini with tools attached. Gemini will execute the create_mcp_server tool
    based on MetaClaw's decision.
    """
    requirements = intent.get("requirements", "")

    # System prompt for Gemini — tell it MetaClaw has already decided
    gemini_system = f"""You are an autonomous MCP server builder assistant.
MetaClaw (the decision-making brain) has already analyzed the user's request and decided that an MCP server should be built.
Your job is to execute this decision by calling the create_mcp_server tool with the appropriate requirements.

DO NOT ask for permission or confirmation — just execute the build immediately.
DO NOT respond with text explanations — just trigger the tool and let the system handle progress reporting.

Requirements from MetaClaw's analysis:
{requirements}

Use these requirements to call create_mcp_server. If the requirements are vague or text-based, interpret them and build the most appropriate MCP server.
"""

    last_turn_index = len(request.messages) - 1

    # Build conversation history for Gemini, including MetaClaw's thinking as context
    gemini_msgs = [SystemMessage(content=gemini_system)]
    for msg in request.messages:
        if msg.role == "user":
            gemini_msgs.append(HumanMessage(content=msg.content))
        else:
            gemini_msgs.append(AIMessage(content=msg.content))

    # Add MetaClaw's thinking as an assistant message for context
    if metaclaw_context:
        gemini_msgs.append(AIMessage(content=f"[MetaClaw Analysis]: {metaclaw_context[:500]}"))

    print(f"[Gemini] Executing with {len(gemini_msgs)} messages, requirements: {requirements[:100]}...")

    # Create Gemini executor with tools
    try:
        gemini_agent = await _create_gemini_executor(request.mcpServers, request.temperature)
    except Exception as e:
        error_msg = str(e)
        async def fallback_stream():
            yield f"data: {json.dumps({'content': f'\\n\\n> [ERROR]: Cannot create Gemini executor: {error_msg}\\n\\n'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(fallback_stream(), media_type="text/event-stream")

    async def gemini_stream():
        try:
            # Use ainvoke (not astream) on the raw LLM-with-tools.
            # This keeps the AIMessage intact so we can read tool_calls directly.
            gemini_response = await gemini_agent.ainvoke(gemini_msgs)

            print(f"[Gemini] Response type: {type(gemini_response)}")
            print(f"[Gemini] tool_calls: {getattr(gemini_response, 'tool_calls', None)}")

            # Collect tool calls from all possible locations
            tool_calls = []
            if hasattr(gemini_response, "tool_calls") and gemini_response.tool_calls:
                tool_calls = gemini_response.tool_calls
            elif hasattr(gemini_response, "additional_kwargs"):
                tool_calls = gemini_response.additional_kwargs.get("tool_calls", [])

            create_mcp_tc = None
            for tc in tool_calls:
                tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                if tc_name == "create_mcp_server":
                    create_mcp_tc = tc
                    break

            if create_mcp_tc:
                tc_args = create_mcp_tc.get("args") if isinstance(create_mcp_tc, dict) else getattr(create_mcp_tc, "args", {})
                if isinstance(tc_args, str):
                    try:
                        tc_args = json.loads(tc_args)
                    except Exception:
                        tc_args = {}
                reqs = tc_args.get("requirements", requirements) if isinstance(tc_args, dict) else requirements

                print(f"[Gemini] TRIGGERING LANGGRAPH BUILD: {reqs[:100]}...")
                system_msg = f"\n\n> [SYSTEM]: Building MCP Server...\n\n"
                yield f"data: {json.dumps({'content': system_msg})}\n\n"

                lg_url = os.getenv("NEXT_PUBLIC_LANGGRAPH_API_URL") or os.getenv("LANGGRAPH_API_URL") or "http://localhost:2024"
                if "localhost" in lg_url and os.path.exists("/.dockerenv"):
                    lg_url = lg_url.replace("localhost", "host.docker.internal")

                print(f"[Gemini] Connecting to LangGraph at: {lg_url}")

                try:
                    lg_client = get_client(url=lg_url)
                    thread = await lg_client.threads.create()

                    # Send only user messages to LangGraph (keep it clean)
                    lg_history = [{"role": "user", "content": reqs}]

                    async for lg_chunk in lg_client.runs.stream(
                        thread["thread_id"],
                        "agent",
                        input={"messages": lg_history},
                        stream_mode="messages"
                    ):
                        if lg_chunk.event == "messages/partial" and isinstance(lg_chunk.data, list):
                            content = lg_chunk.data[0].get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"

                    print("[Gemini] LANGGRAPH BUILD COMPLETED")
                    return

                except Exception as lg_err:
                    print(f"[Gemini] LangGraph Error: {lg_err}")
                    err_msg = f"\n\n> [ERROR]: Cannot connect to LangGraph service: {str(lg_err)}\n\n"
                    yield f"data: {json.dumps({'content': err_msg})}\n\n"
                    return

            else:
                # Gemini chose not to call the tool — fallback: trigger LangGraph directly
                # since MetaClaw already confirmed intent
                print(f"[Gemini] No tool call found, triggering LangGraph directly with MetaClaw requirements")
                system_msg = f"\n\n> [SYSTEM]: Building MCP Server (direct trigger)...\n\n"
                yield f"data: {json.dumps({'content': system_msg})}\n\n"

                lg_url = os.getenv("NEXT_PUBLIC_LANGGRAPH_API_URL") or os.getenv("LANGGRAPH_API_URL") or "http://localhost:2024"
                if "localhost" in lg_url and os.path.exists("/.dockerenv"):
                    lg_url = lg_url.replace("localhost", "host.docker.internal")

                try:
                    lg_client = get_client(url=lg_url)
                    thread = await lg_client.threads.create()
                    lg_history = [{"role": "user", "content": requirements}]

                    async for lg_chunk in lg_client.runs.stream(
                        thread["thread_id"],
                        "agent",
                        input={"messages": lg_history},
                        stream_mode="messages"
                    ):
                        if lg_chunk.event == "messages/partial" and isinstance(lg_chunk.data, list):
                            content = lg_chunk.data[0].get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"

                    print("[Gemini] LANGGRAPH BUILD COMPLETED (direct)")
                    return

                except Exception as lg_err:
                    print(f"[Gemini] LangGraph Error (direct): {lg_err}")
                    err_msg = f"\n\n> [ERROR]: Cannot connect to LangGraph service: {str(lg_err)}\n\n"
                    yield f"data: {json.dumps({'content': err_msg})}\n\n"
                    return

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(gemini_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=backend_port)
