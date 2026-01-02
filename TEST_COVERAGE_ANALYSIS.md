# Test Coverage Analysis - SherlockRamosBot

**Generated:** 2026-01-02
**Status:** ⚠️ **Critical gaps in test coverage**

## Executive Summary

The SherlockRamosBot codebase currently has **minimal test coverage** (~15% estimated), with only 3 test files covering 3 out of 12 source modules. Critical production code paths including Discord bot interactions, LLM completion logic, database operations, and RAG functionality are **completely untested**.

---

## Current Test Coverage

### ✅ Tested Modules (3/12)

| Module | Test File | Coverage | Status |
|--------|-----------|----------|--------|
| `src/cache.py` | `tests/test_cache.py` | ~95% | ✅ Comprehensive |
| `src/profiling.py` | `tests/test_profiling.py` | ~90% | ✅ Good |
| `src/utils.py` | `tests/test_utils.py` | ~20% | ⚠️ Incomplete |

#### Details:

**1. test_cache.py** ✅
- Comprehensive coverage of `LRUCache` class
- Tests: cache hits/misses, TTL expiration, LRU eviction, statistics
- Well-structured with proper mocking
- **No gaps identified**

**2. test_profiling.py** ✅
- Tests `PerformanceMetrics` dataclass
- Tests `@timed` and `@timed_sync` decorators
- Tests metrics summary and reset functionality
- **Minor gap:** No integration tests with real Discord/completion functions

**3. test_utils.py** ⚠️
- **Only tests:** `split_into_shorter_messages()`
- **Untested functions:**
  - `discord_message_to_message()` - Critical for message parsing
  - `is_last_message_stale()` - Important for race condition prevention
  - `close_thread()` - Thread lifecycle management
  - `should_block()` - Access control/security

---

## ❌ Critical Gaps - Untested Modules (9/12)

### 🔴 HIGH PRIORITY (Production-Critical)

#### 1. **src/completion.py** - LLM Interaction Layer
**Lines:** ~150 | **Complexity:** High | **Risk:** 🔴 Critical

**Untested functionality:**
- `generate_completion_response()` - Core LLM API interaction
- RAG context injection logic
- OpenRouter API error handling (rate limits, connection errors, invalid requests)
- Response caching integration
- `CompletionResult` enum state handling
- `process_response()` - Discord message sending with chunking

**Why critical:**
- Handles expensive API calls (cost implications)
- Contains complex error recovery logic
- Integrates with 3 external services (OpenRouter, RAG, Cache)
- Directly impacts user experience

**Test recommendations:**
```python
# tests/test_completion.py
- Mock OpenRouter API responses (success, errors, rate limits)
- Test RAG context injection with mock documents
- Test cache hit/miss scenarios
- Test token limit handling (TOO_LONG result)
- Test response chunking for long replies
- Test moderation flag handling
- Integration test with real API (CI only, use test key)
```

---

#### 2. **src/main.py** - Discord Bot Core
**Lines:** ~200 | **Complexity:** Very High | **Risk:** 🔴 Critical

**Untested functionality:**
- `/chat` command handler
- Thread creation and configuration
- `on_message()` event handler
- Message staleness checks (race condition prevention)
- Thread state management (`thread_data` dictionary)
- Server allowlist enforcement
- Bot initialization and setup

**Why critical:**
- Entry point for all user interactions
- Complex async event handling
- State management without database persistence
- Security-critical (allowlist, DM blocking)

**Test recommendations:**
```python
# tests/test_main.py
- Mock Discord client/interaction objects
- Test /chat command with various model selections
- Test thread creation and prefix assignment
- Test message processing in owned vs non-owned threads
- Test staleness detection with multiple rapid messages
- Test blocked server/DM handling
- Test thread closure on context limit
```

---

#### 3. **src/database.py** - Persistence Layer
**Lines:** ~120 | **Complexity:** Medium | **Risk:** 🔴 High

**Untested functionality:**
- Connection pool management (Neon serverless)
- `save_thread()` - Thread configuration persistence
- `get_thread_config()` - State recovery
- `log_message()` - Message history tracking
- `log_analytics()` - Usage metrics
- Connection error handling and retries
- Pool lifecycle (connect/close)

**Why critical:**
- Neon serverless has cold-start implications
- Connection pool sizing affects costs
- Analytics data impacts business decisions
- State recovery on bot restarts

**Test recommendations:**
```python
# tests/test_database.py
- Mock asyncpg.Pool for unit tests
- Test connection retry logic
- Test thread save/retrieve roundtrip
- Test message logging with token counts
- Test analytics logging with all fields
- Integration test with real Neon DB (CI only)
- Test connection pool exhaustion scenarios
```

