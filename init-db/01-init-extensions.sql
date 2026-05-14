-- PostgreSQL initialization script for TouristGuideLocal
-- Enables necessary extensions for the Croatian tourist host platform

-- Enable pgvector extension for AI embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable PostGIS for geographic data (optional)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable JSON functions
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'TouristGuideLocal database extensions initialized successfully';
END $$; 