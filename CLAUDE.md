# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SherlockRamosBot is a Discord chatbot for Brazilian law students (concurseiros) that uses OpenRouter to access multiple LLM models (GPT-4, Claude, Gemini, LLaMA). It features RAG with Neon PostgreSQL/pgvector, persistent conversation history, and prompt caching for cost optimization.

## Development Commands

### Running the Bot

```bash
# Recommended
uv run sherlock-bot

# Alternative
uv run python -m src.main
```

### Testing

```bash
# Run all tests
uv run pytest -v

# Unit tests only
uv run pytest tests/unit -v

# Integration tests (requires DATABASE_URL)
uv run pytest tests/integration -v

# With coverage
uv run pytest -v --cov=src --cov-report=term-missing
```

### Code Quality

```bash
# Linting and formatting (run in this order)
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run mypy src
```

### RAG Pipeline

```bash
# Ingest documents
uv run python scripts/ingest_docs.py path/to/document.pdf
uv run python scripts/ingest_docs.py ~/docs/juridicos/  # directory (recursive)
uv run python scripts/ingest_docs.py ./docs/ --no-recursive  # non-recursive

# Verify ingestion
uv run python scripts/verify_ingestion.py

# Test RAG E2E
uv run python scripts/test_rag_e2e.py
```

### Database Management

```bash
# Initialize database schema
uv run python scripts/init_db.py

# Verify database connection
uv run python scripts/verify_db.py

# Truncate database (DESTRUCTIVE)
uv run python scripts/truncate_db.py
```

### Environment Setup

Copy `.env.example` to `.env` and configure:

- `OPENROUTER_API_KEY`: OpenRouter API key (sk-or-v1-...)
- `OPENROUTER_BASE_URL`: Must be `https://openrouter.ai/api/v1`
- `DISCORD_BOT_TOKEN`: Discord bot token
- `DISCORD_CLIENT_ID`: Discord application client ID
- `ALLOWED_SERVER_IDS`: Comma-separated server IDs where bot can operate
- `DEFAULT_MODEL`: Default LLM model (see `src/constants.py` for options)
- `DATABASE_URL`: Neon PostgreSQL connection string
- `OPENAI_API_KEY`: For RAG embeddings (text-embedding-3-small)

## Architecture

### Cog-Based Architecture (discord.py 2.x)

The bot uses **Cogs** for modular command organization:

**Entry Point (`src/main.py`)**:
- `SherlockRamosBot` extends `commands.Bot`
- `setup_hook()`: Loads cogs and syncs slash commands to guilds
- Manages bot lifecycle and command registration

**Chat Cog (`src/cogs/chat.py`)**:
- `/chat` slash command: Creates threads for conversations
- `on_message` listener: Handles mentions and thread messages
- Coordinates message flow and moderation

To add new commands:
1. Create a new Cog in `src/cogs/`
2. Load it in `main.py`'s `setup_hook()` via `await self.add_cog(YourCog(self, self.db_service))`
3. Use `@app_commands.command()` for slash commands
4. Commands sync automatically on bot startup to guilds in `ALLOWED_SERVER_IDS`

### Two Conversation Modes

**Thread Mode** (`/chat` command):
1. User runs `/chat message:"question"` in a text channel
2. Bot creates a Discord thread with prefix `💬✅`
3. Thread config (model, temperature, max_tokens) persists in database
4. Messages stored in database for analytics
5. Thread closes at `MAX_THREAD_MESSAGES` (200) or context limit
6. Only responds in threads it owns (`thread.owner_id == bot.user.id`)

**Mention Mode** (direct mentions):
1. User mentions bot: `@SherlockBot qual a diferença entre dolo e culpa?`
2. Bot uses per-user virtual thread ID: `hash(f"{channel_id}_{user_id}")`
3. Retrieves last 10 messages from database for context
4. Responds directly in channel (no Discord thread)
5. Uses default config from constants

### Core Data Flow

```
User Message → Moderation → Database Log → [RAG Query] → LLM Prompt Construction → OpenRouter API → Cache → Response → Split & Send → Database Log
```

**Key Flow Points**:
1. **Staleness Check**: 3s delay + validation that no newer user message exists (`is_last_message_stale`) to batch rapid messages
2. **RAG Injection**: Last user message triggers hybrid search (vector + full-text) before LLM call
3. **Prompt Caching**: Anthropic/Gemini models use structured content with cache_control for invariant parts
4. **Response Cache**: LRU cache with TTL stores recent completions to reduce API calls

### Database Schema (Neon PostgreSQL)

**Tables**:
- `threads`: Thread metadata (guild_id, user_id, model, temperature, max_tokens, is_active)
- `messages`: Conversation history (thread_id, role, content, token_count, created_at)
- `analytics`: Usage metrics (prompt_tokens, completion_tokens, response_time_ms)
- `documents`: RAG knowledge base (content, metadata JSONB, embedding vector(1536), content_search tsvector)

