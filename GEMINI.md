# Gemini Context: SherlockRamosBot 🕵️‍♂️⚖️

This file defines the project context, architectural decisions, and development guidelines for the **SherlockRamosBot** project.

## 📂 Project Overview

**SherlockRamosBot** is a specialized Discord chatbot for Brazilian law students ("concurseiros"). It operates in two modes:
1.  **General Mode**: Casual conversation.
2.  **Juridical Mode**: High-precision legal assistance using RAG (Retrieval-Augmented Generation) with Brazilian laws and jurisprudence.

## 🛠️ Technology Stack & Decisions

- **Language**: Python 3.13+
- **Package Manager**: `uv` (Fast, reliable, rust-based).
- **Framework**: `discord.py` (CommandTree/Slash Commands).
- **LLM Provider**: OpenRouter (Access to Gemini 2.0 Flash, GPT-4o, Claude 3.5).
- **Database (Relational)**: Neon (Serverless PostgreSQL) via `asyncpg`.
- **Database (Vector)**: ChromaDB (Local persistence in `src/data/chroma_db`).
- **Embeddings**: `sentence-transformers` (paraphrase-multilingual).
- **Linting/Formatting**: `ruff`.
- **Type Checking**: `mypy`.
- **Testing**: `pytest`.

## 🏗️ Architecture & Key Files

### Core Components
- **`src/main.py`**: Entry point. Loads extensions and connects to DB.
- **`src/cogs/chat.py`**: Handles Discord interaction (slash commands, events, threads).
- **`src/completion.py`**: The "Brain". Handles RAG retrieval, prompt assembly, and OpenRouter API calls.
- **`src/database.py`**: Handles PostgreSQL connections and ChromaDB querying.
- **`src/base.py`**: Data classes (`Message`, `ThreadConfig`).
- **`src/config.yaml`**: **CRITICAL**. Contains the system prompt, persona definitions, and few-shot examples.

### Data & Scripts
- **`scripts/init_db.py`**: Initializes PostgreSQL schema.
- **`scripts/ingest_docs.py`**: Scrapes/Reads legal documents and populates ChromaDB.
- **`src/data/chroma_db/`**: Persistent storage for vector embeddings.

## 🧠 Database Schema (Simplified)

- **`threads`**: Stores thread configuration (`model`, `temperature`) per Discord thread.
- **`messages`**: Log of all interactions (`role`, `content`, `tokens`).
- **`analytics`**: Performance metrics (`response_time`, `token_usage`).

## 📏 Development Guidelines

### 1. Language & Locale
- **Code/Comments**: English.
- **Bot Output/User Interaction**: **Portuguese (PT-BR)**.
- **Legal Citations**: Must follow Brazilian standards (e.g., "Art. 5º, CF/88").

### 2. Code Quality
- **Type Hinting**: Mandatory for all function arguments and return values.
- **Async/Await**: Use `async` for all I/O bound operations (DB, API, Discord).
- **Error Handling**: Use `try/except` blocks in Cogs to prevent bot crashes. Log errors via `src.utils.logger`.

### 3. Workflow
1.  **Sync Env**: `uv sync`
2.  **Lint/Fix**: `uv run ruff check . --fix`
3.  **Test**: `uv run pytest`
4.  **Run**: `uv run sherlock-bot`

## 🤖 Agent Instructions (for AI)

When working on this codebase:
- **Check `src/config.yaml`** before modifying bot personality.
- **Check `scripts/`** before writing new data processing tools; one likely exists.
- **Respect `pyproject.toml`**: Do not add dependencies manually without `uv add`.
- **RAG Awareness**: If the user asks about "Bot Knowledge", refer to the documents ingested via ChromaDB.