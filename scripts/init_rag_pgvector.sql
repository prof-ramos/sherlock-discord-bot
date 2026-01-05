-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table with vector support
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(1536) NOT NULL, -- 1536 dimensions for text-embedding-3-small
    content_search tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create HNSW index for fast similarity search
-- m=16, ef_construction=64 are reasonable defaults for balance between recall and build time.
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);

-- Additional indexes for performance (metadata and time-based queries)
CREATE INDEX IF NOT EXISTS documents_metadata_idx ON documents USING gin (metadata);
CREATE INDEX IF NOT EXISTS documents_created_at_idx ON documents (created_at);
CREATE INDEX IF NOT EXISTS documents_content_search_idx ON documents USING gin (content_search);
