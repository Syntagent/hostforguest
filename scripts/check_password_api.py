"""
Password Reset via API
Use the backend API to reset the password
"""
import requests
import json

print("="*60)
print("🔐 PASSWORD RESET VIA API")
print("="*60)

API_BASE = "http://localhost:8000/api/v1"

# First, let's check if there's a password reset endpoint
print("\n📋 Available Options:")
print("1. Check API documentation")
print("2. Create password reset endpoint")
print("3. Manual database update")

print("\n🔍 Checking API endpoints...")

try:
    # Get API docs
    response = requests.get(f"{API_BASE}/openapi.json")
    if response.status_code == 200:
        api_spec = response.json()
        paths = api_spec.get('paths', {})
        
        # Look for password-related endpoints
        relevant_endpoints = []
        for path, methods in paths.items():
            if 'password' in path.lower() or 'reset' in path.lower():
                relevant_endpoints.append(path)
        
        if relevant_endpoints:
            print(f"\n✅ Found password endpoints:")
            for endpoint in relevant_endpoints:
                print(f"   • {endpoint}")
        else:
            print(f"\n⚠️  No password reset endpoint found")
            print(f"   We'll need to update the database directly")
    
except Exception as e:
    print(f"❌ Could not fetch API docs: {e}")

print("\n" + "="*60)
print("\n💡 RECOMMENDED SOLUTION:")
print("\nSince we can't easily reset the password, the easiest approach is:")
print("\n1. ✅ Create a NEW account via onboarding:")
print("   http://localhost:3002/onboarding")
print("\n2. ✅ OR: I can create a simple SQL file you can run")
print("\n" + "="*60)
