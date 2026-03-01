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
from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    model: Optional[str] = "gemini-2.0-flash"
    temperature: Optional[float] = 0.0
    mcpServers: Optional[List[str]] = []

# Global state to keep track of the current agent and its config
class AgentState:
    def __init__(self):
        self.agent = None
        self.exit_stack = None
        self.current_model = None
        self.current_mcp_urls = []

state = AgentState()

async def get_or_create_agent(model_name: str, mcp_urls: List[str], temperature: float):
    # Ensure mcp_urls is a clean list of strings
    mcp_urls = [str(url) for url in mcp_urls if url]
    
    # Check if we can reuse the existing agent
    if (state.agent and 
        state.current_model == model_name and 
        sorted(state.current_mcp_urls) == sorted(mcp_urls)):
        return state.agent

    print(f"\n--- CONFIG CHANGE DETECTED ---")
    print(f"Re-initializing agent with {model_name}...")
    
    if state.exit_stack:
        await state.exit_stack.aclose()
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise Exception("GEMINI_API_KEY not found.")

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=2,
        api_key=api_key
    )

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
        state.agent = create_agent(llm, all_tools)
    else:
        state.agent = llm

    state.current_model = model_name
    state.current_mcp_urls = mcp_urls.copy()
    return state.agent

SYSTEM_PROMPT = "You are a helpful AI assistant. Remember and refer back to previous parts of the conversation."

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        agent = await get_or_create_agent(
            model_name=request.model,
            mcp_urls=request.mcpServers,
            temperature=request.temperature
        )

        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        langchain_msgs = [SystemMessage(content=SYSTEM_PROMPT)]
        for msg in request.messages:
            if msg.role == "user":
                langchain_msgs.append(HumanMessage(content=msg.content))
            else:
                langchain_msgs.append(AIMessage(content=msg.content))

        if hasattr(agent, "ainvoke"):
            try:
                response = await agent.ainvoke({"messages": langchain_msgs})
            except Exception:
                response = await agent.ainvoke(langchain_msgs)
        else:
            raise HTTPException(status_code=500, detail="Agent error")

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
