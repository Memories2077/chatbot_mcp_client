# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Ethereal Intelligence** is a unified MCP (Model Context Protocol) ecosystem chatbot application featuring a "Brain + Arms" architecture:
- **Brain (MetaClaw)**: Intent classification and tool selection reasoning engine
- **Arms (Gemini/Groq)**: Execution layer for tool calls and responses
- **Orchestrator (FastAPI)**: Backend handling SSE streaming, session persistence, and MCP proxy

The frontend is a Next.js 15 app with a glassmorphism-inspired UI, supporting real-time streaming, persistent chat history, and dynamic MCP server connections.

## Common Development Commands

### Frontend (Next.js + TypeScript)
```bash
# Install dependencies
npm install

# Start development server (port 9002)
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint

# Type checking
npm run typecheck
```

### Backend (FastAPI + Python)
```bash
cd backend

# Create virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Create virtual environment (Unix/macOS)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server (port 8000)
python main.py

# Or with uvicorn
uvicorn main:app --reload --port 8000
```

### Docker (Full Stack)
```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down

# Rebuild a specific service
docker-compose build backend
```

## Architecture

### Frontend Structure
- `src/app/` - Next.js App Router (layout, page, chat routes)
- `src/components/` - Reusable UI components organized by domain
  - `chat/` - Chat-specific components (ChatLayout, ChatInput, ChatSettings, ChatMessage)
  - `layout/` - App layout (Sidebar, Header)
  - `ui/` - shadcn/ui primitive components
- `src/lib/` - Core utilities and configuration
  - `config.ts` - API endpoints and model configuration
  - `types.ts` - TypeScript type definitions
  - `utils.ts` - Helper functions
  - `hooks/` - Custom hooks including `use-chat-store.ts` (Zustand state management)
- State is persisted to localStorage with session timeout (1 hour) for auto-archiving

### Backend Structure
- `backend/main.py` - FastAPI application with two main endpoints:
  - `/health` - Health check endpoint
  - `/chat` - Streaming chat endpoint with SSE
  - `/mcp/metadata` - MCP server metadata retrieval
- **Agent Factory** (`get_or_create_agent`): Dynamically creates LangChain agents based on provider and MCP connections
- **Two-Stage Routing**: MetaClaw → Gemini executor pattern for autonomous MCP building
- **Tool Integration**: MCP tools loaded via `streamable_http_client` and `load_mcp_tools`
- **LangGraph Build Streaming**: Integrates with external LangGraph service for MCP server generation

### Data Flow
1. User sends message → Frontend Zustand store
2. SSE POST to `/chat` with messages, provider, model, temperature, and MCP server URLs
3. Backend connects to MCP servers (if provided) and loads their tools
4. LangChain agent processes with tool calling capability
5. Stream response back via SSE, frontend updates in real-time
6. Chat persisted to localStorage with auto-archiving after 1 hour of inactivity

## Configuration

### Environment Variables (.env)
Create a `.env` file in the project root. All configuration is centralized in `backend/config.py`:

