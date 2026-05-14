#!/usr/bin/env python
"""
Check and create test user for dev login
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uuid

# Initialize password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database configuration
DATABASE_URL = "sqlite:///./tourist_guide.db"
engine = create_engine(DATABASE_URL)

def check_and_create_test_user():
    """Check if test  user exists, create if not"""
    
    test_email = "benedikt.perak@gmail.com"
    test_password = "test123"
    
    with Session(engine) as session:
        # Check if user exists
        result = session.execute(
            text("SELECT id, email, first_name, last_name FROM hosts WHERE email = :email"),
            {"email": test_email}
        )
        user = result.fetchone()
        
        if user:
            print(f"✅ Test user already exists:")
            print(f"   Email: {user[1]}")
            print(f"   Name: {user[2]} {user[3]}")
            print(f"   ID: {user[0]}")
            return True
        
        # User doesn't exist, create it
        print(f"⚠️  Test user not found. Creating...")
        
        # Hash the password
        hashed_password = pwd_context.hash(test_password)
        user_id = str(uuid.uuid4())
        
        # Create the user
        session.execute(
            text("""
                INSERT INTO hosts (id, email, password_hash, first_name, last_name, is_active, created_at, updated_at)
                VALUES (:id, :email, :password, :first_name, :last_name, :is_active, datetime('now'), datetime('now'))
            """),
            {
                "id": user_id,
                "email": test_email,
                "password": hashed_password,
                "first_name": "Benedikt",
                "last_name": "Perak",
                "is_active": True
            }
        )
        
        session.commit()
        
        print(f"✅ Test user created successfully!")
        print(f"   Email: {test_email}")
        print(f"   Password: {test_password}")
        print(f"   ID: {user_id}")
        
        return True

if __name__ == "__main__":
    try:
        check_and_create_test_user()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
