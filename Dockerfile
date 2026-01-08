# ============================================================================
# Stage 1: Builder - Install dependencies
# ============================================================================
FROM python:3.13-slim AS builder

# Install uv package manager (ultra-fast Python package installer)
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first (better Docker layer caching)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies with uv
# --frozen: Use exact versions from lockfile (no resolution)
# --no-dev: Skip development dependencies (pytest, mypy, ruff)
RUN uv sync --frozen --no-dev

# ============================================================================
# Stage 2: Runtime - Final production image
# ============================================================================
FROM python:3.13-slim

# Install runtime dependencies for native extensions
# libpq5: PostgreSQL client library (required for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
# Using UID 1000 for compatibility with most systems
RUN useradd -m -u 1000 botuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=botuser:botuser /app/.venv /app/.venv

# Copy application source code
COPY --chown=botuser:botuser src/ ./src/
COPY --chown=botuser:botuser scripts/ ./scripts/
COPY --chown=botuser:botuser pyproject.toml ./

# Set environment variables
# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"
# Prevent Python from writing .pyc files (optimization)
ENV PYTHONDONTWRITEBYTECODE=1
# Force stdout/stderr to be unbuffered (better logging)
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER botuser

# Health check: Verify bot is actually healthy (not just process running)
# - Checks every 60s, timeout 10s, 60s startup grace period, 3 retries
# - Primary: Check if /tmp/bot_healthy was updated in last 120s (bot heartbeat)
# - Fallback: Check if Python process exists (if heartbeat file not implemented yet)
# NOTE: Bot should touch /tmp/bot_healthy every 30s in main loop for true health monitoring
HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=3 \
    CMD (test -f /tmp/bot_healthy && [ $(($(date +%s) - $(stat -c %Y /tmp/bot_healthy 2>/dev/null || echo 0))) -lt 120 ]) || pgrep -f "python -m src.main" > /dev/null

# Expose no ports (Discord bot connects outbound only)

# Default command: Run the bot
CMD ["python", "-m", "src.main"]
