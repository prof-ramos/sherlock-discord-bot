#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'EOF'
Usage: ./test.sh [--fix]

Runs:
  - uv run ruff check .
  - uv run ruff format --check .
  - uv run mypy src
  - uv run pytest

Options:
  --fix       Apply autofixes and formatting
  -h, --help  Show this help
EOF
}

FIX=false

for arg in "$@"; do
  case "$arg" in
    --fix)
      FIX=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install uv and try again." >&2
  exit 1
fi

if "$FIX"; then
  echo "Running ruff check (fix)..."
  uv run ruff check . --fix
  echo "Running ruff format..."
  uv run ruff format .
else
  echo "Running ruff check..."
  uv run ruff check .
  echo "Running ruff format (check)..."
  uv run ruff format --check .
fi

echo "Running mypy..."
uv run mypy src

echo "Running pytest..."
uv run pytest
