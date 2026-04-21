# Project History

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

## [2026-04-13] Frontend Reachability & MetaClaw Routing Fixes

### Overview

Resolved critical communication gaps between the browser-based frontend and the containerized agent, and standardized MetaClaw routing for Docker environments.

### Changes

- **Frontend Connectivity**: Updated `NEXT_PUBLIC_LANGGRAPH_API_URL` to `http://localhost:2024` in `docker-compose.yml` and `Dockerfile.frontend`. This ensures the user's browser can reach the LangGraph Agent via the host's mapped port.
- **MetaClaw Integration**: Updated `METACLAW_BASE_URL` to `http://host.docker.internal:30000/v1` in both `backend/main.py` and `.env.example`. This allows the containerized backend to reach a MetaClaw instance running on the host machine.
- **Build Optimization**: Added `NEXT_PUBLIC_LANGGRAPH_API_URL` as a build argument in the frontend Dockerfile to ensure the value is correctly baked into the Next.js client bundle during image creation.

---

## [2026-04-12] Docker Networking & MCP Routing Resolution

### Overview

Resolved critical infrastructure issues hindering communication between the LangGraph Agent and the MCP Server Manager, ensuring stable server creation and tool execution.

### Changes

- **Shared Networking (`mcp-network`)**: Updated `docker-compose.yml` to define `mcp-network` as `external: true`. This allows multiple Docker Compose stacks (Chatbot and LangGraph app) to share the same network infrastructure without ownership conflicts.
- **Service Discovery Fix**: Updated the `MCP_BASE_URL` and internal routing logic in the backend to use the container-native hostname `docker-manager:8080` instead of `localhost` or service-specific IPs.
- **Dynamic Container Attachment**: (In progress) Ensuring newly spawned MCP server containers are programmatically attached to the shared `mcp-network` to enable RAG indexing.

---

## [2026-04-12] LangGraph Stream Response Fix (Blank Output Diagnosis)

### Overview

Fixed the chatbot displaying a blank AI message box (with only the static "Verified Output" footer) after successfully creating an MCP server via LangGraph. The MCP server was created successfully (confirmed via LangSmith), but the response content never reached the UI.

### Root Cause

The LangGraph stream handler in `use-chat-store.ts` used `streamMode: "messages"` which only streamed message chunks. The final response from `supervisor_final_node` (containing `final_response`) was delivered via the `values` stream, not the `messages` stream. Additionally, message content could arrive in multiple formats (plain string, array of content blocks like `[{type: "text", text: "..."}]`) that the frontend didn't fully handle.

### Changes

- **`src/lib/hooks/use-chat-store.ts`**:
  - Added `extractContent()` helper function to handle all LangGraph content formats: plain strings, arrays of text blocks, and arrays of content objects.
  - Changed `streamMode` from `"messages"` to `["messages", "values"]` to capture both message chunks AND final state values.
  - Added handler for `values` stream events to read `final_response` and `values.messages` directly from the state.
  - Added post-stream fallback: if content is still empty after the stream ends, fetches the thread state via `client.threads.get()` as a last resort.
  - Added comprehensive `[LangGraph Stream]` debug logging for every received chunk (event type, data shape, content length, preview).
  - Added user-visible error message if all fallbacks fail, replacing the blank box with actionable feedback.

---

## [2026-04-11] Bug Fixes — Docker Build & LangGraph Thread 404

### Overview

Resolved two bugs: a Docker frontend build failure caused by a newer `npm` version triggering a false workspace detection error, and a LangGraph `404` runtime error caused by streaming runs on thread IDs that were never created server-side.

### Changes Logged

#### 1. Fix: Docker Frontend Build Failure (`npm ci` workspace error)

- **Root Cause**: `Dockerfile.frontend` was upgrading `npm` to the latest version globally (`npm install -g npm@latest`). npm v10.8+ introduced stricter workspace detection that incorrectly flagged this project's `package-lock.json` (lockfileVersion 3) as a workspace root, causing `npm ci` to fail with: `Include the workspace root when workspaces are enabled for a command`.
- **Fix** (`Dockerfile.frontend`):
  - Removed `npm install -g npm@latest` from both the `builder` and production stages. The stable `npm` bundled with `node:20-alpine` is used instead.
  - Replaced the deprecated `--only=production` flag with the modern `--omit=dev` flag in the production stage's `npm ci` command.

