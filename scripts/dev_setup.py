#!/usr/bin/env python3
"""
Development setup script for TouristGuideLocal.

This script helps set up the development environment with API keys
and provides guidance on getting the system running.
"""

import os
import sys

def print_header():
    """Print setup header."""
    print("🇭🇷 TouristGuideLocal Development Setup")
    print("=" * 40)
    print("Croatian Tourism Platform - AI Setup")
    print()

def check_env_file():
    """Check if .env file exists and create if needed."""
    if not os.path.exists('.env'):
        print("📝 Creating .env file from template...")
        
        # Copy from .env.example if it exists
        if os.path.exists('.env.example'):
            with open('.env.example', 'r') as source:
                content = source.read()
            with open('.env', 'w') as dest:
                dest.write(content)
            print("✅ .env file created from .env.example")
        else:
            # Create basic .env file
            basic_env = """# TouristGuideLocal Development Environment
DEBUG=true
ENVIRONMENT=development

# Add your AI API keys here:
# OPENAI_API_KEY=your_openai_key_here
# GOOGLE_AI_API_KEY=your_google_ai_key_here

# AI Configuration
PREFERRED_AI_PROVIDER=google
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.5-flash
"""
            with open('.env', 'w') as f:
                f.write(basic_env)
            print("✅ Basic .env file created")
    else:
        print("✅ .env file already exists")

def check_api_keys():
    """Check current API key status."""
    print("\n🔑 Checking API Keys...")
    
    # Load .env file manually
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    openai_key = env_vars.get('OPENAI_API_KEY', '').strip()
    google_key = env_vars.get('GOOGLE_AI_API_KEY', '').strip()
    
    print(f"OpenAI API Key: {'✅ Set' if openai_key else '❌ Not set'}")
    print(f"Google AI API Key: {'✅ Set' if google_key else '❌ Not set'}")
    
    if not openai_key and not google_key:
        print("\n⚠️  No AI API keys configured!")
        print("The AI features (onboarding, recommendations) won't work without API keys.")
        return False
    elif not openai_key:
        print("\n⚠️  Only Google AI key configured.")
        print("OpenAI features (embeddings) may not work.")
        return True
    elif not google_key:
        print("\n⚠️  Only OpenAI key configured.")
        print("Google AI features may not work.")
        return True
    else:
        print("\n✅ Both API keys configured!")
        return True

def setup_api_keys():
    """Interactive API key setup."""
    print("\n🤖 AI API Key Setup")
    print("-" * 20)
    
    print("\nTo use AI features, you need API keys from:")
    print("• OpenAI: https://platform.openai.com/api-keys")
    print("• Google AI: https://aistudio.google.com/app/apikey")
    print("\nBoth services offer free tiers:")
    print("• OpenAI: $5 free credit")
    print("• Google AI: 60 requests/minute free")
    print()
    
    setup_choice = input("Set up API keys now? (y/n): ").lower().strip()
    if setup_choice != 'y':
        print("⏭️  Skipping API key setup.")
        return
    
    # Read current .env
    env_lines = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_lines = f.readlines()
    
    # Get API keys
    print("\nEnter your API keys (or press Enter to skip):")
    openai_key = input("OpenAI API Key: ").strip()
    google_key = input("Google AI API Key: ").strip()
    
    # Update .env file
    new_lines = []
    openai_updated = False
    google_updated = False
    
    for line in env_lines:
        if line.startswith('OPENAI_API_KEY='):
            if openai_key:
                new_lines.append(f'OPENAI_API_KEY={openai_key}\n')
                openai_updated = True
            else:
                new_lines.append(line)
        elif line.startswith('GOOGLE_AI_API_KEY='):
            if google_key:
                new_lines.append(f'GOOGLE_AI_API_KEY={google_key}\n')
                google_updated = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Add new keys if not already present
    if openai_key and not openai_updated:
        new_lines.append(f'OPENAI_API_KEY={openai_key}\n')
    
    if google_key and not google_updated:
        new_lines.append(f'GOOGLE_AI_API_KEY={google_key}\n')
    
    # Write updated .env
    with open('.env', 'w') as f:
        f.writelines(new_lines)
    
    print("\n✅ API keys saved to .env file")

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking Dependencies...")
    
    missing_deps = []
    
    try:
        import openai
        print("✅ OpenAI library installed")
    except ImportError:
        print("❌ OpenAI library missing")
        missing_deps.append("openai")
    
    try:
        from google import genai  # noqa: F401
        print("✅ Google GenAI library installed")
    except ImportError:
        print("❌ Google GenAI library missing")
        missing_deps.append("google-genai")
    
    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install " + " ".join(missing_deps))
        return False
    
    return True

def print_next_steps():
    """Print next steps for the user."""
    print("\n🚀 Next Steps:")
    print("1. Start the backend server:")
    print("   python start.py")
    print()
    print("2. Start the frontend (in a new terminal):")
    print("   cd frontend")
    print("   npm run dev")
    print()
    print("3. Visit the application:")
    print("   Backend API: http://localhost:8000")
    print("   Frontend: http://localhost:3000")
    print()
    print("4. Test AI features:")
    print("   • Go to http://localhost:3000/onboarding")
    print("   • Try the AI-powered host profile generation")
    print("   • Create a guest group and test recommendations")
    print()
    print("💡 Tips:")
    print("• Check logs/app.log for backend issues")
    print("• Use browser dev tools for frontend debugging")
    print("• Free tier limits apply to AI services")

def main():
    """Main setup function."""
    print_header()
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Setup steps
    check_env_file()
    has_keys = check_api_keys()
    deps_ok = check_dependencies()
    
    if not has_keys:
        setup_api_keys()
    
    if not deps_ok:
        print("\n❌ Please install missing dependencies first.")
        return
    
    print_next_steps()
    print("\n🎉 Development setup complete!")
    print("Happy coding! 🇭🇷")

if __name__ == "__main__":
    main()
