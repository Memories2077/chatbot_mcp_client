# Project History

## [2026-04-24] Feature: MongoDB Integration & Feedback Storage Backend

### Overview

Implemented a robust feedback storage system using MongoDB. This integration allows the chatbot to persist chat logs and user feedback (likes/dislikes) in a shared database infrastructure, enabling long-term analytics and service improvement.

### Changes

- **MongoDB Persistence**: Integrated MongoDB as the primary store for chat logs and user feedback. Both `chatbot_mcp_client` and `mcp-gen` now share the same MongoDB instance but use isolated collections (`chat_logs` vs `logs`).
- **Enhanced Database Layer**: Created `backend/database.py` using `motor` for asynchronous MongoDB operations. Implemented automatic index creation for `messageId` (unique), `serverId`, and `timestamp` to ensure query performance.
- **Feedback API & Routing**: Developed `backend/feedback_routes.py` providing endpoints to:
  - Submit likes/dislikes with atomic `$inc` counters.
  - Store detailed feedback entries with optional `serverId` and `userId` traceability.
  - Retrieve feedback statistics for specific messages.
- **Shared Docker Networking**: Updated `docker-compose.yml` to join the `mcp-network`, allowing the backend to communicate with the `mongodb` container in the `mcp-gen` stack using internal DNS.
- **Configuration & Security**: Added MongoDB connection settings to `backend/config.py` and `.env.example`.
- **Comprehensive Testing**: Created `test_feedback_backend.py` which validates the entire feedback lifecycle, including health checks, atomic increments, and error handling for non-existent messages.
- **Documentation**: Authored `docs/MONGODB_INTEGRATION_GUIDE.md` for network topology and setup, and `docs/DAY4_FEEDBACK_BACKEND_COMPLETE.md` for implementation details.

### Files Created/Modified

- **Created**: `backend/database.py`, `backend/feedback_routes.py`, `backend/models.py`, `test_feedback_backend.py`, `docs/MONGODB_INTEGRATION_GUIDE.md`, `docs/DAY4_FEEDBACK_BACKEND_COMPLETE.md`
- **Modified**: `backend/main.py`, `backend/config.py`, `backend/requirements.txt`, `.env.example`, `docker-compose.yml`, `history.md`

---

## [2026-04-21] Bug Fixes & Integration Polish: MetaClaw Routing & State

### Overview

Fixed several critical logic errors and integration gaps in the `MetaClawClient` refactoring. These fixes ensure that the MetaClaw provider correctly handles tool execution, respects user-selected models, and works reliably in containerized environments.

### Changes

- **Fixed `NameError` for Singleton Context**: Defined `_create_mcp_server_tool_instance` at the module level in `metaclaw_client.py` and updated the initialization check to use `is None`.
- **Docker Container Routing**: Added automatic URL normalization for `metaclaw_base_url` to handle `localhost` to `host.docker.internal` translation when running inside Docker.
- **State & Cache Consistency**: Refactored `chat_endpoint` in `main.py` to remove redundant MetaClaw-specific logic, ensuring all providers flow through the central `get_or_create_agent` factory for proper state management and caching.
- **Model Selection Visibility**: Updated `MetaClawClient` to accept and respect an overriding `model_name` from the frontend, allowing users to dynamically switch between Gemini, Llama, or Claude models via the UI.
- **Typo Corrections**: Renamed `_get_metacaw_llm` to `_get_metaclaw_llm` throughout the codebase.
- **Files Modified**: `backend/metaclaw_client.py`, `backend/main.py`

---

## [2026-04-21] Refactoring: Centralized Configuration & MetaClaw Client Wrapper

### Overview

Completed major refactoring to eliminate configuration scattering and improve code maintainability. This addresses critical technical debt where MetaClaw configuration and logic were spread across multiple files and repositories.

### Changes

#### 1. Centralized Configuration Management

- **Created `backend/config.py`**: New `LLMConfig` dataclass serves as single source of truth for all LLM provider settings
- **Unified Environment Loading**: All `os.getenv()` calls consolidated into `LLMConfig.from_env()` method
- **Improved Type Safety**: Configuration now validated through typed fields with sensible defaults
- **Provider Selection**: Added `get_llm_provider()` and `is_metaclaw_enabled()` helper methods

