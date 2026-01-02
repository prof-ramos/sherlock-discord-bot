#!/usr/bin/env python3
"""
Migration script to transfer data from ChromaDB to pgvector in Neon.

This script reads all documents from the old ChromaDB storage and
inserts them into the new PostgreSQL database with pgvector.

Usage:
    python scripts/migrate_chromadb_to_pgvector.py

Note: This script is only needed if you have existing data in ChromaDB.
For new installations, you can skip this migration.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import db_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def migrate():
    """Migrate documents from ChromaDB to pgvector."""
    try:
        # Try to import chromadb (might not be installed anymore)
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        logger.error("❌ ChromaDB not installed. If you need to migrate data, install it first:")
        logger.error("   pip install chromadb>=0.4.22")
        return False

    # ChromaDB configuration (from old rag_service.py)
    from src.constants import SCRIPT_DIR
    CHROMA_DB_DIR = SCRIPT_DIR / "data" / "chroma_db"
    COLLECTION_NAME = "sherlock_knowledge_base"

    if not CHROMA_DB_DIR.exists():
        logger.info("✅ No ChromaDB data found at %s - nothing to migrate", CHROMA_DB_DIR)
        return True

    logger.info("🔄 Starting migration from ChromaDB to pgvector...")

    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )

        # Get all documents
        results = collection.get(include=["documents", "embeddings", "metadatas"])
        total_docs = len(results["documents"]) if results["documents"] else 0

        if total_docs == 0:
            logger.info("✅ ChromaDB collection is empty - nothing to migrate")
            return True

        logger.info("📚 Found %d documents in ChromaDB", total_docs)

        # Connect to Neon
        await db_service.connect()

        # Extract sources from metadata if available
        documents = results["documents"]
        embeddings = results["embeddings"]
        metadatas = results.get("metadatas", [{}] * total_docs)
        sources = [meta.get("source") for meta in metadatas]

        # Insert into pgvector
        logger.info("🔄 Inserting documents into Neon database...")
        inserted = await db_service.add_legal_documents(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            sources=sources
        )

        logger.info("✅ Migration complete! Inserted %d documents", inserted)
        logger.info("📊 You can now safely delete the ChromaDB directory: %s", CHROMA_DB_DIR)

        return True

    except Exception as e:
        logger.error("❌ Migration failed: %s", e)
        return False


async def main():
    """Main migration entry point."""
    success = await migrate()

    if success:
        logger.info("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
