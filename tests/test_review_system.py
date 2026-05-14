"""
Tests for the enhanced review and moderation system.

Tests cover review creation, moderation, analytics, and guest submission.
"""

import pytest
from datetime import datetime, date, timedelta
from httpx import AsyncClient
import uuid

from app.models import (
    ReviewStatus, ReviewModerationAction, AttractionReviewCreate,
    ReviewModerationRequest, GuestReviewSubmission
)


class TestReviewSystem:
    """Test suite for the enhanced review system."""

    @pytest.fixture
    async def sample_attraction(self, async_client: AsyncClient, host_token_headers):
        """Create a sample attraction for testing."""
        attraction_data = {
            "name": "Test Attraction for Reviews",
            "description": "A test attraction for review system testing",
            "attraction_type": "cultural",
            "city": "Lovran",
            "region": "Istria"
        }
        
        response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=host_token_headers
        )
        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    async def sample_guest_group(self, async_client: AsyncClient, host_token_headers):
        """Create a sample guest group for testing."""
        guest_group_data = {
            "group_name": "Test Review Group",
            "group_size": 4,
            "preferred_language": "en",
            "interests": ["culture", "history"],
            "budget_level": "moderate"
        }
        
        response = await async_client.post(
            "/api/v1/guest-groups/",
            json=guest_group_data,
            headers=host_token_headers
        )
        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    async def sample_access_code(self, async_client: AsyncClient, host_token_headers, sample_guest_group):
        """Create an access code for guest group."""
        access_code_data = {
            "guest_group_id": sample_guest_group["id"],
            "expires_in_hours": 168
        }
        
        response = await async_client.post(
            "/api/v1/guest-groups/access-codes/",
            json=access_code_data,
            headers=host_token_headers
        )
        assert response.status_code == 201
        return response.json()["code"]

    async def test_guest_review_submission_with_access_code(
        self, async_client: AsyncClient, sample_attraction, sample_access_code
    ):
        """Test guest review submission using access code."""
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=5,
            title="Amazing Experience!",
            review_text="This was an incredible attraction with rich history and beautiful views.",
            visit_date=date.today(),
            group_size=4,
            pros=["Beautiful views", "Rich history", "Friendly staff"],
            cons=["Crowded during peak hours"],
            tips_for_others="Visit early morning for best experience",
            guest_age_group="adults",
            guest_travel_style="cultural",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        
        assert response.status_code == 201
        review = response.json()
        assert review["rating"] == 5
        assert review["title"] == "Amazing Experience!"
        assert review["status"] == ReviewStatus.PENDING
        assert review["quality_score"] > 0.5

    async def test_guest_review_submission_invalid_access_code(
        self, async_client: AsyncClient, sample_attraction
    ):
        """Test guest review submission with invalid access code."""
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=4,
            title="Good place",
            review_text="Nice attraction",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code="INVALID123",
            review_data=review_data
        )
        
        response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        
        assert response.status_code == 401
        assert "Invalid or expired access code" in response.json()["detail"]

    async def test_get_reviews_for_moderation(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test getting reviews that need moderation."""
        # First submit a review
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=4,
            title="Nice place",
            review_text="Good attraction for families",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        
        # Get reviews for moderation
        response = await async_client.get(
            "/api/v1/attractions/host/reviews/moderation",
            headers=host_token_headers
        )
        
        assert response.status_code == 200
        reviews = response.json()
        assert len(reviews) >= 1
        assert reviews[0]["status"] == ReviewStatus.PENDING

    async def test_moderate_review_approve(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test approving a review."""
        # Submit a review first
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=5,
            title="Excellent!",
            review_text="Highly recommended attraction",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        review_response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        review_id = review_response.json()["id"]
        
        # Approve the review
        moderation_request = ReviewModerationRequest(
            action=ReviewModerationAction.APPROVE,
            reason="High quality review with helpful details",
            notes="Approved - great content",
            host_response="Thank you for the wonderful review!"
        )
        
        response = await async_client.post(
            f"/api/v1/attractions/reviews/{review_id}/moderate",
            json=moderation_request.model_dump(),
            headers=host_token_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["new_status"] == ReviewStatus.APPROVED
        assert result["action_taken"] == ReviewModerationAction.APPROVE

    async def test_moderate_review_reject(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test rejecting a review."""
        # Submit a review first
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=1,
            title="Bad",
            review_text="Not good",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        review_response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        review_id = review_response.json()["id"]
        
        # Reject the review
        moderation_request = ReviewModerationRequest(
            action=ReviewModerationAction.REJECT,
            reason="Insufficient detail and not constructive",
            notes="Please provide more specific feedback"
        )
        
        response = await async_client.post(
            f"/api/v1/attractions/reviews/{review_id}/moderate",
            json=moderation_request.model_dump(),
            headers=host_token_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["new_status"] == ReviewStatus.REJECTED
        assert result["action_taken"] == ReviewModerationAction.REJECT

    async def test_verify_visit(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test verifying a guest's visit."""
        # Submit and approve a review first
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=4,
            title="Great visit",
            review_text="Really enjoyed our time here",
            visit_date=date.today(),
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        review_response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        review_id = review_response.json()["id"]
        
        # Verify the visit
        moderation_request = ReviewModerationRequest(
            action=ReviewModerationAction.VERIFY_VISIT,
            reason="Confirmed guest visited on specified date",
            notes="Visit verified through booking records"
        )
        
        response = await async_client.post(
            f"/api/v1/attractions/reviews/{review_id}/moderate",
            json=moderation_request.model_dump(),
            headers=host_token_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["action_taken"] == ReviewModerationAction.VERIFY_VISIT

    async def test_get_approved_reviews_only(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test getting only approved reviews for public viewing."""
        # Submit and approve a review
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=5,
            title="Approved Review",
            review_text="This is an approved review",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        review_response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        review_id = review_response.json()["id"]
        
        # Approve the review
        moderation_request = ReviewModerationRequest(
            action=ReviewModerationAction.APPROVE,
            notes="Good review"
        )
        
        await async_client.post(
            f"/api/v1/attractions/reviews/{review_id}/moderate",
            json=moderation_request.model_dump(),
            headers=host_token_headers
        )
        
        # Get public reviews (should only show approved)
        response = await async_client.get(
            f"/api/v1/attractions/{sample_attraction['id']}/reviews"
        )
        
        assert response.status_code == 200
        reviews = response.json()
        for review in reviews:
            assert review["status"] == ReviewStatus.APPROVED

    async def test_review_analytics(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test getting review analytics for an attraction."""
        # Submit and approve multiple reviews with different ratings
        ratings = [5, 4, 5, 3, 4]
        
        for i, rating in enumerate(ratings):
            review_data = AttractionReviewCreate(
                attraction_id=sample_attraction["id"],
                rating=rating,
                title=f"Review {i+1}",
                review_text=f"This is review number {i+1}",
                language="en"
            )
            
            submission = GuestReviewSubmission(
                access_code=sample_access_code,
                review_data=review_data
            )
            
            review_response = await async_client.post(
                "/api/v1/attractions/reviews/submit",
                json=submission.model_dump()
            )
            review_id = review_response.json()["id"]
            
            # Approve some reviews
            if i < 3:  # Approve first 3 reviews
                moderation_request = ReviewModerationRequest(
                    action=ReviewModerationAction.APPROVE,
                    notes=f"Approved review {i+1}"
                )
                
                await async_client.post(
                    f"/api/v1/attractions/reviews/{review_id}/moderate",
                    json=moderation_request.model_dump(),
                    headers=host_token_headers
                )
        
        # Get analytics
        response = await async_client.get(
            f"/api/v1/attractions/{sample_attraction['id']}/reviews/analytics",
            headers=host_token_headers
        )
        
        assert response.status_code == 200
        analytics = response.json()
        assert analytics["total_reviews"] == 5
        assert analytics["approved_reviews"] == 3
        assert analytics["pending_reviews"] == 2
        assert analytics["average_rating"] is not None
        assert len(analytics["rating_distribution"]) > 0

    async def test_host_review_stats(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test getting host review statistics."""
        # Submit a review first
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=4,
            title="Test Review for Stats",
            review_text="Testing host stats",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        
        # Get host stats
        response = await async_client.get(
            "/api/v1/attractions/host/reviews/stats",
            headers=host_token_headers
        )
        
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_reviews_received"] >= 1
        assert stats["pending_moderation"] >= 1
        assert "verification_rate" in stats
        assert "response_rate" in stats

    async def test_review_search_and_filtering(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test advanced review search and filtering."""
        # Submit reviews with different characteristics
        review_configs = [
            {"rating": 5, "language": "en", "verified": True},
            {"rating": 3, "language": "hr", "verified": False},
            {"rating": 4, "language": "en", "verified": True}
        ]
        
        for i, config in enumerate(review_configs):
            review_data = AttractionReviewCreate(
                attraction_id=sample_attraction["id"],
                rating=config["rating"],
                title=f"Search Test Review {i+1}",
                review_text=f"Review in {config['language']}",
                visit_date=date.today() - timedelta(days=i),
                language=config["language"]
            )
            
            submission = GuestReviewSubmission(
                access_code=sample_access_code,
                review_data=review_data
            )
            
            review_response = await async_client.post(
                "/api/v1/attractions/reviews/submit",
                json=submission.model_dump()
            )
            review_id = review_response.json()["id"]
            
            # Approve and optionally verify
            moderation_request = ReviewModerationRequest(
                action=ReviewModerationAction.APPROVE,
                notes=f"Approved search test review {i+1}"
            )
            
            await async_client.post(
                f"/api/v1/attractions/reviews/{review_id}/moderate",
                json=moderation_request.model_dump(),
                headers=host_token_headers
            )
            
            if config["verified"]:
                verify_request = ReviewModerationRequest(
                    action=ReviewModerationAction.VERIFY_VISIT,
                    notes="Verified visit"
                )
                
                await async_client.post(
                    f"/api/v1/attractions/reviews/{review_id}/moderate",
                    json=verify_request.model_dump(),
                    headers=host_token_headers
                )
        
        # Test search with filters
        search_request = {
            "attraction_id": sample_attraction["id"],
            "status": ReviewStatus.APPROVED,
            "rating_min": 4,
            "language": "en",
            "verified_only": True,
            "skip": 0,
            "limit": 10
        }
        
        response = await async_client.post(
            "/api/v1/attractions/reviews/search",
            json=search_request,
            headers=host_token_headers
        )
        
        assert response.status_code == 200
        search_results = response.json()
        assert search_results["total_count"] >= 1
        assert len(search_results["reviews"]) >= 1
        
        # Verify filters were applied
        for review in search_results["reviews"]:
            assert review["rating"] >= 4
            assert review["language"] == "en"
            assert review["status"] == ReviewStatus.APPROVED

    async def test_review_helpfulness_voting(
        self, async_client: AsyncClient, host_token_headers, sample_attraction, sample_access_code
    ):
        """Test voting on review helpfulness."""
        # Submit and approve a review first
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=5,
            title="Helpful Review",
            review_text="Very detailed and helpful review",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        review_response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        review_id = review_response.json()["id"]
        
        # Approve the review
        moderation_request = ReviewModerationRequest(
            action=ReviewModerationAction.APPROVE,
            notes="Good review"
        )
        
        await async_client.post(
            f"/api/v1/attractions/reviews/{review_id}/moderate",
            json=moderation_request.model_dump(),
            headers=host_token_headers
        )
        
        # Vote on helpfulness
        vote_data = {"helpful": True}
        
        response = await async_client.post(
            f"/api/v1/attractions/reviews/{review_id}/helpful",
            json=vote_data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["helpful"] == True

    async def test_moderate_review_unauthorized(
        self, async_client: AsyncClient, sample_attraction, sample_access_code
    ):
        """Test that only the review's host can moderate it."""
        # This would require creating another host and trying to moderate
        # a review that doesn't belong to them. For now, we'll test
        # moderation without authentication.
        
        review_data = AttractionReviewCreate(
            attraction_id=sample_attraction["id"],
            rating=3,
            title="Unauthorized Test",
            review_text="Testing unauthorized moderation",
            language="en"
        )
        
        submission = GuestReviewSubmission(
            access_code=sample_access_code,
            review_data=review_data
        )
        
        review_response = await async_client.post(
            "/api/v1/attractions/reviews/submit",
            json=submission.model_dump()
        )
        review_id = review_response.json()["id"]
        
        # Try to moderate without authentication
        moderation_request = ReviewModerationRequest(
            action=ReviewModerationAction.APPROVE,
            notes="Unauthorized attempt"
        )
        
        response = await async_client.post(
            f"/api/v1/attractions/reviews/{review_id}/moderate",
            json=moderation_request.model_dump()
            # No headers = no authentication
        )
        
        assert response.status_code == 401  # Unauthorized 