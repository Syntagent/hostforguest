#!/usr/bin/env python3
"""
Setup script to configure AI API keys for TouristGuideLocal.

This script helps you set up API keys for OpenAI and Google AI (Gemini)
so that the AI-powered features work properly.
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import get_db
from app.models.settings import HostSettings
from app.services.settings_service import SettingsService

async def setup_ai_keys():
    """Setup AI API keys for the system."""
    print("🤖 TouristGuideLocal AI Configuration Setup")
    print("=" * 50)
    print()
    
    # Check if we should use environment variables
    print("You can provide API keys in two ways:")
    print("1. Environment variables (recommended for development)")
    print("2. Database storage (recommended for production)")
    print()
    
    choice = input("Use environment variables? (y/n): ").lower().strip()
    
    if choice == 'y':
        await setup_env_variables()
    else:
        await setup_database_keys()

async def setup_env_variables():
    """Setup API keys using environment variables."""
    print("\n📝 Setting up environment variables...")
    print()
    
    # Check current .env file
    env_file = ".env"
    env_content = []
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.readlines()
    
    # API key prompts
    openai_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
    google_key = input("Enter your Google AI API key (or press Enter to skip): ").strip()
    
    # Update .env file
    new_env_lines = []
    openai_set = False
    google_set = False
    
    for line in env_content:
        if line.startswith('OPENAI_API_KEY='):
            if openai_key:
                new_env_lines.append(f'OPENAI_API_KEY={openai_key}\n')
                openai_set = True
            else:
                new_env_lines.append(line)
        elif line.startswith('GOOGLE_AI_API_KEY='):
            if google_key:
                new_env_lines.append(f'GOOGLE_AI_API_KEY={google_key}\n')
                google_set = True
            else:
                new_env_lines.append(line)
        else:
            new_env_lines.append(line)
    
    # Add new keys if not already present
    if openai_key and not openai_set:
        new_env_lines.append(f'OPENAI_API_KEY={openai_key}\n')
    
    if google_key and not google_set:
        new_env_lines.append(f'GOOGLE_AI_API_KEY={google_key}\n')
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.writelines(new_env_lines)
    
    print(f"\n✅ Environment variables updated in {env_file}")
    print("\n📋 To get API keys:")
    print("• OpenAI: https://platform.openai.com/api-keys")
    print("• Google AI: https://aistudio.google.com/app/apikey")
    print("\n🔄 Restart your application to use the new keys.")

async def setup_database_keys():
    """Setup API keys in the database."""
    print("\n🗄️ Setting up database API keys...")
    print("Note: This requires a running database and a host account.")
    print()
    
    try:
        # Create database session
        if settings.use_postgresql:
            engine = create_async_engine(settings.async_postgres_url)
        else:
            engine = create_async_engine(settings.database_url)
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            settings_service = SettingsService(session)
            
            # Get host ID
            host_id = input("Enter host ID (UUID): ").strip()
            if not host_id:
                print("❌ Host ID is required for database setup.")
                return
            
            # Get API keys
            openai_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
            google_key = input("Enter your Google AI API key (or press Enter to skip): ").strip()
            
            # Store keys in database
            if openai_key:
                await settings_service.set_host_api_key(host_id, "openai", openai_key)
                print("✅ OpenAI API key stored in database")
            
            if google_key:
                await settings_service.set_host_api_key(host_id, "google_ai", google_key)
                print("✅ Google AI API key stored in database")
            
            # Set up default AI configuration
            ai_config = {
                "preferred_ai_provider": "google",  # Default to Gemini
                "openai_model": "gpt-4o",
                "gemini_model": "gemini-2.5-flash",
                "gemini_pro_model": "gemini-2.5-pro",
                "gemini_temperature": "0.7",
                "embedding_provider": "openai",
                "embedding_model": "text-embedding-3-small",
                "default_language": "en"
            }
            
            await settings_service.update_host_settings(host_id, {"ai_config": ai_config})
            print("✅ Default AI configuration set")
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("Make sure your database is running and accessible.")

async def check_ai_setup():
    """Check current AI setup status."""
    print("\n🔍 Checking AI Setup Status...")
    print("=" * 30)
    
    # Check environment variables
    openai_env = os.getenv('OPENAI_API_KEY')
    google_env = os.getenv('GOOGLE_AI_API_KEY')
    
    print(f"OpenAI API Key (env): {'✅ Set' if openai_env else '❌ Not set'}")
    print(f"Google AI API Key (env): {'✅ Set' if google_env else '❌ Not set'}")
    
    # Check if we can import AI libraries
    try:
        import openai
        print("OpenAI library: ✅ Available")
    except ImportError:
        print("OpenAI library: ❌ Not installed")
    
    try:
        from google import genai  # noqa: F401
        print("Google GenAI library: ✅ Available")
    except ImportError:
        print("Google GenAI library: ❌ Not installed")

if __name__ == "__main__":
    print("🚀 Starting AI setup...")
    
    # Check current status
    asyncio.run(check_ai_setup())
    print()
    
    # Run setup
    asyncio.run(setup_ai_keys())
    
    print("\n🎉 AI setup complete!")
    print("\n💡 Tips:")
    print("• Use 'python setup_ai_keys.py' to run this setup again")
    print("• For development, environment variables are recommended")
    print("• For production, database storage is more secure")
    print("• Free tier limits: OpenAI ($5 credit), Google AI (60 requests/minute)")
