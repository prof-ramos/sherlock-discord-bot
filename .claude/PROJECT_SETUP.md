# SherlockRamosBot - Claude Code Setup Guide

This guide helps Claude Code work effectively with this Discord bot project.

## Project Type: Python Discord Bot

- **Package Manager**: `uv` (NOT npm/yarn)
- **Dependencies**: Defined in `pyproject.toml` (NOT package.json)
- **Python Version**: 3.9+ (specified in `.python-version`)
- **Framework**: discord.py 2.x with Cogs architecture

## Quick Reference Commands

### Development Workflow
```bash
# 1. Lint and format code
uv run ruff check . --fix
uv run ruff format .

# 2. Type checking
uv run mypy src

# 3. Run tests
uv run pytest -v

# 4. Run bot locally
uv run sherlock-bot
```

### Database Operations
```bash
# Initialize schema
uv run python scripts/init_db.py

# Verify connection
uv run python scripts/verify_db.py

# Ingest RAG documents
uv run python scripts/ingest_docs.py path/to/doc.pdf
```

## Available Claude Code Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| `/lint` | Ruff linting & formatting | Code quality checks |
| `/test` | Run pytest suite | Unit + integration tests |
| `/run-bot` | Start Discord bot | Local development |
| `/rag-pipeline` | Manage RAG documents | Document ingestion |
| `/code-review` | Comprehensive code review | Before PR/commit |
| `/architecture-review` | Architecture analysis | Design decisions |

## Project-Specific Context

### Architecture Highlights
- **Cog-based** Discord commands (not traditional commands)
- **Two conversation modes**: Thread mode (`/chat`) + Mention mode
- **RAG pipeline**: Hybrid search (vector + full-text) with pgvector
- **Multi-LLM**: OpenRouter routing to GPT-4, Claude, Gemini, LLaMA
- **Prompt caching**: Anthropic/Gemini cache_control for cost optimization

### Critical Files
```
src/
├── main.py              # Bot entry point, cog loading
├── cogs/
│   └── chat.py         # /chat command + message handler
├── database_service.py # Neon PostgreSQL operations
├── rag_service.py      # RAG hybrid search
├── completion.py       # LLM API calls
├── base.py             # Prompt rendering
└── config.yaml         # Bot personality

scripts/
├── ingest_docs.py      # RAG document ingestion
├── init_db.py          # Database schema setup
└── verify_*.py         # Verification utilities
```

### Environment Variables (Required)
```bash
OPENROUTER_API_KEY      # OpenRouter API (sk-or-v1-...)
DISCORD_BOT_TOKEN       # Discord bot token
DATABASE_URL            # Neon PostgreSQL connection
OPENAI_API_KEY          # For RAG embeddings
ALLOWED_SERVER_IDS      # Comma-separated Discord server IDs
```

## Neon Database Status Line

The custom status line shows:
- 🟢 Active / 🟡 Sleeping database status
- 💾 Storage usage
- 🟢/🟡/🔴 Compute hours usage
- 💰 Estimated monthly cost
- 📈 Recent write activity

## Common Workflows

### Adding a New Feature
1. Read CLAUDE.md for architecture context
2. Use `/architecture-review` to plan approach
3. Use `python-pro` agent for implementation
4. Write tests with `test-engineer` agent
5. Run `/lint` and `/test` before committing
6. Use `/code-review` for final review

### Debugging Issues
1. Use `error-detective` agent for log analysis
2. Check Discord bot logs for errors
3. Verify database connection with `scripts/verify_db.py`
4. Test RAG separately with `scripts/test_rag_e2e.py`

### Database Schema Changes
1. Use `neon-database-architect` agent for design
2. Update `scripts/init_db.py` or create migration
3. Test on Neon branch before merging
4. Update integration tests

### RAG Improvements
1. Use `ai-engineer` agent for RAG optimization
2. Use `prompt-engineer` for prompt tuning
3. Test with `scripts/test_rag_e2e.py`
4. Monitor search quality in production logs

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Mock Discord API, OpenRouter API, database
- Fast execution, no external dependencies
- Run frequently during development

### Integration Tests (`tests/integration/`)
- Require real Neon PostgreSQL database
- Test database operations, RAG pipeline
- Run before pushing to remote

```bash
# Quick test (unit only)
uv run pytest tests/unit -v

# Full test suite
uv run pytest -v
```

## CI/CD Pipeline

GitHub Actions runs on push/PR:
1. **Test Matrix**: Python 3.10, 3.11, 3.12
2. **PostgreSQL Service**: For integration tests
3. **Coverage Upload**: To Codecov

Manual workflow for RAG ingestion:
```bash
gh workflow run ingest-docs.yml -f file_path=data/doc.pdf
```

## Relevant Agents for This Project

**Primary Agents** (use proactively):
- `python-pro` - Python code excellence
- `neon-database-architect` - Database optimization
- `ai-engineer` - RAG and LLM integration
- `test-engineer` - Pytest and testing
- `prompt-engineer` - Bot personality tuning

**Secondary Agents** (use as needed):
- `security-auditor` - Token/API key security
- `error-detective` - Debugging and logs
- `backend-architect` - Architecture decisions
- `code-review` - Code quality review

See `.claude/AGENTS_REVIEW.md` for full agent analysis.

## Important Notes

### What NOT to Assume
- ❌ This is NOT a Node.js/JavaScript project
- ❌ This is NOT using Express/FastAPI (it's a Discord bot)
- ❌ This does NOT use Docker/Kubernetes (serverless Neon)
- ❌ This does NOT have a REST API to document

### What IS True
- ✅ Python 3.9+ with `uv` package manager
- ✅ Discord.py 2.x with Cogs architecture
- ✅ Neon serverless PostgreSQL with pgvector
- ✅ OpenRouter for multi-LLM routing
- ✅ Hybrid RAG with vector + full-text search
- ✅ GitHub Actions CI with pytest

## Troubleshooting Common Issues

**"ModuleNotFoundError"**
```bash
# Ensure dependencies installed
uv sync
```

**"Database connection failed"**
```bash
# Check DATABASE_URL in .env
# Verify Neon compute is active (may be sleeping)
uv run python scripts/verify_db.py
```

**"Bot not responding to commands"**
```bash
# Verify Message Content Intent enabled in Discord Portal
# Check ALLOWED_SERVER_IDS matches your test server
# Commands sync on startup (wait 1-5 minutes)
```

**"RAG returns no results"**
```bash
# Verify documents ingested
uv run python scripts/verify_ingestion.py

# Check OPENAI_API_KEY set correctly
echo $OPENAI_API_KEY
```

## Additional Resources

- **CLAUDE.md**: Comprehensive project documentation
- **README.md**: User-facing setup instructions
- **pyproject.toml**: All dependencies and tool configurations
- **.github/workflows/**: CI/CD pipeline definitions