**Indexes**:
- `documents.embedding`: HNSW index for fast vector similarity search
- `documents.content_search`: GIN index for full-text search

### RAG Pipeline Architecture

**Hybrid Search (RRF - Reciprocal Rank Fusion)**:
1. **Vector Search**: pgvector cosine similarity (`<=>` operator)
2. **Keyword Search**: PostgreSQL full-text search (websearch_to_tsquery)
3. **Ranking**: RRF combines results with score = 1/(k + rank), k=60
4. **Language**: Configurable via `TEXT_SEARCH_LANG` (default: portuguese)

**Embedding Service** (`src/rag_service.py`):
- Uses OpenAI `text-embedding-3-small` model
- Batch processing for efficiency
- Tenacity retry logic (3 attempts, exponential backoff)

**Document Processing** (`scripts/ingest_docs.py`):
- Supports: PDF (pypdf), DOCX (python-docx), HTML (beautifulsoup4), TXT/MD
- Chunking: 1000 chars, 200 overlap (configurable)
- Metadata extraction: source file, type, chunk index
- Deduplication via content hash

### Prompt Engineering

**Structure** (rendered by `Prompt.full_render()` in `src/base.py`):
1. System message with bot instructions
2. "Example conversations:" separator
3. All example conversations from `config.yaml`
4. [RAG context if available - wrapped in `<relevant_context>` XML tags]
5. "Now, you will work with the actual current conversation." separator
6. Actual conversation messages (alternating user/assistant roles)

**Prompt Caching** (provider-specific):
- **Anthropic**: Uses `cache_control: {"type": "ephemeral"}` on static parts
- **Gemini**: Structured content format (no explicit cache_control)
- **OpenAI/Others**: Plain text concatenation

**Bot Personality**: Configured via `src/config.yaml`:
- `name`: Bot display name
- `instructions`: System prompt defining behavior
- `example_conversations`: Few-shot examples for consistent responses

### Response Caching

**LRU Cache** (`src/cache.py`):
- In-memory cache with TTL (default: 3600s)
- Hash key includes: last 5 messages + model + temperature + max_tokens
- Thread-safe with locks
- Stats tracking: hits, misses, evictions, expirations
- Max size: configurable via `CACHE_MAX_SIZE` (default: 100)

### OpenRouter-Specific Behavior

- Base URL must be `https://openrouter.ai/api/v1`
- API key format: `sk-or-v1-...`
- Custom headers required:
  - `HTTP-Referer`: `https://github.com/prof-ramos/sherlock-discord-bot`
  - `X-Title`: `Discord Bot Client`
- No `/moderations` endpoint available (unlike OpenAI)
- Models prefixed by provider (e.g., `openai/gpt-4o`, `anthropic/claude-3-opus`)

### Error Handling & Edge Cases

**CompletionResult States**:
- `OK`: Success, send response
- `TOO_LONG`: Auto-close thread (context limit exceeded)
- `INVALID_REQUEST`: Show error in thread, keep open
- `RATE_LIMIT`: Show rate limit message with retry suggestion
- `OTHER_ERROR`: Generic error handling

**Staleness Prevention**:
- `SECONDS_DELAY_RECEIVING_MSG` (3s) delay before processing
- Check if newer user message exists after delay
- Check again before sending response
- Prevents race conditions and duplicate responses

**Thread Lifecycle**:
- Active threads: `💬✅` prefix
- Closed threads: `💬❌` prefix (changed via `close_thread()`)
- Threads auto-archive after 60 minutes of inactivity
- Bot ignores archived/locked threads

### Moderation System

**Flow** (`src/moderation.py`):
1. `moderate_message()`: Checks content (currently returns empty strings - disabled)
2. `send_moderation_flagged_message()`: Logs to moderation channel
3. `send_moderation_blocked_message()`: Logs blocked content
4. Blocked messages deleted if bot has `Manage Messages` permission

**Configuration**:
- `SERVER_TO_MODERATION_CHANNEL`: Format `server_id:channel_id`
- Moderation channels receive notifications for flagged/blocked content

### Performance Profiling

**Timed Decorator** (`src/profiling.py`):
- `@timed` decorator on key functions
- Tracks execution time, call count, min/max/avg
- Logged on bot shutdown via `close()` in `main.py`
- Use for benchmarking completion, database queries, RAG queries

## Important Implementation Notes

### Discord Thread Management

- Only respond to threads owned by bot (`thread.owner_id == client.user.id`)
- Threads must start with `ACTIVATE_THREAD_PREFIX` (`💬✅`)
- Check thread isn't archived/locked before processing
- Message count tracked via `thread.message_count`
- History fetched with `OPTIMIZED_HISTORY_LIMIT` (min of configured limit and MAX_THREAD_MESSAGES)

