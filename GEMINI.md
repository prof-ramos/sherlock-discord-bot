# Gemini Code Assistant Context: SherlockRamosBot

## 📂 Project Overview

**SherlockRamosBot** is a Python-based Discord chatbot designed for Brazilian law students. It
leverages LLMs via OpenRouter and implements RAG (Retrieval-Augmented Generation) for specialized
legal assistance.

## 🛠️ Technology Stack

- **Core**: Python 3.13+ (managed via `uv`)
- **Discord**: `discord.py`
- **LLM API**: OpenRouter (Unified access to Claude, GPT-4o, Gemini, etc.)
- **Persistence**: Neon (Serverless PostgreSQL)
- **Vector DB**: ChromaDB (for RAG capabilities)
- **Quality**: `ruff` (formatting/linting), `mypy` (type checking), `pytest` (testing)

## 🏗️ Core Architecture

- `src/main.py`: Bot initialization and Discord command/event registration.
- `src/completion.py`: LLM logic, prompt engineering, and response handling.
- `src/database.py`: Neon & ChromaDB interaction logic.
- `src/config.yaml`: Bot persona, instructions, and few-shot examples.
- `pyproject.toml`: Dependencies and tool configurations.
- `scripts/`: Utilities for data ingestion and database setup.

## 💻 Development Workflow

- **Environment**: Always use `uv sync` to manage dependencies.
- **Execution**: Run via `uv run sherlock-bot` or `uv run python -m src.main`.
- **Quality**: Run `uv run ruff check . --fix` and `uv run pytest` before committing.
- **Commits**: Follow conventional commit standards.

> Refer to `README.md` for full installation/user guides and `AGENTS.md` for detailed internal
> patterns.
