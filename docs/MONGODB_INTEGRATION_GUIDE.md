# Connecting chatbot_mcp_client to mcp-gen MongoDB

## Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     mcp-gen Stack                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────────┐           │
│  │ Manager │    │  Proxy  │    │   MongoDB   │           │
│  │ :8080   │    │  :8081  │    │  :27017     │           │
│  └─────────┘    └─────────┘    └─────────────┘           │
│         │              │              │                    │
│         └──────────────┴──────────────┘                    │
│                  mcp-network (bridge)                      │
└─────────────────────────────────────────────────────────────┘
                              │ external
                              │
┌─────────────────────────────────────────────────────────────┐
│              chatbot_mcp_client Stack                      │
│  ┌─────────┐    ┌─────────┐                               │
│  │Frontend │    │Backend  │                               │
│  │ :9002   │    │ :8000   │                               │
│  └─────────┘    └─────────┘                               │
│         │              │                                   │
│         └──────────────┴───────────────────────────────────┘
│                  gemini-network + mcp-network             │
└─────────────────────────────────────────────────────────────┘
```

## Setup Steps

### 1. Start mcp-gen Stack (provides MongoDB)
```bash
cd ../mcp-gen
docker-compose up -d mongodb
# Verify: docker ps | grep mongodb
```

### 2. Start chatbot_mcp_client Stack

#### Option A: Docker (recommended for full integration)
```bash
cd chatbot_mcp_client
docker-compose up -d backend
# Verify: docker-compose logs -f backend
```

The backend container will:
- Join `mcp-network` (external)
- Use `MONGODB_URL=mongodb:27017` (overridden in docker-compose)
- Resolve `mongodb:27017` to the mcp-gen MongoDB container
- Connect to the `docker` database

#### Option B: Local Development
```bash
# Ensure .env has:
MONGODB_URL="mongodb://localhost:27017"
MONGODB_DB="docker"

# Start backend locally
cd backend
source ../.venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn main:app --reload --port 8000
```

### 3. Verify Connection
```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","service":"backend"}
```

### 4. Test Feedback Endpoint
```bash
python test_feedback_backend.py
```

## MongoDB Collections Used

**chatbot_mcp_client** uses:
- `chat_logs` - Chat message logs with feedback fields:
  - `messageId` (unique indexed)
  - `serverId` (indexed, optional) - associates with MCP server
  - `content`, `role`, `timestamp`
  - `likeCount` (default 0)
  - `dislikeCount` (default 0)
  - `feedbacks` (array of FeedbackEntry objects, each may include `serverId`)

**mcp-gen** uses:
- `logs` - MCP server metadata and lifecycle logs

## Troubleshooting

### "mongodb:27017: getaddrinfo failed"
- **Docker mode**: Ensure `mcp-network` exists and MongoDB container is healthy
- **Local mode**: Check `.env` has `MONGODB_URL=mongodb://localhost:27017`
- Verify MongoDB is running: `docker ps | grep mongodb` or `mongosh`

### Connection refused
- Check MongoDB container health: `docker-compose ps mongodb`
- Ensure port 27017 is not blocked
- Verify backend has network access (in Docker: on mcp-network)

### Feedback not persisting
- Check backend logs for MongoDB connection errors
- Verify database name: default is "docker"
- Check MongoDB directly: `mongosh` → `use docker` → `db.chat_logs.find()` (note: collection is `chat_logs`, not `logs`)

## Shared Database Considerations

Both chatbot_mcp_client and mcp-gen share the same MongoDB instance but use **different collections** to avoid collisions:
- **chatbot_mcp_client** uses: `chat_logs`
- **mcp-gen** uses: `logs`, `servers`, `builds`, `users`, etc.

They can safely coexist in the same database (`docker`) without conflicts.