#### 2. Fix: LangGraph Streaming Returns 404 (`/threads/{thread_id}/runs/stream`)

- **Root Cause**: `use-chat-store.ts` was passing the frontend's local `currentChatId` UUID directly as the `thread_id` to `client.runs.stream()`. LangGraph requires threads to be **explicitly created** on the server via `POST /threads` before any runs can be streamed on them. Since these local UUIDs were never registered with the LangGraph API, every streaming request returned a `404 Not Found`.
- **Fix** (`src/lib/hooks/use-chat-store.ts`):
  - Before streaming, the code now searches for an existing LangGraph server-side thread tagged with the local `chatId` via `client.threads.search({ metadata: { localChatId: chatId } })`.
  - If no matching thread is found, a new one is created on the server via `client.threads.create({ metadata: { localChatId: chatId } })`.
  - The **server-assigned `thread_id`** (`lgThreadId`) is then used for the streaming call, not the local UUID.
  - This ensures LangGraph threads are properly created and reused across multiple messages in the same chat session.

---

## [2026-04-11] LangGraph Agent Integration & Streaming Support

### Overview

Successfully integrated the Chatbot with the LangGraph Agent (`langChain-application`), enabling professional-grade streaming responses and seamless inter-container communication via Docker Networking.

### Changes Logged

#### 1. Core Integration

- **LangGraph SDK Implementation**: Integrated `@langchain/langgraph-sdk` to handle communication with the Agent. Created `src/lib/langgraph.ts` as a centralized helper for SDK client instantiation.
- **Streaming Response Engine**: Overhauled the `sendMessage` logic in `use-chat-store.ts`. Replaced the legacy REST-based submission with a streaming listener that updates the message state in real-time as chunks arrive from the Agent.

#### 2. Networking & State

- **Inter-Container Communication**: Configured the frontend to reach the Agent service via a shared Docker bridge network (`mcp-network`). Updated environment variables to use `NEXT_PUBLIC_LANGGRAPH_API_URL`.
- **Thread Linkage**: Synchronized session persistence by using the application's native `currentChatId` as the LangGraph `thread_id`, ensuring the Agent maintains context across page reloads.

---

## [2026-04-11] Docker Optimization & Environment Fixes

### Overview

Enhanced the Docker deployment pipeline by fixing environment-specific script issues and optimizing the build process for better security, log readability, and image efficiency.

### Changes Logged

#### 1. Environment Stability

- **Line Ending Correction**: Restored `entrypoint.sh` consistency by converting CRLF (Windows) line endings to LF (Linux). This fixed a critical boot error where the shell tried to execute carriage return characters, preventing the frontend container from starting.

#### 2. Docker Build Optimization

- **Layer Consolidation**: Refactored `Dockerfile.frontend` to combine multiple `RUN` instructions. By reordering `COPY` operations and grouping `npm` installation, configuration, and cleanup tasks, the final image contains fewer layers and is more efficient.
- **Improved Build UX**:
  - Updated `npm` to latest version within the container to silence version update notices.
  - Disabled `funding` and `audit` informational logs in `npm ci` to produce cleaner, more focused build output.
- **Dependency Security**: Resolved a high-severity vulnerability in the `next` package by finalizing an `npm audit fix` and synchronizing the `package-lock.json` with the host environment.

---

## [2026-04-10] Advanced Intelligence & Logic Implementation

### Overview

Finalized the core logic for chat persistence, Model Context Protocol (MCP) integration, and professional-grade UI refinements, transforming the application into a production-ready AI interface.

### Changes Logged

#### 1. Smart Session & History Management

- **Persistent Memory Vault**: Implemented a comprehensive history system using Zustand middleware.
  - **Auto-Archive**: Sessions are now automatically saved to local storage upon leaving the chat page or after every message.
  - **Intelligent Updating**: Returning to an existing chat session now updates the same entry and moves it to the top of the history instead of creating duplicates.
  - **Session Timeout**: Implemented a 1-hour activity window. If a user returns after an hour, the chat is archived and cleared to start fresh, while retaining provider/model settings.
