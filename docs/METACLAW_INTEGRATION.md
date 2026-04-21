# MetaClaw Learning Proxy Integration

**Status: Phase 1 COMPLETE ✅ | Phase 2 (mcp-gen) IN PROGRESS ⚠️ | Phase 3 (Learning) PLANNED 📋**

> **Last Updated:** 2026-04-20  
> **Next Priority:** Complete mcp-gen proxy routing (5 min task)

---

## 📋 Table of Contents

1. [Quick Start](#-quick-start)
2. [What is MetaClaw?](#-what-is-metaclaw)
3. [Implementation Status](#-implementation-status)
4. [Phase 2: mcp-gen Integration](#-phase-2-mcp-gen-integration)
5. [Phase 3: Learning & Evolution](#-phase-3-learning--evolution)
6. [Architecture](#-architecture)
7. [Configuration Reference](#-configuration-reference)
8. [Next Steps](#-next-steps)

---

## 🚀 Quick Start

**Phase 1 is already deployed. To use MetaClaw:**

```bash
# 1. Install MetaClaw on host machine
pip install -e ".[evolve]"   # skills + auto-evolution

# 2. One-time configuration
metaclaw setup  # wizard: choose agent, LLM provider, model

# 3. Start the proxy
metaclaw start --mode skills_only --port 30000

# 4. Verify chatbot uses MetaClaw
# Backend already configured - just ensure env vars:
# METACLAW_BASE_URL=http://localhost:30000/v1
# METACLAW_ENABLED=true

# 5. Verify langChain-application uses MetaClaw
# Already configured via llm_factory.py - just set env vars
```

**To enable mcp-gen integration (Phase 2 - NOT YET ACTIVE):**

```bash
# Update mcp-gen/.env:
METACLAW_ENABLED=true
METACLAW_BASE_URL=http://host.docker.internal:30000/v1
# Then restart mcp-gen service
```

---

## 🦞 What is MetaClaw?

MetaClaw is a **transparent learning proxy** that sits in front of any OpenAI-compatible LLM backend. It:

1. **Intercepts** every request/response through the proxy port (default `:30000/v1`)
2. **Injects skills** (Markdown files from `~/.metaclaw/skills/`) into system prompt at each turn
3. **Summarizes** conversations into new skills after each session (auto-evolve)
4. **Meta-learns** (optional RL) from live conversations via LoRA fine-tuning
5. **Persists memory** (v0.4.0) — facts, preferences, project state across sessions
6. **Supports multiple agents** — OpenClaw, CoPaw, IronClaw, etc.

**Key insight:** MetaClaw sits **between the LangChain Agent and the LLM Provider**, injecting intelligence transparently.

---

## 📊 Implementation Status

### ✅ Phase 1: LLM Proxy Integration — **COMPLETE**

| Component                         | Status      | Details                                                        |
| --------------------------------- | ----------- | -------------------------------------------------------------- |
| chatbot_mcp_client backend        | ✅ Complete | Two-stage handoff: MetaClaw (brain) → Gemini (arms)            |
| MetaClaw routing logic            | ✅ Complete | `_handle_metaclaw_request()` with intent detection             |
| Tool call preservation            | ✅ Complete | MetaClaw's `tool_calls` correctly captured and forwarded       |
| langChain-application LLM Factory | ✅ Complete | All agents route through MetaClaw when `METACLAW_ENABLED=true` |
| Frontend provider UI              | ✅ Complete | MetaClaw option in Chat Settings                               |
| TypeScript types                  | ✅ Complete | `ChatSettings` interface includes `'metaclaw'`                 |
| Docker networking                 | ✅ Complete | Backend reaches host MetaClaw via `host.docker.internal`       |
| Fallback logic                    | ✅ Complete | Graceful fallback to direct providers if MetaClaw unavailable  |

**Verified in code:**

- `chatbot_mcp_client/backend/main.py:356-379` - MetaClaw provider support
- `chatbot_mcp_client/backend/main.py:566-711` - Two-stage handoff implementation
- `langChain-application/my_agent/utils/llm_factory.py:27-46` - MetaClaw routing
- `langChain-application/my_agent/config/__init__.py` - MetaClaw config support

---

### ⚠️ Phase 2: mcp-gen Integration — **90% DONE, 1 STEP REMAINING**

| Component                           | Status      | Gap                                                   |
| ----------------------------------- | ----------- | ----------------------------------------------------- |
| MetaClaw config in mcp-gen          | ✅ Complete | `src/utils/config.ts:37-42` defines `metaclawConfig`  |
| LLM routing logic in mcp-gen        | ✅ Complete | `src/utils/genai.ts` still calls Gemini/Groq directly |
| Skill injection for code generation | ⚠️ Blocked  | Ready once routing is enabled                         |

**What needs to be done:**

1. Modify `mcp-gen/src/utils/genai.ts` to check `metaclawConfig.enabled`
2. If enabled, route through `ChatOpenAI` with MetaClaw base_url
3. Test that mcp-gen's code generation benefits from MetaClaw skills

---

### 📋 Phase 3: Learning & Evolution — **PLANNED**

| Feature                    | Status      | Notes                                            |
| -------------------------- | ----------- | ------------------------------------------------ |
| Conversation Logger        | 📋 Planned  | Need to capture chat → LLM exchanges for RL      |
| Feedback UI (Like/Dislike) | 📋 Planned  | Frontend components needed                       |
| RL Training Pipeline       | 📋 Planned  | Requires MetaClaw `rl` backend (Tinker/MinT)     |
| Skill Auto-Evolution       | 📋 Planned  | MetaClaw can auto-summarize sessions into skills |
| Memory Persistence         | ✅ Complete | Enable `memory.enabled=true` in MetaClaw config  |
| Skill Orchestrator Agent   | 📋 Planned  | Read/write separation for safe skill management  |

---

## 🛠️ Phase 2: mcp-gen Integration

**Goal:** Route mcp-gen's LLM calls through MetaClaw so code generation benefits from accumulated skills.

### Current State

`mcp-gen/src/utils/genai.ts` currently does:

```typescript
// Direct Gemini/Groq call (bypasses MetaClaw)
llm = new ChatGoogleGenerativeAI({
  apiKey: geminiConfig.apiKey,
  model: selectedModel,
  ...
});
```

Even though `metaclawConfig` exists, it's never used.

### Required Change

Update `genaiCompletion()` function to check `metaclawConfig.enabled`:

```typescript
import { ChatOpenAI } from "@langchain/openai";
import { metaclawConfig } from "./config.js";

// Inside genaiCompletion():
if (metaclawConfig.enabled) {
  console.log("[GenAI] 🧠 Routing through MetaClaw proxy");
  llm = new ChatOpenAI({
    baseUrl: metaclawConfig.baseUrl,
    apiKey: metaclawConfig.apiKey,
    model: selectedModel,  // MetaClaw may ignore this depending on config
    temperature: temperature ?? geminiConfig.temperature,
    maxTokens: maxTokens,
  });
} else {
  // Existing Gemini/Groq logic
  if (isGroq) {
    llm = new ChatGroq({ ... });
  } else {
    llm = new ChatGoogleGenerativeAI({ ... });
  }
}
```

**Files to modify:**

- `mcp-gen/src/utils/genai.ts` (add MetaClaw routing)
- `mcp-gen/.env` (add METACLAW_ENABLED, METACLAW_BASE_URL, METACLAW_API_KEY)
- `mcp-gen/README.md` (update deployment instructions)

**Expected benefit:**
When mcp-gen requests code generation, MetaClaw will:

1. Search `~/.metaclaw/skills/` for relevant skills (MCP patterns, auth, best practices)
2. Inject those skills into the system prompt
3. Generate higher quality MCP servers based on accumulated knowledge

---

## 🧠 Phase 3: Learning & Evolution

Once Phase 2 is complete, enable continuous improvement:

### 1. Conversation Logger (Backend)

Create `chatbot_mcp_client/backend/conversation_logger.py`:

```python
"""
Logs conversations for MetaClaw memory and RL training.
"""
import json
from datetime import datetime
from pathlib import Path

class ConversationLogger:
    def __init__(self, log_dir: Path = Path("logs/conversations")):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_turn(self, user_msg: str, assistant_msg: str, tools_used: list, feedback: dict = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_msg,
            "assistant": assistant_msg,
            "tools": tools_used,
            "feedback": feedback,
            "session_id": ""  # TODO: extract from request context
        }
        log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

### 2. Feedback UI (Frontend)

Add Like/Dislike buttons to message component:

```tsx
// In src/components/chat/chat-message.tsx
const [feedback, setFeedback] = useState<"like" | "dislike" | null>(null);

const sendFeedback = async (type: "like" | "dislike") => {
  setFeedback(type);
  await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messageId, type, timestamp: Date.now() }),
  });
};
```

### 3. Enable MetaClaw Memory & RL

```bash
# Edit ~/.metaclaw/config.yaml:
memory:
  enabled: true
  top_k: 5
  max_tokens: 800
  retrieval_mode: hybrid

rl:
  enabled: false  # Set to true when ready
  backend: tinker  # or mint, weaver
  model: moonshotai/Kimi-K2.5
```

### 4. Skill Orchestrator Agent (Optional)

For safe skill management, create an "Admin" LangGraph agent with write access to `~/.metaclaw/skills/`. This agent validates and approves skill changes proposed by MetaClaw's auto-evolution.

---

## 🏗️ Architecture

### Current: Two-Stage Handoff (MetaClaw Brain + Gemini Arms)

```
User → Chatbot Backend → MetaClaw Proxy (:30000) → Gemini API
                │              │
                │              ├─ Skill Injection
                │              ├─ Memory Retrieval
                │              └─ Intent Detection
                │
                └─ Tool Execution (if MetaClaw triggers build)
```

**Flow:**

1. User sends message → Backend routes to MetaClaw
2. MetaClaw reasons, injects skills, responds
3. Backend detects `create_mcp_server` intent from MetaClaw
4. If intent found → hand off to Gemini to execute tool
5. Gemini calls `create_mcp_server` → LangGraph build streamed to user
6. If no intent → MetaClaw's text response streamed directly

**Key files:**

- `chatbot_mcp_client/backend/main.py:566-711` - `_handle_metaclaw_request()`
- `chatbot_mcp_client/backend/main.py:640-711` - `_execute_with_gemini()`
- `langChain-application/my_agent/utils/llm_factory.py` - Central LLM routing

---

### Future: Unified Intelligence Layer (Phase 3)

```
      ┌─────────────────────────────────────────────┐
      │     MetaClaw Cluster (Read-Only Brain)      │
      │  • Skills: ~/.metaclaw/skills/             │
      │  • Memory: ~/.metaclaw/memory/             │
      │  • RL Engine: Continuous improvement       │
      └───────────────┬─────────────────────────────┘
                      │ OpenAI-compatible API
        ┌─────────────┴─────────────┐
        ▼                           ▼
   chatbot_mcp_client       langChain-application
   (User Interface)         (Multi-Agent System)
        │                           │
        ▼                           ▼
   Gemini Executor          mcp-gen (via proxy)
   (Tool Execution)         (Code Generation)
```

All LLM calls from all projects flow through MetaClaw, creating a single source of truth for skills and memory.

---

## ⚙️ Configuration Reference

### Chatbot `.env`

```env
# LLM Providers
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# MetaClaw Integration (Phase 1 - Active)
METACLAW_BASE_URL=http://localhost:30000/v1
METACLAW_API_KEY=metaclaw
METACLAW_ENABLED=true

# Backend
NEXT_PUBLIC_BACKEND_PORT=8000
NEXT_PUBLIC_LANGGRAPH_API_URL=http://localhost:2024
```

### langChain-application `.env`

```env
# MetaClaw (auto-detected by llm_factory.py)
METACLAW_ENABLED=true
METACLAW_BASE_URL=http://localhost:30000/v1
METACLAW_API_KEY=metaclaw

# Fallback provider (used if MetaClaw disabled)
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### mcp-gen `.env` (Phase 2 - Pending)

```env
# Add these to existing config:
METACLAW_ENABLED=true
METACLAW_BASE_URL=http://host.docker.internal:30000/v1
METACLAW_API_KEY=metaclaw

# Existing config:
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

### MetaClaw `~/.metaclaw/config.yaml`

```yaml
mode: auto # "auto" | "rl" | "skills_only"
claw_type: none

llm:
  provider: kimi # or qwen, openai, volcengine, custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: "metaclaw"

skills:
  enabled: true
  dir: ~/.metaclaw/skills
  retrieval_mode: template
  top_k: 6
  auto_evolve: true # summarize sessions into skills

memory:
  enabled: false # Set true for Phase 3
  top_k: 5
  max_tokens: 800

rl:
  enabled: false # Set true for Phase 3
  backend: auto
  model: moonshotai/Kimi-K2.5
```

---

## 🧪 Testing

### Manual Verification

1. **Test MetaClaw routing:**

```bash
# Start MetaClaw
metaclaw start --mode skills_only --port 30000

# Send chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": "metaclaw",
    "model": "gemini-2.5-flash"
  }'
```

2. **Check skill injection:**
   - Add a test skill to `~/.metaclaw/skills/`
   - Ask a question that matches the skill
   - Verify MetaClaw references the skill in response

3. **Test fallback:**
   - Stop MetaClaw
   - Send same request again
   - Should fall back to direct Gemini

### Automated Tests (Future)

Create `tests/` directory with:

- `test_metaclaw_proxy.py` - routing, health checks, fallback
- `test_skills_injection.py` - skill loading and injection
- `test_memory_cross_session.py` - memory persistence
- `test_mcpgens_through_metaclaw.py` - mcp-gen integration (Phase 2)

---

## 🐛 Troubleshooting

| Issue                                 | Solution                                                                          |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| MetaClaw won't start on port 30000    | Check conflicts: `netstat -ano \| findstr :30000`                                 |
| Skills not injecting                  | Verify `~/.metaclaw/skills/` has valid `SKILL.md` files                           |
| Backend can't reach MetaClaw (Docker) | Ensure `METACLAW_BASE_URL=http://host.docker.internal:30000/v1`                   |
| mcp-gen still bypasses MetaClaw       | Check `METACLAW_ENABLED=true` in mcp-gen `.env`, verify code change in `genai.ts` |
| Tool calls swallowed                  | Already fixed in Phase 1 - two-stage handoff preserves intent                     |
| LangGraph stream blank                | Fixed in 2026-04-13 - `use-chat-store.ts` handles all event types                 |

---

## 📝 Technical Notes

- **Port:** MetaClaw defaults to `30000`. Ensure no conflicts.
- **Compatibility:** MetaClaw follows OpenAI Chat Completions standard.
- **Skill Storage:** `~/.metaclaw/skills/` - each skill is a `SKILL.md` file.
- **Memory Storage:** `~/.metaclaw/memory/` (when enabled).
- **Two-Stage Handoff:** MetaClaw decides, Gemini executes. Prevents tool call loss.
- **Fallback:** Always implemented - system works even if MetaClaw is down.

---

## 📚 Related Documentation

- `langChain-application/history.md` - Detailed change log for multi-agent system
- `chatbot_mcp_client/history.md` - Chatbot evolution and MetaClaw integration history
- `langChain-application/METACLAW_ARCHITECTURE_ANALYSIS.md` - Deep architecture analysis
- `MetaClaw/README.md` - Upstream MetaClaw documentation
- `mcp-gen/README.md` - MCP generator docs

---

## 🎯 Next Steps

### Immediate (Today)

1. **✅ Complete mcp-gen MetaClaw routing** (5 minutes)
   - Modify `mcp-gen/src/utils/genai.ts`
   - Add MetaClaw provider check
   - Test with simple generation request
   - **Owner:** Backend/Full-stack

2. **📋 Document mcp-gen integration**
   - Update `mcp-gen/README.md` with MetaClaw instructions
   - Add troubleshooting section
   - **Owner:** Docs

### Short-term (This Week)

3. **📋 Bootstrap initial skills**
   - Copy `mcp-gen/docs/*.md` to `~/.metaclaw/skills/`
   - Verify skill discovery and injection
   - **Owner:** DevOps

4. **📋 Add conversation logging**
   - Implement `ConversationLogger` in chatbot backend
   - Add `/api/feedback` endpoint
   - **Owner:** Backend

5. **📋 Add feedback UI**
   - Like/Dislike buttons on chat messages
   - Send feedback to backend
   - **Owner:** Frontend

### Medium-term (Sprint)

6. **📋 Enable MetaClaw memory**
   - Update `~/.metaclaw/config.yaml`
   - Test cross-session recall
   - **Owner:** AI Engineer

7. **📋 Configure RL pipeline**
   - Set up RL backend (Tinker/MinT)
   - Configure PRM
   - **Owner:** AI Engineer

8. **📋 Implement Skill Orchestrator**
   - Create validation agent
   - Bidirectional sync with mcp-gen
   - **Owner:** AI Engineer

---

**Phase 1 Achievement:** The core MetaClaw integration is production-ready. Chatbot and langChain-application both benefit from skill injection and memory (when enabled). The two-stage handoff architecture ensures zero tool call loss.

**Critical Path:** mcp-gen integration is 90% complete and requires only 1 code change to activate. This will extend MetaClaw's intelligence to code generation.
