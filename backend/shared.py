"""
Shared utilities for backend modules.

This module contains common functions used across main.py and metaclaw_client.py
to avoid code duplication and ensure consistent behavior.
"""

import json
import logging
import os
import asyncio
from typing import Any, Dict, Optional, AsyncGenerator, Callable
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools import tool

logger = logging.getLogger(__name__)

# Constants
MCP_SERVER_TOOL_NAME = "create_mcp_server"
MCP_SERVER_TOOL_DESC = "Build a custom MCP server with specific tools and resources"
USE_MCP_TOOLS_NAME = "use_mcp_tools"
USE_MCP_TOOLS_DESC = "Signals that the user wants to use the connected MCP servers/tools"
DOCKER_HOST_REPLACEMENTS = {
    "host.docker.internal": "localhost",
    "172.17.0.1": "localhost",
}
DEFAULT_MCP_TIMEOUT = 10.0

# Tool singleton cache
_create_mcp_server_tool_instance = None
_use_mcp_tools_tool_instance = None


# ==================== Tool Factories ====================

def create_mcp_server_tool() -> Callable:
    """
    Get or create the create_mcp_server tool (singleton pattern).
    Returns a decorated LangChain tool function.
    """
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


def create_use_mcp_tools_tool() -> Callable:
    """
    Get or create the use_mcp_tools tool (singleton pattern).
    Returns a decorated LangChain tool function.
    """
    global _use_mcp_tools_tool_instance
    if _use_mcp_tools_tool_instance is None:
        @tool
        async def use_mcp_tools() -> str:
            """
            Signals that the user wants to use the connected MCP servers/tools.
            Call this when the user asks to utilize existing MCP tools or sessions.
            """
            return "USE_MCP_TOOLS_TRIGGERED"
        _use_mcp_tools_tool_instance = use_mcp_tools
    return _use_mcp_tools_tool_instance


# ==================== Tool Extraction ====================

def extract_create_mcp_tool_call(response: Any) -> Optional[str]:
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


def extract_use_mcp_tool_call(response: Any) -> bool:
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


# ==================== URL Normalization ====================

def normalize_docker_urls_in_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Docker-specific hostnames to localhost for local development.
    Returns a new dict without mutating the input.
    """
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            new_value = value
            for docker_host, local_host in DOCKER_HOST_REPLACEMENTS.items():
                if docker_host in new_value:
                    new_value = new_value.replace(docker_host, local_host)
                    logger.debug(f"Normalized {key}: {value} -> {new_value}")
            result[key] = new_value
        elif isinstance(value, dict):
            result[key] = normalize_docker_urls_in_dict(value)
        else:
            result[key] = value
    return result


# ==================== LangGraph Streaming ====================

async def stream_langgraph_build(
    requirements: str, langgraph_url: str
) -> AsyncGenerator[str, None]:
    """
    Stream build progress from LangGraph service using the LangGraph SDK.
    Yields SSE data chunks as they arrive.
    """
    from langgraph_sdk import get_client

    # Normalize URL for Docker
    normalized_url = langgraph_url
    if "localhost" in normalized_url and os.path.exists("/.dockerenv"):
        normalized_url = normalized_url.replace("localhost", "host.docker.internal")

    yield f"data: {json.dumps({'content': chr(10) + chr(10) + '> [SYSTEM]: Building MCP Server...' + chr(10) + chr(10)})}\n\n"

    lg_client = None
    try:
        lg_client = get_client(url=normalized_url)
        logger.info(f"Connected to LangGraph service at {normalized_url}")
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

        logger.info("--- LangGraph build completed ---")

    except Exception as lg_err:
        logger.exception("LangGraph build error")
        err_msg = f"\n\n> [ERROR]: Cannot connect to LangGraph service: {str(lg_err)}\n\n"
        yield f"data: {json.dumps({'content': err_msg})}\n\n"
    finally:
        # LangGraph client does not require explicit cleanup, but if it has aclose(), call it
        if lg_client is not None:
            try:
                if hasattr(lg_client, "aclose") and callable(getattr(lg_client, "aclose")):
                    await lg_client.aclose()
                    logger.debug("LangGraph client closed via aclose()")
                elif hasattr(lg_client, "close") and callable(getattr(lg_client, "close")):
                    # If close is async, we need to check if it's a coroutine
                    close_method = getattr(lg_client, "close")
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
                    logger.debug("LangGraph client closed via close()")
                else:
                    logger.debug("LangGraph client has no close/aclose method, skipping cleanup")
            except Exception as close_err:
                logger.warning(f"Error closing LangGraph client: {close_err}")


def build_langgraph_sse_payload(requirements: str) -> str:
    """Build the SSE payload for initiating a LangGraph build."""
    payload = {
        "event": "build",
        "data": {
            "requirements": requirements,
            "project_type": "mcp-server",
        },
    }
    return f"data: {json.dumps(payload)}\n\n"
