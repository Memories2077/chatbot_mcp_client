#!/usr/bin/env python
"""
MCP client that connects to multiple MCP servers, loads all tools, and runs a chat loop using Google Gemini LLM.
Core idea for this project's backend implementation
"""

import asyncio
import os
import sys
import json
from contextlib import AsyncExitStack
from typing import Optional, List

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
load_dotenv()

# Custom JSON encoder for objects with 'content' attribute
class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)

def get_mcp_urls_from_config(config_path: str) -> List[str]:
    """Extracts MCP server URLs from the config file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        urls = []
        for server_name, server_config in config.get("mcpServers", {}).items():
            args = server_config.get("args", [])
            # Find the URL which is typically the second argument after 'mcp-remote'
            for arg in args:
                if arg.startswith("http"):
                    urls.append(arg)
                    break
        return urls
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing {config_path}: {e}")
        return []

api_key = os.getenv("GEMINI_API_KEY", "")

# Instantiate Google Gemini LLM with deterministic output and retry logic
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_retries=2,
    api_key=api_key
)

# Main async function: connect to all servers, load tools, create agent, run chat loop
async def run_agent():
    all_tools = []
    mcp_urls = get_mcp_urls_from_config("mcp_config.json")

    if not mcp_urls:
        print("No MCP server URLs found in config. Exiting.")
        return

    print(f"Found MCP servers: {mcp_urls}")

    async with AsyncExitStack() as stack:
        sessions = []
        for url in mcp_urls:
            try:
                # Enter the context for each client
                read, write, callback = await stack.enter_async_context(streamable_http_client(url))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                sessions.append(session)
                print(f"Successfully connected to {url}")
            except Exception as e:
                print(f"Failed to connect to MCP server at {url}: {e}")
                continue

        # Load tools from all successfully connected sessions
        for i, session in enumerate(sessions):
            try:
                # Note: The global mcp_client holder is not ideal for multi-session.
                # Langchain adapter might need adjustment for a more robust multi-client scenario.
                # For now, we load tools from each session sequentially.
                mcp_client = type("MCPClientHolder", (), {"session": session})()
                tools = await load_mcp_tools(session)
                all_tools.extend(tools)
                print(f"Loaded {len(tools)} tools from {mcp_urls[i]}")
            except Exception as e:
                print(f"Failed to load tools from {mcp_urls[i]}: {e}")

        if not all_tools:
            print("No tools loaded from any MCP server. Exiting.")
            return
            
        agent = create_agent(llm, all_tools)
        print("\nMCP Client Started with all tools! Type 'quit' to exit.")
        
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break
            
            # Send user query to agent and print formatted response
            response = await agent.ainvoke({"messages": [("user", query)]})
            try:
                formatted = json.dumps(response, indent=2, cls=CustomEncoder)
            except Exception:
                formatted = str(response)
            
            print("\nResponse:")
            print(formatted)

    return

# Entry point: run the async agent loop
if __name__ == "__main__":
    asyncio.run(run_agent())