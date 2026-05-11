# Fix Plan: Critical Logic Errors in MCP Chatbot

## Context

The code review identified 12 issues ranging from CRITICAL to LOW severity. The most urgent is the **broken SSE streaming parser** in the frontend, which causes lost content in AI responses. Secondary issues include agent factory race conditions, misleading system prompts, and silent failures.

This plan addresses all issues in order of severity impact, following TDD principles and ensuring backward compatibility.

---

## Issues to Fix

### CRITICAL (1)
1. **Frontend SSE parser loses content** - Buffer needed for chunked lines

### HIGH (6)
2. System prompt mentions unavailable tools
3. Redundant agent creation + state race condition
4. MCP connection failures silently ignored
5. `normalize_docker_urls_in_dict` mutates input
6. Frontend error handling loses error context
7. Backend agent state shared globally

### MEDIUM (4)
8. Exit stack cleanup swallows exceptions
9. Hardcoded timeouts/retries
10. Database index creation may fail silently
11. Missing error messages in streaming

### LOW (2)
12. Session migration incomplete
13. Print statements instead of logging

---

## Implementation Order

**Phase 1 (Critical):** Fix SSE streaming parser (Issue #1)
- This blocks all users from getting complete responses

**Phase 2 (High):** Backend agent factory refactor (Issues #2, #3, #7)
- Fix system prompt generation
- Eliminate redundant agent creation
- Remove shared state race condition

**Phase 3 (High):** Error handling improvements (Issues #4, #5, #6)
- MCP connection errors
- Immutable normalization
- Frontend error typing

**Phase 4 (Medium):** Robustness improvements (Issues #8-#11)
- Better cleanup logging
- Configurable timeouts
- Database error handling

**Phase 5 (Low):** Polish (Issue #12, #13)
- Migration completeness
- Replace print with logger

---

## Detailed Steps

### Phase 1: Fix SSE Streaming Parser

**Files to modify:**
- `src/lib/hooks/use-chat-store.ts`

**Changes:**
1. Add `buffer: string` state variable (useRef) before the reader loop (around line 212)
2. Modify chunk processing to:
   - Append chunk to buffer
   - Split by `\n\n`
   - Keep incomplete last line in buffer (pop and save)
   - Process complete lines only
3. Handle edge cases:
   - Buffer grows too large (8KB limit, force split on non-SSE boundaries)
   - Empty lines between SSE events
   - Final buffer flush when `done` is true
4. Add unit test for multi-chunk line scenario (simulate with mock fetch)

**Implementation:**
```typescript
const bufferRef = useRef("");

// Inside the reader loop:
const chunk = decoder.decode(value, { stream: true });
bufferRef.current += chunk;
const lines = bufferRef.current.split("\n\n");
bufferRef.current = lines.pop() || ""; // Save incomplete line

for (const line of lines) {
  if (line.startsWith("data: ")) {
    // Parse and handle
  }
}

// After loop, if done and buffer remains, try to parse it:
if (done && bufferRef.current) {
  const line = bufferRef.current;
  if (line.startsWith("data: ")) {
    // Parse final line
  }
}
```

**Testing:**
- Manual test: Use mock server that sends `data: {"content":"Hello"}\n\ndata: {"content":"World"}\n\n` split across chunks (e.g., send `"data: {\"content\":\"Hel"` then `"lo\"}\n\ndata:..."`)
- Verify full content appears without loss

---

### Phase 2: Backend Agent Factory Refactor

**Files to modify:**
- `backend/main.py`
- `backend/metaclaw_client.py` (minor)

**Changes:**

1. **Fix `_stream_standard_agent_response` to use passed `mcp_urls`**:
   - Line 480: Change `state.current_mcp_urls` to `mcp_urls` parameter

2. **Eliminate redundant agent creation**:
   - Line 394: Store agent in a local variable
   - Pass that agent to `_stream_standard_agent_response` as optional parameter
   - If agent provided, skip `get_or_create_agent` inside helper

3. **Fix system prompt for standard agents**:
   - Modify `get_system_prompt` to accept `has_create_mcp_server_tool: bool`
   - Remove `create_mcp_server` references when false
   - Update callers appropriately

4. **Remove global state race** (option A - keep but fix usage):
   - Already using lock; ensure all state reads use local params
   - Or option B: Remove `state` entirely, create fresh agent per request
   - Given cache benefits, keep cache but ensure consistency

5. **MetaClaw agent handling**:
   - When provider is "metaclaw", `get_or_create_agent` returns `MetaClawClient`
   - The `isinstance(agent, BaseLanguageModel)` check on line 478 won't work for MetaClaw
   - Need to detect MetaClaw client explicitly

**Implementation approach:**
```python
# In chat_endpoint:
agent = await get_or_create_agent(...)

# Pass agent to helper to avoid double creation:
return StreamingResponse(
    _stream_standard_agent_response(
        request=request,
        messages=...,
        mcp_urls=...,
        temperature=...,
        agent=agent,  # NEW
        state=state
    ),
    ...
)

# Update helper signature:
async def _stream_standard_agent_response(
    request: ChatRequest,
    messages: List[Dict[str, Any]],
    mcp_urls: Optional[List[str]],
    temperature: float,
    state: AgentState,
    agent: Optional[Union[BaseLanguageModel, MetaClawClient]] = None  # NEW
) -> AsyncGenerator[str, None]:
    # If agent is None, create it; otherwise use provided
    if agent is None:
        agent = await get_or_create_agent(...)
    
    # Determine has_tools correctly:
    if isinstance(agent, MetaClawClient):
        has_tools = False  # MetaClaw handled separately
    else:
        has_tools = hasattr(agent, 'tools') and bool(agent.tools)
```

---

### Phase 3: Error Handling Improvements

**Files to modify:**
- `backend/main.py`
- `backend/shared.py`
- `src/lib/hooks/use-chat-store.ts`

**Changes:**

1. **MCP connection failures** (main.py lines 236-237):
   ```python
   if not connected:
       logger.error(f"All {max_retries} connection attempts failed for {url}")
       # Add to failed_urls list
   # After loop, if failed_urls not empty:
   if failed_urls and not mcp_urls_that_succeeded:
       # Either raise or yield warning message
   ```

2. **Immutable normalization** (shared.py):
   - Rewrite to create new dict recursively without mutating input

3. **Frontend error handling** (use-chat-store.ts):
   ```typescript
   catch (error: unknown) {
     const errorMessage = error instanceof Error ? error.message : String(error);
     // ...
   }
   ```

---

### Phase 4: Robustness Improvements

**Files to modify:**
- `backend/main.py`
- `backend/database.py`

**Changes:**

1. **Better cleanup logging** (main.py lines 92-97, 161-166):
   ```python
   except Exception as e:
       logger.warning(f"Error closing exit stack during shutdown: {e}")
   ```

2. **Configurable timeouts**:
   - Add `MCP_CONNECTION_RETRIES=3`, `MCP_RETRY_DELAY=2` to config
   - Replace hardcoded values

3. **Database index error surfacing**:
   - In `_create_indexes`, if index creation fails, log ERROR and re-raise
   - Startup should fail fast on DB schema issues

---

### Phase 5: Polish

**Files to modify:**
- `src/lib/hooks/use-chat-store.ts`
- `backend/database.py`

**Changes:**

1. **Session migration completeness**:
   ```typescript
   const validProviders = ['gemini', 'groq'];
   if (!validProviders.includes(state.settings?.provider)) {
     state.settings.provider = 'gemini';
   }
   ```

2. **Replace print with logger** in database.py

---

## Testing Strategy

### Unit Tests
- SSE buffer logic: Test single-line, multi-line, split-chunk scenarios
- Normalization function: Verify immutability with nested dicts
- System prompt: Test with/without `create_mcp_server` tool

### Integration Tests
- Full chat flow with standard provider
- MetaClaw routing flow
- MCP connection failure handling

### Manual Verification
1. Start backend + frontend
2. Send multi-paragraph message
3. Verify all content appears (Phase 1 fix)
4. Disconnect MCP server, verify warning appears (Phase 3)
5. Check logs for proper error reporting

---

## Rollback Considerations

All changes are backward compatible:
- SSE format unchanged (only internal parsing)
- API contracts unchanged
- Config additions are additive with defaults
- If issues arise, revert individual commits

---

## Critical Files Reference

| File | Issues | Priority |
|------|--------|----------|
| `src/lib/hooks/use-chat-store.ts` | #1, #6, #12 | CRITICAL |
| `backend/main.py` | #2, #3, #4, #7, #8, #9 | HIGH |
| `backend/shared.py` | #5 | HIGH |
| `backend/database.py` | #10, #13 | MEDIUM |
| `backend/metaclaw_client.py` | #7 context | LOW |

---

## Success Criteria

- [ ] SSE streaming delivers 100% of content (no missing chunks)
- [ ] No shared state race conditions in concurrent requests
- [ ] MCP connection failures produce user-visible warnings
- [ ] All functions are pure or documented side effects
- [ ] All error messages reach appropriate log level
- [ ] 80%+ test coverage on modified modules

---

## Phase 6: Testing & Verification

### Run Existing Tests
```bash
cd backend
pytest tests/test_metaclaw_integration.py -v
```

### Add New Tests

1. **Test SSE buffer logic** (frontend):
   - Create `src/lib/hooks/use-chat-store.test.ts` (or add to existing test file)
   - Mock fetch with chunked SSE response
   - Verify all chunks are assembled correctly

2. **Test normalization immutability**:
   - Verify input dict unchanged after calling `normalize_docker_urls_in_dict`

3. **Test system prompt generation**:
   - With `has_create_mcp_server_tool=true`: verify tool instructions included
   - With `false`: verify tool instructions excluded

4. **Test agent factory**:
   - Concurrent requests don't interfere
   - Agent reuse works correctly
   - MetaClaw agent handled properly

### Manual E2E Verification

1. Start full stack:
```bash
docker-compose up -d backend
npm run dev
```

2. Test multi-chunk responses:
   - Send a message that triggers a long response
   - Verify all content appears in chat

3. Test MCP connection failure:
   - Provide invalid MCP URL
   - Verify error message appears in chat

4. Test concurrent requests:
   - Send two rapid messages
   - Verify both responses complete correctly

### Code Review
After each phase, run code-reviewer agent on modified files to catch regressions.
