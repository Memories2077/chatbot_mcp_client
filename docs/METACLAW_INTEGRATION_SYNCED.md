# MetaClaw Integration - Comprehensive Synchronized Plan

**Status: Phase 1 COMPLETE ✅ | Phase 2 (mcp-gen) 100% DONE ✅ | Phase 3 (Learning) PLANNED 📋**

> **Last Updated:** 2026-04-22  
> **Sync Source:** This document synthesizes `conductor/metaclaw_integration_plan.md` (phase structure + skill separation emphasis) and `chatbot_mcp_client/docs/METACLAW_INTEGRATION.md` (detailed implementation + status tracking)  
> **Next Priority:** Bootstrap MCP-focused MetaClaw skills and enable memory (Phase 3)

---

## 📋 Table of Contents

1. [Objective](#-objective)
2. [Architecture Overview](#-architecture-overview)
3. [Implementation Status](#-implementation-status)
4. [Phase 1: Deployment & Connectivity](#-phase-1-deployment--connectivity)
5. [Phase 2: Sub-System Integration](#-phase-2-sub-system-integration)
   - [2.1 chatbot_mcp_client](#21-chatbot_mcp_client)
   - [2.2 mcp-gen](#22-mcp-gen)
   - [2.3 langChain-application](#23-langchain-application)
6. [Phase 3: Skill Development & Learning](#-phase-3-skill-development--learning)
   - [3.1 Create MCP-Focused MetaClaw Skills](#31-create-mcp-focused-metaclaw-skills)
   - [3.2 Skill Separation Principle](#32-skill-separation-principle)
   - [3.3 Leverage MetaClaw Memory](#33-leverage-metaclaw-memory)
7. [Phase 4: Verification & Testing](#-phase-4-verification--testing)
8. [Configuration Reference](#-configuration-reference)
9. [Troubleshooting](#-troubleshooting)
10. [Next Steps](#-next-steps)

---

## 🎯 Objective

Fully integrate MetaClaw as the central AI proxy across all three core components (`chatbot_mcp_client`, `mcp-gen`, and `langChain-application`). This enables the entire ecosystem to benefit from MetaClaw's continuous meta-learning, skill injection, and cross-session memory.

**Success criteria:** All LLM requests from all three components route through MetaClaw, which acts as a transparent OpenAI-compatible proxy, injecting skills and building persistent memory.

---

## 🏗️ Architecture Overview

MetaClaw acts as a transparent OpenAI-compatible proxy for all LLM requests in the system.

- **Chatbot** requests flow through MetaClaw to build user/project memory.
- **MCP Generation** tasks (from `mcp-gen` and LangChain) flow through MetaClaw to utilize and evolve specialized coding skills.
- The underlying LLM (e.g., Gemini or Groq) is only called by MetaClaw, never directly by individual services.

### Two-Stage Handoff Pattern (MetaClaw Brain + Gemini Arms)

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
- `chatbot_mcp_client/backend/main.py:566-711` - `_handle_metaclaw_request()` and `_execute_with_gemini()`
- `langChain-application/my_agent/utils/llm_factory.py:27-46` - MetaClaw routing

---

## 📊 Implementation Status

### ✅ Phase 1: Deployment & Connectivity — **COMPLETE**

| Component                         | Status      | Details                                                        |
| --------------------------------- | ----------- | -------------------------------------------------------------- |
| MetaClaw installation             | ✅ Complete | Installed with `[evolve]` extras                               |
| MetaClaw initial configuration    | ✅ Complete | `metaclaw setup` wizard completed                              |
| MetaClaw proxy service            | ✅ Complete | Running on port 30000 with `skills_only` mode                  |
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

### ✅ Phase 2: mcp-gen Integration — **COMPLETE**

| Component                           | Status      | Details                                                   |
| ----------------------------------- | ----------- | --------------------------------------------------------- |
| MetaClaw config in mcp-gen          | ✅ Complete | `src/utils/config.ts:37-42` defines `metaclawConfig`     |
| LLM routing logic in mcp-gen        | ✅ Complete | `src/utils/genai.ts:79-92` routes through MetaClaw proxy |
| Environment configuration           | ✅ Complete | `.env` supports `METACLAW_ENABLED=true`                  |
| Documentation updated              | ✅ Complete | `README.md` includes MetaClaw setup instructions         |

**Completed tasks:**
1. ✅ Modified `mcp-gen/src/utils/genai.ts` to check `metaclawConfig.enabled`
2. ✅ If enabled, routes through `ChatOpenAI` with MetaClaw base_url
3. ✅ Maintains fallback to direct Gemini/Groq if disabled
4. ✅ Updated `.env.example` with MetaClaw configuration
5. ✅ Updated README with MetaClaw setup instructions
6. ✅ TypeScript compilation passes with no errors

**How it works:**
- When `METACLAW_ENABLED=true`, all LLM requests from mcp-gen route through MetaClaw proxy
- MetaClaw injects relevant skills (MCP patterns, authentication, best practices) into the system prompt
- Code generation quality improves as MetaClaw accumulates skills over time
- If MetaClaw is unavailable or disabled, automatic fallback to Gemini/Groq ensures continuity

**Files modified:**
- `mcp-gen/src/utils/genai.ts` (lines 79-92)
- `mcp-gen/README.md` (added MetaClaw section)
- `mcp-gen/.env.example` (already had MetaClaw config)
- `mcp-gen/.env` (set `METACLAW_ENABLED=true` in actual environment)

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

## 🚀 Phase 1: Deployment & Connectivity

Ensure MetaClaw is accessible to all Docker containers.

### 1.1 Install MetaClaw on Host Machine

```bash
pip install -e ".[evolve]"   # skills + auto-evolution
```

### 1.2 Initial Configuration

```bash
metaclaw setup  # wizard: choose agent, LLM provider, model
```

### 1.3 Start MetaClaw Proxy

```bash
metaclaw start --mode skills_only --port 30000
```

MetaClaw will listen on `http://localhost:30000/v1`.

### 1.4 Container Access Configuration

All Dockerized services must route to `http://host.docker.internal:30000/v1` (or equivalent host IP on Linux):

- **chatbot_mcp_client backend** → `METACLAW_BASE_URL=http://host.docker.internal:30000/v1`
- **mcp-gen** → `METACLAW_BASE_URL=http://host.docker.internal:30000/v1`
- **langChain-application** → `METACLAW_BASE_URL=http://localhost:30000/v1` (or host IP if containerized)

### 1.5 MetaClaw Configuration

Edit `~/.metaclaw/config.yaml`:

```yaml
mode: auto  # "auto" | "rl" | "skills_only"
claw_type: none

llm:
  provider: kimi  # or qwen, openai, volcengine, custom
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
  auto_evolve: true  # summarize sessions into skills

memory:
  enabled: false  # Set true for Phase 3
  top_k: 5
  max_tokens: 800

rl:
  enabled: false  # Set true for Phase 3
  backend: auto
  model: moonshotai/Kimi-K2.5
```

---

## 🔧 Phase 2: Sub-System Integration

Update each component to route LLM requests through MetaClaw.

### 2.1 chatbot_mcp_client

**Status:** ✅ Complete (Phase 1)

The backend already has full MetaClaw support with two-stage handoff.

**Actions completed:**

- Updated `.env.example` and `docker-compose.yml` with:
  ```env
  METACLAW_BASE_URL="http://host.docker.internal:30000/v1"
  METACLAW_API_KEY="metaclaw"
  METACLAW_ENABLED=true
  ```
- UI allows users to select "metaclaw" as the default LLM provider
- TypeScript `ChatSettings` interface includes `'metaclaw'`
- Two-stage handoff implementation preserves tool calls from MetaClaw

**Key implementation details:**

- `backend/main.py:356-379` - MetaClaw provider configuration
- `backend/main.py:566-711` - `_handle_metaclaw_request()` with intent detection and `_execute_with_gemini()` for tool execution
- `src/components/chat/chat-settings.tsx` - Provider selection UI

**Verification:**
1. Start MetaClaw on port 30000
2. Ensure `METACLAW_ENABLED=true` in chatbot `.env`
3. Select "MetaClaw" in Chat Settings
4. Send a message that triggers MCP server creation
5. Observe two-stage flow: MetaClaw response → Gemini tool execution

---

### 2.2 mcp-gen

**Status:** ⚠️ 90% Complete, routing not yet active

**Current state:**
`mcp-gen/src/utils/genai.ts` currently only supports direct calls to Gemini and Groq. The `metaclawConfig` exists (`src/utils/config.ts:37-42`) but is never used.

**Required change:**

Modify `mcp-gen/src/utils/genai.ts` - `genaiCompletion()` function:

```typescript
import { ChatOpenAI } from "@langchain/openai";
import { metaclawConfig } from "./config.js";

// Inside genaiCompletion():
if (metaclawConfig.enabled) {
  console.log("[GenAI] 🧠 Routing through MetaClaw proxy");
  llm = new ChatOpenAI({
    baseUrl: metaclawConfig.baseUrl,
    apiKey: metaclawConfig.apiKey,
    model: selectedModel,  // MetaClaw may ignore depending on config
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
- `mcp-gen/src/utils/genai.ts` (add MetaClaw routing logic)
- `mcp-gen/.env` (add MetaClaw environment variables)
- `mcp-gen/README.md` (update deployment instructions)

**After completing this change:**
1. Rebuild mcp-gen Docker container
2. Set `METACLAW_ENABLED=true` in `.env`
3. Test with simple MCP server generation request
4. Verify MetaClaw logs show skill injection for code generation

**Expected benefit:**
When mcp-gen requests code generation, MetaClaw will:
1. Search `~/.metaclaw/skills/` for relevant skills (MCP patterns, auth, best practices)
2. Inject those skills into the system prompt
3. Generate higher quality MCP servers based on accumulated knowledge

---

### 2.3 langChain-application

**Status:** ✅ Complete (Phase 1)

The multi-agent system already routes through MetaClaw when enabled.

**Implementation:**

- `my_agent/config/__init__.py` - Parses `METACLAW_BASE_URL`, `METACLAW_API_KEY`, `METACLAW_ENABLED`
- `my_agent/utils/llm_factory.py:27-46` - Conditional MetaClaw routing:
  ```python
  if metaclaw_enabled:
      return ChatOpenAI(
          model=config["model"],
          api_key=metaclaw_api_key,
          base_url=metaclaw_base_url
      )
  ```

**Environment variables:**
```env
METACLAW_ENABLED=true
METACLAW_BASE_URL=http://localhost:30000/v1
METACLAW_API_KEY=metaclaw
GEMINI_API_KEY=your_key_here  # Fallback if MetaClaw disabled
GEMINI_MODEL=gemini-2.5-flash
```

---

## 🧠 Phase 3: Skill Development & Learning

### 3.1 Create MCP-Focused MetaClaw Skills

**Important distinction:** Do NOT attempt to sync `mcp-gen` prompt fragments with MetaClaw — they are fundamentally different skill types:

- **mcp-gen skills**: Code generation templates (TypeScript structure, Zod patterns). Statically injected into prompts by the generator.
- **MetaClaw skills**: Conversational behavior guidance used during chat interactions. Dynamically retrieved based on user queries.

Add new MetaClaw skills to `~/.metaclaw/skills/` that help MetaClaw assist users with MCP-related questions:

- **mcp-server-architecture**: Explain how MCP servers work, the MCP protocol
- **mcp-tool-design-patterns**: Guide on designing effective MCP tools, parameter handling, response formatting
- **mcp-security-best-practices**: Authentication, authorization, secure MCP server deployment
- **mcp-troubleshooting**: Debugging common MCP integration issues

Each skill should follow MetaClaw `SKILL.md` format with YAML frontmatter:

```markdown
---
name: mcp-server-architecture
description: Explains MCP server architecture and protocol fundamentals
category: technical_guidance
tags: [mcp, protocol, architecture]
---

# MCP Server Architecture

MCP (Model Context Protocol) servers...
```

---

### 3.2 Skill Separation Principle

**Maintain strict separation:**

| Aspect | mcp-gen Skills | MetaClaw Skills |
|--------|---------------|-----------------|
| Location | `mcp-gen/src/skills/` | `~/.metaclaw/skills/` |
| Format | Code templates, prompts | Markdown conversational guidance |
| Usage | Statically injected | Dynamically retrieved |
| Evolution | Manual edits | Auto-evolution via conversations |
| Scope | Code generation | Conversational intelligence |

**Keep mcp-gen skills isolated:**
- Tightly coupled to generator's internal architecture
- Not designed for conversational retrieval
- Changing them could break the generation pipeline

**Summary:** Separate concerns — mcp-gen for code generation, MetaClaw for conversational intelligence about MCP concepts.

---

### 3.3 Leverage MetaClaw Memory for Cross-Session Learning

MetaClaw's continuous meta-learning will automatically improve responses to MCP-related questions over time:

- User corrections on MCP explanations will evolve the skills
- Successful patterns from mcp-gen outputs can inform skill refinement
- Cross-project learnings (from chatbot and LangChain applications) will be shared

**Enable memory persistence:**
Update `~/.metaclaw/config.yaml`:
```yaml
memory:
  enabled: true
  top_k: 5
  max_tokens: 800
  retrieval_mode: hybrid
```

---

## ✅ Phase 4: Verification & Testing

### 4.1 Pre-Verification Checklist

- [ ] MetaClaw running locally on port 30000
- [ ] All Docker containers rebuilt with updated environment variables
- [ ] `METACLAW_ENABLED=true` set in all component `.env` files
- [ ] `METACLAW_BASE_URL` correctly set for each component's network context
- [ ] At least one MCP-focused skill in `~/.metaclaw/skills/`

### 4.2 Verification Steps

1. **Start MetaClaw:**
   ```bash
   metaclaw start --mode skills_only --port 30000
   ```

2. **Rebuild and launch all services:**
   ```bash
   docker-compose up --build -d
   ```

3. **Test chatbot → MetaClaw flow:**
   - Open chat interface
   - Select "MetaClaw" as provider
   - Send a message about MCP concepts (should trigger MCP skills)
   - Send a message requesting MCP server creation
   - Verify: MetaClaw intercepts, skills injected, then hands off to Gemini for tool execution
   - Check MetaClaw terminal/logs for request interception

4. **Test mcp-gen → MetaClaw flow (after Step 2.2 completed):**
   - Trigger MCP server generation via chatbot
   - Watch mcp-gen logs for "Routing through MetaClaw proxy"
   - Verify MetaClaw logs show code generation request with skill injection

5. **Test fallback behavior:**
   - Stop MetaClaw (`metaclaw stop`)
   - Repeat chat request
   - Should fall back to direct Gemini provider seamlessly

6. **Test skill injection:**
   - Add a distinctive test skill to `~/.metaclaw/skills/`
   - Ask a question that should match that skill
   - Verify MetaClaw references the skill content in response

### 4.3 Automated Tests

Run existing integration tests:
```bash
cd backend
pytest tests/test_metaclaw_integration.py -v
```

Create additional tests:
- `test_mcpgens_through_metaclaw.py` - mcp-gen integration (Phase 2)
- `test_skills_injection.py` - skill loading and injection
- `test_memory_cross_session.py` - memory persistence
- `test_conversation_logging.py` - logging for RL training

---

## ⚙️ Configuration Reference

### chatbot_mcp_client `.env`

```env
# LLM Providers
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# MetaClaw Integration (Phase 1 - Active)
METACLAW_BASE_URL=http://host.docker.internal:30000/v1
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

### mcp-gen `.env` (Phase 2 - Pending activation)

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
mode: auto  # "auto" | "rl" | "skills_only"
claw_type: none

llm:
  provider: kimi  # or qwen, openai, volcengine, custom
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
  auto_evolve: true

memory:
  enabled: false  # Set true for Phase 3
  top_k: 5
  max_tokens: 800

rl:
  enabled: false  # Set true for Phase 3
  backend: auto
  model: moonshotai/Kimi-K2.5
```

---

## 🐛 Troubleshooting

| Issue                                 | Solution                                                                          |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| MetaClaw won't start on port 30000    | Check conflicts: `netstat -ano \| findstr :30000` (Windows) or `lsof -i:30000`   |
| Skills not injecting                  | Verify `~/.metaclaw/skills/` has valid `SKILL.md` files with YAML frontmatter    |
| Backend can't reach MetaClaw (Docker) | Ensure `METACLAW_BASE_URL=http://host.docker.internal:30000/v1`                  |
| mcp-gen still bypasses MetaClaw       | Check `METACLAW_ENABLED=true` in mcp-gen `.env`, verify code change in `genai.ts` |
| Tool calls swallowed                  | Already fixed in Phase 1 - two-stage handoff preserves intent                    |
| LangGraph stream blank                | Fixed - `use-chat-store.ts` handles all event types                              |
| Memory not persisting                 | Set `memory.enabled: true` in MetaClaw config, restart MetaClaw                  |

---

## 📝 Technical Notes

- **Port:** MetaClaw defaults to `30000`. Ensure no conflicts.
- **Compatibility:** MetaClaw follows OpenAI Chat Completions standard.
- **Skill Storage:** `~/.metaclaw/skills/` - each skill is a `SKILL.md` file with YAML frontmatter.
- **Memory Storage:** `~/.metaclaw/memory/` (when enabled).
- **Two-Stage Handoff:** MetaClaw decides, Gemini executes. Prevents tool call loss.
- **Fallback:** Always implemented - system works even if MetaClaw is down.
- **Docker Networking:** Use `host.docker.internal` for macOS/Windows Docker to reach host services.

---

## 📚 Related Documentation

- `langChain-application/history.md` - Detailed change log for multi-agent system
- `chatbot_mcp_client/history.md` - Chatbot evolution and MetaClaw integration history
- `langChain-application/METACLAW_ARCHITECTURE_ANALYSIS.md` - Deep architecture analysis
- `MetaClaw/README.md` - Upstream MetaClaw documentation
- `mcp-gen/README.md` - MCP generator docs
- `conductor/metaclaw_integration_plan.md` - Original integration plan (phase structure)
- `chatbot_mcp_client/CLAUDE.md` - Project CLAUDE.md with development commands

---

## 🎯 Next Steps

### Immediate (Complete ✅)

1. **✅ Complete mcp-gen MetaClaw routing** (completed)
   - Modified `mcp-gen/src/utils/genai.ts:79-92` to route through MetaClaw when enabled
   - Verified TypeScript compilation passes
   - Tested configuration with `METACLAW_ENABLED=true`
   - **Status:** COMPLETE

2. **✅ Document mcp-gen integration**
   - Updated `mcp-gen/README.md` with comprehensive MetaClaw setup instructions
   - Added AI provider configuration section
   - Updated `.env.example` with clear MetaClaw documentation
   - **Status:** COMPLETE

### Short-term (This Week)

3. **📋 Bootstrap initial MCP skills**
   - Create 4 MCP-focused skills in `~/.metaclaw/skills/` (architecture, design patterns, security, troubleshooting)
   - Verify skill discovery and injection
   - **Owner:** DevOps / AI Engineer

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
   - Create validation agent with write access to `~/.metaclaw/skills/`
   - Bidirectional sync with mcp-gen
   - **Owner:** AI Engineer

---

## Summary

**Phase 1 Achievement:** The core MetaClaw integration is production-ready. Chatbot and langChain-application both benefit from skill injection and memory (when enabled). The two-stage handoff architecture ensures zero tool call loss.

**Phase 2 Achievement:** mcp-gen integration is **complete**. All code generation requests now route through MetaClaw when enabled (`METACLAW_ENABLED=true`). MetaClaw injects MCP-specific skills into every generation, improving quality and consistency. The fallback to direct Gemini/Groq ensures reliability if MetaClaw is unavailable.

**Architecture Principle:** Maintain clear separation between mcp-gen's static code templates and MetaClaw's dynamic conversational skills. Both coexist without interference.
