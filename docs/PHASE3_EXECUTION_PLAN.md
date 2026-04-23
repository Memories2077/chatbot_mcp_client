# Phase 3 Execution Plan - April 30 Deadline
**Status:** READY FOR EXECUTION  
**Deadline:** April 30, 2026  
**Days Available:** 7 (April 23-30)  
**Strategy:** Safe, demonstrable progress without RL infrastructure

---

## 🎯 Context & Constraints

### Current State (as of April 23)
- ✅ **Phase 1 Complete**: MetaClaw integration working in chatbot backend
- ✅ **Phase 2 Complete**: mcp-gen routing through MetaClaw (verified in docs)
- ⚠️ **Critical Gap**: No MCP-specific skills deployed yet
- ⚠️ **Critical Gap**: Memory not enabled in MetaClaw config
- ❌ **Missing**: Feedback collection mechanism
- ❌ **Missing**: RL pipeline (Tinker/MinT) - **cannot complete by deadline**

### Deadline Reality
April 30 is **7 days away**. RL pipeline requires:
- Tinker/MinT infrastructure setup (2-3 days minimum)
- PRM configuration and testing (1-2 days)
- Integration with existing system (1-2 days)
- **Total: 5-7 days of uncertain work**

**Verdict:** RL pipeline is **IMPOSSIBLE** to complete reliably by deadline.

---

## ✅ Safe Plan: What We CAN Deliver

### Goal
Deliver a **working, demonstrable system** that shows MetaClaw's learning capability without RL infrastructure.

### Deliverables (April 30)
1. ✅ MetaClaw fully operational with memory
2. ✅ 4 MCP-specific skills deployed and tested
3. ✅ Basic feedback collection (Like/Dislike)
4. ✅ Cross-session memory demonstration
5. ✅ Complete documentation and demo script

### Deferred to Post-Deadline
- RL training pipeline (Tinker/MinT setup)
- Opinion dialog with text feedback
- Advanced skill auto-evolution workflows
- MCP-specific feedback linking (generic is fine)

---

## 📅 Day-by-Day Execution Plan

### **Day 1-2 (April 23-24): Bootstrap MCP Skills**

**Objective**: Create and deploy 4 foundational MCP skills

**Tasks**:
1. Create skill files in `~/.metaclaw/skills/`:
   - `mcp-server-architecture.md`
   - `mcp-tool-design-patterns.md`
   - `mcp-security-best-practices.md`
   - `mcp-troubleshooting.md`
2. Each skill follows MetaClaw `SKILL.md` format with YAML frontmatter
3. Test each skill:
   - Ask MetaClaw questions that should trigger each skill
   - Verify skill content appears in responses
   - Check MetaClaw logs for skill retrieval

**Success Criteria**:
- All 4 skills visible in MetaClaw
- MetaClaw references skills when answering MCP questions
- Skills properly categorized and tagged

**Files to Create**:
- `~/.metaclaw/skills/mcp-server-architecture.md`
- `~/.metaclaw/skills/mcp-tool-design-patterns.md`
- `~/.metaclaw/skills/mcp-security-best-practices.md`
- `~/.metaclaw/skills/mcp-troubleshooting.md`

---

### **Day 3 (April 25): Enable Memory Persistence**

**Objective**: Enable cross-session learning

**Tasks**:
1. Update `~/.metaclaw/config.yaml`:
   ```yaml
   memory:
     enabled: true
     top_k: 5
     max_tokens: 800
     retrieval_mode: hybrid
   ```
2. Restart MetaClaw service
3. Test memory persistence:
   - Start MetaClaw, ask about MCP servers
   - Stop MetaClaw, restart
   - Ask follow-up question referencing previous context
   - Verify memory persists across restarts

**Success Criteria**:
- Memory directory populated with storage files
- Conversations recalled after MetaClaw restart
- No errors in MetaClaw logs about memory

**Files to Modify**:
- `~/.metaclaw/config.yaml`

---

### **Day 4 (April 26): Feedback Storage Backend**

