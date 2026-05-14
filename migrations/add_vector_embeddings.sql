-- Migration: Add vector embeddings to attractions and guest_groups
-- This migration adds pgvector embedding columns for semantic search

-- Add embedding column to attractions table
ALTER TABLE attractions 
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Add preference_embedding column to guest_groups table
ALTER TABLE guest_groups 
ADD COLUMN IF NOT EXISTS preference_embedding vector(384);

-- Create vector indexes for performance
-- Using IVFFlat index for approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS attractions_embedding_idx 
ON attractions 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS guest_groups_preference_embedding_idx 
ON guest_groups 
USING ivfflat (preference_embedding vector_cosine_ops)
WITH (lists = 100);

-- Add full-text search index for Croatian/English content
CREATE INDEX IF NOT EXISTS attractions_fulltext_idx 
ON attractions 
USING gin(to_tsvector('croatian', COALESCE(name, '') || ' ' || COALESCE(description, '')));

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Vector embeddings migration completed successfully';
END $$;

