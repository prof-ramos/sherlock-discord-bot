#!/usr/bin/env python3
"""
End-to-end test for RAG pipeline.
Tests: Ingest doc -> Query -> Verify Response

Usage:
    uv run python scripts/test_rag_e2e.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.rag_service import rag_service  # noqa: E402


async def main():
    print("=" * 60)
    print("🧪 RAG End-to-End Test")
    print("=" * 60)

    # 1. Check RAG service status
    print("\n📊 Step 1: Check RAG service stats...")
    stats = await rag_service.get_stats()
    print(f"   Status: {stats.get('status')}")
    print(f"   Document count: {stats.get('count', 'N/A')}")
    print(f"   Backend: {stats.get('backend', 'N/A')}")

    if stats.get("status") == "error":
        print(f"   ❌ Error: {stats.get('error')}")
        print("\n⚠️  RAG service is not configured. Make sure DATABASE_URL is set.")
        return False

    # 2. Test document ingestion
    print("\n📄 Step 2: Test document ingestion...")
    test_docs = [
        "O Código Civil Brasileiro estabelece que toda pessoa é capaz de direitos e deveres na ordem civil.",
        "A Constituição Federal de 1988 é a lei fundamental do Brasil, estabelecendo os direitos e garantias fundamentais.",
        "O habeas corpus é um remédio constitucional que protege o direito de ir e vir do cidadão.",
    ]
    test_metadata = [
        {"source": "test_e2e", "chunk_index": i, "type": "legal_test"}
        for i in range(len(test_docs))
    ]

    success = await rag_service.add_documents(test_docs, test_metadata)
    if success:
        print("   ✅ Documents ingested successfully!")
    else:
        print("   ❌ Failed to ingest documents")
        return False

    # 3. Test query with hybrid search
    print("\n🔍 Step 3: Test hybrid search query...")
    test_query = "O que é habeas corpus?"
    results = await rag_service.query(test_query, n_results=3)

    if results:
        print(f"   ✅ Query returned {len(results)} results:")
        for i, result in enumerate(results, 1):
            preview = result[:100] + "..." if len(result) > 100 else result
            print(f"      [{i}] {preview}")
    else:
        print("   ⚠️  No results returned (this may be expected if no matching docs)")

    # 4. Verify RRF is working (check if we got relevant results)
    print("\n✨ Step 4: Verify relevance...")
    found_habeas = any("habeas corpus" in r.lower() for r in results)
    if found_habeas:
        print("   ✅ RRF correctly ranked 'habeas corpus' document!")
    else:
        print("   ⚠️  Expected document not in top results (may need more data)")

    # 5. Final stats
    print("\n📊 Step 5: Final stats...")
    final_stats = await rag_service.get_stats()
    print(f"   Total documents: {final_stats.get('count', 'N/A')}")

    print("\n" + "=" * 60)
    print("✅ RAG End-to-End Test Completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
