# chatbot_mcp_client repository change plan

Repository: `chatbot_mcp_client`
Primary role: Browser-facing Next.js chat UI plus FastAPI backend that streams LLM responses, connects to MCP servers, and delegates MCP server generation requests to the LangGraph agent service.

## Goal

Make the client and FastAPI bridge unambiguous about which services it talks to, which URLs are browser-facing versus container-facing, and how MetaClaw, LangGraph, and mcp-gen are represented to users and developers.

## Parallelization boundary

This plan can be assigned to an agent focused only on the `chatbot_mcp_client` repository. Coordinate with other repository agents only on shared service map, API contract, and environment variable names.

## Priority 0 changes

### 1. Separate browser URLs from backend/container URLs

Current confusion:

- The frontend uses `NEXT_PUBLIC_BACKEND_URL` and `NEXT_PUBLIC_BACKEND_PORT` to call FastAPI.
- The backend also reads `NEXT_PUBLIC_BACKEND_PORT`, even though `NEXT_PUBLIC_` implies browser-safe frontend config.
- The backend reads `NEXT_PUBLIC_LANGGRAPH_API_URL` before `LANGGRAPH_API_URL`, even though LangGraph is a backend-to-backend service.
- The frontend directly calls mcp-gen through `NEXT_PUBLIC_MCP_GEN_URL`.

Recommended change:

Define clear environment variable groups:

Browser/public variables:

- `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000`
- `NEXT_PUBLIC_MCP_GEN_URL=http://localhost:8080`

Backend-only variables:

- `BACKEND_PORT=8000`
- `LANGGRAPH_API_URL=http://agent-service:2024` in Docker
- `LANGGRAPH_API_URL=http://localhost:2024` in host-local development
- `MONGODB_URL=mongodb://mongodb:27017` in Docker

Backward compatibility:

- Keep reading `NEXT_PUBLIC_BACKEND_PORT` temporarily, but prefer `BACKEND_PORT` in backend config.
- Keep reading `NEXT_PUBLIC_LANGGRAPH_API_URL` temporarily only as fallback, but prefer `LANGGRAPH_API_URL`.

Files likely affected:

- `backend/config.py`
- `.env.example`
- `docker-compose.yml`
- `src/lib/config.ts`
- `src/lib/mcp-server-api.ts`

### 2. Correct Docker service names and URLs in `.env.example` and Compose

Current confusion:

- `.env.example` says Docker `NEXT_PUBLIC_MCP_GEN_URL` can use `http://mcp-gen:8080`, but the actual inspected mcp-gen service is `docker-manager`.
- Browser-side URLs cannot use Docker-internal service names unless the browser runs inside the Docker network, which it does not.

Recommended change:

Use explicit examples:

- Browser from host to mcp-gen manager: `NEXT_PUBLIC_MCP_GEN_URL=http://localhost:8080`
- FastAPI container to LangGraph: `LANGGRAPH_API_URL=http://agent-service:2024`
- FastAPI container to MongoDB: `MONGODB_URL=mongodb://mongodb:27017`

If the frontend container builds a browser bundle, avoid embedding container-only URLs in `NEXT_PUBLIC_*` variables.

### 3. Align documented ports and startup commands

Current confusion:

- `README.md` says frontend at `http://localhost:9002`, which matches Compose and package script.
- Cross-project `manage.sh` in the LangGraph repo reports frontend at `http://localhost:3000`, which conflicts with this repo.

Recommended change in this repo:

- Keep `9002` as canonical unless the entire ecosystem changes.
- Add a short “When started by cross-project manage script” section that still points to `http://localhost:9002`.
- Ensure README local and Docker commands are Windows-friendly where possible, because the workspace is on Windows.

## Priority 1 changes

### 4. Clarify MetaClaw semantics in UI and backend

Current confusion:

- Frontend settings expose Gemini/Groq provider choices.
- Backend forces provider to `metaclaw` whenever `METACLAW_ENABLED=true`.
- Frontend model list does not include MetaClaw, but user selections can be ignored.

Recommended product decision:

Choose one model and document it:

Option A: MetaClaw as proxy mode

