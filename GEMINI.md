# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the SherlockRamosBot project.

## 📂 Project Overview

**SherlockRamosBot** is a sophisticated Discord chatbot designed to assist Brazilian law students and those preparing for civil service exams. It leverages various Large Language Models (LLMs) via the OpenRouter API to answer questions on a wide range of legal topics. The bot is built with Python, using the `discord.py` library for Discord integration, `uv` for package management, and `chromadb` for Retrieval-Augmented Generation (RAG) capabilities.

### Key Technologies

*   **Language:** Python 3.9+
*   **Discord Integration:** `discord.py`
*   **LLM Integration:** `openai` library (via OpenRouter)
*   **Package Management:** `uv`
*   **Vector Database:** `chromadb`
*   **Linting & Formatting:** `ruff`
*   **Type Checking:** `mypy`
*   **Testing:** `pytest`

### Architecture

The project is structured into several key components:

*   `src/main.py`: The main entry point of the application, responsible for initializing the Discord client, handling commands, and managing message events.
*   `src/completion.py`: Handles the logic for generating completions from the LLM, including constructing prompts and processing responses.
*   `src/database.py`: Manages the interaction with the `chromadb` vector store for RAG.
*   `src/config.yaml`: Defines the bot's personality, including the system prompt and few-shot examples.
*   `pyproject.toml`: Defines project dependencies, scripts, and tool configurations.
*   `scripts/`: Contains utility scripts for tasks like database initialization and document ingestion.

## 🚀 Building and Running

### Prerequisites

*   Python 3.9+
*   `uv` package manager
*   Discord Bot Token and other credentials (see `.env.example`)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/prof-ramos/sherlock-discord-bot.git
    cd sherlock-discord-bot
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

### Configuration

1.  **Set up environment variables:**
    ```bash
    cp .env.example .env
    ```
    Then, edit the `.env` file with your Discord and OpenRouter API keys.

2.  **Customize the bot's personality (optional):**
    Edit `src/config.yaml` to change the system prompt and example conversations.

### Running the Bot

*   **Run the bot:**
    ```bash
    uv run python -m src.main
    ```

### Running Tests

*   **Execute the test suite:**
    ```bash
    uv run pytest
    ```

## 💻 Development Conventions

*   **Code Style:** The project uses `ruff` for linting and formatting. The configuration is in `pyproject.toml`.
*   **Type Checking:** `mypy` is used for static type checking, with configuration in `pyproject.toml`.
*   **Testing:** `pytest` is used for testing. Tests are located in the `tests/` directory.
*   **Package Management:** `uv` is the standard for managing dependencies and running scripts. Always use `uv sync` to install dependencies and `uv run` to execute scripts.
*   **Commits:** Adhere to conventional commit message standards.
