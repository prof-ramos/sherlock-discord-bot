import logging
from typing import List, Optional

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Embedding model configuration
# all-MiniLM-L6-v2: Fast, lightweight, 384 dimensions, good for semantic search
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) service using pgvector in Neon PostgreSQL.

    This service manages legal document embeddings for semantic search,
    replacing the previous ChromaDB implementation with a more robust
    database-backed solution.
    """

    def __init__(self, db_service=None):
        """
        Initialize the RAG service with embedding model and database connection.

        Args:
            db_service: DatabaseService instance (injected for testability)
        """
        self._db = db_service
        self._model: Optional[SentenceTransformer] = None
        self._initialized = False

        try:
            # Load embedding model (downloaded on first use, cached locally)
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            self._initialized = True
            logger.info("📚 RAG Service initialized with model: %s", EMBEDDING_MODEL)
        except Exception as e:
            logger.error("❌ Failed to initialize RAG embedding model: %s", e)
            # We don't raise here to avoid blocking the bot, but RAG won't work

    def _ensure_db(self):
        """Lazy initialization of database service."""
        if self._db is None:
            from src.database import db_service
            self._db = db_service

    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        sources: Optional[List[str]] = None
    ) -> bool:
        """
        Add legal documents to the knowledge base with automatic embedding generation.

        Args:
            documents: List of document texts to add
            metadatas: Optional list of metadata dicts (e.g., {"article": "Art. 5º"})
            sources: Optional list of source identifiers (e.g., "CF/88", "CP")

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or not self._model:
            logger.warning("RAG Service not initialized, cannot add documents.")
            return False

        self._ensure_db()

        try:
            # Generate embeddings for all documents (batch processing)
            logger.info("🔄 Generating embeddings for %d documents...", len(documents))
            embeddings = self._model.encode(documents, show_progress_bar=False)

            # Convert numpy arrays to lists for PostgreSQL
            embeddings_list = [emb.tolist() for emb in embeddings]

            # Store in database
            count = await self._db.add_legal_documents(
                documents=documents,
                embeddings=embeddings_list,
                metadatas=metadatas,
                sources=sources
            )

            logger.info("✅ Added %d documents to knowledge base.", count)
            return True

        except Exception as e:
            logger.error("Failed to add documents to RAG: %s", e)
            return False

    async def query(
        self,
        query_text: str,
        n_results: int = 3,
        source_filter: Optional[str] = None
    ) -> List[str]:
        """
        Search for relevant documents using semantic similarity.

        Args:
            query_text: The query text to search for
            n_results: Number of results to return (default: 3)
            source_filter: Optional filter by source (e.g., "CF/88")

        Returns:
            List of relevant document texts, ordered by similarity
        """
        if not self._initialized or not self._model:
            logger.warning("RAG Service not initialized, returning empty results.")
            return []

        self._ensure_db()

        try:
            # Generate query embedding
            query_embedding = self._model.encode([query_text], show_progress_bar=False)[0]

            # Search database
            results = await self._db.query_legal_documents(
                query_embedding=query_embedding.tolist(),
                n_results=n_results,
                source_filter=source_filter
            )

            # Extract just the content texts
            documents = [result["content"] for result in results]

            if documents:
                logger.info(
                    "📚 RAG: Found %d documents (similarity: %.2f - %.2f)",
                    len(documents),
                    results[0]["similarity"] if results else 0,
                    results[-1]["similarity"] if results else 0
                )

            return documents

        except Exception as e:
            logger.error("RAG Query failed: %s", e)
            return []

    async def get_stats(self) -> dict:
        """
        Get statistics about the knowledge base.

        Returns:
            Dict with keys: status, count, model
        """
        if not self._initialized:
            return {"status": "error", "count": 0, "model": None}

        self._ensure_db()

        try:
            count = await self._db.get_legal_documents_count()
            return {
                "status": "active",
                "count": count,
                "model": EMBEDDING_MODEL,
                "dimensions": 384
            }
        except Exception as e:
            logger.error("Failed to get RAG stats: %s", e)
            return {"status": "error", "count": 0, "model": EMBEDDING_MODEL}

    async def delete_source(self, source: str) -> int:
        """
        Delete all documents from a specific source.

        Args:
            source: Source identifier (e.g., "CF/88")

        Returns:
            Number of documents deleted
        """
        if not self._initialized:
            logger.warning("RAG Service not initialized.")
            return 0

        self._ensure_db()

        try:
            return await self._db.delete_legal_documents_by_source(source)
        except Exception as e:
            logger.error("Failed to delete documents from source %s: %s", source, e)
            return 0


# Global instance (initialized without db_service for lazy loading)
rag_service = RAGService()
