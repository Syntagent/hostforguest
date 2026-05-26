---
name: hostforguest-pgvector
description: Fix missing pgvector extension in HostForGuest PostgreSQL Docker containers. Use when the database fails with 'extension "vector" is not available' or similar errors.
---

# HostForGuest -- pgvector Troubleshooting

## Quick Fix

If `vector` extension is missing:
   docker compose exec postgres psql -U postgres -d touristguide -c "CREATE EXTENSION IF NOT EXISTS vector;"

## Verify

Check if extension exists:
   docker compose exec postgres psql -U postgres -d touristguide -c "\\dx"

Should show `vector` in the list.

## Root Cause

The official `postgres:16` image does NOT include pgvector. You need either:
1. `pgvector/pgvector:pg16` image
2. Custom Dockerfile that installs pgvector

Current prod compose uses a custom-built image with pgvector baked in.