---

#### 4. **src/rag_service.py** - Knowledge Base
**Lines:** ~100 | **Complexity:** Medium | **Risk:** 🔴 High

**Untested functionality:**
- ChromaDB initialization and persistence
- `add_documents()` - Knowledge ingestion
- `query()` - Semantic search
- `get_stats()` - Collection metadata
- Embedding function configuration
- Error handling when ChromaDB fails to initialize

**Why critical:**
- RAG quality directly impacts answer accuracy
- ChromaDB failures could silently degrade responses
- Document ingestion errors could corrupt knowledge base

**Test recommendations:**
```python
# tests/test_rag_service.py
- Mock ChromaDB client for unit tests
- Test document addition with metadata
- Test query with varying n_results
- Test query with no results
- Test stats reporting
- Test initialization failure handling
- Integration test with temporary ChromaDB instance
```

---

### 🟡 MEDIUM PRIORITY (Important)

#### 5. **src/base.py** - Data Models
**Lines:** ~90 | **Complexity:** Low | **Risk:** 🟡 Medium

**Untested functionality:**
- `Message.render()` - Text formatting
- `Conversation.prepend()` and `render()`
- `Prompt.full_render()` - OpenAI format conversion
- `Prompt.render_system_prompt()` - System message construction
- `Prompt.render_messages()` - Role assignment logic

**Test recommendations:**
```python
# tests/test_base.py
- Test message rendering with/without text
- Test conversation rendering with separator tokens
- Test prompt rendering with examples
- Test role assignment (user vs assistant)
- Test system prompt structure
```

---

#### 6. **src/moderation.py** - Content Safety
**Lines:** ~55 | **Complexity:** Low | **Risk:** 🟡 Medium

**Untested functionality:**
- `moderate_message()` - Currently disabled but should be testable
- `fetch_moderation_channel()` - Guild channel lookup
- `send_moderation_flagged_message()` - Alert notifications
- `send_moderation_blocked_message()` - Block notifications

**Test recommendations:**
```python
# tests/test_moderation.py
- Test moderation channel fetching (success/missing)
- Test flagged message notifications
- Test blocked message notifications
- Test message truncation (100/500 char limits)
- Prepare for future moderation re-enablement
```

---

#### 7. **src/constants.py** - Configuration
**Lines:** ~150 | **Complexity:** Medium | **Risk:** 🟡 Medium

**Current issue:** Config loading fails in tests due to YAML parsing

**Untested functionality:**
- Environment variable loading (`get_env()`)
- Config YAML parsing with dacite
- Model validation (AVAILABLE_MODELS)
- Server allowlist parsing
- Bot invite URL generation

**Test recommendations:**
```python
# tests/test_constants.py
- Test get_env() with missing required variables
- Test config loading with valid/invalid YAML
- Test model list validation
- Test server ID parsing from env
- Mock environment variables in tests
```

---

### 🟢 LOW PRIORITY (Non-Critical)

#### 8. **src/exceptions.py**
- Likely contains custom exception classes
- Low complexity, but should have basic tests

#### 9. **src/utils.py** (remaining functions)
- Complete coverage for remaining utility functions
- Medium priority but easier to test

---

## Test Infrastructure Issues

### 🔧 Configuration Problems

**Problem:** Tests fail during collection due to config.yaml parsing
```
ConfigError: Failed to load config.yaml: missing value for field "example_conversations.messages.user"
```

**Impact:** Prevents running ANY tests that import `src.constants`

**Root cause:** Config loading happens at module import time, not runtime

**Solution:**
```python
# Recommended approach: Lazy config loading or test fixtures
# Option 1: Use pytest fixtures to mock config
@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    # Mock config before any imports
    pass

# Option 2: Refactor constants.py to lazy-load config
def get_config():
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load_config()
    return _CONFIG
```

### 📦 Missing Test Dependencies

**Current setup:**
- ✅ pytest, pytest-asyncio configured in pyproject.toml
- ❌ pytest-cov not in dev dependencies (installed manually)
- ❌ No mocking library (pytest-mock or unittest.mock patterns)
- ❌ No test fixtures for Discord objects

**Recommended additions to pyproject.toml:**
```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.8.0",
    "mypy>=1.14.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=7.0.0",        # ADD: Coverage reporting
    "pytest-mock>=3.12.0",      # ADD: Mocking utilities
    "httpx>=0.27.0",            # ADD: For testing HTTP clients
    "respx>=0.21.0",            # ADD: For mocking httpx/AsyncOpenAI
]
```

