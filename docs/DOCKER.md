# Docker Deployment Guide

This guide explains how to run the Ethereal Intelligence chatbot client and FastAPI bridge with Docker Compose.

## 🚀 Quick Start with Docker Compose

### Prerequisites

- Docker and Docker Compose installed.
- A provider key such as `GEMINI_API_KEY`, `GROQ_API_KEY`, or MetaClaw credentials.
- The external `mcp-network` must exist when integrating with the mcp-gen stack.

### Step 1: Prepare Environment File

Create a `.env` file in the project root by copying the example:

```powershell
copy .env.example .env
```

Set at least these values:

```env
GEMINI_API_KEY="your_gemini_api_key_here"
BACKEND_PORT=8000
NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"
```

`NEXT_PUBLIC_BACKEND_URL` is browser-facing and must be reachable from the user's browser. Do not set it to Docker-internal service names.

### Step 2: Build and Run Services

```powershell
docker compose up --build -d
```

This command builds the FastAPI backend and Next.js frontend, starts both containers, and waits for the backend health check before starting the frontend.

### Step 3: Access the Application

- Frontend application: `http://localhost:9002`
- Backend API: `http://localhost:8000`
- Backend health check: `http://localhost:8000/health`

## ⚙️ Environment Variable Flow

```text
.env file
  BACKEND_PORT=8000
  NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
  GEMINI_API_KEY=...
        │
        ▼
docker-compose.yml
  backend runtime:
    BACKEND_PORT=8000
    LANGGRAPH_API_URL=http://agent-service:2024
    MCP_GEN_URL=http://docker-manager:8080
    MONGODB_URL=mongodb://mongodb:27017
  frontend build/runtime:
    NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
        │
        ▼
Browser and containers
  browser calls FastAPI at http://localhost:8000
  FastAPI calls Docker services by service name on mcp-network
```

Key rule: `NEXT_PUBLIC_*` variables are embedded into browser JavaScript. Backend-only service URLs use non-public variables such as `LANGGRAPH_API_URL`, `MCP_GEN_URL`, and `MONGODB_URL`.

## 🛠️ Useful Docker Commands

- View service status:

```powershell
docker compose ps
```

- View logs:

```powershell
docker compose logs -f
docker compose logs -f backend
```

- Stop services:

```powershell
docker compose down
```

- Rebuild images:

```powershell
docker compose up -d --build --no-cache
docker compose build frontend
```

- Access a container shell:

```powershell
docker compose exec backend bash
docker compose exec frontend sh
```

## Troubleshooting

### Port Conflict

If backend port `8000` is already in use, change `BACKEND_PORT` and `NEXT_PUBLIC_BACKEND_URL` together, for example:

```env
BACKEND_PORT=8001
NEXT_PUBLIC_BACKEND_URL="http://localhost:8001"
```

Then restart with:

```powershell
docker compose up -d --build
```

### Frontend Shows Connection Error

1. Check backend logs with `docker compose logs backend`.
2. Visit `http://localhost:8000/health` and verify it returns `status`, `metaclawEnabled`, `effectiveProvider`, and `configuredFallbacks`.
3. Rebuild frontend if `NEXT_PUBLIC_BACKEND_URL` changed because it is embedded in the browser bundle.

### Generated MCP Servers Do Not Load

The frontend calls FastAPI, and FastAPI proxies to mcp-gen through `MCP_GEN_URL=http://docker-manager:8080` in Docker. Ensure the mcp-gen stack is running and both stacks share the external `mcp-network`.
