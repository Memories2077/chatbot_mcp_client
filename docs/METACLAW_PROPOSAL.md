# MetaClaw Integration Proposal

> **Note:** This proposal has been merged into the comprehensive [METACLAW_INTEGRATION.md](./METACLAW_INTEGRATION.md) document, which contains the full implementation plan, testing strategy, and configuration reference. This file is kept for historical context.

## 📐 Current Architecture

```
User
 │
 ▼
chatbot_mcp_client  (Next.js frontend + FastAPI backend)
 │  • UI/chat interface
 │  • LangChain agent with MCP tool loading
 │  • Provider: Gemini / Groq
 │
 ▼
langChain-application  (Python, LangGraph)
 │  • Agent orchestration
 │  • Tool calling
 │  • ChromaDB vector store
 │
 ▼
mcp-gen  (TypeScript, Node.js)
 │  • MCP Server generator
 │  • Skill Router (SKILLS.md)
 │  • Dynamic Proxy
 │  • MCP Server Manager (50KB!)
```

## 🦞 MetaClaw là gì?

MetaClaw là một **transparent learning proxy** đặt trước bất kỳ OpenAI-compatible LLM backend nào. Nó:

1. **Intercepts** mọi request/response qua proxy port (mặc định `:30000/v1`)
2. **Injects skills** (Markdown files) vào system prompt ở mỗi turn
3. **Summarizes** conversation thành skills mới sau mỗi session
4. **Meta-learns** (optional RL) từ live conversations qua LoRA fine-tuning
5. **Persists memory** (v0.4.0) — facts, preferences, project state across sessions

---

## 🤔 Câu hỏi: MetaClaw nên là Proxy giữa User ↔ chatbot_mcp_client?

**Câu trả lời ngắn: KHÔNG phải proxy ở tầng User↔frontend, mà nên chèn vào tầng LLM Backend.**

### Phân tích điểm chèn lý tưởng

MetaClaw hoạt động như **proxy OpenAI-compatible** — nó cần đứng **giữa LangChain Agent và LLM Provider**, không phải giữa User và frontend:

```
TRƯỚC (hiện tại):
chatbot_mcp_client backend
  └── LangChain Agent
        └── ChatGoogleGenerativeAI / ChatGroq  ──► Gemini/Groq API

SAU (với MetaClaw):
chatbot_mcp_client backend
  └── LangChain Agent
        └── ChatOpenAI(base_url="http://localhost:30000/v1")  ──► MetaClaw Proxy
                                                                      │
                                                                      ├── Skill Injection
                                                                      ├── Memory Retrieval
                                                                      ▼
                                                                 Gemini/Groq/Any LLM API
```

---

## 🏗️ Ba chiến lược tích hợp

### Option A — MetaClaw as LLM Proxy (Recommended ✅)

**Đây là đúng với thiết kế của MetaClaw.**

```
User ──► chatbot_mcp_client (frontend)
              │
              ▼
         FastAPI backend (main.py)
              │
              ▼ (thay LLM provider bằng MetaClaw endpoint)
         MetaClaw Proxy :30000/v1
              │  ┌─────────────────────────────────┐
              │  │  Skill injection vào system prompt │
              │  │  Memory retrieval (v0.4.0)        │
              │  │  Session summarization → skills   │
              │  │  (Optional) RL fine-tuning        │
              │  └─────────────────────────────────┘
              │
              ▼
         LLM Provider (Gemini/Groq/OpenAI)
              │
              ▼
         ◄── Response ──► mcp-gen tools (via MCP protocol)
```

**Thay đổi cần thiết** trong `chatbot_mcp_client/backend/main.py`:
```python
# TRƯỚC:
llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key)

# SAU (khi MetaClaw active):
llm = ChatOpenAI(
    base_url="http://localhost:30000/v1",
    api_key="metaclaw",  # local proxy, key không quan trọng
    model=model_name
)
```

**Ưu điểm:**
- ✅ Zero code change ở frontend
- ✅ Skills được inject tự động, agent "học" qua mỗi conversation
- ✅ Memory layer: nhớ preferences, project state của user
- ✅ Hoàn toàn transparent với mcp-gen và langChain layers below
- ✅ Có thể toggle on/off qua config

**Nhược điểm:**
- ⚠️ MetaClaw cần chạy như separate process/service
- ⚠️ Skills trong MetaClaw riêng biệt với Skill System trong mcp-gen (cần sync)

---

### Option B — MetaClaw as Intelligence Sidecar trong mcp-gen

**Tận dụng MetaClaw chỉ cho phần skill evolution, không dùng proxy.**

