import asyncio
import json
import os
from typing import List, Optional

import asyncpg

from src.base import ThreadConfig
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
                        min_size=1,            # Keep at least one connection warm
                        max_size=5,            # Limit max connections to share resources
                        command_timeout=30,    # Fail fast if DB is sleeping/cold
                        max_inactive_connection_lifetime=300 # Recycle connections commonly
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
                thread_id, guild_id, user_id, config.model, config.temperature, config.max_tokens
            )

    async def get_thread_config(self, thread_id: int) -> Optional[ThreadConfig]:
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT model, temperature, max_tokens FROM threads WHERE thread_id = $1 AND is_active = TRUE",
                thread_id
            )
            if row:
                return ThreadConfig(
                    model=row['model'],
                    temperature=row['temperature'],
                    max_tokens=row['max_tokens']
                )
            return None

    async def log_message(self, thread_id: int, role: str, content: str, tokens: int = 0):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (thread_id, role, content, token_count) VALUES ($1, $2, $3, $4)",
                thread_id, role, content, tokens
            )

    async def log_analytics(self, thread_id: int, guild_id: int, user_id: int, model: str, prompt_tokens: int, completion_tokens: int, response_time_ms: int):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO analytics (thread_id, guild_id, user_id, model, prompt_tokens, completion_tokens, response_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                thread_id, guild_id, user_id, model, prompt_tokens, completion_tokens, response_time_ms
            )

    # ========================================================================
    # RAG Methods - Legal Documents with Vector Embeddings
    # ========================================================================

    async def add_legal_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
        sources: Optional[List[str]] = None
    ) -> int:
        """
        Add legal documents with their embeddings to the knowledge base.

        Args:
            documents: List of document texts
            embeddings: List of embedding vectors (384-dimensional for all-MiniLM-L6-v2)
            metadatas: Optional list of metadata dicts
            sources: Optional list of source identifiers (e.g., "CF/88", "CP")

        Returns:
            Number of documents inserted
        """
        await self.connect()

        if metadatas is None:
            metadatas = [{}] * len(documents)
        if sources is None:
            sources = [None] * len(documents)

        async with self.pool.acquire() as conn:
            # Use executemany for batch insert
            await conn.executemany(
                """
                INSERT INTO legal_documents (content, metadata, embedding, source)
                VALUES ($1, $2, $3, $4)
                """,
                [
                    (doc, json.dumps(meta), emb, src)
                    for doc, meta, emb, src in zip(documents, metadatas, embeddings, sources)
                ]
            )

        logger.info("✅ Added %d legal documents to knowledge base", len(documents))
        return len(documents)

    async def query_legal_documents(
        self,
        query_embedding: List[float],
        n_results: int = 3,
        source_filter: Optional[str] = None
    ) -> List[dict]:
        """
        Semantic search for legal documents using cosine similarity.

        Args:
            query_embedding: Query embedding vector (384-dimensional)
            n_results: Number of results to return
            source_filter: Optional filter by source (e.g., "CF/88")

        Returns:
            List of dicts with keys: id, content, metadata, source, similarity
        """
        await self.connect()

        async with self.pool.acquire() as conn:
            if source_filter:
                rows = await conn.fetch(
                    """
                    SELECT
                        id,
                        content,
                        metadata,
                        source,
                        1 - (embedding <=> $1::vector) AS similarity
                    FROM legal_documents
                    WHERE source = $3
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    query_embedding, n_results, source_filter
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT
                        id,
                        content,
                        metadata,
                        source,
                        1 - (embedding <=> $1::vector) AS similarity
                    FROM legal_documents
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    query_embedding, n_results
                )

            return [
                {
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "source": row["source"],
                    "similarity": float(row["similarity"])
                }
                for row in rows
            ]

    async def get_legal_documents_count(self) -> int:
        """Get total count of legal documents in knowledge base."""
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) as count FROM legal_documents")
            return row["count"] if row else 0

    async def delete_legal_documents_by_source(self, source: str) -> int:
        """Delete all documents from a specific source."""
        await self.connect()
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM legal_documents WHERE source = $1",
                source
            )
            # Extract number from "DELETE N" string
            deleted_count = int(result.split()[-1]) if result else 0
            logger.info("🗑️ Deleted %d documents from source: %s", deleted_count, source)
            return deleted_count

db_service = DatabaseService()
