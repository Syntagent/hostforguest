#!/usr/bin/env python
"""Test direct PostgreSQL connection."""

import asyncio
import asyncpg

async def test_connection():
    """Test direct connection to PostgreSQL."""
    try:
        # Try connection without password
        conn = await asyncpg.connect(
            host='localhost',
            port=5434,
            user='tourist_guide_user',
            database='tourist_guide_db'
        )
        
        result = await conn.fetchrow('SELECT 1 as test')
        print(f"✅ Connection successful! Result: {result}")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        
        # Try with empty password
        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5434,
                user='tourist_guide_user',
                password='',
                database='tourist_guide_db'
            )
            
            result = await conn.fetchrow('SELECT 1 as test')
            print(f"✅ Connection with empty password successful! Result: {result}")
            await conn.close()
            
        except Exception as e2:
            print(f"❌ Connection with empty password also failed: {e2}")

if __name__ == "__main__":
    asyncio.run(test_connection())
