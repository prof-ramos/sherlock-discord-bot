import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

from src.database import db_service  # noqa: E402


async def check_duplicates():
    print("Connecting to DB...")
    await db_service.connect()
    async with db_service.pool.acquire() as conn:
        print("Checking for duplicate chunks (same source + chunk_index)...")
        duplicates = await conn.fetch("""
            SELECT
                metadata->>'source' as source,
                metadata->>'chunk_index' as chunk_index,
                COUNT(*) as count
            FROM documents
            GROUP BY 1, 2
            HAVING COUNT(*) > 1
        """)

        if duplicates:
            print(f"❌ Found {len(duplicates)} duplicate chunks!")
            for row in duplicates[:5]:
                print(f"   - {row['source']} (chunk {row['chunk_index']}): {row['count']} copies")
        else:
            print("✅ No duplicate chunks found (Unique constraint satisfied implicitly).")

        print("\nChecking for file duplication (files appearing multiple times)...")
        # This is harder to define without a 'ingestion_id', but we can check total files
        files = await conn.fetch("""
            SELECT DISTINCT metadata->>'source' as source FROM documents ORDER BY source
        """)
        print(f"ℹ️ Total unique files in knowledge base: {len(files)}")


if __name__ == "__main__":
    asyncio.run(check_duplicates())
