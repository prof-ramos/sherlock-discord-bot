import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

from src.database import db_service  # noqa: E402


async def clean_db(force: bool):
    if not force:
        # Check if running interactively
        if not sys.stdin.isatty():
            print("❌ Cannot run interactively without a TTY. Use --force to skip confirmation.")
            sys.exit(1)

        confirm = input(
            "⚠️  WARNING: This will TRUNCATE the 'documents' table. ALL DATA WILL BE LOST.\nAre you sure you want to proceed? [y/N] "
        )
        if confirm.lower() != "y":
            print("Aborted.")
            return

    try:
        print("Connecting to DB...")
        await db_service.connect()
        async with db_service.pool.acquire() as conn:
            print("Truncating documents table...")
            # Using CASCADE to handle any foreign key dependencies
            # Using RESTART IDENTITY to reset auto-increment counters
            await conn.execute("TRUNCATE TABLE documents RESTART IDENTITY CASCADE;")
            print("✅ Documents table truncated successfully.")
    except Exception as e:
        print(f"❌ Failed to truncate table due to error (potentially constraints/locks): {e}")
    finally:
        await db_service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Truncate the RAG documents table.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    try:
        asyncio.run(clean_db(args.force))
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
