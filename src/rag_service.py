import json
import os
from typing import Optional

from openai import AsyncOpenAI

from src.database import db_service
from src.utils import logger

# Helper class to manage embeddings
class EmbeddingService:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found. RAG functionality will be disabled.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

        # OpenRouter might not support embeddings strictly, best to use direct OpenAI or compatible
        # If the user wants to use another provider, they can change the base_url here.
        self.model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        if not self.client:
            return None
        try:
            # Replace newlines to improve performance as recommended by OpenAI
            text = text.replace("\n", " ")
            response = await self.client.embeddings.create(input=[text], model=self.model)
            return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to generate embedding: %s", str(e))
            return None

class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]) -> bool:
        """Add documents to the Neon/Postgres vector store."""
        if not self.embedding_service.client:
            logger.error("Embedding service not configured. Cannot add documents.")
            return False

        try:
            # Ensure DB connection
            await db_service.connect()

            # We insert one by one or batch. Batch is better.
            # But we need embeddings first.
            embeddings = []
            for doc in documents:
                emb = await self.embedding_service.get_embedding(doc)
                if emb:
                    embeddings.append(emb)
                else:
                    # In case of failure, we skip or abort. Let's abort for data integrity.
                    logger.error("Could not generate embedding for a document. Aborting batch.")
                    return False

            async with db_service.pool.acquire() as conn:
                async with conn.transaction():
                    for doc, meta, emb in zip(documents, metadatas, embeddings):
                        await conn.execute(
                            """
                            INSERT INTO documents (content, metadata, embedding)
                            VALUES ($1, $2, $3)
                            """,
                            doc, json.dumps(meta), emb
                        )

            logger.info("✅ Added %d documents to Neon vector store.", len(documents))
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
                    query_embedding, n_results  # Pass raw list, cast to vector in SQL
                )

        # Note: We pass the raw list of floats and cast it to vector in SQL
        # using $1::vector syntax for compatibility with pgvector via asyncpg.

        return [row['content'] for row in rows]

        except Exception as e:
            # Log the full stack trace internally
            logger.exception("RAG Query failed: %s", str(e))
            # Return empty list to caller to degrade gracefully
            return []

    async def get_stats(self) -> dict:
        try:
            await db_service.connect()
            async with db_service.pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                return {
                    "status": "active",
                    "count": count,
                    "backend": "neon-pgvector"
                }
        except Exception as e:
            logger.error("Failed to get RAG stats: %s", str(e))
            return {"status": "error", "error": str(e)}

rag_service = RAGService()