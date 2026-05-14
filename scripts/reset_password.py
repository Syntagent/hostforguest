#!/usr/bin/env python
"""
Reset password for test user to 'test123' - Simple Version
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

# Initialize password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_password():
    """Reset password for benedikt.perak@gmail.com to test123"""
    
    email = "benedikt.perak@gmail.com"
    new_password = "test123"
    
    print("="*60)
    print("🔐 PASSWORD RESET UTILITY")
    print("="*60)
    
    try:
        from app.db.postgresql.connection import AsyncSessionLocal
        
        # Hash the new password
        print(f"\n🔒 Hashing new password...")
        password_hash = pwd_context.hash(new_password)
        print(f"✅ Password hashed successfully")
        
        # Update the database
        print(f"\n💾 Updating database for: {email}")
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    text("""
                        UPDATE hosts 
                        SET password_hash = :hash 
                        WHERE email = :email
                        RETURNING id, email, first_name, last_name
                    """),
                    {"hash": password_hash, "email": email}
                )
                
                updated_user = result.fetchone()
                
                if updated_user:
                    print(f"✅ Password updated successfully!")
                    print(f"\n📋 Updated Account:")
                    print(f"   Email: {updated_user.email}")
                    print(f"   Name: {updated_user.first_name} {updated_user.last_name}")
                    print(f"   ID: {updated_user.id}")
                    print(f"\n🔑 New Credentials:")
                    print(f"   Email: {email}")
                    print(f"   Password: {new_password}")
                    print(f"\n✅ You can now use the Dev Login button!")
                    print(f"   Or log in normally with these credentials.")
                    return True
                else:
                    print(f"❌ User not found: {email}")
                    print(f"   Account may not exist in database.")
                    return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n" + "="*60)

if __name__ == "__main__":
    success = asyncio.run(reset_password())
    sys.exit(0 if success else 1)