#### 2. MetaClaw Client Wrapper

- **Created `backend/metaclaw_client.py`**: Encapsulates all MetaClaw-specific logic into reusable `MetaClawClient` class
- **Two-Stage Routing**: Handles MetaClaw → Gemini handoff internally, simplifying main.py
- **Tool Intent Detection**: Moved `_detect_tool_intent()` and `_extract_create_mcp_tool_call()` to wrapper
- **LangGraph Streaming**: Integrated `_stream_langgraph_build()` using centralized config
- **Custom Exceptions**: Added `MetaClawError` and `MetaClawDisabledError` for clearer error handling

#### 3. Main Backend Simplification

- **Removed 150+ lines** of MetaClaw-specific code from `backend/main.py`
- **Updated `get_or_create_agent()`**: MetaClaw branch now returns `MetaClawClient` instance directly
- **Updated `chat_endpoint()`**: Added MetaClaw-specific handling but logic is now declarative
- **Updated `health_check()`**: Uses centralized config instead of scattered `os.getenv()` calls
- **Removed Duplicate Functions**: Deleted `_handle_metaclaw_request()` and `_execute_with_gemini()` (now in wrapper)

#### 4. Testing & Quality

- **Created `backend/tests/test_metaclaw_integration.py`**: Comprehensive test suite covering:
  - Configuration loading and validation
  - MetaClaw client initialization (success/failure)
  - Tool call extraction from multiple formats (tool_calls, additional_kwargs)
  - Intent detection from structured and text responses
  - Two-stage handoff flow
  - Fallback behavior when MetaClaw disabled
  - LangGraph build streaming
- **Test Fixtures**: Proper environment setup and mock objects for isolated testing

#### 5. Documentation Updates

- **Updated `chatbot_mcp_client/.env.example`**: Added comprehensive documentation for all config options including MetaClaw, LangGraph, MCP settings
- **Updated `CLAUDE.md`**: Added references to new `config.py` and `metaclaw_client.py` files; enhanced Configuration section with detailed examples
- **Updated `mcp-gen/.env.example`**: Added MetaClaw configuration documentation (already implemented in code)

#### 6. mcp-gen Integration (Already Complete)

- Verified that `mcp-gen/src/utils/genai.ts` already properly uses `metaclawConfig.enabled` to route through MetaClaw proxy
- Configuration already centralized in `mcp-gen/src/utils/config.ts`

### Benefits

- **Single Source of Truth**: All configuration in one place (`LLMConfig`)
- **Reduced Duplication**: No more scattered `os.getenv("METACLAW_*")` calls across 4+ files
- **Easier Testing**: MetaClaw client can be instantiated with mock config for unit tests
- **Better Maintainability**: MetaClaw logic isolated, making future changes safer
- **Consistent Behavior**: All modules using `LLMConfig` see identical configuration

### Files Modified/Created

- **Created**: `backend/config.py`, `backend/metaclaw_client.py`, `backend/tests/test_metaclaw_integration.py`
- **Modified**: `backend/main.py` (net -150 lines), `.env.example`, `CLAUDE.md`
- **Verified**: `mcp-gen/src/utils/genai.ts` (already correct)

---

## [2026-04-15] Bug Fix: Gemini Tool Handoff Interception

### Overview

Resolved an issue where the Gemini executor (the "arms") was using a ReAct agent loop that consumed tool calls internally. This prevented the backend from seeing the `create_mcp_server` signal and triggering the LangGraph build process. The system now uses a raw LLM call to preserve tool metadata for the backend to handle.

### Changes

