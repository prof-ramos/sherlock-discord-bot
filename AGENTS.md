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
8. [Testing Guidelines](#testing-guidelines-future)
9. [Performance Considerations](#performance-considerations)
10. [Deployment Notes](#deployment-notes)
11. [Extending the Bot](#extending-the-bot)

## Project Overview

SherlockRamosBot is a Python Discord chatbot for Brazilian law students (concurseiros) that uses
OpenRouter API to provide access to multiple LLM models. The bot maintains contextual conversations
in Discord threads and is designed for answering legal questions in Portuguese.

## Development Commands

### Running the Bot

```bash
# Recommended way (uses uv package manager)
uv run sherlock-bot

# Alternative (direct module execution)
uv run python -m src.main

# Install dependencies
uv sync
```

### Testing

```bash
# No test framework currently configured
# When adding tests, use: uv run pytest
# Run single test: uv run pytest tests/test_file.py::test_function
```

### Code Quality (TO BE ADDED)

```bash
# Code formatting (when configured)
uv run black src/
uv run ruff format src/

# Linting (when configured)
uv run ruff check src/
uv run flake8 src/

# Type checking (when configured)
uv run pyright src/
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

### Thread-Based Conversations

- **Create threads** for each conversation via `/chat` command
- **Maintain context** using `thread_data` defaultdict with `ThreadConfig`
- **Message limits**: Respect `MAX_THREAD_MESSAGES` (200) and token limits
- **Thread lifecycle**: Use `ACTIVATE_THREAD_PREFIX` (💬✅) and `INACTIVATE_THREAD_PREFIX` (💬❌)

### OpenRouter Integration

- **Base URL**: Must be `https://openrouter.ai/api/v1`
- **API key format**: `sk-or-v1-...`
- **Custom headers**: Required `HTTP-Referer` and `X-Title`
- **Model selection**: Use `AVAILABLE_MODELS` literal type for type safety

### Error Recovery

- **Graceful degradation**: Always provide user-friendly error messages
- **Thread state**: Don't leave threads in broken state
- **Retry logic**: Implement for transient API errors
- **Logging**: Log all errors with context for debugging

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
