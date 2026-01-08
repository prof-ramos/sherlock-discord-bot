# AGENTS.md

Development guidelines for agentic coding agents working on the SherlockRamosBot Discord chatbot.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Development Commands](#development-commands)
3. [Code Style Guidelines](#code-style-guidelines)
4. [Architecture Guidelines](#architecture-guidelines)
5. [Development Workflow](#development-workflow)
6. [Bot Personality Guidelines](#bot-personality-guidelines)
7. [Security & Permissions](#security--permissions)
8. [Testing Guidelines](#testing-guidelines)
9. [Performance Considerations](#performance-considerations)
10. [Deployment Notes](#deployment-notes)
11. [Extending the Bot](#extending-the-bot)
12. [Common Gotchas & Implementation Notes](#common-gotchas--implementation-notes)

## Project Overview

SherlockRamosBot is a Discord chatbot for Brazilian law students (concurseiros) that uses OpenRouter to access multiple LLM models (GPT-4, Claude, Gemini, LLaMA). It features RAG with Neon PostgreSQL/pgvector, persistent conversation history, and prompt caching for cost optimization. The bot maintains contextual conversations in Discord threads and is designed for answering legal questions in Portuguese.

## Development Commands

### Running the Bot

```bash
# Recommended
uv run sherlock-bot

# Alternative
uv run python -m src.main

# Install dependencies
uv sync
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

## Code Style Guidelines

### Import Organization

**Order**: Standard library → Third-party → Local imports

```python
# Standard library
from collections import defaultdict
from typing import Optional, List
import os
import asyncio

# Third-party
import discord
from discord import Message as DiscordMessage, app_commands
import yaml
import dacite

# Local imports
from src.base import Message, Conversation, ThreadConfig
from src.constants import BOT_NAME, DEFAULT_MODEL
from src.utils import logger, should_block
```

### Type Hints Requirements

- **Mandatory**: All functions must have type hints for parameters and return values
- **Use Optional** for nullable values: `Optional[str]`
- **Use Literal** for string constants: `Literal["openai/gpt-3.5-turbo", "anthropic/claude-3-opus"]`
- **Use Final** for constants: `Final[str]`, `Final[List[int]]`
- **Prefer specific types** over generics when possible

### Naming Conventions

- **Variables/Functions**: `snake_case`
- **Classes/Enums**: `PascalCase`
- **Constants**: `UPPER_CASE_WITH_UNDERSCORES`
- **Descriptive names**: `discord_message_to_message` (not `convert_msg`)
- **Consistent prefixes**: `BOT_`, `SERVER_TO_`, `MY_BOT_`

### Error Handling Patterns

```python
# Use custom exception hierarchy from src.exceptions
from src.exceptions import SherlockBotError, ConfigError, OpenRouterError

# Structured error handling with specific catches
try:
    result = await some_operation()
except OpenRouterError as e:
    logger.exception("OpenRouter API error")
    await send_error_message(ctx, f"API Error: {e}")
except ConfigError as e:
    logger.exception("Configuration error")
    await send_error_message(ctx, f"Configuration Error: {e}")
except Exception as e:
    logger.exception("Unexpected error")
    await send_error_message(ctx, "An unexpected error occurred")
```

### Async/Await Patterns

- **All Discord operations must be async**
- **Use proper async context managers**: `async with thread.typing():`
- **Chain async calls properly**: `result = await func1(await func2())`
- **Handle async errors with try/except blocks**

### Discord.py Specific Patterns

```python
# Type aliases for Discord objects
from discord import Message as DiscordMessage, Guild as DiscordGuild

# Command decorators with permission checks
@tree.command(
    name="chat",
    description="Inicia uma conversa com o bot",
    guild=discord.Object(id=guild_id)
)
@app_commands.describe(message="Sua pergunta ou dúvida")
async def chat_command(
    interaction: discord.Interaction,
    message: str,
    temperature: Optional[float] = 1.0
) -> None:
    # Implementation
```

### Data Structures

```python
# Use dataclasses for structured data
@dataclass(frozen=True)
class Message:
    user: str
    text: Optional[str] = None

# Use enums for status codes and constants
class CompletionResult(Enum):
    SUCCESS = "success"
    TOO_LONG = "too_long"
    INVALID_REQUEST = "invalid_request"
    OTHER_ERROR = "other_error"
```

### Configuration Management

- **Environment variables**: Use `get_env()` from `src.constants`
- **YAML config**: Bot personality in `src/config.yaml`
- **Type-safe config**: Use dacite with dataclasses for YAML parsing
- **Validation**: Raise `ConfigError` for missing required variables

### Logging Patterns

```python
# Use logger from src.utils
from src.utils import logger

# Structured logging with context
logger.info("Processing message", extra={
    "user_id": interaction.user.id,
    "channel_id": interaction.channel.id,
    "message_length": len(message)
})

# Exception logging with full traceback
logger.exception("Error processing completion")
```

### Documentation Standards

- **Docstrings**: All public functions must have docstrings
- **Type hints**: Serve as documentation - make them descriptive
- **Inline comments**: Use for complex logic, especially Portuguese legal concepts
- **TODO markers**: Use for future improvements with specific context

### File Organization

```
src/
├── main.py          # Entry point, Discord events, slash commands
├── base.py          # Core data structures (Message, Conversation, etc.)
├── completion.py    # LLM API interaction and response handling
├── constants.py     # Configuration loading, environment variables
├── utils.py         # Helper utilities, Discord operations
├── moderation.py    # Content moderation (currently disabled)
├── exceptions.py    # Custom exception hierarchy
└── config.yaml      # Bot personality and example conversations
```

## Architecture Guidelines

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

### OpenRouter Integration

- Base URL must be `https://openrouter.ai/api/v1`
- API key format: `sk-or-v1-...`
- Custom headers required:
  - `HTTP-Referer`: `https://github.com/prof-ramos/sherlock-discord-bot`
  - `X-Title`: `Discord Bot Client`
- No `/moderations` endpoint available (unlike OpenAI)
- Models prefixed by provider (e.g., `openai/gpt-4o`, `anthropic/claude-3-opus`)

### Error Recovery

- **Graceful degradation**: Always provide user-friendly error messages
- **Thread state**: Don't leave threads in broken state
- **Retry logic**: Implement for transient API errors
- **Logging**: Log all errors with context for debugging

### Thread-Based Conversations

- **Create threads** for each conversation via `/chat` command
- **Maintain context** using database storage with `ThreadConfig`
- **Message limits**: Respect `MAX_THREAD_MESSAGES` (200) and token limits
- **Thread lifecycle**: Use `ACTIVATE_THREAD_PREFIX` (💬✅) and `INACTIVATE_THREAD_PREFIX` (💬❌)

## Development Workflow

### Environment Setup

1. Copy `.env.example` to `.env` and configure variables
2. Run `uv sync` to install dependencies
3. Ensure Python 3.13+ is installed
4. Configure Discord bot with proper intents (Message Content Intent required)

### Making Changes

1. **Understand existing patterns** before modifying code
2. **Follow type hints** and error handling patterns
3. **Test Discord interactions** carefully (threads, permissions)
4. **Update configuration** if adding new models or features
5. **Log changes** appropriately for debugging

### Common Pitfalls

- **Missing Message Content Intent**: Bot won't receive message content
- **Thread state loss on restart**: `thread_data` is in-memory only
- **OpenRouter headers**: Required for API requests
- **Server allowlist**: Only `ALLOWED_SERVER_IDS` can use bot
- **Async context**: All Discord operations must be async

## Bot Personality Guidelines

### Legal Focus

- **Brazilian law**: Specialize in Brazilian legal topics
- **Concurseiros**: Target audience studying for public exams
- **Portuguese language**: All responses in Portuguese
- **Professional tone**: Maintain helpful, educational tone

### Response Patterns

- **Structured answers**: Use clear organization for legal concepts
- **Examples provided**: Include practical examples when helpful
- **Citations**: Reference laws, articles, and jurisprudence when applicable
- **Study focus**: Emphasize exam-relevant information

## Security & Permissions

### Required Discord Permissions

- Send Messages
- Send Messages in Threads
- Create Public Threads
- Manage Messages (moderation)
- Manage Threads
- Read Message History
- Use Slash Commands

### Security Considerations

- **Server allowlist**: Enforce `ALLOWED_SERVER_IDS`
- **API key security**: Never commit API keys to repository
- **Input validation**: Validate user inputs appropriately
- **Rate limiting**: Respect API rate limits

## Testing Guidelines (Future)

### When Adding Tests

- **Use pytest**: Framework of choice for Python testing
- **Mock Discord**: Use pytest-discord or similar for Discord.py testing
- **Test async functions**: Use pytest-asyncio for async test functions
- **Configuration testing**: Test config loading and validation
- **Error scenarios**: Test error handling and recovery

### Test Structure

```
tests/
├── test_main.py           # Discord event handlers
├── test_completion.py     # OpenRouter API integration
├── test_base.py          # Data structures
├── test_constants.py     # Configuration loading
├── test_utils.py         # Helper utilities
└── conftest.py           # Test fixtures and configuration
```

## Performance Considerations

### Memory Management

- **Thread limits**: Respect `MAX_THREAD_MESSAGES` to prevent memory bloat
- **Generator patterns**: Use generators for large data processing
- **Context cleanup**: Clean up thread data when threads close

### API Optimization

- **Batch operations**: Batch Discord operations when possible
- **Caching**: Cache frequently accessed configuration
- **Rate limiting**: Implement appropriate rate limiting for API calls

## Deployment Notes

### Environment Variables

- **Required**: `OPENROUTER_API_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_CLIENT_ID`
- **Optional**: `ALLOWED_SERVER_IDS`, `SERVER_TO_MODERATION_CHANNEL`, `DEFAULT_MODEL`
- **Validation**: Use `get_env()` with `required=True` for critical variables

### Production Considerations

- **Logging**: Configure appropriate log levels for production
- **Error monitoring**: Consider adding error monitoring service
- **Resource limits**: Monitor memory and API usage
- **Backup strategy**: Thread state is lost on restart

## Extending the Bot

### Adding a New Slash Command

To add a new slash command, define it in `src/main.py`:

```python
@tree.command(
    name="jurisprudencia",
    description="Busca jurisprudência no banco de dados",
    guild=discord.Object(id=guild_id)
)
@app_commands.describe(termo="Termo para busca")
async def jurisprudencia_command(interaction: discord.Interaction, termo: str):
    await interaction.response.defer()
    # Lógica de busca...
    results = await search_jurisprudence(termo)
    await interaction.followup.send(f"Resultados para {termo}: ...")
```

### Adding a New RAG Source

To ingest a new type of document, create a handler in `scripts/ingest_docs.py`:

```python
def extract_text_from_html(file_path: Path) -> str:
    # Use BeautifulSoup or similar
    ...
```
