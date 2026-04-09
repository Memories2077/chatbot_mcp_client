import asyncio
import os
import json
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from langchain_core.language_models import BaseLanguageModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


from dotenv import load_dotenv
load_dotenv()

# For local development, read the port from .env and ensure it's a valid integer.
# This is ignored in Docker, which uses the 'command' from docker-compose.yml.
try:
    backend_port = int(os.getenv("NEXT_PUBLIC_BACKEND_PORT", "8000"))
except (ValueError, TypeError):
    backend_port = 8000

app = FastAPI()

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
        self.exit_stack = None
        self.current_provider = None
        self.current_model = None
        self.current_mcp_urls = []
        self.lock = asyncio.Lock() # Add lock to prevent race conditions

state = AgentState()

async def get_or_create_agent(provider: str, model_name: str, mcp_urls: List[str], temperature: float):
    # Ensure mcp_urls is a clean list of strings
    mcp_urls = [str(url) for url in mcp_urls if url]
    
    async with state.lock:
        # Check if we can reuse the existing agent
        if (state.agent and
            state.current_provider == provider and
            state.current_model == model_name and 
            sorted(state.current_mcp_urls) == sorted(mcp_urls)):
            return state.agent

        print(f"\n--- CONFIG CHANGE DETECTED ---")
        print(f"Re-initializing agent for provider '{provider}' with model '{model_name}'...")
        
        # Aggressive cleanup of the old stack
        if state.exit_stack:
            try:
                # We wrap this in a protected block to catch anyio's task-mismatch errors
                await state.exit_stack.aclose()
            except Exception as e:
                print(f"Note: Cleanup of old MCP sessions was messy (Task mismatch), but moving on: {e}")
            finally:
                state.exit_stack = None
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
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    all_tools = []
    state.exit_stack = AsyncExitStack()
    
    if mcp_urls:
        sessions = []
        for url in mcp_urls:
            try:
                print(f"Attempting to connect to: {url}...")
                streams = await asyncio.wait_for(
                    state.exit_stack.enter_async_context(streamable_http_client(url)), 
                    timeout=10.0
                )
                read, write, callback = streams
                session = await state.exit_stack.enter_async_context(ClientSession(read, write))
                await asyncio.wait_for(session.initialize(), timeout=10.0)
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
    return state.agent

def get_system_prompt(has_tools: bool, mcp_urls: List[str], last_turn_index: int):
    base = f"""You are a helpful and intelligent AI assistant. 
The conversation history is provided with [Turn Index] and [Timestamp] for each message. 
The current message is [Turn {last_turn_index}].
Always prioritize the latest information and the current configuration state over historical turns."""
    
    if has_tools:
        tools_list = ", ".join(mcp_urls) if mcp_urls else "active sessions"
        return f"{base}\n\nCURRENT STATUS (Turn {last_turn_index}): MCP Tools are ENABLED. You have access to: {tools_list}. Use them if the user request requires real-time or external data."
    else:
        return f"{base}\n\nCURRENT STATUS (Turn {last_turn_index}): MCP Tools are DISABLED. No external tools or files are available in this turn. You MUST answer based ONLY on your internal knowledge. Do NOT attempt to use tools or mention that you might have them in the future unless the user adds them."""

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        agent = await get_or_create_agent(
            provider=request.provider,
            model_name=request.model,
            mcp_urls=request.mcpServers,
            temperature=request.temperature
        )

        # Check if the agent is actually an agent with tools or just the LLM
        has_tools = not isinstance(agent, BaseLanguageModel)
        
        last_turn_index = len(request.messages) - 1
        dynamic_prompt = get_system_prompt(has_tools, state.current_mcp_urls, last_turn_index)

        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        langchain_msgs = [SystemMessage(content=dynamic_prompt)]
        for msg in request.messages:
            if msg.role == "user":
                langchain_msgs.append(HumanMessage(content=msg.content))
            else:
                langchain_msgs.append(AIMessage(content=msg.content))

        if hasattr(agent, "ainvoke"):
            if has_tools:
                # When using tools, the agent is a LangGraph, which requires a dict {"messages": ...}
                try:
                    response = await agent.ainvoke({"messages": langchain_msgs})
                except Exception as e:
                    print(f"\n[AGENT ERROR] Actual error from Groq/Agent: {e}")
                    raise HTTPException(status_code=500, detail=f"Agent Tool Calling Error: {str(e)}")
            else:
                # When no tools are provided, the agent is a pure BaseLanguageModel, which accepts a list directly
                try:
                    response = await agent.ainvoke(langchain_msgs)
                except Exception as e:
                    print(f"\n[LLM ERROR] Actual error from Groq/LLM: {e}")
                    raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail="Agent does not have a valid ainvoke method")

        res_text = ""
        if isinstance(response, dict) and "messages" in response:
            last_msg = response["messages"][-1]
            if hasattr(last_msg, "content"):
                res_text = last_msg.content
            else:
                res_text = str(last_msg)
        elif hasattr(response, "content"):
            res_text = response.content
        else:
            res_text = str(response)

        # Final safety check: ensure res_text is a string
        if not isinstance(res_text, str):
            try:
                if isinstance(res_text, list):
                    res_text = "\n".join([str(b.get("text", b) if isinstance(b, dict) else b) for b in res_text])
                else:
                    res_text = json.dumps(res_text, cls=CustomEncoder)
            except:
                res_text = str(res_text)

        return {"response": res_text}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=backend_port)
