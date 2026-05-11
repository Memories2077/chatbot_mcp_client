# Fix MCP Server Misuse: Bypass MetaClaw When MCP Servers Provided

## Context

The chatbot backend supports two operational modes:

1. **Standard Mode** (Gemini/Groq): Connects to user-provided MCP servers, loads their tools, and creates an agent that can use those tools to fulfill user requests.

2. **MetaClaw Mode** (Brain+Arms architecture): MetaClaw acts as an intent classifier. When it detects that the user wants to build an MCP server (e.g., provides API documentation), it hands off to Gemini to call `create_mcp_server` and trigger a LangGraph build.

**Problem**: When MetaClaw is enabled in configuration (`METACLAW_ENABLED=true`), the backend **forces all requests into MetaClaw mode**, even when the user explicitly provides MCP server URLs via the `mcpServers` parameter with the intention of **using** those existing servers. The provided MCP servers are completely ignored, and the system incorrectly attempts to build a new MCP server.

## Root Cause

In `backend/main.py`, the `/chat` endpoint has this logic:

```python
if llm_config.is_metaclaw_enabled():
    print("[MetaClaw] MetaClaw enabled in config. Forcing provider to 'metaclaw'.")
    effective_provider = "metaclaw"
    effective_model = llm_config.metaclaw_model
```

This unconditionally forces MetaClaw when it's enabled, **without checking** whether the user provided `mcpServers`. The `mcpServers` parameter is then passed to `get_or_create_agent`, but:

- When provider is `"metaclaw"`, `get_or_create_agent` creates a `MetaClawClient` and returns it **without connecting to the provided MCP servers** (see lines 323-338).
- The MetaClawClient has no knowledge of the user's MCP servers and only knows about `create_mcp_server`.
- The chat response is streamed from `MetaClawClient.chat()`, which never uses the user's MCP tools.

Thus, user-provided MCP servers are silently ignored.

## User Impact

- User connects an MCP server (e.g., a filesystem or database tool).
- User asks the chatbot to use that tool: "List files using the connected MCP server."
- Instead of using the connected tool, the system says it will build a new MCP server.
- The actual connected MCP server remains unused.

## Proposed Solution

**Primary fix**: Modify the provider selection logic in the `/chat` endpoint to **bypass MetaClaw when the user provides MCP servers**. The user's explicit intent to use existing MCP servers should take precedence over the global MetaClaw configuration.

### Logic

```python
if request.mcpServers and len(request.mcpServers) > 0:
    # User wants to use existing MCP servers → standard provider flow
    effective_provider = request.provider
    effective_model = request.model
    print(f"[MCP Servers] Using direct provider '{effective_provider}' to connect to {len(request.mcpServers)} MCP server(s).")
elif llm_config.is_metaclaw_enabled():
    # No MCP servers provided → MetaClaw can decide to build
    effective_provider = "metaclaw"
    effective_model = llm_config.metaclaw_model
    print("[MetaClaw] MetaClaw enabled. Using MetaClaw routing.")
else:
    # Standard flow without MetaClaw
    effective_provider = request.provider
    effective_model = request.model
```

### Why This Works

