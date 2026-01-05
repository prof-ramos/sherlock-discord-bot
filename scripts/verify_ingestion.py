import asyncio
import logging
import sys
from pathlib import Path

# Ensure src is in python path if running as script
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.rag_service import rag_service  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_ingestion():
    """Verify that documents exist in the RAG store."""
    try:
        logger.info("Verifying RAG ingestion status...")
        stats = await rag_service.get_stats()
        logger.info(f"RAG Stats: {stats}")

        count = stats.get("count", 0)
        if count == 0:
            logger.error("❌ No documents found in vector store.")
            sys.exit(1)

        logger.info("✅ Verification successful.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error during verification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify_ingestion())