```
mcp-gen
  ├── SkillRouter (SKILLS.md hiện tại)
  └── MetaClaw Skills Library (~/.metaclaw/skills/)
        ▲
        │ (import/sync skills sau mỗi session)
        │
  MetaClaw Evolver (background process)
        ▲
        │ (analyze conversation logs)
        │
  Session logs từ chatbot_mcp_client
```

**Thay đổi:** mcp-gen đọc thêm `~/.metaclaw/skills/*.md` vào SkillRouter, MetaClaw evolver chạy background để generate skills mới từ conversation logs.

**Ưu điểm:**
- ✅ Tận dụng được Evolver (LLM-powered skill extraction)
- ✅ Skills tự grow qua real usage
- ✅ Không thay đổi LLM routing

**Nhược điểm:**
- ❌ Không có memory layer
- ❌ Không có real-time skill injection (skills chỉ update sau session, không mid-conversation)

---

### Option C — Hybrid Intelligence Layer (Most Powerful 🚀)

**Kết hợp cả hai: MetaClaw làm LLM proxy VÀ skill evolver đồng bộ với mcp-gen.**

```
User
 │
 ▼
chatbot_mcp_client  ──► MetaClaw Proxy (:30000)
                              │
                         ┌────┴────────────────────┐
                         │   Shared Skill Library   │
                         │  ~/.metaclaw/skills/     │◄──── mcp-gen SkillRouter
                         │   + memory store         │      (bidirectional sync)
                         └────┬────────────────────┘
                              │
                         LLM API (Gemini/Groq)
                              │
                         Tool calls ──► mcp-gen MCP Server
                              │         langChain-application
                              ▼
                         Response
```

**Kiến trúc mục tiêu:**

```
┌─────────────────────────────────────────────────────────┐
│                   INTELLIGENCE LAYER                       │
│  metaclaw-bridge service                                   │
│   • Sync skills: mcp-gen/skills/ ↔ ~/.metaclaw/skills/   │
│   • Export conversation sessions → MetaClaw format        │
│   • Import evolved skills → mcp-gen SKILLS.md            │
└─────────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
  MetaClaw Proxy              mcp-gen SkillRouter
  (LLM gateway)               (MCP generation)
        │                           │
        └──────────┬────────────────┘
                   ▼
           Unified Agent Response
```

---

## 🎯 Đề xuất cuối cùng

**Implement theo 3 phases:**

### Phase 1 — Quick Win
Deploy MetaClaw với `claw_type=none` (manual wiring), trỏ `ChatOpenAI` trong `main.py` vào `http://localhost:30000/v1`. Kích hoạt **skills_only mode** — không cần GPU, không cần RL.

```bash
pip install -e ".[evolve]"   # skills + auto-evolution
metaclaw setup               # chọn claw_type=none, trỏ vào Gemini/Groq
metaclaw start --mode skills_only
```

Kết quả: Mọi conversation đi qua MetaClaw, skills tự động accumulate.

### Phase 2 — Skill Sync
Viết `metaclaw-bridge` script để:
- Copy skills mới từ `~/.metaclaw/skills/` → mcp-gen's skill system
- Export mcp-gen's `SKILLS.md` → MetaClaw skill format
- Chạy như scheduled job (cron/Windows Task Scheduler)

Kết quả: Skills grow qua conversations, mcp-gen generation quality improves.

### Phase 3 — Memory + RL (Tùy chọn)
```bash
metaclaw config memory.enabled true
pip install -e ".[rl,evolve,scheduler]"
metaclaw start  # auto mode với RL scheduler
```
Kết quả: Agent nhớ user preferences cross-session, continuously improves với RL.

---

## ⚠️ Trade-offs cần cân nhắc

| | Option A (LLM Proxy) | Option B (Sidecar) | Option C (Hybrid) |
|---|---|---|---|
| Complexity | Thấp | Trung bình | Cao |
| Skill Injection | Real-time ✅ | After session ⚠️ | Real-time ✅ |
| Memory | ✅ | ❌ | ✅ |
| mcp-gen Integration | Minimal | Deep | Deep |
| Production Risk | Thấp | Thấp | Trung bình |
| Recommended for | Bắt đầu | Research | Scale up |

> [!IMPORTANT]
> MetaClaw **không thay thế** LangChain Agent hay mcp-gen — nó là một **intelligence layer** bao quanh LLM backend, giúp agent *học* từ experience. Flow vẫn là: `chatbot_mcp_client → langChain → mcp-gen`, nhưng mỗi LLM call sẽ thông qua MetaClaw để enriched với skills + memory.

> [!TIP]
> Bắt đầu với **Phase 1 (Option A, skills_only mode)** — chỉ cần thay 5 dòng code trong `main.py` và chạy `metaclaw start`. Sau khi verify hoạt động tốt mới proceed sang Phase 2 & 3.
