import json
import os
from typing import Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

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
    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def add_documents(self, documents: list[str], metadatas: list[dict]) -> bool:
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
                records.append((doc, meta_json, str(emb)))

            async with db_service.pool.acquire() as conn, conn.transaction():
                # Use executemany for valid batch insertion
                # Note: asyncpg executemany corresponds to executing the same statement with different arguments
                await conn.executemany(
                    """
                    INSERT INTO documents (content, metadata, embedding)
                    VALUES ($1, $2, $3::vector)
                    """,
                    records,
                )

            logger.info("✅ Added %d documents to Neon vector store in batch.", len(documents))
            return True

        except Exception as e:
            logger.error("Failed to add documents to RAG: %s", str(e))
            return False

    async def query(
        self, query_text: str, n_results: int = 5, filter_metadata: dict = None
    ) -> list[str]:
        """
        Search for relevant documents using Hybrid Search (Vector + Keyword) with RRF.

        Args:
            query_text: The search query
            n_results: Number of results to return
            filter_metadata: Optional dictionary to filter results by metadata (e.g. {"type": "Súmula"})
        """
        if not self.embedding_service.client:
            return []

        try:
            # 1. Get Vector Embeddings
            query_embedding = await self.embedding_service.get_embedding(query_text)
            if not query_embedding:
                return []
            embedding_str = str(query_embedding)

            await db_service.connect()

            # Text search language configuration
            allowed_languages = {
                "portuguese",
                "english",
                "spanish",
                "french",
                "german",
                "italian",
                "dutch",
                "russian",
                "simple",
            }
            text_search_lang = os.environ.get("TEXT_SEARCH_LANG", "portuguese").lower()
            if text_search_lang not in allowed_languages:
                text_search_lang = "portuguese"

            # Build metadata filter clause
            filter_clause = ""
            filter_params = []
            if filter_metadata:
                clauses = []
                # Start index at 3 because $1 and $2 are reserved for specific query params
                current_idx = 3
                for key, value in filter_metadata.items():
                    # Sanitize key to prevent SQL injection (metadata keys should be simple identifiers)
                    if not key.replace("_", "").isalnum():
                        logger.warning("Skipping invalid metadata filter key: %s", key)
                        continue

                    clauses.append(f"metadata->>'{key}' = ${current_idx}")
                    filter_params.append(str(value))
                    current_idx += 1
                if clauses:
                    filter_clause = "AND " + " AND ".join(clauses)

            async with db_service.pool.acquire() as conn:
                # Vector Search
                # Params: $1=embedding, $2=limit, $3...=filters
                vector_args = [embedding_str, n_results * 2] + filter_params
                vector_rows = await conn.fetch(
                    f"""
                    SELECT id, content
                    FROM documents
                    WHERE 1=1 {filter_clause}
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    *vector_args,
                )

                # Keyword Search (Full Text)
                # Params: $1=query, $2=limit, $3...=filters
                keyword_args = [query_text, n_results * 2] + filter_params
                keyword_rows = await conn.fetch(
                    f"""
                    SELECT id, content
                    FROM documents
                    WHERE content_search @@ websearch_to_tsquery('{text_search_lang}', $1)
                    {filter_clause}
                    ORDER BY ts_rank(content_search, websearch_to_tsquery('{text_search_lang}', $1)) DESC
                    LIMIT $2
                    """,
                    *keyword_args,
                )

            # 3. Reciprocal Rank Fusion (RRF)
            # RRF score = 1 / (k + rank)
            k = 60
            scores = {}

            # Process Vector Results
            for rank, row in enumerate(vector_rows):
                doc_id = row["id"]
                scores[doc_id] = scores.get(doc_id, {"score": 0, "content": row["content"]})
                scores[doc_id]["score"] += 1 / (k + rank + 1)

            # Process Keyword Results
            for rank, row in enumerate(keyword_rows):
                doc_id = row["id"]
                # If we have a match, boost it
                if doc_id not in scores:
                    scores[doc_id] = {"score": 0, "content": row["content"]}
                scores[doc_id]["score"] += 1 / (k + rank + 1)

            # Sort by combined score
            sorted_docs = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

            # Return top N content
            return [doc["content"] for doc in sorted_docs[:n_results]]

        except Exception as e:
            # Log the full stack trace internally
            logger.exception("RAG Query failed: %s", str(e))
            # Return empty list to degrade gracefully
            return []

    async def get_stats(self) -> dict:
        try:
            await db_service.connect()
            async with db_service.pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                return {"status": "active", "count": count, "backend": "neon-pgvector"}
        except Exception as e:
            logger.error("Failed to get RAG stats: %s", str(e))
            return {"status": "error", "error": str(e)}


rag_service = RAGService()