- **Agent-to-LLM Transition**: Replaced `create_agent()` with `llm.bind_tools()` in `_create_gemini_executor`. This ensures that when Gemini responds, its `tool_calls` are visible in the resulting `AIMessage` rather than being hidden inside an autonomous agent loop.
- **Manual Tool Handling**: Refactored `gemini_stream` to use `ainvoke()` and manually parse the `AIMessage` for tool intent.
- **Intent Fallback**: Implemented an "Intent Fallback" mechanism. If MetaClaw has already expressed the intent to build a server, but Gemini fails to explicitly call the `create_mcp_server` tool, the backend now triggers the LangGraph build directly using the requirements extracted from MetaClaw's analysis.
- **Files Modified**: `backend/main.py`

---

## [2026-04-15] Bug Fix: MetaClaw Tool Call Detection

### Overview

Resolved a critical issue where tool calls from MetaClaw were being "swallowed" by the backend's agent loop, preventing the handoff to the LangGraph build service. This ensures that when MetaClaw decides to build an MCP server, the backend correctly detects that intent and triggers the execution phase.

### Changes

- **Raw LLM Handoff**: Modified `_handle_metaclaw_request` in `backend/main.py` to use a raw `ChatOpenAI` instance with `bind_tools` for Stage 1 (thinking) instead of the high-level agent loop. This prevents the agent from executing the tool call internally and losing the "intent" signal.
- **Intent Capture**: Ensured that the Stage 1 response preserves `tool_calls` from MetaClaw, which are now correctly picked up by `_detect_tool_intent`.
- **Enhanced Logging**: Added debug logs for `tool_calls` in the MetaClaw flow to verify detection early in the pipeline.
- **Files Modified**: `backend/main.py`

---

## [2026-04-15] MetaClaw → Gemini Two-Stage Handoff Architecture

### Overview

Implemented a "brain + arms" architecture where MetaClaw acts as the decision-making brain (skill injection, memory, reasoning) and Gemini acts as the executor (tool execution via LangChain agents). This solves the issue where MetaClaw would "think" about building an MCP server but had no way to actually execute the tool calls.

### Changes

- **Two-Stage Routing**: When `provider="metaclaw"`, the backend now:
  1. Sends the conversation to MetaClaw via `ainvoke()` to get its full response
  2. Analyzes the response for tool-call intent (structured `tool_calls`, keyword patterns like "build MCP server", "create_mcp_server", etc.)
  3. If intent detected → hands off to Gemini with tools attached for execution
  4. If no intent → streams MetaClaw's response directly to the user
- **Tool Intent Detection** (`_detect_tool_intent`): Parses MetaClaw responses for:
  - Structured `tool_calls` in OpenAI format
  - `additional_kwargs` provider-specific tool call formats
  - Text-based keyword matching with requirements extraction
- **Gemini Handoff Executor** (`_execute_with_gemini`): Creates a `ChatGoogleGenerativeAI` + `create_agent()` with:
  - `create_mcp_server` built-in tool
  - Any connected external MCP server tools
  - System prompt: "MetaClaw has already decided, just execute"
  - MetaClaw's analysis included as conversation context
- **LangGraph Build Triggering**: When Gemini's agent calls `create_mcp_server`, the backend intercepts and proxies the LangGraph build stream to the frontend (same pipeline as existing flow)
- **No User-Facing Duplication**: User sees ONE coherent response — either MetaClaw's direct answer (normal chat) or Gemini's execution output (tool action)
- **Files Modified**: `backend/main.py` — added `_handle_metaclaw_request()`, `_execute_with_gemini()`, `_create_gemini_executor()`, `_detect_tool_intent()`, `_extract_requirements_from_text()`, `_create_mcp_server_tool()`

---

## [2026-04-14] LangGraph Build Proxying & Hallucination Fix

### Overview

Solved the issue where the local agent would hallucinate tool execution reports after triggering a build, and implemented a robust backend-to-backend streaming proxy for LangGraph.

### Changes

- **Streaming Proxy**: Modified `backend/main.py` to intercept `create_mcp_server` tool calls and proxy the LangGraph progress stream directly to the frontend.
- **Hallucination Prevention**: Implemented a "hard-stop" mechanism and refined the system prompt to prevent the local agent from generating fake success messages after triggering a build.
- **Docker Networking**: Optimized the backend to automatically resolve LangGraph URLs using `NEXT_PUBLIC_LANGGRAPH_API_URL` and `host.docker.internal` for cross-container compatibility.

