#!/usr/bin/env python
"""
Check database status and connection
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

async def check_database():
    """Check which database is connected and query hosts"""
    try:
        from app.db.postgresql.connection import postgresql_manager, USE_POSTGRESQL, engine
        from app.core.config import settings
        
        print("="*60)
        print("🔍 DATABASE CONNECTION STATUS")
        print("="*60)
        
        # Check configuration
        print(f"\n📋 Configuration:")
        print(f"   use_postgresql setting: {settings.use_postgresql}")
        print(f"   Actually using PostgreSQL: {USE_POSTGRESQL}")
        print(f"   PostgreSQL URL: {settings.async_postgres_url}")
        print(f"   SQLite fallback URL: {settings.database_url}")
        
        # Check health
        print(f"\n🏥 Health Check:")
        is_healthy = await postgresql_manager.health_check()
        print(f"   Database healthy: {'✅ YES' if is_healthy else '❌ NO'}")
        
        if not is_healthy:
            print("\n❌ Database is not responding!")
            return
        
        # Check which database type
        print(f"\n💾 Connected to: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
        
        # Try to query hosts table
        print(f"\n👥 Checking hosts table:")
        async with await postgresql_manager.get_session() as session:
            try:
                # Check if table exists
                result = await session.execute(
                    text("SELECT COUNT(*) as count FROM hosts")
                )
                count = result.scalar()
                print(f"   ✅ Hosts table exists")
                print(f"   📊 Total hosts: {count}")
                
                if count > 0:
                    print(f"\n👤 Host accounts:")
                    result = await session.execute(
                        text("SELECT id, email, first_name, last_name, is_active FROM hosts")
                    )
                    for row in result:
                        print(f"   • {row.email} ({row.first_name} {row.last_name}) - Active: {row.is_active}")
                else:
                    print(f"\n⚠️  No host accounts found in database")
                    print(f"   Need to create a host account via:")
                    print(f"   1. Onboarding flow: http://localhost:3002/onboarding")
                    print(f"   2. API registration: http://localhost:8000/api/v1/docs")
                    
            except Exception as e:
                if "no such table" in str(e).lower():
                    print(f"   ❌ Table 'hosts' does not exist")
                    print(f"   Need to run database initialization!")
                else:
                    print(f"   ❌ Error querying hosts: {e}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_database())