```bash
# ============================================================================
# LLM Provider Configuration (At least ONE required)
# ============================================================================

# Google Gemini API (Primary recommendation)
# Get from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY="your_gemini_api_key"
GEMINI_MODEL="gemini-2.5-flash"

# Groq API (Alternative high-performance option)
# Get from: https://console.groq.com/keys
GROQ_API_KEY="your-groq-api-key"
GROQ_MODEL="llama-3.3-70b-versatile"

# MetaClaw Proxy Integration (Brain architecture)
# When enabled, ALL requests route through MetaClaw regardless of provider setting.
# Requires: METACLAW_BASE_URL (running MetaClaw instance) and METACLAW_API_KEY
METACLAW_ENABLED=false  # Set to "true" to enable MetaClaw routing
METACLAW_BASE_URL="http://host.docker.internal:30000/v1"
METACLAW_API_KEY="your-metaclaw-api-key"
# Optional: Override model name for MetaClaw
METACLAW_MODEL="gemini-2.5-flash"

# ============================================================================
# Backend Configuration
# ============================================================================

# Backend port (default: 8000)
NEXT_PUBLIC_BACKEND_PORT=8000

# Optional: Direct backend URL override (for remote deployments)
# NEXT_PUBLIC_BACKEND_URL="http://your-backend:8000"

# ============================================================================
# LangGraph Configuration (for MCP Server Generation)
# ============================================================================

# LangGraph API URL (where the agent service runs)
NEXT_PUBLIC_LANGGRAPH_API_URL="http://localhost:2024"
# or
LANGGRAPH_API_URL="http://localhost:2024"

# ============================================================================
# General LLM Settings
# ============================================================================

LLM_TEMPERATURE=0.0
LLM_TIMEOUT_MS=300000

# ============================================================================
# MCP Server Connection Settings
# ============================================================================

MCP_CONNECTION_TIMEOUT=10.0
MCP_INIT_TIMEOUT=10.0
```

### Provider-Specific Notes
- **gemini**: Requires `GEMINI_API_KEY` from Google AI Studio
- **groq**: Requires `GROQ_API_KEY` from Groq Cloud
- **metaclaw**: Requires MetaClaw instance running; uses OpenAI-compatible API format. When enabled, acts as intelligent proxy with two-stage routing (MetaClaw → Gemini executor).

## Docker Setup

Two Dockerfiles defined:
- `Dockerfile.backend` - Python FastAPI with uvicorn
- `Dockerfile.frontend` - Next.js production build

Services communicate via custom bridge networks (`gemini-network`, `mcp-network`). Frontend runs on port 9002, backend on configured port (default 8000).

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/main.py` | Core backend logic, agent factory, SSE streaming |
| `backend/config.py` | **Centralized configuration management** - single source of truth for all LLM providers |
| `backend/metaclaw_client.py` | **MetaClaw client wrapper** - encapsulates two-stage routing logic |
| `backend/tests/test_metaclaw_integration.py` | Integration tests for MetaClaw functionality |
| `src/lib/hooks/use-chat-store.ts` | Zustand state management, chat persistence |
| `src/lib/config.ts` | API configuration and model provider settings (frontend) |
| `src/components/chat/chat-layout.tsx` | Main chat UI container |
| `src/components/chat/chat-settings.tsx` | Provider/model/MCP server configuration |
| `docker-compose.yml` | Full-stack orchestration |
| `docs/README_DEV.md` | Detailed Vietnamese developer guide |

## Testing Notes

### Automated Tests
Run the integration test suite:
```bash
cd backend
pytest tests/test_metaclaw_integration.py -v
```

The test suite covers:
- Configuration loading and validation
- MetaClaw client initialization
- Tool intent detection from structured and text responses
- Two-stage handoff flow (MetaClaw → Gemini)
- Fallback behavior when MetaClaw disabled
- LangGraph build streaming

### Manual Testing Workflow
1. Start backend: `python backend/main.py` or `docker-compose up backend`
2. Start frontend: `npm run dev`
3. Open `http://localhost:9002`
4. Verify health: `curl http://localhost:8000/health`
5. Test chat flow with and without MCP servers

## Known Constraints

- Backend caches agent instances; configuration changes trigger re-initialization
- MCP server connections have 10-second timeout
- SSE streaming assumes proper event format (`data: {json}`)
- LangGraph build service must be reachable at `LANGGRAPH_API_URL` for MCP server generation

## Debugging Tips

- Frontend: Use `window.chatHistory()` and `window.purge()` console helpers (see `src/app/layout.tsx`)
- Backend: Check logs for "CONFIG CHANGE DETECTED" and MCP connection status
- MetaClaw flow: Look for `[MetaClaw]` and `[Gemini]` log prefixes
- State inspection: Zustand DevTools can be enabled if needed
