# Python Linter (Ruff)

Run Python code linting and formatting with Ruff.

## Purpose

This command runs Ruff, a fast all-in-one Python linter and formatter that replaces flake8, black, isort, and more.

## Usage

```
/lint
```

## What this command does

1. **Lints code** with Ruff (replaces flake8, pylint, isort)
2. **Formats code** with Ruff formatter (replaces black)
3. **Auto-fixes issues** where possible
4. **Type checking** with mypy (if configured)

## Commands

### Ruff Linting
```bash
# Check all files for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Check specific directory
uv run ruff check src/

# Check specific file
uv run ruff check src/main.py
```

### Ruff Formatting
```bash
# Format all Python files
uv run ruff format .

# Check formatting without changing files
uv run ruff format --check .

# Format specific directory
uv run ruff format src/
```

### Type Checking (mypy)
```bash
# Check types in src/
uv run mypy src

# Check specific file
uv run mypy src/main.py

# Strict mode
uv run mypy --strict src/
```

### Combined Workflow (Recommended)
```bash
# Run in this order for best results:
uv run ruff check . --fix
uv run ruff format .
uv run mypy src
```

## Configuration

This project's configuration in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py39"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
```

## Best Practices

- Run `ruff check --fix` before committing
- Use `ruff format` for consistent code style
- Fix type errors found by mypy
- Ruff is much faster than black + flake8 + isort combined