- UI has a visible “MetaClaw proxy enabled” indicator.
- Provider dropdown remains Gemini/Groq only for fallback or direct mode.
- Backend `/health` returns `metaclawEnabled`, `effectiveProvider`, and `configuredFallbacks`.

Option B: MetaClaw as provider

- UI adds MetaClaw as a provider option.
- Backend honors user provider unless policy forces MetaClaw.
- Model list includes configured `METACLAW_MODEL`.

Recommended implementation path:

- Prefer Option A if MetaClaw is intended as the “Brain” layer.
- Update `src/lib/config.ts`, chat settings UI, and `backend/main.py` health response accordingly.

### 5. Decide whether frontend should call mcp-gen directly or through FastAPI

Current behavior:

- `src/lib/mcp-server-api.ts` directly calls mcp-gen for server list and feedback.
- This requires mcp-gen CORS to allow the frontend origin.

Recommended options:

Option A: Keep direct frontend-to-mcp-gen calls

- Document `CORS_ORIGINS=http://localhost:9002` in mcp-gen.
- Keep `NEXT_PUBLIC_MCP_GEN_URL` browser-reachable only.

Option B: Proxy mcp-gen calls through FastAPI

- Add FastAPI routes for server list and feedback.
- Frontend calls only FastAPI.
- Reduces CORS and service exposure complexity.

Recommended implementation path:

- Prefer Option B for simpler browser security and fewer public endpoints, unless direct access is required for architecture reasons.

### 6. Make chat streaming contract explicit

Current behavior:

- Frontend expects SSE `data: {"content":"..."}` chunks and `[DONE]`.
- Backend emits control events for MetaClaw fallback routing and may emit `error` fields.

Recommended change:

Document an SSE contract:

```json
{"type":"content","content":"text"}
{"type":"error","error":"message"}
{"type":"status","message":"text"}
{"type":"done"}
```

Then adapt frontend parsing to support typed events while remaining backward compatible with current `{ "content": "..." }` chunks.

Files likely affected:

- `backend/main.py`
- `backend/metaclaw_client.py`
- `backend/shared.py`
- `src/lib/hooks/use-chat-store.ts`

### 7. Improve MCP metadata UX and error handling

Current behavior:

- `POST /mcp/metadata` returns status `error` with a fallback name if connection fails.
- This is useful, but UI should distinguish unreachable, timeout, and invalid MCP server.

Recommended change:

- Return structured error codes:
  - `timeout`
  - `connect_error`
  - `initialization_error`
  - `unsupported_transport`
- Display actionable user messages in the UI.

## Priority 2 changes

### 8. Reduce duplicated or misleading naming

Current naming examples:

- Product name: “Ethereal Intelligence”.
- Container names: `gemini-backend`, `gemini-frontend`.
- README mentions “Brain + Arms”.

Recommended change:

- Keep product branding in README, but rename container comments/docs to neutral component names:
  - `chatbot-backend`
  - `chatbot-frontend`
- If renaming containers is disruptive, add an alias table in docs.

### 9. Add integration smoke checks

Recommended tests or scripts:

- Backend `/health` returns healthy when at least one provider is configured.
- Backend can reach `LANGGRAPH_API_URL` when generation is enabled.
- Frontend config points to a reachable backend URL.
- MCP server list API is reachable either directly or through FastAPI proxy.
- CORS works for `http://localhost:9002`.

## Coordination points with other repository agents

Coordinate before finalizing changes to:

- Whether `NEXT_PUBLIC_MCP_GEN_URL` remains direct or is removed in favor of FastAPI proxy.
- Canonical frontend port: likely `9002`.
- Canonical FastAPI backend port: likely `8000`.
- Canonical LangGraph URL from backend container: `http://agent-service:2024`.
- Canonical mcp-gen manager browser URL: `http://localhost:8080`.
- MetaClaw key and provider semantics.
- Shared SSE event schema if LangGraph/MetaClaw event behavior is changed.

## Suggested acceptance criteria

- A developer can tell from `.env.example` whether a variable is browser-facing or backend-only.
- UI provider choices match actual backend routing behavior.
- Frontend and FastAPI startup docs match real ports.
- Browser-facing calls do not require Docker-internal service names.
- MCP server list and feedback work without hidden CORS assumptions.
- The chat streaming format is documented and robust to content, status, done, and error events.
