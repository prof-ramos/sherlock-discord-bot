-- scripts/init_schema.sql

-- Use gen_random_uuid() for UUID generation (available in Postgres 13+)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enable pgvector for RAG semantic search
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS threads (
    thread_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    model TEXT NOT NULL,
    temperature FLOAT NOT NULL,
    max_tokens INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    thread_id BIGINT REFERENCES threads(thread_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Analytics table (independent of thread lifecycle for data retention)
CREATE TABLE IF NOT EXISTS analytics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    thread_id BIGINT REFERENCES threads(thread_id) ON DELETE SET NULL,
    guild_id BIGINT,
    user_id BIGINT,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optimization: Indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_threads_active ON threads(thread_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics(created_at);

-- Additional Indexes for filtering by Guild/User
CREATE INDEX IF NOT EXISTS idx_threads_guild_id ON threads(guild_id);
CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_guild_id ON analytics(guild_id);
CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics(user_id);

-- RAG: Legal documents with vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS legal_documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dimensional embeddings
    source TEXT,  -- e.g., "CF/88", "CP", "CPC", etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optimization: IVFFlat index for fast cosine similarity search
-- Note: This index is created AFTER inserting data (requires at least ~1000 rows for best performance)
-- For initial deployment with few documents, sequential scan is actually faster
-- CREATE INDEX IF NOT EXISTS idx_legal_documents_embedding ON legal_documents
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for filtering by source
CREATE INDEX IF NOT EXISTS idx_legal_documents_source ON legal_documents(source);

-- Trigger to automatically update 'updated_at'
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_timestamp ON threads;
CREATE TRIGGER trg_update_timestamp
BEFORE UPDATE ON threads
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trg_update_timestamp_legal_docs ON legal_documents;
CREATE TRIGGER trg_update_timestamp_legal_docs
BEFORE UPDATE ON legal_documents
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();
