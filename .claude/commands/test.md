# Test Runner (pytest)

Run Python tests with pytest for this Discord bot project.

## Purpose

This command runs the test suite using pytest with coverage reporting.

## Usage

```
/test
```

## What this command does

1. **Runs pytest** with asyncio support
2. **Generates coverage reports** (terminal, HTML, XML)
3. **Runs unit and integration tests** separately if needed
4. **Shows detailed failure information**

## Commands

### Run All Tests
```bash
# Run all tests with coverage
uv run pytest -v

# Run without stopping on first failure
uv run pytest -v --maxfail=0

# Run with detailed output
uv run pytest -vv
```

### Run Specific Test Types
```bash
# Unit tests only (no database required)
uv run pytest tests/unit -v

# Integration tests only (requires DATABASE_URL)
uv run pytest tests/integration -v

# Run specific test file
uv run pytest tests/unit/test_completion.py -v

# Run specific test function
uv run pytest tests/unit/test_completion.py::test_basic_completion -v
```

### Coverage Reports
```bash
# Run with coverage (default config includes this)
uv run pytest -v --cov=src --cov-report=term-missing

# Generate HTML coverage report
uv run pytest -v --cov=src --cov-report=html:coverage_html

# Generate XML coverage report (for CI)
uv run pytest -v --cov=src --cov-report=xml:coverage.xml

# View HTML coverage report
open coverage_html/index.html
```

### Debugging Tests
```bash
# Run with print statements visible
uv run pytest -v -s

# Run with debugger on failure
uv run pytest -v --pdb

# Run last failed tests
uv run pytest -v --lf

# Run tests matching pattern
uv run pytest -v -k "test_rag"
```

### CI/GitHub Actions Commands
```bash
# Run all tests with coverage append (for combining coverage)
uv run pytest -v --cov=src --cov-append
```

## Configuration

This project's pytest configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = "src"
addopts = [
    "-v",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:coverage_html",
    "--cov-report=xml:coverage.xml",
]
asyncio_mode = "auto"
```

## Test Structure

```
tests/
├── unit/           # Unit tests (mocked dependencies)
│   ├── test_completion.py
│   ├── test_moderation.py
│   └── test_message_handling.py
└── integration/    # Integration tests (real database)
    ├── test_database.py
    └── test_rag_service.py
```

## Requirements

- **Unit tests**: No special setup required
- **Integration tests**: Require `DATABASE_URL` environment variable
  - Use Neon PostgreSQL database
  - Schema must be initialized with `uv run python scripts/init_db.py`

## Best Practices

- Run unit tests frequently during development
- Run integration tests before pushing to remote
- Maintain >80% code coverage
- Use `pytest-mock` for mocking Discord API calls
- Use `pytest-asyncio` for async test functions
- Keep tests isolated and independent

## Common Issues

**Integration tests fail with database connection error:**
```bash
# Ensure DATABASE_URL is set in .env
# Initialize database schema:
uv run python scripts/init_db.py
```

**Tests hang or timeout:**
```bash
# Check for missing `await` in async functions
# Verify asyncio_mode = "auto" in pyproject.toml
```
