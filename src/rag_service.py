import json
import os
from typing import Any, Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from src.database import db_service
from src.utils import logger


# Helper class to manage embeddings
class EmbeddingService:
    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client: Optional[AsyncOpenAI]
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found. RAG functionality will be disabled.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

        # OpenRouter might not support embeddings strictly, best to use direct OpenAI or compatible
        # If the user wants to use another provider, they can change the base_url here.
        self.model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not self.client:
            logger.error("Attempted to generate embeddings with no client configured.")
            raise RuntimeError("Embedding service is not configured (missing OPENAI_API_KEY).")
        try:
            # Replace newlines in all texts
            cleaned_texts = [t.replace("\n", " ") for t in texts]
            response = await self.client.embeddings.create(input=cleaned_texts, model=self.model)
            # Sort by index to ensure order matches input
            return [data.embedding for data in sorted(response.data, key=lambda x: x.index)]
        except Exception as e:
            logger.error("Failed to generate embeddings batch: %s", str(e))
            raise e

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        # Wrapper for single text backward compatibility if needed, using the batch method
        try:
            embs = await self.get_embeddings([text])
            return embs[0] if embs else None
        except Exception as e:
            logger.error("Failed to generate single embedding: %s", str(e))
            return None


class RAGService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()

    async def add_documents(self, documents: list[str], metadatas: list[dict[str, Any]]) -> bool:
        """Add documents to the Neon/Postgres vector store."""
        if not self.embedding_service.client:
            logger.error("Embedding service not configured. Cannot add documents.")
            return False

        try:
            # Ensure DB connection
            await db_service.connect()

            # We insert one by one or batch. Batch is better.
            # But we need embeddings first.
            # Generate embeddings in batch
            try:
                embeddings = await self.embedding_service.get_embeddings(documents)
            except Exception:
                logger.error("Failed to generate embeddings after retries. Aborting batch.")
                return False

            if len(embeddings) != len(documents):
                logger.error("Mismatch in embedding count. Aborting.")
                return False

            records = []
            for doc, meta, emb in zip(documents, metadatas, embeddings):
                try:
                    meta_json = json.dumps(meta)
                except (TypeError, ValueError) as e:
                    logger.warning(
                        "Failed to serialize metadata for document (first 100 chars: %s): %s. "
                        "Using fallback serialization (default=str). in index %d",
                        doc[:100] if doc else "N/A",
                        str(e),
                        documents.index(doc),
                    )
                    meta_json = json.dumps(meta, default=str)
                records.append((doc, meta_json, emb))

            assert db_service.pool is not None, "Database pool must be initialized"
            async with db_service.pool.acquire() as conn, conn.transaction():
                # Use executemany for valid batch insertion
                # Note: asyncpg executemany corresponds to executing the same statement with different arguments
                await conn.executemany(
                    """
                    INSERT INTO documents (content, metadata, embedding)
                    VALUES ($1, $2, $3)
                    """,
                    records,
                )

            logger.info("✅ Added %d documents to Neon vector store in batch.", len(documents))
            return True

        except Exception as e:
            logger.error("Failed to add documents to RAG: %s", str(e))
            return False

    async def query(self, query_text: str, n_results: int = 3) -> list[str]:
        """Search for relevant documents using vector similarity."""
        if not self.embedding_service.client:
            return []

        try:
            query_embedding = await self.embedding_service.get_embedding(query_text)
            if not query_embedding:
                return []

            await db_service.connect()
            assert db_service.pool is not None, "Database pool must be initialized"
            async with db_service.pool.acquire() as conn:
                # Use <=> operator for cosine distance (pgvector)
                # We want the closest distance (smallest value)
                rows = await conn.fetch(
                    """
                    SELECT content
                    FROM documents
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    query_embedding,
                    n_results,  # Pass raw list, cast to vector in SQL
                )

                # Note: We pass the raw list of floats and cast it to vector in SQL
                # using $1::vector syntax for compatibility with pgvector via asyncpg.
                return [row["content"] for row in rows]

        except Exception as e:
            # Log the full stack trace internally
            logger.exception("RAG Query failed: %s", str(e))
            # Return empty list to caller to degrade gracefully
            return []

    async def get_stats(self) -> dict[str, Any]:
        try:
            await db_service.connect()
            assert db_service.pool is not None, "Database pool must be initialized"
            async with db_service.pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                return {"status": "active", "count": count, "backend": "neon-pgvector"}
        except Exception as e:
            logger.error("Failed to get RAG stats: %s", str(e))
            return {"status": "error", "error": str(e)}


rag_service = RAGService()
