#!/usr/bin/env python3
"""
Migration script to create user_sessions table.
"""

import asyncio
from sqlalchemy import text
from app.core.database import engine

async def run_migration():
    """Run the user sessions table migration."""
    try:
        async with engine.begin() as conn:
            # Read and execute migration SQL
            with open('migrations/create_user_sessions_table.sql', 'r') as f:
                migration_sql = f.read()
            
            await conn.execute(text(migration_sql))
            print("✅ User sessions table created successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
