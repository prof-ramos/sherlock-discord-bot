# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

SherlockRamosBot is a Discord chatbot designed for Brazilian law students (concurseiros). It uses
OpenRouter API to provide access to multiple LLM models (GPT-4, Claude, Gemini, LLaMA) for answering
legal questions in Portuguese.

## Development Commands

### Running the Bot

```bash
# Recommended way
uv run sherlock-bot

# Alternative (direct module)
uv run python -m src.main
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Setup

Copy `.env.example` to `.env` and configure:

- `OPENROUTER_API_KEY`: OpenRouter API key (sk-or-v1-...)
- `OPENROUTER_BASE_URL`: Must be `https://openrouter.ai/api/v1`
- `DISCORD_BOT_TOKEN`: Discord bot token
- `DISCORD_CLIENT_ID`: Discord application client ID
- `ALLOWED_SERVER_IDS`: Comma-separated server IDs
- `SERVER_TO_MODERATION_CHANNEL`: Format `server_id:channel_id`
- `DEFAULT_MODEL`: One of the available models (see `src/constants.py`)

## Architecture

### Core Flow: Thread-Based Conversations

The bot creates **Discord threads** for each conversation initiated via `/chat`:

1. User runs `/chat message:"question"` in a text channel
2. Bot creates a public thread with prefix `💬✅`
3. Thread maintains conversation context automatically
4. Thread closes when reaching `MAX_THREAD_MESSAGES` (200) or context limit

### Key Components

**[src/main.py](src/main.py)**: Entry point and Discord event handlers

- `chat_command()`: Slash command that creates threads and initiates conversations
- `on_message()`: Processes messages within bot-owned threads
- Uses `thread_data` dict to store `ThreadConfig` per thread ID
- Implements message staleness checks to avoid processing outdated messages

**[src/completion.py](src/completion.py)**: LLM interaction via OpenRouter

- `generate_completion_response()`: Builds prompt and calls OpenRouter API
- `process_response()`: Handles different completion statuses and sends Discord messages
- Uses AsyncOpenAI client with custom base URL
- Note: API-based moderation is disabled (OpenRouter doesn't support `/moderations` endpoint)

**[src/base.py](src/base.py)**: Core data structures

- `Message`, `Conversation`: Represent chat history
- `Prompt`: Constructs system prompt with examples and converts to OpenAI format
- `ThreadConfig`: Per-thread settings (model, temperature, max_tokens)
- Uses `<|endoftext|>` as separator token

**[src/constants.py](src/constants.py)**: Configuration loading

- Loads `config.yaml` for bot personality and example conversations
- Parses environment variables
- Defines `AVAILABLE_MODELS` as Literal type for type safety
- Creates bot invite URL with required permissions

**[src/moderation.py](src/moderation.py)**: Content moderation (currently disabled)

- `moderate_message()`: Returns empty strings (no moderation active)
- Moderation channel notifications for flagged/blocked content
- Note: OpenRouter applies native filtering on many models

**[src/utils.py](src/utils.py)**: Helper utilities

- `discord_message_to_message()`: Converts Discord messages to internal format
- `split_into_shorter_messages()`: Chunks responses to fit Discord's 2k character limit
- `is_last_message_stale()`: Prevents race conditions from multiple user messages
- `should_block()`: Server allowlist enforcement
- `close_thread()`: Marks threads as closed when context limit reached

### Configuration System

**[src/config.yaml](src/config.yaml)**: Bot personality definition

- `name`: Bot display name
- `instructions`: System prompt defining bot behavior
- `example_conversations`: Few-shot examples for consistent responses

> [!IMPORTANT] > **TODO**: The config currently uses placeholder "Lenard" - must be customized for
> SherlockRamosBot personality!

### Message Flow & Timing

1. User sends message in thread
2. Bot waits `SECONDS_DELAY_RECEIVING_MSG` (3s) to batch multiple user messages
3. Checks if message is stale (newer user message exists)
4. Fetches thread history up to `MAX_THREAD_MESSAGES`
5. Generates completion with thread's saved config
6. Checks staleness again before sending
7. Sends response, chunked if needed (`MAX_CHARS_PER_REPLY_MSG` = 1500)

### Thread State Management

Threads use `defaultdict` in `main.py` to store per-thread configuration:

- Key: `thread.id`
- Value: `ThreadConfig(model, max_tokens, temperature)`
- Config set during `/chat` command, persists for thread lifetime
- No database - state lost on restart (threads become unresponsive)

### Server Allowlist & Moderation

- Only servers in `ALLOWED_SERVER_IDS` can use the bot
- DMs are blocked (`should_block()` in `utils.py`)
- Moderation channels receive notifications (if configured)
- Messages can be deleted if moderation blocks them (requires Manage Messages permission)

## Important Implementation Notes

### OpenRouter-Specific Behavior

- Must set `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- API key format: `sk-or-v1-...`
- Custom headers required: `HTTP-Referer` and `X-Title` (see `extra_headers` in
  `generate_completion_response` function within `src/completion.py`)
- No moderation endpoint available (unlike OpenAI)
- Models prefixed by provider (e.g., `openai/gpt-4o`, `anthropic/claude-3-opus`)

### Discord Thread Lifecycle

- Threads auto-archive after 60 minutes of inactivity
- Archived threads can be unarchived by users
- Bot only responds to threads it created (`thread.owner_id == client.user.id`)
- Thread names start with `ACTIVATE_THREAD_PREFX` (`💬✅`) when active
- Changed to `INACTIVATE_THREAD_PREFIX` (`💬❌`) when closed

### Prompt Engineering

The system constructs prompts in this order (see `Prompt.full_render()` method in `src/base.py`):

1. System message with bot instructions
2. "Example conversations:" separator
3. All example conversations from `config.yaml`
4. "Now, you will work with the actual current conversation." separator
5. Actual conversation messages (alternating user/assistant roles)

### Error Handling

- `CompletionResult.TOO_LONG`: Closes thread automatically
- `CompletionResult.INVALID_REQUEST`: Shows error in thread, keeps thread open
- `CompletionResult.OTHER_ERROR`: Shows generic error
- Empty responses trigger yellow warning embed

## Testing & Debugging

### Bot Permissions Required

Bot invite URL includes these permissions (value: 328565073920):

- Send Messages
- Send Messages in Threads
- Create Public Threads
- Manage Messages (for moderation)
- Manage Threads
- Read Message History
- Use Slash Commands

### Common Issues

1. **Bot doesn't respond**: Check `ALLOWED_SERVER_IDS` includes your server
2. **Message Content Intent**: Must be enabled in Discord Developer Portal
3. **Thread state lost on restart**: `thread_data` dict is in-memory only
4. **Config not updating**: Must restart bot after changing `config.yaml`

## Planned Features (from README)

- **RAG with Supabase**: Vector database for Brazilian legal documents, jurisprudence
- **Flashcards & Quiz System**: Spaced repetition, exam simulation
- **Legislative Updates**: Auto-sync with official sources
- **Gamification**: Points, badges, rankings
