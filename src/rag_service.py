import logging
import os
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions

from src.constants import SCRIPT_DIR

logger = logging.getLogger(__name__)

# Directory for storing the vector database
CHROMA_DB_DIR = SCRIPT_DIR / "data" / "chroma_db"
COLLECTION_NAME = "sherlock_knowledge_base"

class RAGService:
    def __init__(self):
        """Initialize the RAG service with a persistent ChromaDB client."""
        self._client = None
        self._collection = None

        # Ensure the data directory exists
        CHROMA_DB_DIR.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

            # Use default embedding function (all-MiniLM-L6-v2)
            # This runs locally and is free/fast for basic semantic search
            self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()

            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"description": "Legal knowledge base for Sherlock Bot"}
            )
            logger.info("📚 RAG Service initialized. Collection size: %d", self._collection.count())

        except Exception as e:
            logger.error("❌ Failed to initialize RAG Service: %s", e)
            # We don't raise here to avoid blocking the bot, but RAG won't work
            self._client = None

    def add_documents(self, documents: List[str], metadatas: List[dict], ids: List[str]) -> bool:
        """Add documents to the knowledge base."""
        if not self._collection:
            logger.warning("RAG Service not initialized, cannot add documents.")
            return False

        try:
            self._collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info("✅ Added %d documents to knowledge base.", len(documents))
            return True
        except Exception as e:
            logger.error("Failed to add documents to RAG: %s", e)
            return False

    def query(self, query_text: str, n_results: int = 3) -> List[str]:
        """Search for relevant documents."""
        if not self._collection:
            return []

        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results
            )

            # Results is a dict with lists of lists (batch processing)
            # We only queried one text, so we take the first list of documents
            if results and results['documents']:
                return results['documents'][0]

            return []
        except Exception as e:
            logger.error("RAG Query failed: %s", e)
            return []

    def get_stats(self) -> dict:
        """Return stats about the knowledge base."""
        if not self._collection:
            return {"status": "error", "count": 0}

        return {
            "status": "active",
            "count": self._collection.count(),
            "db_path": str(CHROMA_DB_DIR)
        }

# Global instance
rag_service = RAGService()
