# RAG Pipeline Management

Manage the RAG (Retrieval-Augmented Generation) pipeline for document ingestion and knowledge base.

## Purpose

This command helps you ingest documents, verify ingestion, and test the RAG system.

## Usage

```
/rag-pipeline
```

## Commands

### Document Ingestion

```bash
# Ingest single PDF document
uv run python scripts/ingest_docs.py path/to/document.pdf

# Ingest all documents in a directory (recursive)
uv run python scripts/ingest_docs.py ~/docs/juridicos/

# Ingest directory non-recursively
uv run python scripts/ingest_docs.py ./docs/ --no-recursive

# Ingest DOCX file
uv run python scripts/ingest_docs.py contract.docx

# Ingest HTML file
uv run python scripts/ingest_docs.py webpage.html

# Ingest text/markdown
uv run python scripts/ingest_docs.py notes.txt
```

### Verify Ingestion

```bash
# Check what documents are in the database
uv run python scripts/verify_ingestion.py

# Output shows:
# - Total documents count
# - Sample documents with metadata
# - Chunk sizes and embeddings
```

### Test RAG End-to-End

```bash
# Test RAG system with sample queries
uv run python scripts/test_rag_e2e.py

# Tests:
# - Vector similarity search
# - Full-text keyword search
# - Hybrid search (RRF - Reciprocal Rank Fusion)
# - Metadata filtering
```

### Check for Duplicates

```bash
# Find duplicate document chunks
uv run python scripts/check_duplicates.py

# Shows documents with identical content hashes
```

### Database Management

```bash
# Initialize RAG schema (pgvector + indexes)
uv run python scripts/init_db.py

# Truncate all RAG documents (DESTRUCTIVE!)
uv run python scripts/truncate_db.py

# Verify database connection
uv run python scripts/verify_db.py
```

## Supported Document Formats

| Format | Extension      | Library         |
|--------|----------------|-----------------|
| PDF    | `.pdf`         | `pypdf`         |
| Word   | `.docx`        | `python-docx`   |
| HTML   | `.html`        | `beautifulsoup4`|
| Text   | `.txt`, `.md`  | Built-in        |

## How RAG Works in This Project

### 1. Document Processing
- Documents split into 1000-char chunks (200 overlap)
- Each chunk embedded with OpenAI `text-embedding-3-small`
- Stored in Neon PostgreSQL with pgvector extension

### 2. Hybrid Search (RRF)
When user sends message, bot runs:
1. **Vector Search**: Cosine similarity on embeddings
2. **Keyword Search**: PostgreSQL full-text search (Portuguese)
3. **RRF Ranking**: Combines results with score = 1/(k + rank), k=60

### 3. Context Injection
Top 5 results wrapped in XML and injected into LLM prompt:
```xml
<relevant_context>
  <doc index='1'>Document content here...</doc>
  <doc index='2'>More content...</doc>
</relevant_context>
```

## Configuration

Key environment variables:
```bash
# Required for RAG
OPENAI_API_KEY=sk-...           # For embeddings
DATABASE_URL=postgresql://...   # Neon PostgreSQL

# Optional RAG settings
TEXT_SEARCH_LANG=portuguese     # Full-text search language
```

## Database Schema

```sql
-- Documents table with pgvector
CREATE TABLE documents (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  metadata JSONB,
  embedding vector(1536),           -- OpenAI embedding dimension
  content_search tsvector,          -- Full-text search
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast search
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON documents USING gin (content_search);
```

## Performance Notes

- **HNSW index**: Requires 1000+ documents for optimal performance
- **Hybrid search**: More robust than pure vector search
- **Portuguese text search**: Requires `TEXT_SEARCH_LANG=portuguese`
- **Metadata filtering**: Uses JSONB operators (`metadata->>'key'`)

## Troubleshooting

**Ingestion fails with encoding error:**
```bash
# Ensure files are UTF-8 encoded
# Try converting: iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt
```

**Search returns no results:**
```bash
# Verify documents exist
uv run python scripts/verify_ingestion.py

# Check embeddings are created
# Verify OPENAI_API_KEY is set correctly
```

**Slow search performance:**
```bash
# Ensure HNSW index exists
# Check database has enough documents (>1000 recommended)
# Monitor Neon compute state (should be active, not sleeping)
```

## GitHub Actions Workflow

```bash
# Ingest documents using Neon branching (manual workflow)
gh workflow run ingest-docs.yml -f file_path=data/documento.pdf

# Creates temporary Neon branch for safe ingestion
# Review changes before merging to main branch
```
