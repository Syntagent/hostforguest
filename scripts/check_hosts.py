#!/usr/bin/env python3
"""
Simple script to check hosts in the database
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import get_db

async def main():
    try:
        async for db in get_db():
            # Check hosts table
            result = await db.execute('SELECT id, email, first_name, last_name FROM hosts LIMIT 5')
            hosts = result.fetchall()
            print(f"Found {len(hosts)} hosts:")
            for host in hosts:
                print(f"  - {host[1]} ({host[2]} {host[3]})")
            
            # Check user_sessions table
            result = await db.execute('SELECT host_id, session_token, is_active FROM user_sessions LIMIT 5')
            sessions = result.fetchall()
            print(f"\nFound {len(sessions)} sessions:")
            for session in sessions:
                print(f"  - Host: {session[0]}, Active: {session[2]}")
            
            break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