---

## [2026-04-14] Unified Routing Architecture & MetaClaw Integration

### Overview

Successfully overhauled the chatbot's interaction model by unifying all routing through a single backend endpoint, removing manual mode toggles, and integrating MetaClaw as a smart LLM proxy.

### Changes

- **Unified Routing**: Removed "MCP Mode" toggle from the frontend. All messages are now routed through the `/chat` endpoint at the backend.
- **Smart Tool Triggering**: Integrated the `create_mcp_server` tool into the backend's default LLM agent. The agent now autonomously decides when to trigger the LangGraph-based MCP creation flow.
- **SSE Streaming**: Implemented Server-Sent Events (SSE) in the backend to support seamless streaming of text and tool outputs from multiple providers.
- **MetaClaw Integration**: Configured the backend to use MetaClaw as the primary LLM provider, enabling persistent skills and memory injection.
- **Context Forwarding**: Implemented full conversation history forwarding from the backend to the LangGraph agent during tool invocation.

---

## [2026-04-14] MCP Streaming UI Polishing & Duplication Fix

### Overview

Enhanced MCP response rendering with structured delegate/context cards, success summaries, and more stable LangGraph stream handling to prevent duplicate or empty server result bubbles.

### Changes

- **Structured MCP output**: Added `DelegateBox`, `EnrichedContextBox`, and `McpSuccessCard` in `src/components/chat/chat-message.tsx` to render `DELEGATE_TO_EXAMINER`, `DELEGATE_TO_GENERATOR`, `ENRICHED_CONTEXT (RAG)`, and MCP success payloads as interactive, collapsible sections.
- **Better MCP feedback**: Added copy-to-clipboard support, status indicators, and JSON configuration previews for successful MCP server creations.
- **Streaming robustness**: Updated `src/lib/hooks/use-chat-store.ts` to track LangGraph message IDs and deduplicate repeated chunk events, avoiding stale or duplicated AI content during MCP creation.
- **Empty bubble fix**: Improved MCP stream handling so the AI message content is accumulated and updated cleanly, preventing blank model bubbles during initial LangGraph streaming.

---

## [2026-04-13] MCP Configuration UI Formatting

### Overview

Improved the presentation of MCP server configurations in the chat interface by automatically detecting and formatting raw JSON into Markdown code blocks.

### Changes

- **Auto-Formatting Logic**: Implemented `formatBotResponse` in `use-chat-store.ts` to wrap raw JSON objects (containing `mcpServers`) into triple-backtick JSON blocks.
- **Ubiquitous Application**: Applied formatting to all LangGraph streaming event handlers (messages, partials, values) and the casual chat fallback, ensuring consistent output regardless of the processing path.
- **UX Improvement**: JSON configurations are now clearly separated from conversational text, making them easier to read and copy.

---

## [2026-04-13] LangGraph Streaming Fix & Message Deduplication

### Overview

Resolved a critical UX issue where the user's input was echoed back as part of the AI response, and improved the stability of multi-agent streaming by implementing intelligent message tracking.

### Changes

- **Smart Message Accumulation**: Overhauled `use-chat-store.ts` to track LangGraph message IDs (`msg.id`). The frontend now distinguishes between different agents/messages in a single stream, preventing intermediate tool-call tasks (which often repeat the user's input) from being concatenated into the final response.
- **Agent Output Prioritization**: Implemented a "prefer-final" logic where the frontend prioritizes the `final_response` from the LangGraph `values` event. This ensures the user sees the definitive, cleaned output from the Supervisor Agent instead of raw intermediate chunks.
- **Enhanced Streaming Logic**:
  - Added support for clearing short, non-meaningful preambles when a definitive response starts (e.g., when "Configuration:" or JSON blocks are detected).
  - Improved delta handling for `messages/partial` vs. full content handling for `messages` events.
- **Robust Fallbacks**: Refined the thread-state fallback to ensure that even if a stream terminates abruptly, the final message content is correctly retrieved from the LangGraph server's persistent state.

---