**Objective**: Store user feedback in MongoDB

**Tasks**:
1. Extend MongoDB `logs` collection schema in `mcp-gen` stack:
   - Add `likeCount: number` (default 0)
   - Add `dislikeCount: number` (default 0)
   - Add `feedbacks: Array<FeedbackEntry>`
2. Create feedback endpoint in chatbot backend `main.py`:
   - `POST /api/feedback` - generic feedback for any message
   - Schema: `{ messageId, type: 'like'|'dislike', userId?, comment? }`
   - Use atomic MongoDB updates (`$inc`, `$push`)
3. Update `docker-compose.yml` if needed to ensure MongoDB persistence

**Success Criteria**:
- Feedback endpoint accepts POST requests
- Data correctly stored in MongoDB
- Counts increment atomically
- Feedback array accumulates entries

**Files to Modify**:
- `backend/main.py` - add feedback endpoint
- `docker-compose.yml` - verify MongoDB volume mounts (if needed)

---

### **Day 5 (April 27): Feedback UI (Minimal)**

**Objective**: Add Like/Dislike buttons to chat messages

**Tasks**:
1. Update `ChatMessage` interface in `src/lib/types.ts`:
   ```typescript
   interface ChatMessage {
     // ... existing fields
     feedback?: 'like' | 'dislike' | null;
   }
   ```
2. Create `ChatMessageFeedback.tsx` component:
   - Like/Dislike buttons
   - Visual state (filled when clicked)
   - Send feedback to `/api/feedback` on click
3. Integrate into `ChatMessage.tsx` or `ChatLayout.tsx`
4. Update `useChatStore` to track feedback state locally

**Success Criteria**:
- Like/Dislike buttons appear on each message
- Clicking sends feedback to backend
- Button state updates immediately (optimistic UI)
- No console errors

**Files to Create/Modify**:
- `src/components/chat/ChatMessageFeedback.tsx` (new)
- `src/lib/types.ts` - add feedback field
- `src/components/chat/chat-message.tsx` or `chat-layout.tsx` - integrate feedback

---

### **Day 6 (April 28): Integration Testing**

**Objective**: Verify end-to-end learning demonstration

**Tasks**:
1. Start all services with MetaClaw enabled
2. Test full flow:
   - Chat with MetaClaw about MCP → verify skill injection
   - Provide feedback on responses → verify stored in MongoDB
   - Restart MetaClaw → ask similar question → verify memory recall
   - Check that feedback counts persist
3. Document test results with screenshots/logs
4. Create demo script showing:
   - MetaClaw using MCP skills
   - User giving feedback
   - Memory recall across sessions

**Success Criteria**:
- All components work together
- Clear evidence of learning (skill injection + memory)
- Feedback system operational
- Demo script ready for presentation

**Files to Create**:
- `docs/PHASE3_DEMO_GUIDE.md` - step-by-step demo
- `docs/PHASE3_TEST_RESULTS.md` - test outcomes

---

### **Day 7 (April 29): Buffer & Polish**

**Objective**: Fix bugs, improve docs, prepare for submission

**Tasks**:
1. Bug fixes from Day 6 testing
2. Update `METACLAW_INTEGRATION_SYNCED.md` with Phase 3 status
3. Create `PHASE3_DEPLOYMENT.md` with setup instructions
4. Verify all environment variables documented
5. Final integration test

**Success Criteria**:
- No known bugs
- Documentation complete
- System demonstrable end-to-end

**Files to Update**:
- `docs/METACLAW_INTEGRATION_SYNCED.md` - mark Phase 3 complete
- `docs/PHASE3_DEPLOYMENT.md` - new deployment guide
- `README.md` - update if needed

---

### **Day 8 (April 30): Submission Day**

**Objective**: Deliver working system

**Tasks**:
1. Final health check
2. Run demo script
3. Package documentation
4. Submit

---

## 🔧 Implementation Details

### 1. MetaClaw Skill Format

Each skill follows this template:

