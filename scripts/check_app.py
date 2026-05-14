#!/usr/bin/env python
"""
Quick check script for TouristGuideLocal application.
Tests backend and frontend connectivity.
"""
import requests
import time
import sys

def check_backend():
    """Check if backend is running."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running on http://localhost:8000")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"⚠️ Backend responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend is NOT running on http://localhost:8000")
        print("   Start it with: python start.py")
        return False
    except Exception as e:
        print(f"❌ Backend check failed: {e}")
        return False

def check_frontend():
    """Check if frontend is running."""
    ports = [3000, 3001, 3002]
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}", timeout=5)
            if response.status_code == 200:
                print(f"✅ Frontend is running on http://localhost:{port}")
                return True, port
        except requests.exceptions.ConnectionError:
            continue
        except Exception as e:
            continue
    
    print("❌ Frontend is NOT running on any port (3000, 3001, 3002)")
    print("   Start it with: cd frontend && npm run dev:3002")
    return False, None

def check_api_endpoint():
    """Check if API endpoint is accessible."""
    try:
        response = requests.get("http://localhost:8000/api/v1/hosts/me", timeout=5)
        print(f"   API endpoint status: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("   ⚠️ API endpoint not reachable (backend might not be running)")
        return False
    except Exception as e:
        print(f"   ℹ️ API endpoint check: {e}")
        return True  # Endpoint exists, just needs auth

if __name__ == "__main__":
    print("=" * 60)
    print("TouristGuideLocal Application Check")
    print("=" * 60)
    print()
    
    backend_ok = check_backend()
    print()
    
    frontend_ok, frontend_port = check_frontend()
    print()
    
    if backend_ok:
        check_api_endpoint()
        print()
    
    print("=" * 60)
    if backend_ok and frontend_ok:
        print("✅ Application is ready!")
        print(f"   Frontend: http://localhost:{frontend_port}")
        print("   Backend: http://localhost:8000")
        print("   API Docs: http://localhost:8000/docs")
    else:
        print("⚠️ Some services are not running")
        print("   Please start the missing services and run this check again")
    print("=" * 60)











