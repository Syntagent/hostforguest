"""
Simple test for AI attraction content generation feature.
"""

import asyncio
import httpx
import json

async def test_ai_attraction_generation():
    """Test the AI attraction content generation endpoint."""
    
    # Test data
    test_data = {
        "name": "Konoba Stari Grad",
        "category": "Restaurant", 
        "location": "Lovran, Istria"
    }
    
    print("🧪 Testing AI Attraction Content Generation...")
    print(f"📝 Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        # Make request to the API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/attractions/generate-content",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ AI content generation successful!")
                print(f"📊 Data source: {data.get('data_source', 'unknown')}")
                print(f"🔗 Sources used: {data.get('sources_used', 0)}")
                print(f"🎯 Personalization: {data.get('personalization_level', 'unknown')}")
                
                if 'content' in data:
                    content = data['content']
                    print(f"📝 Generated content:")
                    print(f"   Name: {content.get('name', 'N/A')}")
                    print(f"   Category: {content.get('category', 'N/A')}")
                    print(f"   Location: {content.get('location', 'N/A')}")
                    print(f"   Description: {content.get('description', 'N/A')[:100]}...")
                    print(f"   Cost: {content.get('cost_estimate', 'N/A')}")
                    print(f"   Authenticity: {content.get('authenticity_level', 'N/A')}")
                    print(f"   Enhanced: {content.get('enhanced', False)}")
                    print(f"   AI Generated: {content.get('ai_generated', False)}")
                
                return True
            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing AI attraction generation: {e}")
        return False

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_ai_attraction_generation())
    if result:
        print("\n🎉 AI attraction generation test PASSED!")
    else:
        print("\n💥 AI attraction generation test FAILED!")
