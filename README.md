# 🚀 Ethereal Intelligence: Unified MCP Ecosystem

![Ethereal Intelligence Preview](./img/demo.gif)

## 🧠 Architecture: Brain + Arms

This repository owns the browser-facing chat client and the FastAPI bridge. External ecosystem services stay behind explicit URL boundaries so the browser never depends on Docker-only hostnames.

| Component               | Role                                                                 | Browser-facing URL                              | Backend/container URL                                                                    |
| ----------------------- | -------------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Next.js frontend        | Chat UI, settings panel, generated-server feedback UI, local history | `http://localhost:9002`                         | n/a                                                                                      |
| FastAPI backend         | Chat SSE, provider routing, MCP checks, mcp-gen proxy                | `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` | `BACKEND_PORT=8000`                                                                      |
| MetaClaw gateway        | Optional intent router and memory/context layer                      | n/a                                             | `METACLAW_BASE_URL`, commonly `http://host.docker.internal:30000/v1` in Docker           |
| LangGraph agent service | MCP server generation/build orchestration                            | n/a                                             | `LANGGRAPH_API_URL=http://agent-service:2024` in Docker, `http://localhost:2024` locally |
| mcp-gen manager         | Generated MCP server list and feedback API                           | proxied through FastAPI by default              | `MCP_GEN_URL=http://docker-manager:8080` in Docker, `http://localhost:8080` locally      |
| MongoDB                 | Backend feedback/log storage dependency for the wider MCP ecosystem  | n/a                                             | `MONGODB_URL=mongodb://mongodb:27017` in Docker                                          |

Runtime request paths:

- **Chat**: Browser `POST /chat` -> FastAPI -> MetaClaw when `METACLAW_ENABLED=true`, otherwise Gemini/Groq directly.
- **MetaClaw build handoff**: MetaClaw detects MCP-build intent -> Gemini executor confirms/normalizes the tool call -> FastAPI streams LangGraph build progress back over SSE.
- **Connected MCP tools**: Browser submits active MCP URLs -> FastAPI verifies them with `POST /mcp/metadata` and attaches streamable HTTP MCP tools to the standard LangChain agent.
- **Generated MCP servers**: Browser calls FastAPI `GET /mcp/servers` and `POST /mcp/{server_id}/feedback`; FastAPI proxies those calls to mcp-gen to avoid browser CORS and Docker service-name leakage.
- **Chat history**: The current frontend stores chat history/settings locally with Zustand `persist` and `localStorage`; it is not persisted through MongoDB by this app.

Core runtime roles:

- **Brain (MetaClaw Proxy)**: Optional reasoning, memory/context, and intent-routing layer. When `METACLAW_ENABLED=true`, FastAPI routes chat requests through MetaClaw regardless of the selected frontend provider.
- **Execution providers (Gemini/Groq)**: Used directly when MetaClaw is disabled, and used as fallback/execution providers when MetaClaw delegates.
- **Orchestrator (FastAPI Backend)**: Owns SSE streaming, provider selection, MCP session setup, generated-server proxy routes, and LangGraph build streaming.

## ✨ Key Features

- Real-time SSE chat streaming.
- Autonomous MCP server build handoff through LangGraph.
- MCP server connection metadata checks with structured error codes.
- Generated MCP server feedback list proxied through FastAPI, avoiding browser CORS and Docker service-name assumptions.
- Local persistent chat history/settings via Zustand and `localStorage`.
- Responsive Next.js UI with chat, archive, MCP tool settings, and generated-server feedback views.

## 🛠️ Technical Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, Shadcn UI.
- **Backend**: FastAPI, LangChain, LangGraph SDK, MCP client libraries.
- **Services**: MetaClaw gateway, LangGraph agent service, mcp-gen manager, MongoDB.

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose.
- Node.js 20+ for local frontend development.
- Python 3.12+ for local backend development.
- At least one configured provider: `GEMINI_API_KEY`, `GROQ_API_KEY`, or `METACLAW_ENABLED=true` with `METACLAW_API_KEY`.

### Configuration

Copy the example file and edit values:

```powershell
copy .env.example .env
```

Important variable groups:

```env
# Browser/public: embedded in the Next.js browser bundle
NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"

# Backend-only/container runtime
BACKEND_PORT=8000
LANGGRAPH_API_URL="http://localhost:2024"
MCP_GEN_URL="http://localhost:8080"
MONGODB_URL="mongodb://mongodb:27017"
```

Do not use Docker-internal service names such as `agent-service`, `docker-manager`, or `mongodb` in browser-facing `NEXT_PUBLIC_*` variables. The user's browser runs on the host, not inside the Docker network.

## 🐳 Docker Startup

```powershell
docker compose up --build -d
```

Canonical ports for this repository:

- Frontend: `http://localhost:9002`
- Backend: `http://localhost:8000`

When this repository is started by a cross-project manage script, this frontend remains canonical at `http://localhost:9002` unless the whole ecosystem changes ports together.

## 🛠️ Local Development

Backend on Windows PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:9002`.

## 📡 Chat SSE Contract

The backend emits Server-Sent Events with JSON `data:` payloads. The frontend remains backward compatible with older `{ "content": "..." }` chunks and the `[DONE]` sentinel.

Preferred typed events:

```json
{"type":"content","content":"text"}
{"type":"status","message":"text"}
{"type":"error","error":"message"}
{"type":"done"}
```

Legacy events still accepted by the frontend:

```json
{"content":"text"}
{"error":"message"}
```

```text
data: [DONE]
```

## 🔌 MCP Metadata Errors

`POST /mcp/metadata` returns structured error information when a server cannot be reached:

- `timeout`: connection or initialization timed out.
- `connect_error`: backend could not connect to the URL.
- `initialization_error`: transport connected but MCP initialization failed.
- `unsupported_transport`: invalid URL or unsupported transport.

## 📄 License

MIT License.