---

## Recommended Testing Strategy

### Phase 1: Foundation (Week 1)
1. **Fix test infrastructure**
   - Resolve config.yaml loading issue
   - Add pytest-cov to pyproject.toml
   - Set up test fixtures for common Discord objects

2. **Complete utils.py coverage**
   - Test `discord_message_to_message()`
   - Test `is_last_message_stale()`
   - Test `close_thread()`
   - Test `should_block()`

3. **Add base.py tests**
   - Test all data model rendering methods
   - Validate prompt structure

### Phase 2: Core Logic (Week 2)
4. **completion.py tests**
   - Mock OpenRouter client with respx
   - Test all CompletionResult states
   - Test RAG injection
   - Test caching integration

5. **database.py tests**
   - Mock asyncpg Pool
   - Test all CRUD operations
   - Test connection lifecycle

### Phase 3: Integration (Week 3)
6. **main.py tests**
   - Mock discord.py client
   - Test /chat command flow
   - Test message event handling

7. **rag_service.py tests**
   - Test with temporary ChromaDB
   - Test document ingestion pipeline

### Phase 4: Polish (Week 4)
8. **Add integration tests**
   - End-to-end test with real APIs (CI only)
   - Performance regression tests

9. **Set up CI/CD**
   - GitHub Actions workflow
   - Coverage reporting with codecov.io
   - Require 80% coverage on new PRs

---

## Coverage Goals

| Phase | Target Coverage | Timeline |
|-------|----------------|----------|
| Current | ~15% | - |
| Phase 1 | 40% | Week 1 |
| Phase 2 | 65% | Week 2 |
| Phase 3 | 80% | Week 3 |
| Phase 4 | 85%+ | Week 4 |

---

## Mock Architecture Recommendations

### Discord Objects
```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_discord_message():
    """Mock Discord message for testing."""
    msg = MagicMock()
    msg.author.name = "test_user"
    msg.content = "test message"
    msg.channel.id = 12345
    return msg

@pytest.fixture
def mock_discord_thread():
    """Mock Discord thread for testing."""
    thread = MagicMock()
    thread.id = 67890
    thread.owner_id = 11111
    thread.send = AsyncMock()
    thread.edit = AsyncMock()
    return thread
```

### OpenRouter API
```python
# tests/test_completion.py
import respx
from httpx import Response

@respx.mock
async def test_completion_success():
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        })
    )
    # Test completion logic
```

### Database
```python
# tests/test_database.py
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db_pool():
    """Mock asyncpg pool."""
    pool = MagicMock()
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"model": "gpt-4", "temperature": 0.7})
    pool.acquire = AsyncMock(return_value=conn)
    return pool
```

---

## Metrics to Track

1. **Code Coverage:** Target 85%+ for critical paths
2. **Test Execution Time:** Keep under 30 seconds for unit tests
3. **Integration Test Success Rate:** Monitor flakiness
4. **Mutation Testing Score:** Consider using mutmut for quality
5. **Test-to-Code Ratio:** Aim for 1.5:1 (test lines : source lines)

---

## Next Steps

### Immediate Actions (This Sprint)
1. [ ] Fix config.yaml loading in test environment
2. [ ] Add pytest-cov, pytest-mock, respx to dev dependencies
3. [ ] Create `tests/conftest.py` with common fixtures
4. [ ] Write tests for `src/utils.py` (remaining functions)
5. [ ] Write tests for `src/base.py`

### Short-term (Next 2 Weeks)
6. [ ] Complete `tests/test_completion.py` with mocked OpenRouter
7. [ ] Complete `tests/test_database.py` with mocked asyncpg
8. [ ] Complete `tests/test_rag_service.py` with temp ChromaDB
9. [ ] Begin `tests/test_main.py` with mocked Discord client

### Long-term (Month 2)
10. [ ] Set up GitHub Actions CI pipeline
11. [ ] Add coverage reporting to PRs
12. [ ] Write integration tests for critical paths
13. [ ] Add performance benchmarks

---

## Conclusion

The SherlockRamosBot currently has **critical gaps in test coverage** that pose risks to:
- **Reliability:** Untested error handling in production code
- **Cost:** Unvalidated API usage patterns
- **Security:** Untested access control logic
- **Maintainability:** No regression detection for refactors

**Priority recommendation:** Focus on testing `completion.py`, `database.py`, and `main.py` first, as these represent the highest-risk, highest-complexity components.

---

**Analysis conducted by:** Claude Code
**Review status:** Pending team review
**Next review date:** After Phase 1 completion