- **Memory Vault UI**: Enhanced the `/history` view with:
  - **Aura Backgrounds**: Blurred radial gradients (primary, secondary, tertiary) behind each history item for a premium depth effect.
  - **Interactive States**: Smooth hover transitions and quick-action delete buttons.

#### 2. MCP Ecosystem Enhancements

- **Metadata Discovery**: Added a new FastAPI endpoint `/mcp/metadata` that performs a "handshake" with MCP servers to retrieve their actual names.
- **Verified Tooling UI**: Updated the Right Utility Panel to show verified server names (e.g., "Postgres-MCP") instead of generic URLs, including a visual loading state during verification.
- **Improved Management**: Enhanced the MCP addition flow with input validation, duplicate checks, and toast notifications.

#### 3. Professional Chat UX Redesign

- **Neural Textbox Layout**: Moved away from traditional mobile-style chat bubbles to a centered, professional "Content Area" for AI responses, maximizing readability for long outputs and code.
- **Multimodal Input Support**:
  - Swapped the standard input for an **auto-expanding textarea**.
  - Added support for **Shift+Enter** for new lines while keeping **Enter** for sending.
  - **Auto-Focus**: Converted logic to ensure the cursor automatically returns to the input field after the AI finishes its response.
- **Vietnamese IME Optimization**: Fixed a critical bug where typing in Vietnamese (Telex/VNI) caused double message submissions by implementing `isComposing` state checks.

#### 4. Developer Productivity

- **Console Debug Tools**: Exposed `chatHistory()` and `purge()` functions to the global `window` object, allowing developers to inspect data or reset the environment directly from the browser console.

---

## [2026-04-09] UI/UX Refactor & Next.js Migration

### Overview

Successfully migrated the application from monolithic HTML prototypes to a modular Next.js architecture featuring the "Ethereal Intelligence" design system.

### Changes Logged

#### 1. Design System & Theming

- **Color Alignment**: Standardized all background and surface colors to a neutral dark hex (`#060f15`) for visual consistency.
- **Accessibility Fix**: Darkened all "on" color tokens to ensure high contrast for text.
- **Tailwind Configuration**: Overhauled `tailwind.config.ts` with custom design tokens (M3 system).

#### 2. Architecture & Layout

- **Persistent Shell**: Integrated globally persistent Sidebar and Header.
- **Componentization**: Created modular components for Sidebar, Header, Right Panel, and Chat Input.

#### 3. New Routes & Page Implementation

- **`/` (Home)**: Welcome Page with Hero section and feature bento-grid.
- **`/chat`**: Main Chat Interface.
- **`/history`**: Archives view.

#### 4. Cleanup

- **Legacy Files Removal**: Deleted old diagnostic HTML files.

---

## [2026-04-09] MetaClaw Integration (Phase 1)

### Overview

Successfully integrated the **MetaClaw Learning Proxy** (Phase 1) to enable persistent memory and skill injection. This architecture places MetaClaw as a transparent proxy between the frontend and the LLM providers.

### Changes Logged

#### 1. Backend LLM Adapter

- **Provider Support**: Added `metaclaw` provider to the backend's `get_or_create_agent` factory.
- **Protocol**: Switched to `ChatOpenAI` adapter for MetaClaw communication to maintain OpenAI compatibility.
- **Dependencies**: Added `langchain-openai` to `backend/requirements.txt`.
- **Environment**: Updated `.env.example` with `METACLAW_API_KEY` and `METACLAW_BASE_URL`.

#### 2. Frontend Configuration

- **Model Config**: Updated `src/lib/config.ts` to include MetaClaw as a valid provider with an expanded model list (Gemini, Llama, Claude).
- **Settings UI**: Updated `src/components/chat/chat-settings.tsx` to include provider selection and custom API key reminders for the proxy.
- **Type Safety**: Updated `src/lib/types.ts` to include `'metaclaw'` in the `ChatSettings` provider union type.

#### 3. Documentation & Organization

- **Architecture**: Created `docs/METACLAW_PROPOSAL.md` (Design) and `docs/METACLAW_INTEGRATION.md` (Roadmap).
- **Relocation**: Moved all standalone `.md` files (DOCKER, METACLAW, history, etc.) into the `docs/` folder for better repository structure.
- **Verification**: Created `scratch/test_metaclaw.py` for automated proxy connection testing.

_End of log for 2026-04-11._
