#!/usr/bin/env python
"""
Reset password using direct SQL - Works around async issues
"""
import sys
import os

# Very simple - just generate the hash and show the SQL
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

email = "benedikt.perak@gmail.com"
new_password = "test123"

print("="*60)
print("🔐 PASSWORD RESET - SQL GENERATOR")
print("="*60)

# Generate the hash
print(f"\n🔒 Generating password hash for: {new_password}")
password_hash = pwd_context.hash(new_password)
print(f"✅ Hash generated")

# Show the SQL to run
print(f"\n📋 Run this SQL command to reset password:")
print(f"\n" + "-"*60)
print(f"UPDATE hosts")
print(f"SET password_hash = '{password_hash}'")
print(f"WHERE email = '{email}';")
print(f"-"*60)

# Try to run it
print(f"\n🔄 Attempting to execute...")

try:
    import psycopg2
    
    conn = psycopg2.connect(
        host="localhost",
        port=5434,
        database="tourist_guide_db",
        user="tourist_guide_user",
        password=""
    )
    
    cur = conn.cursor()
    cur.execute(
        "UPDATE hosts SET password_hash = %s WHERE email = %s RETURNING id, email, first_name, last_name",
        (password_hash, email)
    )
    
    result = cur.fetchone()
    conn.commit()
    
    if result:
        print(f"✅ Password reset successful!")
        print(f"\n📋 Account Updated:")
        print(f"   ID: {result[0]}")
        print(f"   Email: {result[1]}")
        print(f"   Name: {result[2]} {result[3]}")
        print(f"\n🔑 NEW CREDENTIALS:")
        print(f"   📧 Email: {email}")
        print(f"   🔒 Password: {new_password}")
        print(f"\n✅ DEV LOGIN NOW WORKS!")
        success  = True
    else:
        print(f"❌ No user found with email: {email}")
        success = False
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"⚠️  Could not connect to database directly")
    print(f"   Error: {e}")
    print(f"\n📝 Manual option: Run the SQL above manually")
    success = False

print("\n" + "="*60)
sys.exit(0 if success else 1)
