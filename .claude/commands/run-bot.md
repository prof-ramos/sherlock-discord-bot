# Run Discord Bot

Start the SherlockRamosBot Discord chatbot locally.

## Purpose

This command starts the Discord bot with proper environment configuration.

## Usage

```
/run-bot
```

## Commands

### Start Bot (Recommended)
```bash
# Using the configured entry point
uv run sherlock-bot
```

### Alternative Methods
```bash
# Direct module execution
uv run python -m src.main

# With specific Python version
uv run --python 3.11 sherlock-bot
```

### Development Mode
```bash
# With debug logging
DISCORD_LOG_LEVEL=DEBUG uv run sherlock-bot

# With specific model override
DEFAULT_MODEL="anthropic/claude-3.5-sonnet" uv run sherlock-bot
```

## Prerequisites

1. **Environment Variables** (in `.env`):
   ```bash
   # Required
   OPENROUTER_API_KEY=sk-or-v1-...
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   DISCORD_BOT_TOKEN=your_discord_bot_token
   DISCORD_CLIENT_ID=your_client_id
   ALLOWED_SERVER_IDS=server1,server2
   DATABASE_URL=postgresql://...
   OPENAI_API_KEY=sk-...  # For RAG embeddings

   # Optional
   DEFAULT_MODEL=openai/gpt-4o
   ```

2. **Database Setup**:
   ```bash
   # Initialize database schema
   uv run python scripts/init_db.py

   # Verify database connection
   uv run python scripts/verify_db.py
   ```

3. **Discord Permissions**:
   - Message Content Intent enabled in Discord Developer Portal
   - Bot invited with permissions: 328565073920
     - Send Messages, Send Messages in Threads
     - Create Public Threads, Manage Threads
     - Manage Messages, Read Message History
     - Use Slash Commands

## Verifying Bot is Running

```bash
# You should see output like:
# INFO:discord.client:Logged in as SherlockRamosBot#1234
# INFO:discord.gateway:Shard ID None has connected to Gateway
# INFO:sherlock_bot:Bot is ready! Guilds: 2
```

## Troubleshooting

**Bot fails to start:**
```bash
# Check environment variables
cat .env | grep -E "DISCORD|OPENROUTER|DATABASE"

# Verify database connection
uv run python scripts/verify_db.py
```

**Commands not syncing:**
```bash
# Commands sync automatically on startup to ALLOWED_SERVER_IDS
# Wait 1-5 minutes for Discord to propagate commands
# Try in a different channel if not appearing
```

**RAG not working:**
```bash
# Verify OpenAI API key is set
echo $OPENAI_API_KEY

# Ingest test document
uv run python scripts/ingest_docs.py data/test_doc.txt

# Verify ingestion
uv run python scripts/verify_ingestion.py
```

## Stopping the Bot

- Press `Ctrl+C` to gracefully shut down
- Bot will log profiling stats on shutdown
