-- DocIntel AI — Supabase Schema
-- Run this in the Supabase SQL Editor to create all tables
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    organization_id VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Documents ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name   VARCHAR(500) NOT NULL,
    file_path   VARCHAR(1000) NOT NULL,
    page_count  INTEGER DEFAULT 0,
    file_size   BIGINT DEFAULT 0,
    status      VARCHAR(50) DEFAULT 'processing',  -- processing | ready | failed
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    indexed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status  ON documents(status);

-- ── Queries (Chat history) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS queries (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id      UUID REFERENCES documents(id) ON DELETE SET NULL,
    question         TEXT NOT NULL,
    answer           TEXT,
    mode             VARCHAR(50) DEFAULT 'normal',  -- normal | deep
    response_time_ms FLOAT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_created ON queries(created_at);

-- ── Summaries ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS summaries (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id  UUID REFERENCES documents(id) ON DELETE CASCADE,
    summary_type VARCHAR(50) DEFAULT 'short',  -- short | executive | exam
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_summaries_user_id ON summaries(user_id);

-- ── Exports ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exports (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    export_type VARCHAR(50) DEFAULT 'pdf',  -- pdf | json | text
    file_path   VARCHAR(1000),
    file_size   BIGINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exports_user_id ON exports(user_id);

-- ── Enable Realtime on all tables ─────────────────────────────────────────────
-- Run these in the Supabase dashboard → Database → Replication
-- or via the SQL editor:

ALTER PUBLICATION supabase_realtime ADD TABLE documents;
ALTER PUBLICATION supabase_realtime ADD TABLE queries;
ALTER PUBLICATION supabase_realtime ADD TABLE summaries;
ALTER PUBLICATION supabase_realtime ADD TABLE exports;

-- ── Row Level Security (RLS) ──────────────────────────────────────────────────
-- Enable RLS on all tables (backend uses service key which bypasses RLS)
ALTER TABLE users      ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents  ENABLE ROW LEVEL SECURITY;
ALTER TABLE queries    ENABLE ROW LEVEL SECURITY;
ALTER TABLE summaries  ENABLE ROW LEVEL SECURITY;
ALTER TABLE exports    ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (backend uses service key)
-- Frontend uses anon key only for Realtime subscriptions, not direct DB access

-- ── Updated_at trigger for users ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