```markdown
---
name: mcp-server-architecture
description: Explains MCP server architecture and protocol fundamentals
category: technical_guidance
tags: [mcp, protocol, architecture]
---

# MCP Server Architecture

MCP (Model Context Protocol) servers provide tools and resources to LLM applications...

## Key Concepts

- **Transport**: SSE over HTTP
- **Tools**: Callable functions exposed by the server
- **Resources**: Read-only data accessible via URIs
- **Prompts**: Reusable message templates

## Implementation Pattern

1. Define tools with clear schemas
2. Implement resource handlers
3. Handle initialization properly
4. Support streaming responses where appropriate
```

### 2. Feedback API Endpoint

```python
# In backend/main.py

class FeedbackRequest(BaseModel):
    messageId: str
    type: Literal['like', 'dislike']
    userId: Optional[str] = None
    comment: Optional[str] = None

@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    # Store in MongoDB logs collection
    # Use $inc for counts, $push for feedbacks array
    pass
```

### 3. MongoDB Schema Extension

Existing `logs` collection documents will have:

```javascript
{
  // ... existing fields (serverId, metadata, etc.)
  likeCount: 5,
  dislikeCount: 1,
  feedbacks: [
    {
      feedbackId: "uuid",
      feedbackType: "like",
      feedbackText: "Great explanation!",
      userId: "user123",
      timestamp: ISODate("2026-04-28T...")
    }
  ]
}
```

---

## 🧪 Verification Checklist

### Pre-Deadline (April 29)
- [ ] MetaClaw running with `memory.enabled=true`
- [ ] 4 MCP skills deployed in `~/.metaclaw/skills/`
- [ ] Skills trigger on relevant questions
- [ ] Memory persists across MetaClaw restarts
- [ ] Feedback endpoint accepting requests
- [ ] MongoDB storing feedback correctly
- [ ] Like/Dislike UI functional on all messages
- [ ] No console errors in browser
- [ ] All TypeScript compilation passing
- [ ] Backend starting without errors

### Demo Readiness (April 30)
- [ ] Demo script executed successfully
- [ ] Screenshots/videos captured
- [ ] Documentation complete
- [ ] Environment setup documented
- [ ] Known issues documented (if any)

---

## 🚨 Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| MetaClaw memory bugs | High | Test thoroughly on Day 6; if unstable, disable and document |
| MongoDB connection issues | High | Verify docker-compose volumes; test early |
| Frontend TypeScript errors | Medium | Build frequently; use `npm run typecheck` |
| Skills not triggering | Medium | Test each skill individually; adjust descriptions |
| Feedback lost on restart | Medium | Verify MongoDB persistence; test restart scenarios |

**If something breaks:**
1. Document the issue
2. Implement fallback (e.g., disable feature)
3. Continue with remaining tasks
4. Note limitation in final submission

---

## 📊 Success Metrics

### Minimum Viable Success (Pass)
- MetaClaw operational with memory
- 2+ MCP skills triggering correctly
- Feedback collection working
- Demo script executes without errors

### Target Success (Good)
- All 4 MCP skills working
- Cross-session memory demonstrated
- Feedback UI polished
- Complete documentation

### Stretch Success (Excellent)
- All targets + no known bugs + video demo

---

## 🔄 Post-Deadline Roadmap (For Reference)

### Week 1-2 (May 1-14)
- Set up Tinker/MinT RL backend
- Configure PRM (Preference Reward Model)
- Enable `rl.enabled=true` in MetaClaw
- Connect feedback data to RL training

### Week 3-4 (May 15-31)
- Test RL training loop
- Implement opinion dialog UI
- Add feedback-to-skill evolution
- Performance optimization

---

## 📝 Notes

- **No RL**: We explicitly defer RL to post-deadline. It's too complex and risky.
- **Minimal Viable**: Focus on working system, not feature completeness.
- **Documentation**: As important as code for academic submission.
- **Demo**: Prepare a 5-minute demo showing the learning loop.

---

**Approved by:** Tú (April 23, 2026)  
**Plan Owner:** Claude Code  
**Status:** Ready for execution
