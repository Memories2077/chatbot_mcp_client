# Project History

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

_End of log for 2026-04-11._
