"""
Attraction service layer for the Croatian tourist host platform.

Enables hosts to contribute local knowledge, create attractions,
and manage content with moderation and quality control.
"""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, date
import uuid
import requests

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models import (
    Attraction, AttractionReview, ReviewModerationLog, SeasonalEvent,
    AttractionCreate, AttractionUpdate, AttractionResponse,
    AttractionAnalyticsResponse,
    AttractionReviewCreate, AttractionReviewResponse, AttractionReviewUpdate,
    ReviewModerationRequest, ReviewModerationResponse, ReviewAnalytics,
    HostReviewStats, ReviewSearchRequest, ReviewSearchResponse,
    SeasonalEventCreate, SeasonalEventResponse, HostContributionStats,
    HostContributionCreate, HostContributionResponse,
    AttractionStatus, ReviewStatus, ReviewModerationAction
)

logger = logging.getLogger(__name__)


class AttractionService:
    """
    Service class for host-contributed attraction management.
    
    Enables hosts to create, manage, and contribute local knowledge
    to build comprehensive attraction databases for Croatian tourism.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the attraction service.
        
        Args:
            db: Database session
        """
        self.db = db

    @staticmethod
    def _build_geocode_query(address: Optional[str], city: Optional[str]) -> Optional[str]:
        parts = [part.strip() for part in [address, city] if isinstance(part, str) and part.strip()]
        if not parts:
            return None
        query = ", ".join(parts)
        if "croatia" not in query.lower():
            query = f"{query}, Croatia"
        return query

    @staticmethod
    def _geocode_with_google(query: str) -> Optional[Tuple[float, float]]:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            return None
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": query, "key": api_key},
                timeout=8,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            results = payload.get("results") or []
            if not results:
                return None
            location = (results[0].get("geometry") or {}).get("location") or {}
            lat = location.get("lat")
            lng = location.get("lng")
            if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                return float(lat), float(lng)
        except Exception:
            return None
        return None

    @staticmethod
    def _geocode_with_nominatim(query: str) -> Optional[Tuple[float, float]]:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "hr",
                    "addressdetails": 0,
                },
                headers={"User-Agent": "HostForGuest/1.0"},
                timeout=8,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            if not payload:
                return None
            first = payload[0]
            lat = float(first.get("lat"))
            lng = float(first.get("lon"))
            return lat, lng
        except Exception:
            return None

    def _resolve_with_query_variants(self, base_query: str) -> Optional[Tuple[float, float]]:
        candidate_queries = [
            base_query,
            base_query.replace("Marsala", "Maršala"),
            base_query.replace(" Tita", " Tita, Hrvatska"),
            base_query.replace("Obala", "Šetalište"),
        ]

        # Preserve order but de-duplicate variants.
        unique_queries = []
        for query in candidate_queries:
            normalized = query.strip()
            if normalized and normalized not in unique_queries:
                unique_queries.append(normalized)

        for query in unique_queries:
            google_coordinates = self._geocode_with_google(query)
            if google_coordinates:
                return google_coordinates

            nominatim_coordinates = self._geocode_with_nominatim(query)
            if nominatim_coordinates:
                return nominatim_coordinates

        return None

    def _resolve_coordinates(
        self,
        address: Optional[str],
        city: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            if latitude == 0 and longitude == 0:
                latitude = None
                longitude = None
            else:
                return float(latitude), float(longitude)

        query = self._build_geocode_query(address=address, city=city)
        if not query:
            return latitude, longitude

        resolved = self._resolve_with_query_variants(query)
        if resolved:
            return resolved

        return latitude, longitude

    def _ensure_coordinates(
        self,
        address: Optional[str],
        city: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Tuple[float, float]:
        resolved_latitude, resolved_longitude = self._resolve_coordinates(
            address=address,
            city=city,
            latitude=latitude,
            longitude=longitude,
        )
        if resolved_latitude is None or resolved_longitude is None:
            raise ValueError(
                "Attraction requires geolocation. Provide a resolvable address/city or explicit coordinates."
            )
        return float(resolved_latitude), float(resolved_longitude)
    
    # Host Content Creation
    async def create_attraction(self, host_id: uuid.UUID, attraction_data: AttractionCreate) -> Optional[AttractionResponse]:
        """
        Create a new attraction with host contribution.
        
        Args:
            host_id: Host UUID creating the attraction
            attraction_data: Attraction creation data
            
        Returns:
            AttractionResponse: Created attraction or None if failed
        """
        try:
            resolved_latitude, resolved_longitude = self._ensure_coordinates(
                address=attraction_data.address,
                city=attraction_data.city,
                latitude=attraction_data.latitude,
                longitude=attraction_data.longitude,
            )

            # Create attraction
            attraction = Attraction(
                created_by_host_id=host_id,
                name=attraction_data.name,
                description=attraction_data.description,
                short_description=attraction_data.short_description,
                attraction_type=attraction_data.attraction_type,
                category_tags=attraction_data.category_tags,
                address=attraction_data.address,
                city=attraction_data.city,
                region=attraction_data.region,
                county=attraction_data.county,
                latitude=resolved_latitude,
                longitude=resolved_longitude,
                host_personal_tip=attraction_data.host_personal_tip,
                host_favorite_time=attraction_data.host_favorite_time,
                host_insider_info=attraction_data.host_insider_info,
                host_story=attraction_data.host_story,
                host_recommended_duration=attraction_data.host_recommended_duration,
                opening_hours=attraction_data.opening_hours,
                admission_fee=attraction_data.admission_fee,
                contact_info=attraction_data.contact_info,
                difficulty_level=attraction_data.difficulty_level,
                duration_hours=attraction_data.duration_hours,
                group_size_recommendation=attraction_data.group_size_recommendation,
                seasonal_availability=attraction_data.seasonal_availability,
                best_months=attraction_data.best_months,
                seasonal_notes=attraction_data.seasonal_notes,
                accessibility_info=attraction_data.accessibility_info,
                age_suitability=attraction_data.age_suitability,
                required_equipment=attraction_data.required_equipment,
                name_translations=attraction_data.name_translations,
                description_translations=attraction_data.description_translations,
                featured_image_url=attraction_data.featured_image_url,
                image_gallery=attraction_data.image_gallery,
                status=AttractionStatus.DRAFT  # Start as draft
            )
            
            self.db.add(attraction)
            await self.db.commit()
            await self.db.refresh(attraction)
            
            logger.info(f"Attraction created successfully: {attraction.name} by host {host_id}")
            return AttractionResponse.model_validate(attraction)
            
        except Exception as e:
            if self.db is not None:
                await self.db.rollback()
            logger.error(f"Error creating attraction for host {host_id}: {e}")
            raise
    
    async def update_attraction(self, host_id: uuid.UUID, attraction_id: uuid.UUID, 
                              attraction_data: AttractionUpdate) -> Optional[AttractionResponse]:
        """
        Update an attraction (only by the creating host or collaborating hosts).
        
        Args:
            host_id: Host UUID requesting the update
            attraction_id: Attraction UUID to update
            attraction_data: Updated attraction data
            
        Returns:
            AttractionResponse: Updated attraction or None if failed
        """
        try:
            # Get existing attraction
            attraction = await self.get_attraction_by_id(attraction_id)
            if not attraction:
                logger.warning(f"Attraction update failed: Attraction not found {attraction_id}")
                return None
            
            # Check if host has permission to update
            if not await self._host_can_edit_attraction(host_id, attraction):
                logger.warning(f"Host {host_id} not authorized to update attraction {attraction_id}")
                return None
            
            # Update only provided fields
            update_data = attraction_data.model_dump(exclude_unset=True)
            if update_data:
                existing_address = getattr(attraction, "address", None)
                existing_city = getattr(attraction, "city", None)
                existing_latitude = getattr(attraction, "latitude", None)
                existing_longitude = getattr(attraction, "longitude", None)

                proposed_address = update_data.get("address", existing_address)
                proposed_city = update_data.get("city", existing_city)
                proposed_latitude = update_data.get("latitude", existing_latitude)
                proposed_longitude = update_data.get("longitude", existing_longitude)

                resolved_latitude, resolved_longitude = self._ensure_coordinates(
                    address=proposed_address,
                    city=proposed_city,
                    latitude=proposed_latitude,
                    longitude=proposed_longitude,
                )
                update_data["latitude"] = resolved_latitude
                update_data["longitude"] = resolved_longitude

                update_data['updated_at'] = datetime.utcnow()
                update_data['last_updated_by_host_id'] = host_id
                
                # If content changed, reset to draft for re-approval
                content_fields = ['name', 'description', 'host_personal_tip', 'host_insider_info']
                if any(field in update_data for field in content_fields):
                    if attraction.status == AttractionStatus.APPROVED:
                        update_data['status'] = AttractionStatus.PENDING
                        logger.info(f"Attraction {attraction_id} moved to pending due to content changes")
                
                stmt = update(Attraction).where(Attraction.id == attraction_id).values(**update_data)
                await self.db.execute(stmt)
                await self.db.commit()
                
                # Refresh attraction data
                await self.db.refresh(attraction)
                
                logger.info(f"Attraction updated successfully: {attraction_id} by host {host_id}")
                return AttractionResponse.model_validate(attraction)
            
            return AttractionResponse.model_validate(attraction)
            
        except ValueError:
            if self.db is not None:
                await self.db.rollback()
            raise
        except Exception as e:
            if self.db is not None:
                await self.db.rollback()
            logger.error(f"Error updating attraction {attraction_id}: {e}")
            return None

    async def delete_attraction(self, host_id: uuid.UUID, attraction_id: uuid.UUID) -> bool:
        """
        Delete an attraction (only by the creating host).
        
        Args:
            host_id: Host UUID requesting the deletion
            attraction_id: Attraction UUID to delete
            
        Returns:
            bool: True if successful
        """
        try:
            # Get existing attraction
            attraction = await self.get_attraction_by_id(attraction_id)
            if not attraction:
                logger.warning(f"Attraction deletion failed: Attraction not found {attraction_id}")
                return False
            
            # Check if host has permission to delete
            if not await self._host_can_edit_attraction(host_id, attraction):
                logger.warning(f"Host {host_id} not authorized to delete attraction {attraction_id}")
                return False
            
            # Delete the attraction
            await self.db.delete(attraction)
            await self.db.commit()
            
            logger.info(f"Attraction deleted successfully: {attraction_id} by host {host_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting attraction {attraction_id}: {e}")
            return False
    
    async def submit_for_approval(self, host_id: uuid.UUID, attraction_id: uuid.UUID) -> bool:
        """
        Submit an attraction for approval.
        
        Args:
            host_id: Host UUID submitting for approval
            attraction_id: Attraction UUID to submit
            
        Returns:
            bool: True if successful
        """
        try:
            # Verify host ownership
            attraction = await self.get_attraction_by_id(attraction_id)
            if not attraction or not await self._host_can_edit_attraction(host_id, attraction):
                return False
            
            # Only draft or rejected attractions can be submitted
            if attraction.status not in [AttractionStatus.DRAFT, AttractionStatus.REJECTED]:
                logger.warning(f"Cannot submit attraction {attraction_id} with status {attraction.status}")
                return False
            
            # Update status
            stmt = update(Attraction).where(Attraction.id == attraction_id).values(
                status=AttractionStatus.PENDING,
                updated_at=datetime.utcnow()
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Attraction submitted for approval: {attraction_id} by host {host_id}")
                return True
            
            return False
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error submitting attraction {attraction_id} for approval: {e}")
            return False
    
    # Content Discovery and Search
    async def get_host_attractions(self, host_id: uuid.UUID, status_filter: Optional[str] = None) -> List[AttractionResponse]:
        """
        Get all attractions created by a host.
        
        Args:
            host_id: Host UUID
            status_filter: Optional status filter
            
        Returns:
            List[AttractionResponse]: Host's attractions
        """
        try:
            stmt = select(Attraction).where(Attraction.created_by_host_id == host_id)
            
            if status_filter:
                stmt = stmt.where(Attraction.status == status_filter)
            
            stmt = stmt.order_by(desc(Attraction.updated_at))
            result = await self.db.execute(stmt)
            attractions = result.scalars().all()
            
            return [AttractionResponse.model_validate(attraction) for attraction in attractions]
            
        except Exception as e:
            logger.error(f"Error getting attractions for host {host_id}: {e}")
            return []
    
    async def search_attractions(self, 
                               city: Optional[str] = None,
                               region: Optional[str] = None,
                               attraction_type: Optional[str] = None,
                               category_tags: Optional[List[str]] = None,
                               seasonal_filter: Optional[str] = None,
                               difficulty_level: Optional[str] = None,
                               host_id: Optional[uuid.UUID] = None,
                               only_approved: bool = True,
                               skip: int = 0,
                               limit: int = 50) -> List[Attraction]:
        """
        Search attractions with various filters.
        
        Args:
            city: Filter by city
            region: Filter by Croatian region
            attraction_type: Filter by attraction type
            category_tags: Filter by category tags
            seasonal_filter: Filter by seasonal availability
            difficulty_level: Filter by difficulty
            host_id: Filter by specific host (for host-specific recommendations)
            only_approved: Only return approved attractions
            limit: Maximum results
            
        Returns:
            List[Attraction]: Matching attraction rows (sanitize at API boundary)
        """
        try:
            stmt = select(Attraction)
            
            # Base filters
            if only_approved:
                stmt = stmt.where(Attraction.status == AttractionStatus.APPROVED)
            
            if city:
                stmt = stmt.where(Attraction.city.ilike(f"%{city}%"))
            
            if region:
                stmt = stmt.where(Attraction.region.ilike(f"%{region}%"))
            
            if attraction_type:
                stmt = stmt.where(Attraction.attraction_type == attraction_type)
            
            if difficulty_level:
                stmt = stmt.where(Attraction.difficulty_level == difficulty_level)
            
            if seasonal_filter:
                stmt = stmt.where(Attraction.seasonal_availability == seasonal_filter)
            
            if host_id:
                stmt = stmt.where(Attraction.created_by_host_id == host_id)
            
            # Category tags filter (JSON array contains)
            if category_tags:
                for tag in category_tags:
                    stmt = stmt.where(Attraction.category_tags.contains([tag]))
            
            # Order by recommendation count and rating for quality
            stmt = stmt.order_by(
                desc(Attraction.recommendation_count),
                desc(Attraction.guest_rating),
                desc(Attraction.created_at)
            ).offset(skip).limit(limit)
            
            result = await self.db.execute(stmt)
            attractions = result.scalars().all()
            
            return list(attractions)
            
        except Exception as e:
            logger.error(f"Error searching attractions: {e}")
            return []

    async def get_attractions_by_city(
        self,
        city: str,
        skip: int = 0,
        limit: int = 100,
        language: Optional[str] = None,
    ) -> List[Attraction]:
        """Public city listing — approved attractions only."""
        _ = language
        return await self.search_attractions(
            city=city,
            only_approved=True,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def is_attraction_visible(
        attraction: Attraction,
        viewer_host_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Approved attractions are public; hosts may view their own drafts."""
        if attraction.status == AttractionStatus.APPROVED:
            return True
        if viewer_host_id and attraction.created_by_host_id == viewer_host_id:
            return True
        return False

    async def add_host_contribution(
        self,
        attraction_id: uuid.UUID,
        host_id: uuid.UUID,
        contribution_data: HostContributionCreate,
    ) -> HostContributionResponse:
        new_id = uuid.uuid4()
        now = datetime.utcnow()
        q = text(
            """
            INSERT INTO attraction_host_contributions (
                id, attraction_id, host_id, contribution_type, title, content,
                is_public, language, created_at, updated_at
            ) VALUES (
                CAST(:id AS uuid), CAST(:aid AS uuid), CAST(:hid AS uuid),
                :ctype, :title, :content, :pub, :lang, :ca, :ua
            )
            """
        )
        await self.db.execute(
            q,
            {
                "id": str(new_id),
                "aid": str(attraction_id),
                "hid": str(host_id),
                "ctype": contribution_data.contribution_type,
                "title": contribution_data.title,
                "content": contribution_data.content,
                "pub": contribution_data.is_public,
                "lang": contribution_data.language,
                "ca": now,
                "ua": now,
            },
        )
        await self.db.commit()
        return HostContributionResponse(
            id=new_id,
            attraction_id=attraction_id,
            host_id=host_id,
            contribution_type=contribution_data.contribution_type,
            title=contribution_data.title,
            content=contribution_data.content,
            is_public=contribution_data.is_public,
            language=contribution_data.language,
            created_at=now,
            updated_at=now,
        )

    async def get_host_contributions(
        self,
        attraction_id: uuid.UUID,
        viewer_host_id: Optional[uuid.UUID] = None,
    ) -> List[HostContributionResponse]:
        visibility = "is_public = true"
        params: dict = {"aid": str(attraction_id)}
        if viewer_host_id:
            visibility = "(is_public = true OR host_id = CAST(:viewer AS uuid))"
            params["viewer"] = str(viewer_host_id)
        q = text(
            f"""
            SELECT id, attraction_id, host_id, contribution_type, title, content,
                   is_public, language, created_at, updated_at
            FROM attraction_host_contributions
            WHERE attraction_id = CAST(:aid AS uuid) AND {visibility}
            ORDER BY created_at DESC
            """
        )
        result = await self.db.execute(q, params)
        rows = result.mappings().all()
        return [
            HostContributionResponse(
                id=r["id"],
                attraction_id=r["attraction_id"],
                host_id=r["host_id"],
                contribution_type=r["contribution_type"],
                title=r["title"],
                content=r["content"],
                is_public=r["is_public"],
                language=r["language"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def get_host_contributions_by_host(
        self,
        host_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HostContributionResponse]:
        q = text(
            """
            SELECT id, attraction_id, host_id, contribution_type, title, content,
                   is_public, language, created_at, updated_at
            FROM attraction_host_contributions
            WHERE host_id = CAST(:hid AS uuid)
            ORDER BY created_at DESC
            OFFSET :skip LIMIT :lim
            """
        )
        result = await self.db.execute(
            q, {"hid": str(host_id), "skip": skip, "lim": limit}
        )
        rows = result.mappings().all()
        return [
            HostContributionResponse(
                id=r["id"],
                attraction_id=r["attraction_id"],
                host_id=r["host_id"],
                contribution_type=r["contribution_type"],
                title=r["title"],
                content=r["content"],
                is_public=r["is_public"],
                language=r["language"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]
    
    async def get_attraction_by_id(self, attraction_id: uuid.UUID) -> Optional[Attraction]:
        """
        Get attraction by ID.
        
        Args:
            attraction_id: Attraction UUID
            
        Returns:
            Attraction: Attraction object or None
        """
        try:
            stmt = select(Attraction).where(Attraction.id == attraction_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting attraction by ID {attraction_id}: {e}")
            return None
    
    async def get_popular_attractions(self, city: Optional[str] = None, limit: int = 10) -> List[AttractionResponse]:
        """
        Get popular attractions based on views and recommendations.
        
        Args:
            city: Optional city filter
            limit: Maximum results
            
        Returns:
            List[AttractionResponse]: Popular attractions
        """
        try:
            stmt = select(Attraction).where(Attraction.status == AttractionStatus.APPROVED)
            
            if city:
                stmt = stmt.where(Attraction.city.ilike(f"%{city}%"))
            
            # Order by popularity metrics
            stmt = stmt.order_by(
                desc(Attraction.recommendation_count * 2 + Attraction.view_count),
                desc(Attraction.guest_rating)
            ).limit(limit)
            
            result = await self.db.execute(stmt)
            attractions = result.scalars().all()
            
            return [AttractionResponse.model_validate(attraction) for attraction in attractions]
            
        except Exception as e:
            logger.error(f"Error getting popular attractions: {e}")
            return []
    
    # Enhanced Reviews and Moderation System
    async def add_review(self, host_id: uuid.UUID, guest_group_id: uuid.UUID, 
                        review_data: AttractionReviewCreate) -> Optional[AttractionReviewResponse]:
        """
        Add a guest review for an attraction with enhanced moderation support.
        
        Args:
            host_id: Host UUID (who recommended the attraction)
            guest_group_id: Guest group UUID
            review_data: Review data
            
        Returns:
            AttractionReviewResponse: Created review or None
        """
        try:
            # Verify attraction exists
            attraction = await self.get_attraction_by_id(review_data.attraction_id)
            if not attraction:
                logger.warning(f"Cannot review non-existent attraction: {review_data.attraction_id}")
                return None
            
            # Calculate initial quality score based on content
            quality_score = await self._calculate_review_quality_score(review_data)
            
            # Create review with pending status for moderation
            review = AttractionReview(
                attraction_id=review_data.attraction_id,
                guest_group_id=guest_group_id,
                host_id=host_id,
                rating=review_data.rating,
                title=review_data.title,
                review_text=review_data.review_text,
                visit_date=review_data.visit_date,
                group_size=review_data.group_size,
                visit_duration=review_data.visit_duration,
                pros=review_data.pros,
                cons=review_data.cons,
                tips_for_others=review_data.tips_for_others,
                guest_age_group=review_data.guest_age_group,
                guest_travel_style=review_data.guest_travel_style,
                language=review_data.language,
                quality_score=quality_score,
                status=ReviewStatus.PENDING  # All reviews start as pending
            )
            
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            logger.info(f"Review added for attraction {review_data.attraction_id} by guest group {guest_group_id}")
            return AttractionReviewResponse.model_validate(review)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding attraction review: {e}")
            return None
    
    async def moderate_review(self, host_id: uuid.UUID, review_id: uuid.UUID, 
                            moderation_request: ReviewModerationRequest) -> Optional[ReviewModerationResponse]:
        """
        Moderate a review (approve, reject, verify, etc.).
        
        Args:
            host_id: Host performing the moderation
            review_id: Review to moderate
            moderation_request: Moderation action details
            
        Returns:
            ReviewModerationResponse: Moderation result
        """
        try:
            # Get the review
            stmt = select(AttractionReview).where(AttractionReview.id == review_id)
            result = await self.db.execute(stmt)
            review = result.scalar_one_or_none()
            
            if not review:
                logger.warning(f"Review not found: {review_id}")
                return None
            
            # Verify host has permission to moderate this review
            if review.host_id != host_id:
                logger.warning(f"Host {host_id} attempted to moderate review {review_id} not owned by them")
                return None
            
            # Store previous status for logging
            previous_status = review.status
            
            # Apply moderation action
            new_status = await self._apply_moderation_action(review, moderation_request)
            
            # Update review
            review.status = new_status
            review.moderated_at = datetime.utcnow()
            review.moderated_by_host_id = host_id
            review.moderation_notes = moderation_request.notes
            
            # Handle special actions
            if moderation_request.action in ["verify_visit", "unverify_visit"]:
                review.verified_visit = moderation_request.action == "verify_visit"
                review.verified_at = datetime.utcnow() if review.verified_visit else None
            
            if moderation_request.host_response:
                review.response_from_host = moderation_request.host_response
                review.host_response_at = datetime.utcnow()
            
            # Log the moderation action
            log_entry = ReviewModerationLog(
                review_id=review_id,
                host_id=host_id,
                action=moderation_request.action,
                previous_status=previous_status,
                new_status=new_status,
                reason=moderation_request.reason,
                notes=moderation_request.notes
            )
            
            self.db.add(log_entry)
            await self.db.commit()
            await self.db.refresh(review)
            
            # Update attraction rating if review was approved/rejected
            if moderation_request.action in ["approve", "reject"]:
                await self._update_attraction_rating(review.attraction_id)
            
            logger.info(f"Review {review_id} moderated by host {host_id}: {moderation_request.action}")
            
            return ReviewModerationResponse(
                success=True,
                message=f"Review {moderation_request.action}d successfully",
                review_id=review_id,
                new_status=new_status,
                action_taken=moderation_request.action,
                moderated_at=review.moderated_at
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error moderating review {review_id}: {e}")
            return None
    
    async def get_reviews(self, attraction_id: uuid.UUID, 
                         status_filter: Optional[str] = None,
                         skip: int = 0, limit: int = 20) -> List[AttractionReviewResponse]:
        """
        Get reviews for an attraction with status filtering.
        
        Args:
            attraction_id: Attraction UUID
            status_filter: Filter by review status (default: approved only)
            skip: Records to skip
            limit: Maximum reviews to return
            
        Returns:
            List[AttractionReviewResponse]: Reviews
        """
        try:
            stmt = select(AttractionReview).where(
                AttractionReview.attraction_id == attraction_id
            )
            
            # Default to approved reviews for public viewing
            if status_filter:
                stmt = stmt.where(AttractionReview.status == status_filter)
            else:
                stmt = stmt.where(AttractionReview.status == ReviewStatus.APPROVED)
            
            stmt = stmt.order_by(desc(AttractionReview.created_at)).offset(skip).limit(limit)
            
            result = await self.db.execute(stmt)
            reviews = result.scalars().all()
            
            return [AttractionReviewResponse.model_validate(review) for review in reviews]
            
        except Exception as e:
            logger.error(f"Error getting reviews for attraction {attraction_id}: {e}")
            return []
    
    async def get_host_reviews_for_moderation(self, host_id: uuid.UUID, 
                                            status: Optional[str] = None,
                                            skip: int = 0, limit: int = 50) -> List[AttractionReviewResponse]:
        """
        Get reviews that need moderation by a specific host.
        
        Args:
            host_id: Host UUID
            status: Filter by review status (default: pending)
            skip: Records to skip
            limit: Maximum reviews to return
            
        Returns:
            List[AttractionReviewResponse]: Reviews needing moderation
        """
        try:
            stmt = select(AttractionReview).where(AttractionReview.host_id == host_id)
            
            if status:
                stmt = stmt.where(AttractionReview.status == status)
            else:
                stmt = stmt.where(AttractionReview.status == ReviewStatus.PENDING)
            
            stmt = stmt.order_by(desc(AttractionReview.created_at)).offset(skip).limit(limit)
            
            result = await self.db.execute(stmt)
            reviews = result.scalars().all()
            
            return [AttractionReviewResponse.model_validate(review) for review in reviews]
            
        except Exception as e:
            logger.error(f"Error getting reviews for moderation by host {host_id}: {e}")
            return []
    
    async def search_reviews(
        self,
        search_request: ReviewSearchRequest,
        host_id: Optional[uuid.UUID] = None,
    ) -> ReviewSearchResponse:
        """
        Search and filter reviews with advanced criteria.
        
        Args:
            search_request: Search criteria
            host_id: When set, limit to attractions the host has contributed to
            
        Returns:
            ReviewSearchResponse: Search results
        """
        try:
            stmt = select(AttractionReview)
            filters_applied = {}

            if host_id:
                aid_result = await self.db.execute(
                    text(
                        """
                        SELECT DISTINCT attraction_id FROM (
                            SELECT attraction_id
                            FROM attraction_host_contributions
                            WHERE host_id = CAST(:hid AS uuid)
                            UNION
                            SELECT id AS attraction_id
                            FROM attractions
                            WHERE created_by_host_id = CAST(:hid AS uuid)
                        ) scoped
                        """
                    ),
                    {"hid": str(host_id)},
                )
                attraction_ids = [row[0] for row in aid_result.fetchall()]
                filters_applied["host_id"] = str(host_id)
                if not attraction_ids:
                    return ReviewSearchResponse(
                        reviews=[],
                        total_count=0,
                        page=1,
                        per_page=search_request.limit,
                        filters_applied=filters_applied,
                    )
                stmt = stmt.where(AttractionReview.attraction_id.in_(attraction_ids))
            
            # Apply filters
            if search_request.attraction_id:
                stmt = stmt.where(AttractionReview.attraction_id == search_request.attraction_id)
                filters_applied["attraction_id"] = str(search_request.attraction_id)
            
            if search_request.status:
                stmt = stmt.where(AttractionReview.status == search_request.status)
                filters_applied["status"] = search_request.status
            
            if search_request.rating_min:
                stmt = stmt.where(AttractionReview.rating >= search_request.rating_min)
                filters_applied["rating_min"] = search_request.rating_min
            
            if search_request.rating_max:
                stmt = stmt.where(AttractionReview.rating <= search_request.rating_max)
                filters_applied["rating_max"] = search_request.rating_max
            
            if search_request.verified_only:
                stmt = stmt.where(AttractionReview.verified_visit == True)
                filters_applied["verified_only"] = True
            
            if search_request.language:
                stmt = stmt.where(AttractionReview.language == search_request.language)
                filters_applied["language"] = search_request.language
            
            if search_request.date_from:
                stmt = stmt.where(AttractionReview.visit_date >= search_request.date_from)
                filters_applied["date_from"] = search_request.date_from.isoformat()
            
            if search_request.date_to:
                stmt = stmt.where(AttractionReview.visit_date <= search_request.date_to)
                filters_applied["date_to"] = search_request.date_to.isoformat()
            
            # Get total count
            count_stmt = select(func.count(AttractionReview.id)).select_from(stmt.subquery())
            count_result = await self.db.execute(count_stmt)
            total_count = count_result.scalar()
            
            # Apply pagination and ordering
            stmt = stmt.order_by(desc(AttractionReview.created_at))
            stmt = stmt.offset(search_request.skip).limit(search_request.limit)
            
            result = await self.db.execute(stmt)
            reviews = result.scalars().all()
            
            return ReviewSearchResponse(
                reviews=[AttractionReviewResponse.model_validate(review) for review in reviews],
                total_count=total_count,
                page=search_request.skip // search_request.limit + 1,
                per_page=search_request.limit,
                filters_applied=filters_applied
            )
            
        except Exception as e:
            logger.error(f"Error searching reviews: {e}")
            return ReviewSearchResponse(
                reviews=[],
                total_count=0,
                page=1,
                per_page=search_request.limit,
                filters_applied={}
            )
    
    async def get_review_analytics(self, attraction_id: uuid.UUID) -> Optional[ReviewAnalytics]:
        """
        Get comprehensive analytics for attraction reviews.
        
        Args:
            attraction_id: Attraction UUID
            
        Returns:
            ReviewAnalytics: Review analytics data
        """
        try:
            # Basic counts by status
            status_counts = await self.db.execute(
                select(
                    AttractionReview.status,
                    func.count(AttractionReview.id).label('count')
                ).where(
                    AttractionReview.attraction_id == attraction_id
                ).group_by(AttractionReview.status)
            )
            
            status_data = {row.status: row.count for row in status_counts}
            
            # Rating distribution
            rating_dist = await self.db.execute(
                select(
                    AttractionReview.rating,
                    func.count(AttractionReview.id).label('count')
                ).where(
                    and_(
                        AttractionReview.attraction_id == attraction_id,
                        AttractionReview.status == ReviewStatus.APPROVED
                    )
                ).group_by(AttractionReview.rating)
            )
            
            rating_distribution = {row.rating: row.count for row in rating_dist}
            
            # Average rating
            avg_rating_result = await self.db.execute(
                select(func.avg(AttractionReview.rating)).where(
                    and_(
                        AttractionReview.attraction_id == attraction_id,
                        AttractionReview.status == ReviewStatus.APPROVED
                    )
                )
            )
            average_rating = avg_rating_result.scalar()
            
            # Additional metrics
            verified_count = status_data.get(ReviewStatus.APPROVED, 0)  # Simplified
            recent_count = await self._get_recent_reviews_count(attraction_id)
            most_helpful = await self._get_most_helpful_review(attraction_id)
            response_rate = await self._calculate_response_rate(attraction_id)
            
            return ReviewAnalytics(
                attraction_id=attraction_id,
                total_reviews=sum(status_data.values()),
                approved_reviews=status_data.get(ReviewStatus.APPROVED, 0),
                pending_reviews=status_data.get(ReviewStatus.PENDING, 0),
                rejected_reviews=status_data.get(ReviewStatus.REJECTED, 0),
                average_rating=float(average_rating) if average_rating else None,
                rating_distribution=rating_distribution,
                verified_reviews=verified_count,
                recent_reviews=recent_count,
                most_helpful_review_id=most_helpful,
                response_rate=response_rate
            )
            
        except Exception as e:
            logger.error(f"Error getting review analytics for attraction {attraction_id}: {e}")
            return None
    
    async def get_host_review_stats(self, host_id: uuid.UUID) -> Optional[HostReviewStats]:
        """
        Get review management statistics for a host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            HostReviewStats: Host review statistics
        """
        try:
            # Total reviews received
            total_reviews = await self.db.execute(
                select(func.count(AttractionReview.id)).where(
                    AttractionReview.host_id == host_id
                )
            )
            total_count = total_reviews.scalar()
            
            # Pending moderation
            pending_reviews = await self.db.execute(
                select(func.count(AttractionReview.id)).where(
                    and_(
                        AttractionReview.host_id == host_id,
                        AttractionReview.status == ReviewStatus.PENDING
                    )
                )
            )
            pending_count = pending_reviews.scalar()
            
            # This month's activity
            current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            approved_this_month = await self.db.execute(
                select(func.count(AttractionReview.id)).where(
                    and_(
                        AttractionReview.moderated_by_host_id == host_id,
                        AttractionReview.status == ReviewStatus.APPROVED,
                        AttractionReview.moderated_at >= current_month
                    )
                )
            )
            approved_count = approved_this_month.scalar()
            
            rejected_this_month = await self.db.execute(
                select(func.count(AttractionReview.id)).where(
                    and_(
                        AttractionReview.moderated_by_host_id == host_id,
                        AttractionReview.status == ReviewStatus.REJECTED,
                        AttractionReview.moderated_at >= current_month
                    )
                )
            )
            rejected_count = rejected_this_month.scalar()
            
            # Additional metrics
            verification_rate = await self._calculate_verification_rate(host_id)
            response_rate = await self._calculate_host_response_rate(host_id)
            avg_response_time = await self._calculate_avg_response_time(host_id)
            
            return HostReviewStats(
                host_id=host_id,
                total_reviews_received=total_count,
                pending_moderation=pending_count,
                approved_this_month=approved_count,
                rejected_this_month=rejected_count,
                average_response_time_hours=avg_response_time,
                verification_rate=verification_rate,
                response_rate=response_rate
            )
            
        except Exception as e:
            logger.error(f"Error getting host review stats for {host_id}: {e}")
            return None
    
    # Helper methods for review system
    async def _calculate_review_quality_score(self, review_data: AttractionReviewCreate) -> float:
        """Calculate quality score for a review based on content."""
        score = 0.5  # Base score
        
        # Length and detail bonus
        if review_data.review_text and len(review_data.review_text) > 50:
            score += 0.2
        
        if review_data.pros or review_data.cons:
            score += 0.1
        
        if review_data.tips_for_others:
            score += 0.1
        
        if review_data.visit_date:
            score += 0.1
        
        return min(1.0, score)
    
    async def _apply_moderation_action(self, review: AttractionReview, 
                                     request: ReviewModerationRequest) -> str:
        """Apply moderation action and return new status."""
        action_status_map = {
            ReviewModerationAction.APPROVE: ReviewStatus.APPROVED,
            ReviewModerationAction.REJECT: ReviewStatus.REJECTED,
            ReviewModerationAction.FLAG: ReviewStatus.FLAGGED,
            ReviewModerationAction.ARCHIVE: ReviewStatus.ARCHIVED,
            ReviewModerationAction.VERIFY_VISIT: review.status,  # Keep current status
            ReviewModerationAction.UNVERIFY_VISIT: review.status  # Keep current status
        }
        
        return action_status_map.get(request.action, review.status)
    
    async def _get_recent_reviews_count(self, attraction_id: uuid.UUID) -> int:
        """Get count of reviews in last 30 days."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.db.execute(
            select(func.count(AttractionReview.id)).where(
                and_(
                    AttractionReview.attraction_id == attraction_id,
                    AttractionReview.created_at >= thirty_days_ago,
                    AttractionReview.status == ReviewStatus.APPROVED
                )
            )
        )
        return result.scalar()
    
    async def _get_most_helpful_review(self, attraction_id: uuid.UUID) -> Optional[uuid.UUID]:
        """Get the most helpful review ID."""
        result = await self.db.execute(
            select(AttractionReview.id).where(
                and_(
                    AttractionReview.attraction_id == attraction_id,
                    AttractionReview.status == ReviewStatus.APPROVED
                )
            ).order_by(desc(AttractionReview.helpfulness_score)).limit(1)
        )
        review = result.scalar_one_or_none()
        return review if review else None
    
    async def _calculate_response_rate(self, attraction_id: uuid.UUID) -> float:
        """Calculate percentage of reviews with host responses."""
        total_result = await self.db.execute(
            select(func.count(AttractionReview.id)).where(
                and_(
                    AttractionReview.attraction_id == attraction_id,
                    AttractionReview.status == ReviewStatus.APPROVED
                )
            )
        )
        total = total_result.scalar()
        
        if total == 0:
            return 0.0
        
        responded_result = await self.db.execute(
            select(func.count(AttractionReview.id)).where(
                and_(
                    AttractionReview.attraction_id == attraction_id,
                    AttractionReview.status == ReviewStatus.APPROVED,
                    AttractionReview.response_from_host.isnot(None)
                )
            )
        )
        responded = responded_result.scalar()
        
        return (responded / total) * 100.0
    
    async def _calculate_verification_rate(self, host_id: uuid.UUID) -> float:
        """Calculate percentage of reviews verified by host."""
        total_result = await self.db.execute(
            select(func.count(AttractionReview.id)).where(
                AttractionReview.host_id == host_id
            )
        )
        total = total_result.scalar()
        
        if total == 0:
            return 0.0
        
        verified_result = await self.db.execute(
            select(func.count(AttractionReview.id)).where(
                and_(
                    AttractionReview.host_id == host_id,
                    AttractionReview.verified_visit == True
                )
            )
        )
        verified = verified_result.scalar()
        
        return (verified / total) * 100.0
    
    async def _calculate_host_response_rate(self, host_id: uuid.UUID) -> float:
        """Calculate percentage of reviews with host responses."""
        total_result = await self.db.execute(
            select(func.count(AttractionReview.id)).where(
                AttractionReview.host_id == host_id
            )
        )
        total = total_result.scalar()
        
        if total == 0:
            return 0.0
        
        responded_result = await self.db.execute(
            select(func.count(AttractionReview.id)).where(
                and_(
                    AttractionReview.host_id == host_id,
                    AttractionReview.response_from_host.isnot(None)
                )
            )
        )
        responded = responded_result.scalar()
        
        return (responded / total) * 100.0
    
    async def _calculate_avg_response_time(self, host_id: uuid.UUID) -> Optional[float]:
        """Calculate average response time in hours."""
        result = await self.db.execute(
            select(
                func.avg(
                    func.extract('epoch', AttractionReview.host_response_at - AttractionReview.created_at) / 3600
                )
            ).where(
                and_(
                    AttractionReview.host_id == host_id,
                    AttractionReview.host_response_at.isnot(None)
                )
            )
        )
        avg_hours = result.scalar()
        return float(avg_hours) if avg_hours else None
    
    # Seasonal Events
    async def create_seasonal_event(self, host_id: uuid.UUID, event_data: SeasonalEventCreate) -> Optional[SeasonalEventResponse]:
        """
        Create a seasonal event.
        
        Args:
            host_id: Host UUID creating the event
            event_data: Event creation data
            
        Returns:
            SeasonalEventResponse: Created event or None
        """
        try:
            event = SeasonalEvent(
                created_by_host_id=host_id,
                name=event_data.name,
                description=event_data.description,
                event_type=event_data.event_type,
                location=event_data.location,
                city=event_data.city,
                venue_details=event_data.venue_details,
                start_date=event_data.start_date,
                end_date=event_data.end_date,
                recurring_pattern=event_data.recurring_pattern,
                time_of_day=event_data.time_of_day,
                host_recommendation=event_data.host_recommendation,
                best_time_to_visit=event_data.best_time_to_visit,
                what_to_expect=event_data.what_to_expect,
                host_personal_experience=event_data.host_personal_experience,
                admission_info=event_data.admission_info,
                booking_required=event_data.booking_required,
                contact_info=event_data.contact_info
            )
            
            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)
            
            logger.info(f"Seasonal event created: {event.name} by host {host_id}")
            return SeasonalEventResponse.model_validate(event)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating seasonal event for host {host_id}: {e}")
            return None
    
    async def get_seasonal_events(self, city: Optional[str] = None, 
                                event_type: Optional[str] = None,
                                active_only: bool = True) -> List[SeasonalEventResponse]:
        """
        Get seasonal events with filters.
        
        Args:
            city: Filter by city
            event_type: Filter by event type
            active_only: Only return active events
            
        Returns:
            List[SeasonalEventResponse]: Seasonal events
        """
        try:
            stmt = select(SeasonalEvent)
            
            if active_only:
                stmt = stmt.where(SeasonalEvent.is_active == True)
            
            if city:
                stmt = stmt.where(SeasonalEvent.city.ilike(f"%{city}%"))
            
            if event_type:
                stmt = stmt.where(SeasonalEvent.event_type == event_type)
            
            stmt = stmt.order_by(SeasonalEvent.start_date, SeasonalEvent.created_at)
            result = await self.db.execute(stmt)
            events = result.scalars().all()
            
            return [SeasonalEventResponse.model_validate(event) for event in events]
            
        except Exception as e:
            logger.error(f"Error getting seasonal events: {e}")
            return []
    
    # Host Analytics and Contribution Tracking
    async def get_host_contribution_stats(self, host_id: uuid.UUID) -> HostContributionStats:
        """
        Get contribution statistics for a host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            HostContributionStats: Host contribution statistics
        """
        try:
            # Get attraction counts by status
            attraction_stats = await self.db.execute(
                select(
                    Attraction.status,
                    func.count(Attraction.id).label('count'),
                    func.sum(Attraction.view_count).label('total_views'),
                    func.sum(Attraction.recommendation_count).label('total_recommendations'),
                    func.avg(Attraction.guest_rating).label('avg_rating')
                ).where(
                    Attraction.created_by_host_id == host_id
                ).group_by(Attraction.status)
            )
            
            stats = {
                'total_attractions': 0,
                'approved_attractions': 0,
                'pending_attractions': 0,
                'total_views': 0,
                'total_recommendations': 0,
                'average_rating': None
            }
            
            for row in attraction_stats:
                stats['total_attractions'] += row.count
                stats['total_views'] += row.total_views or 0
                stats['total_recommendations'] += row.total_recommendations or 0
                
                if row.status == AttractionStatus.APPROVED:
                    stats['approved_attractions'] = row.count
                    stats['average_rating'] = float(row.avg_rating) if row.avg_rating else None
                elif row.status == AttractionStatus.PENDING:
                    stats['pending_attractions'] = row.count
            
            # Get expertise areas (most common attraction types)
            expertise_query = await self.db.execute(
                select(
                    Attraction.attraction_type,
                    func.count(Attraction.id).label('count')
                ).where(
                    and_(
                        Attraction.created_by_host_id == host_id,
                        Attraction.status == AttractionStatus.APPROVED
                    )
                ).group_by(Attraction.attraction_type).order_by(desc('count')).limit(5)
            )
            
            expertise_areas = [row.attraction_type for row in expertise_query]
            
            # Calculate contribution score (algorithm-based)
            contribution_score = self._calculate_contribution_score(stats, expertise_areas)
            
            return HostContributionStats(
                host_id=host_id,
                total_attractions=stats['total_attractions'],
                approved_attractions=stats['approved_attractions'],
                pending_attractions=stats['pending_attractions'],
                total_views=stats['total_views'],
                total_recommendations=stats['total_recommendations'],
                average_rating=stats['average_rating'],
                expertise_areas=expertise_areas,
                contribution_score=contribution_score
            )
            
        except Exception as e:
            logger.error(f"Error getting contribution stats for host {host_id}: {e}")
            return HostContributionStats(
                host_id=host_id,
                total_attractions=0,
                approved_attractions=0,
                pending_attractions=0,
                total_views=0,
                total_recommendations=0,
                contribution_score=0.0
            )
    
    async def increment_view_count(self, attraction_id: uuid.UUID) -> bool:
        """
        Increment view count for an attraction.
        
        Args:
            attraction_id: Attraction UUID
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(Attraction).where(Attraction.id == attraction_id).values(
                view_count=Attraction.view_count + 1,
                updated_at=datetime.utcnow()
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error incrementing view count for attraction {attraction_id}: {e}")
            return False
    
    async def increment_recommendation_count(self, attraction_id: uuid.UUID) -> bool:
        """
        Increment recommendation count for an attraction.
        
        Args:
            attraction_id: Attraction UUID
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(Attraction).where(Attraction.id == attraction_id).values(
                recommendation_count=Attraction.recommendation_count + 1,
                updated_at=datetime.utcnow()
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error incrementing recommendation count for attraction {attraction_id}: {e}")
            return False

    async def can_host_view_analytics(
        self, attraction_id: uuid.UUID, host_id: uuid.UUID
    ) -> bool:
        """True if host may open analytics for this attraction (owner or contributor)."""
        attraction = await self.get_attraction_by_id(attraction_id)
        if not attraction:
            return False
        return await self._host_can_edit_attraction(host_id, attraction)

    async def get_attraction_analytics(
        self, attraction_id: uuid.UUID
    ) -> AttractionAnalyticsResponse:
        """Summary metrics for host dashboard (used by GET .../analytics)."""
        attraction = await self.get_attraction_by_id(attraction_id)
        if not attraction:
            return AttractionAnalyticsResponse()
        return AttractionAnalyticsResponse(
            views=int(attraction.view_count or 0),
            recommendations=int(attraction.recommendation_count or 0),
            average_rating=float(attraction.guest_rating or 0.0),
            review_count=int(attraction.total_ratings or 0),
            guest_feedback=[],
        )
    
    # Private Helper Methods
    async def host_can_guest_review_attraction(
        self, host_id: uuid.UUID, attraction: Attraction
    ) -> bool:
        """Guests may review attractions their host created or contributed to."""
        if await self._host_can_edit_attraction(host_id, attraction):
            return True
        row = await self.db.execute(
            text(
                """
                SELECT 1 FROM attraction_host_contributions
                WHERE host_id = CAST(:hid AS uuid) AND attraction_id = CAST(:aid AS uuid)
                LIMIT 1
                """
            ),
            {"hid": str(host_id), "aid": str(attraction.id)},
        )
        return row.scalar_one_or_none() is not None

    async def _host_can_edit_attraction(self, host_id: uuid.UUID, attraction: Attraction) -> bool:
        """Check if host can edit an attraction."""
        # Host can edit if they created it or are in contributing_hosts
        if attraction.created_by_host_id == host_id:
            return True
        
        # Check if host is in contributing_hosts list
        if attraction.contributing_hosts and str(host_id) in attraction.contributing_hosts:
            return True
        
        return False
    
    async def _update_attraction_rating(self, attraction_id: uuid.UUID) -> None:
        """Update the average rating for an attraction."""
        try:
            # Calculate average rating from reviews
            rating_stats = await self.db.execute(
                select(
                    func.avg(AttractionReview.rating).label('avg_rating'),
                    func.count(AttractionReview.id).label('total_ratings')
                ).where(AttractionReview.attraction_id == attraction_id)
            )
            
            row = rating_stats.first()
            if row and row.avg_rating:
                stmt = update(Attraction).where(Attraction.id == attraction_id).values(
                    guest_rating=float(row.avg_rating),
                    total_ratings=row.total_ratings,
                    updated_at=datetime.utcnow()
                )
                
                await self.db.execute(stmt)
                await self.db.commit()
                
        except Exception as e:
            logger.error(f"Error updating attraction rating for {attraction_id}: {e}")
    
    def _calculate_contribution_score(self, stats: Dict[str, Any], expertise_areas: List[str]) -> float:
        """Calculate a contribution score for a host."""
        score = 0.0
        
        # Base points for approved attractions
        score += stats['approved_attractions'] * 10
        
        # Bonus for views and recommendations
        score += (stats['total_views'] * 0.1)
        score += (stats['total_recommendations'] * 2)
        
        # Rating bonus
        if stats['average_rating']:
            score += (stats['average_rating'] - 3) * 5  # Bonus for above-average ratings
        
        # Expertise bonus
        score += len(expertise_areas) * 5
        
        return round(max(0.0, score), 2) 