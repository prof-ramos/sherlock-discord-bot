import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure src is in python path
sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

from src.database import db_service  # noqa: E402
from src.rag_service import rag_service  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_filtering():
    """Verify metadata extraction and filtering for Lei 14133."""
    try:
        # 1. Verify Metadata Persistence
        logger.info("🔍 Step 1: Checking metadata in database...")
        await db_service.connect()
        async with db_service.pool.acquire() as conn:
            # Check one random chunk from this file
            row = await conn.fetchrow("""
                SELECT metadata
                FROM documents
                WHERE metadata->>'source' LIKE '%Lei 14133%'
                LIMIT 1
            """)

            if not row:
                logger.error("❌ No documents found for Lei 14133")
                return  # Exit gracefully instead of sys.exit(1) to allow finally cleanup

            if isinstance(row["metadata"], str):
                meta = json.loads(row["metadata"])
            else:
                meta = row["metadata"]
            logger.info(f"   found metadata: {meta}")

            expected = {"type": "Lei", "number": "14133"}
            if meta.get("type") == "Lei" and meta.get("number") == "14133":
                logger.info("   ✅ Metadata extraction verified!")
            else:
                logger.error(f"   ❌ Metadata mismatch. Expected parts of {expected}")

        # 2. Verify RAG Filtering (Correct Filter)
        logger.info("\n🔍 Step 2: Testing RAG with CORRECT filter (number=14133)...")
        try:
            results = await rag_service.query(
                "licitação", n_results=3, filter_metadata={"number": "14133"}
            )
            if results:
                logger.info(f"   ✅ Got {len(results)} results (GOOD)")
            else:
                logger.error("   ❌ Got 0 results with correct filter (BAD)")
        except Exception as e:
            logger.error("   ❌ Failed during Correct Filter Query: %s", e)

        # 3. Verify RAG Filtering (Incorrect Filter)
        logger.info("\n🔍 Step 3: Testing RAG with INCORRECT filter (number=99999)...")
        try:
            results_bad = await rag_service.query(
                "licitação", n_results=3, filter_metadata={"number": "99999"}
            )
            if not results_bad:
                logger.info("   ✅ Got 0 results (GOOD - filter excluded everything)")
            else:
                logger.error(
                    f"   ❌ Got {len(results_bad)} results (BAD - filter should have excluded these)"
                )
        except Exception as e:
            logger.error("   ❌ Failed during Incorrect Filter Query: %s", e)

    except Exception as e:
        logger.critical("❌ Critical error during verification: %s", e)
    finally:
        await db_service.close()


if __name__ == "__main__":
    asyncio.run(verify_filtering())