### Message Processing Order

1. **Allowlist Check**: `should_block()` validates guild is in `ALLOWED_SERVER_IDS`
2. **Staleness Delay**: Wait 3s to batch rapid user messages
3. **History Fetch**: Retrieve thread history (Discord API) or database (mentions)
4. **RAG Query**: Extract last user message, query knowledge base
5. **Completion**: Generate response with RAG context
6. **Staleness Recheck**: Ensure no newer messages before sending
7. **Response Send**: Split into chunks if > `MAX_CHARS_PER_REPLY_MSG` (1500)

### Bot Personality Injection

- `BOT_NAME` from config.yaml is replaced with actual Discord username
- `example_conversations` dynamically updated in `SherlockRamosBot.example_conversations` property
- Cached to avoid rebuilding on every request

### Database Connection Management

- Connection pool created lazily on first use
- Pool config: min_size=1, max_size=5, command_timeout=30s
- Neon serverless: connections recycle after 300s (`max_inactive_connection_lifetime`)
- All database methods call `await self.connect()` first

### RAG Context Injection

- RAG runs on every message with the **last user message** as query
- Returns top 5 documents by default
- Results wrapped in XML: `<relevant_context><doc index='1'>content</doc>...</relevant_context>`
- Injected between examples and current conversation
- HTML-escaped to prevent injection attacks
- Failures logged but don't block LLM call (degrades gracefully)

## Testing Strategy

**Unit Tests** (`tests/unit/`):
- Mock external dependencies (Discord API, OpenRouter, database)
- Focus on business logic isolation
- Run fast, no network/database required

**Integration Tests** (`tests/integration/`):
- Require real PostgreSQL database (uses `DATABASE_URL` env var)
- Test database operations, RAG pipeline
- GitHub Actions provides PostgreSQL service container

**Test Execution**:
- Both test suites run in CI on Python 3.10, 3.11, 3.12
- Coverage reports uploaded to Codecov
- Integration tests use `--cov-append` to merge coverage with unit tests

## GitHub Actions Workflows

### Ingest Documents (`ingest-docs.yml`)

Manual workflow to ingest documents using Neon branching:

```bash
gh workflow run ingest-docs.yml -f file_path=data/documento.pdf
```

**Process**:
1. Creates temporary Neon branch (`ingest-{run_id}`)
2. Runs `scripts/ingest_docs.py` on branch
3. Runs `scripts/verify_ingestion.py` for validation
4. Displays branch info for manual review/merge

**Required Secrets**:
- `NEON_PROJECT_ID`: Neon project ID
- `NEON_API_KEY`: Neon API key
- `NEON_DATABASE_USERNAME`: Database username
- `OPENAI_API_KEY`: For embeddings

### Test Pipeline (`test.yml`)

Runs on push/PR to main/develop:
- Matrix: Python 3.10, 3.11, 3.12
- PostgreSQL service container for integration tests
- Coverage upload to Codecov

## Common Gotchas

### Discord Permissions

Bot invite URL requires these permissions (328565073920):
- Send Messages, Send Messages in Threads
- Create Public Threads, Manage Threads
- Manage Messages (for moderation)
- Read Message History
- Use Slash Commands

**Message Content Intent** must be enabled in Discord Developer Portal.

### Model Selection

Available models defined in `src/constants.py` as `Literal` type for type safety. Add new models to `AVAILABLE_MODELS` literal and update type hints.

### Thread State Persistence

Thread configs stored in database, but if bot restarts:
- Thread entry persists in database
- Bot can still respond (retrieves config from DB)
- If thread not in DB, uses default config from constants

### RAG Performance

- HNSW index requires sufficient data for optimal performance (>1000 documents)
- Hybrid search (vector + keyword) more robust than pure vector search
- Portuguese text search requires `TEXT_SEARCH_LANG=portuguese`
- Metadata filtering uses JSONB operators (`metadata->>'key'`)

### Prompt Caching Gotchas

- Only works with Anthropic and Gemini models
- Static parts (instructions + examples) must be identical across requests
- Cache TTL controlled by provider (typically 5 minutes)
- Cache miss when dynamic parts (RAG context) change

### Environment Variables

The bot fails fast if critical variables missing:
- `OPENROUTER_API_KEY`: Required, raises error
- `DISCORD_BOT_TOKEN`: Required, raises error
- `DATABASE_URL`: Required, raises RuntimeError
- `OPENAI_API_KEY`: Optional, disables RAG if missing

### Logging Levels

- `discord`: INFO (connection events, API calls)
- `httpx`, `httpcore`: WARNING (reduce noise from HTTP libraries)
- Default: INFO
- Use structured logging with `extra` dict for context (user_id, thread_id, etc.)
