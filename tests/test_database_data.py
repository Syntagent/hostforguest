#!/usr/bin/env python3
"""
Test script to check what real data exists in the database for analytics.
"""

import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def check_database_data():
    """Check what real data exists in the database for analytics."""
    
    try:
        # Import required modules
        from app.core.database import get_db
        from app.models.host import Host
        from app.models.guest_group import GuestGroup
        from app.models.attraction import Attraction, AttractionReview
        from app.models.recommendation import RecommendationSet
        from sqlalchemy import select, func
        
        print("🔍 Checking Database for Real Analytics Data")
        print("=" * 60)
        
        # Get database session
        async for db in get_db():
            print("✅ Database connection established")
            
            # Check hosts
            hosts_result = await db.execute(select(func.count(Host.id)))
            total_hosts = hosts_result.scalar()
            print(f"📊 Total Hosts: {total_hosts}")
            
            if total_hosts > 0:
                # Get first host for testing
                host_result = await db.execute(select(Host).limit(1))
                host = host_result.scalar_one()
                print(f"   Sample Host: {host.first_name} {host.last_name} ({host.email})")
                
                # Check guest groups for this host
                groups_result = await db.execute(
                    select(func.count(GuestGroup.id)).where(GuestGroup.host_id == host.id)
                )
                total_groups = groups_result.scalar()
                print(f"   Guest Groups for this host: {total_groups}")
                
                # Check attractions for this host
                attractions_result = await db.execute(
                    select(func.count(Attraction.id)).where(Attraction.created_by_host_id == host.id)
                )
                total_attractions = attractions_result.scalar()
                print(f"   Attractions for this host: {total_attractions}")
                
                # Check recommendations for this host
                recommendations_result = await db.execute(
                    select(func.count(RecommendationSet.id)).where(RecommendationSet.host_id == host.id)
                )
                total_recommendations = recommendations_result.scalar()
                print(f"   Recommendations for this host: {total_recommendations}")
                
                # Check reviews for this host
                reviews_result = await db.execute(
                    select(func.count(AttractionReview.id)).where(AttractionReview.host_id == host.id)
                )
                total_reviews = reviews_result.scalar()
                print(f"   Reviews for this host: {total_reviews}")
                
                if total_reviews > 0:
                    # Get average rating
                    avg_rating_result = await db.execute(
                        select(func.avg(AttractionReview.rating)).where(AttractionReview.host_id == host.id)
                    )
                    avg_rating = avg_rating_result.scalar()
                    print(f"   Average Rating: {avg_rating:.1f}/5")
                
                print(f"\n🎯 Analytics Endpoint Should Return:")
                print(f"   Guest Groups: {{'total': {total_groups}, 'active': 0, 'inactive': {total_groups}}}")
                print(f"   Attractions: {{'total': {total_attractions}, 'categories': {{}}}}")
                print(f"   Recommendations: {{'total_given': {total_recommendations}, 'this_month': 0}}")
                print(f"   Satisfaction: {{'average_rating': {avg_rating if total_reviews > 0 else 0.0}, 'total_reviews': {total_reviews}}}")
                
                if total_groups == 0 and total_attractions == 0 and total_recommendations == 0:
                    print("\n⚠️  WARNING: No data found for analytics!")
                    print("   This explains why you're seeing 0s in the dashboard.")
                    print("   You need to create some test data first:")
                    print("   1. Create a guest group")
                    print("   2. Add some attractions")
                    print("   3. Generate some recommendations")
                    print("   4. Add some reviews")
                else:
                    print("\n✅ Data found! Analytics should show real numbers.")
                    print("   If you're still seeing 0s, try refreshing the frontend.")
                    
            else:
                print("❌ No hosts found in database!")
                print("   You need to register a host first.")
            
            break  # Exit the async generator
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Checking Database for Real Analytics Data")
    print("=" * 60)
    
    success = asyncio.run(check_database_data())
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Database check completed!")
    else:
        print("\n" + "=" * 60)
        print("❌ Database check failed. Check the errors above.")
        sys.exit(1)
