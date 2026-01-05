import asyncio
import os
from typing import Optional

import asyncpg

from src.base import Message, ThreadConfig
from src.utils import logger


class DatabaseService:
    def __init__(self):
        self.dsn = os.environ.get("DATABASE_URL")
        if not self.dsn:
            logger.error("❌ DATABASE_URL is not set in environment")
            # We don't raise here to allow the bot to start if DB is optional,
            # but methods will fail. Actually, better to raise if it's required.
            # The plan says "fail fast".
            raise RuntimeError("DATABASE_URL is not set")

        self.pool: Optional[asyncpg.Pool] = None
        self._connect_lock = asyncio.Lock()

    async def connect(self):
        """Establish connection pool if not already connected."""
        if self.pool:
            return

        async with self._connect_lock:
            # Re-check after acquiring lock
            if not self.pool:
                try:
                    self.pool = await asyncpg.create_pool(
                        self.dsn,
                        min_size=1,  # Keep at least one connection warm
                        max_size=5,  # Limit max connections to share resources
                        command_timeout=30,  # Fail fast if DB is sleeping/cold
                        max_inactive_connection_lifetime=300,  # Recycle connections commonly
                    )
                    logger.info("✅ Connected to Neon Database pool")
                except Exception as e:
                    logger.error("❌ Failed to connect to Neon: %s", e)
                    raise

    async def close(self):
        """Close the database pool."""
        async with self._connect_lock:
            if self.pool:
                await self.pool.close()
                self.pool = None
                logger.info("🔌 Database pool closed")

    async def save_thread(self, thread_id: int, guild_id: int, user_id: int, config: ThreadConfig):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO threads (thread_id, guild_id, user_id, model, temperature, max_tokens)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (thread_id) DO UPDATE SET
                    model = EXCLUDED.model,
                    temperature = EXCLUDED.temperature,
                    max_tokens = EXCLUDED.max_tokens,
                    updated_at = CURRENT_TIMESTAMP
                """,
                thread_id,
                guild_id,
                user_id,
                config.model,
                config.temperature,
                config.max_tokens,
            )

    async def get_thread_config(self, thread_id: int) -> Optional[ThreadConfig]:
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT model, temperature, max_tokens FROM threads WHERE thread_id = $1 AND is_active = TRUE",
                thread_id,
            )
            if row:
                return ThreadConfig(
                    model=row["model"], temperature=row["temperature"], max_tokens=row["max_tokens"]
                )
            return None

    async def log_message(self, thread_id: int, role: str, content: str, tokens: int = 0):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (thread_id, role, content, token_count) VALUES ($1, $2, $3, $4)",
                thread_id,
                role,
                content,
                tokens,
            )

    async def log_analytics(
        self,
        thread_id: int,
        guild_id: int,
        user_id: int,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        response_time_ms: int,
    ):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO analytics (thread_id, guild_id, user_id, model, prompt_tokens, completion_tokens, response_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                thread_id,
                guild_id,
                user_id,
                model,
                prompt_tokens,
                completion_tokens,
                response_time_ms,
            )

    async def get_messages(self, thread_id: int, limit: int = 10) -> list[Message]:
        """Fetch chronologically ordered history for a thread/channel (last N messages)."""
        # Proper clamping: min 1, max 100
        limit = max(1, min(limit, 100))

        await self.connect()
        async with self.pool.acquire() as conn:
            # Fetch last N messages (DESC limit), then order them chronologically (ASC)
            rows = await conn.fetch(
                """
                SELECT role, content
                FROM (
                    SELECT role, content, created_at
                    FROM messages
                    WHERE thread_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                ) AS sub
                ORDER BY created_at ASC
                """,
                thread_id,
                limit,
            )
            return [Message(user=row["role"], text=row["content"]) for row in rows]

    async def get_analytics_count(self, thread_id: int) -> int:
        """Get the count of analytics entries for a thread (for testing)."""
        await self.connect()
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM analytics WHERE thread_id = $1", thread_id
            )
            return count or 0


db_service = DatabaseService()