- Standard flow (`get_or_create_agent` with provider `"gemini"` or `"groq"`) **does** connect to `mcpServers`, load their tools via `load_mcp_tools()`, and create an agent that can use those tools.
- The `create_mcp_server` tool is **not** bound to standard agents (it's only bound to MetaClaw/Gemini in the MetaClaw flow), so the agent will only use the actual MCP tools the user provided.
- The safety net that catches `create_mcp_server` calls (lines 577-584) will not trigger in standard flow because the tool is not available.

## Alternative Approaches Considered

### 1. Enhance MetaClaw to also use provided MCP servers
- Merge MCP tools from `mcpServers` into MetaClawClient's tool set.
- **Rejected**: Complex; would require significant refactoring of MetaClawClient and its handoff logic. The two use cases (use existing tools vs. build new ones) are semantically different and should be separate flows.

### 2. Add explicit `useMetaClaw` flag in request
- Let frontend choose per-request whether to use MetaClaw.
- **Deferred**: Could be a future enhancement, but the current fix (bypass when MCP servers provided) aligns with user intent and is simpler.

## Implementation Plan

### Files to Modify

1. **`backend/main.py`** – Update the `/chat` endpoint provider selection logic.

### Changes

In `chat_endpoint()` function (around line 517-527):

Replace:
```python
# Determine the effective provider and model based on MetaClaw configuration
effective_provider = request.provider
effective_model = request.model

if llm_config.is_metaclaw_enabled():
    print("[MetaClaw] MetaClaw enabled in config. Forcing provider to 'metaclaw'.")
    effective_provider = "metaclaw"
    effective_model = llm_config.metaclaw_model # Use metaclaw's configured model
```

With:
```python
# Determine the effective provider and model
effective_provider = request.provider
effective_model = request.model

# Priority 1: If user provided MCP servers, use direct provider to consume them
# (MetaClaw is for building MCP servers, not using existing ones)
if request.mcpServers and len(request.mcpServers) > 0:
    print(f"[MCP Servers] User provided {len(request.mcpServers)} MCP server(s). Using direct provider '{effective_provider}' to connect and use them.")
    # effective_provider remains request.provider
# Priority 2: If MetaClaw is enabled and no MCP servers, use MetaClaw routing
elif llm_config.is_metaclaw_enabled():
    print("[MetaClaw] MetaClaw enabled in config. Forcing provider to 'metaclaw'.")
    effective_provider = "metaclaw"
    effective_model = llm_config.metaclaw_model
# Priority 3: Standard flow (no MCP servers, MetaClaw disabled)
else:
    # effective_provider remains request.provider
    pass
```

### No Other Changes Needed

- `get_or_create_agent` already handles standard provider flow correctly (connects to MCP servers, loads tools).
- MetaClawClient remains unchanged (used only when MetaClaw is selected).
- The safety net (lines 577-584) is harmless in standard flow and can remain as a fallback.

## Testing & Verification

### Manual Test Cases

1. **Setup**: Ensure `METACLAW_ENABLED=true` in `.env`. Start backend and frontend.

2. **Test Case A: Use MCP servers (expected: tools are used)**
   - In frontend, add an MCP server URL (e.g., a filesystem server).
   - Send message: "List files in the current directory using the connected MCP server."
   - **Expected behavior**: Backend connects to the MCP server, loads its tools, and the agent calls the appropriate tool (e.g., `list_files`). Response shows tool execution results.
   - **Not expected**: No "Building MCP Server" message, no LangGraph streaming.

3. **Test Case B: Request new MCP server build (MetaClaw flow)**
   - Ensure no MCP servers are connected in the UI.
   - Send message with API documentation: "Here's my API spec. Build an MCP server for it: ..."
   - **Expected behavior**: Backend uses MetaClaw, detects intent, and streams LangGraph build progress.
   - **Not expected**: Standard agent response without building.

4. **Test Case C: Normal chat without MCP (MetaClaw disabled or fallback)**
   - No MCP servers, simple chat: "Hello, how are you?"
   - **Expected**: Normal chat response from Gemini/Groq.

### Automated Tests

- Existing unit tests in `backend/tests/test_metaclaw_integration.py` should continue to pass (they test MetaClawClient in isolation).
- No new tests required for this fix, as it's a routing change. However, consider adding an integration test for the `/chat` endpoint with `mcpServers` provided while MetaClaw enabled, asserting that the response does **not** contain LangGraph build streaming.

### Regression Prevention

- The change is confined to the provider selection block.
- No modifications to `get_or_create_agent` or MetaClawClient, so existing MetaClaw functionality remains intact when no MCP servers are provided.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| User might want both MetaClaw and MCP servers (combined use) | This is an advanced scenario not currently supported. The fix prioritizes user's explicit `mcpServers` parameter. Can be revisited later if needed. |
| Edge case: empty `mcpServers` array (`[]`) | Condition `if request.mcpServers and len(request.mcpServers) > 0` treats empty array as "no servers", so MetaClaw can still be used. |
| Frontend might send `mcpServers` even when not intended | The UI only sends `mcpServers` when user configures them, so this is safe. |

## Success Criteria

- When `mcpServers` is provided, the backend connects to those servers and the agent uses their tools.
- No "Building MCP Server" streaming appears when MCP servers are provided.
- MetaClaw flow still works when `mcpServers` is empty and `METACLAW_ENABLED=true`.
- All existing tests pass.
