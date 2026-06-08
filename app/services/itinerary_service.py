"""
Itinerary planning service for guest trip management.

Handles creation, management, and optimization of guest itineraries with
Google Maps integration, transportation planning, and collaborative features.
"""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
import uuid
import asyncio
import aiohttp
import json
from urllib.parse import quote

from app.models import (
    Itinerary, DayPlan, ItineraryActivity, ActivityVote, Attraction, GuestGroup, Host,
    ItineraryCreate, ItineraryResponse, ItineraryWithDetails, ItineraryAssignFromTemplate,
    DayPlanCreate, DayPlanResponse, DayPlanWithActivities,
    ActivityCreate, ActivityUpdate, ActivityResponse, ActivityVoteCreate, ActivityVoteResponse,
    ItineraryUpdate, RoutePointCreate, RoutePointReorder, RoutePointResponse,
    GoogleMapsDirectionsRequest, GoogleMapsDirectionsResponse,
    ItinerarySuggestionRequest, ItinerarySuggestionResponse,
    ItineraryStatus, ActivityStatus, TransportMode, WeatherSuitability,
    LLMItineraryPlanResult,
)
from app.services.settings_service import SettingsService
from app.services.attraction_service import AttractionService
from app.services.recommendation_service import RecommendationService
from app.services.ai_service_fallback import AIServiceWithFallback
from app.services.guest_group_service import host_owns_guest_group

logger = logging.getLogger(__name__)


def _naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetimes for TIMESTAMP WITHOUT TIME ZONE columns."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _strip_markdown_json_fence(text: str) -> str:
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_llm_itinerary_json(text: str) -> Optional[Dict[str, Any]]:
    raw = _strip_markdown_json_fence(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _llm_plan_is_usable(
    plan: LLMItineraryPlanResult,
    duration_days: int,
    catalog_ids: set,
    must_see: List[uuid.UUID],
) -> bool:
    if not plan.days or len(plan.days) != duration_days:
        return False
    if {d.day_number for d in plan.days} != set(range(1, duration_days + 1)):
        return False
    seen: set = set()
    for d in plan.days:
        if not d.ordered_attraction_ids:
            return False
        for aid in d.ordered_attraction_ids:
            if aid not in catalog_ids:
                return False
            seen.add(aid)
    for mid in must_see:
        if str(mid) not in seen:
            return False
    return True


class ItineraryService:
    """
    Service for comprehensive itinerary planning and management.
    
    Provides full itinerary lifecycle management with Google Maps integration,
    collaborative planning features, and Croatian tourism optimization.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings_service = SettingsService(db)
        self.attraction_service = AttractionService(db)
        self.recommendation_service = RecommendationService(db)
        self._ai_service = AIServiceWithFallback(self.settings_service)

    # Core Itinerary Management
    
    async def create_itinerary(
        self,
        host_id: uuid.UUID,
        guest_group_id: Optional[uuid.UUID],
        itinerary_data: ItineraryCreate,
    ) -> Optional[ItineraryResponse]:
        """
        Create a new itinerary for a guest group, or a reusable route template (no guest group).
        """
        try:
            if itinerary_data.is_template:
                guest_group_id = None
                if itinerary_data.start_date and itinerary_data.end_date:
                    total_days = (
                        itinerary_data.end_date - itinerary_data.start_date
                    ).days + 1
                    start_d = itinerary_data.start_date
                    end_d = itinerary_data.end_date
                else:
                    total_days = 1
                    start_d = None
                    end_d = None
            else:
                if guest_group_id is None:
                    logger.error("guest_group_id required for non-template itinerary")
                    return None
                total_days = (
                    itinerary_data.end_date - itinerary_data.start_date
                ).days + 1
                start_d = itinerary_data.start_date
                end_d = itinerary_data.end_date

            base_coords = await self._geocode_address(host_id, itinerary_data.base_location)

            itinerary = Itinerary(
                guest_group_id=guest_group_id,
                host_id=host_id,
                title=itinerary_data.title,
                description=itinerary_data.description,
                start_date=start_d,
                end_date=end_d,
                total_days=total_days,
                is_template=itinerary_data.is_template,
                base_location=itinerary_data.base_location,
                base_latitude=base_coords[0] if base_coords else None,
                base_longitude=base_coords[1] if base_coords else None,
                pace=itinerary_data.pace,
                budget_level=itinerary_data.budget_level,
                transportation_preference=itinerary_data.transportation_preference,
                language=itinerary_data.language,
                group_interests=itinerary_data.group_interests,
                mobility_considerations=itinerary_data.mobility_considerations,
                weather_backup_plans=itinerary_data.weather_backup_plans,
                shared_with_guests=itinerary_data.shared_with_guests,
                allows_guest_modifications=itinerary_data.allows_guest_modifications,
                voting_enabled=itinerary_data.voting_enabled,
            )

            self.db.add(itinerary)
            await self.db.commit()
            await self.db.refresh(itinerary)

            log_ref = guest_group_id or "template"
            logger.info("Created itinerary %s for %s", itinerary.id, log_ref)
            return ItineraryResponse.model_validate(itinerary)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating itinerary: {e}")
            return None

    async def list_host_templates(self, host_id: uuid.UUID) -> List[ItineraryResponse]:
        """All route templates for this host."""
        try:
            stmt = (
                select(Itinerary)
                .where(Itinerary.host_id == host_id, Itinerary.is_template.is_(True))
                .order_by(desc(Itinerary.updated_at))
            )
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            return [ItineraryResponse.model_validate(r) for r in rows]
        except Exception as e:
            logger.error("Error listing templates for host %s: %s", host_id, e)
            return []

    async def list_host_itineraries(self, host_id: uuid.UUID) -> List[ItineraryResponse]:
        """Guest itineraries (non-templates) for this host."""
        try:
            stmt = (
                select(Itinerary)
                .where(Itinerary.host_id == host_id, Itinerary.is_template.is_(False))
                .order_by(desc(Itinerary.updated_at))
            )
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            return [ItineraryResponse.model_validate(r) for r in rows]
        except Exception as e:
            logger.error("Error listing itineraries for host %s: %s", host_id, e)
            return []

    async def assign_template_to_group(
        self,
        host_id: uuid.UUID,
        template_id: uuid.UUID,
        assign: ItineraryAssignFromTemplate,
    ) -> Optional[ItineraryWithDetails]:
        """
        Copy a template itinerary (day plans + activities) to a new guest-specific itinerary.
        """
        from app.services.guest_group_service import GuestGroupService

        try:
            tpl_stmt = select(Itinerary).where(Itinerary.id == template_id)
            tpl_row = await self.db.execute(tpl_stmt)
            template = tpl_row.scalar_one_or_none()
            if not template or template.host_id != host_id or not template.is_template:
                return None

            guest_svc = GuestGroupService(self.db)
            group = await guest_svc.get_guest_group_by_id(assign.guest_group_id)
            if not host_owns_guest_group(group, host_id):
                return None

            existing = await self.get_itinerary_by_guest_group(assign.guest_group_id, False)
            if existing:
                logger.warning(
                    "Guest group %s already has itinerary %s",
                    assign.guest_group_id,
                    existing.id,
                )
                return None

            dp_stmt = (
                select(DayPlan)
                .where(DayPlan.itinerary_id == template_id)
                .order_by(DayPlan.day_number)
            )
            dp_result = await self.db.execute(dp_stmt)
            day_plans_orm = list(dp_result.scalars().all())
            if not day_plans_orm:
                return None

            num_days = len(day_plans_orm)
            end_date = assign.start_date + timedelta(days=num_days - 1)

            new_it = Itinerary(
                guest_group_id=assign.guest_group_id,
                host_id=host_id,
                title=template.title,
                description=template.description,
                start_date=assign.start_date,
                end_date=end_date,
                total_days=num_days,
                is_template=False,
                base_location=template.base_location,
                base_latitude=template.base_latitude,
                base_longitude=template.base_longitude,
                pace=template.pace,
                budget_level=template.budget_level,
                transportation_preference=template.transportation_preference,
                language=template.language,
                group_interests=template.group_interests or [],
                mobility_considerations=template.mobility_considerations or [],
                weather_backup_plans=template.weather_backup_plans,
                shared_with_guests=template.shared_with_guests,
                allows_guest_modifications=template.allows_guest_modifications,
                voting_enabled=template.voting_enabled,
            )
            self.db.add(new_it)
            await self.db.flush()

            for dp in day_plans_orm:
                new_date = assign.start_date + timedelta(days=dp.day_number - 1)
                new_dp = DayPlan(
                    itinerary_id=new_it.id,
                    day_number=dp.day_number,
                    date=new_date,
                    title=dp.title,
                    theme=dp.theme,
                    start_time=dp.start_time,
                    end_time=dp.end_time,
                    description=dp.description,
                    weather_dependent=dp.weather_dependent,
                    main_transport_mode=dp.main_transport_mode,
                    estimated_cost=dp.estimated_cost,
                    host_tips=dp.host_tips,
                )
                self.db.add(new_dp)
                await self.db.flush()

                act_stmt = (
                    select(ItineraryActivity)
                    .where(ItineraryActivity.day_plan_id == dp.id)
                    .order_by(ItineraryActivity.sequence_order)
                )
                act_result = await self.db.execute(act_stmt)
                for act in act_result.scalars().all():
                    old_start = act.scheduled_start_time
                    old_end = act.scheduled_end_time
                    new_start = old_start.replace(
                        year=new_date.year, month=new_date.month, day=new_date.day
                    )
                    new_end = old_end.replace(
                        year=new_date.year, month=new_date.month, day=new_date.day
                    )
                    new_act = ItineraryActivity(
                        day_plan_id=new_dp.id,
                        attraction_id=act.attraction_id,
                        title=act.title,
                        description=act.description,
                        activity_type=act.activity_type,
                        category=act.category,
                        sequence_order=act.sequence_order,
                        scheduled_start_time=new_start,
                        scheduled_end_time=new_end,
                        estimated_duration=act.estimated_duration,
                        buffer_time=act.buffer_time,
                        location_name=act.location_name,
                        address=act.address,
                        latitude=act.latitude,
                        longitude=act.longitude,
                        google_place_id=act.google_place_id,
                        google_maps_url=act.google_maps_url,
                        transport_from_previous=act.transport_from_previous,
                        travel_time_minutes=act.travel_time_minutes,
                        travel_distance_km=act.travel_distance_km,
                        transport_cost=act.transport_cost,
                        transport_instructions=act.transport_instructions,
                        cost_per_person=act.cost_per_person,
                        currency=act.currency,
                        booking_required=act.booking_required,
                        booking_info=act.booking_info or {},
                        opening_hours=act.opening_hours or {},
                        weather_suitability=act.weather_suitability,
                        indoor_activity=act.indoor_activity,
                        host_tip=act.host_tip,
                        host_story=act.host_story,
                        insider_info=act.insider_info,
                        best_time_to_visit=act.best_time_to_visit,
                        priority_level=act.priority_level,
                        allows_skipping=act.allows_skipping,
                    )
                    self.db.add(new_act)

            await self.db.commit()
            await self.db.refresh(new_it)
            return await self.get_itinerary_with_details(new_it.id, True)

        except Exception as e:
            await self.db.rollback()
            logger.error("Error assigning template %s: %s", template_id, e)
            return None

    async def get_itinerary_by_guest_group(self, guest_group_id: uuid.UUID,
                                         include_activities: bool = True) -> Optional[ItineraryWithDetails]:
        """
        Get itinerary for a guest group by guest group ID.
        
        Args:
            guest_group_id: Guest group UUID
            include_activities: Whether to include activities in day plans
            
        Returns:
            ItineraryWithDetails: Complete itinerary or None
        """
        try:
            # Get itinerary by guest group ID
            stmt = select(Itinerary).where(Itinerary.guest_group_id == guest_group_id)
            result = await self.db.execute(stmt)
            itinerary = result.scalar_one_or_none()
            
            if not itinerary:
                return None
            
            # Use existing method to get full details
            return await self.get_itinerary_with_details(itinerary.id, include_activities)
            
        except Exception as e:
            logger.error(f"Error getting itinerary by guest group {guest_group_id}: {e}")
            return None

    async def get_map_view_data_for_host(
        self, day_plan_id: uuid.UUID, host_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Map view data if the day plan belongs to an itinerary owned by host_id."""
        day_plan = await self._get_day_plan(day_plan_id)
        if not day_plan:
            return None
        itinerary = await self._get_itinerary(day_plan.itinerary_id)
        if not itinerary or itinerary.host_id != host_id:
            return None
        data = await self.get_map_view_data(day_plan_id)
        return data if data else None

    async def get_map_view_data(self, day_plan_id: uuid.UUID) -> Dict[str, Any]:
        """
        Generate map view data for a day plan with locations and routes.
        
        Args:
            day_plan_id: Day plan UUID
            
        Returns:
            Dict with map data including locations, routes, and center coordinates
        """
        try:
            # Get day plan
            day_plan = await self._get_day_plan(day_plan_id)
            if not day_plan:
                return {}
            
            # Get itinerary for base location
            itinerary = await self._get_itinerary(day_plan.itinerary_id)
            if not itinerary:
                return {}
            
            # Get activities for this day plan
            activities_stmt = select(ItineraryActivity).where(
                ItineraryActivity.day_plan_id == day_plan_id
            ).order_by(ItineraryActivity.sequence_order)
            
            activities_result = await self.db.execute(activities_stmt)
            activities = activities_result.scalars().all()
            
            # Build locations list
            locations = []
            route_waypoints = []
            
            # Add base location if available
            if itinerary.base_latitude and itinerary.base_longitude:
                locations.append({
                    "id": "base",
                    "name": itinerary.base_location or "Base Location",
                    "lat": float(itinerary.base_latitude),
                    "lng": float(itinerary.base_longitude),
                    "type": "base",
                    "marker_color": "blue"
                })
                route_waypoints.append(f"{itinerary.base_latitude},{itinerary.base_longitude}")
            
            # Add activity locations
            for activity in activities:
                if activity.attraction_id:
                    # Get attraction coordinates
                    attraction_stmt = select(Attraction).where(Attraction.id == activity.attraction_id)
                    attraction_result = await self.db.execute(attraction_stmt)
                    attraction = attraction_result.scalar_one_or_none()
                    
                    if attraction and attraction.latitude and attraction.longitude:
                        locations.append({
                            "id": str(activity.id),
                            "name": activity.title or attraction.name,
                            "lat": float(attraction.latitude),
                            "lng": float(attraction.longitude),
                            "type": "activity",
                            "marker_color": "green",
                            "start_time": activity.scheduled_start_time.isoformat() if activity.scheduled_start_time else None,
                            "sequence": activity.sequence_order
                        })
                        route_waypoints.append(f"{attraction.latitude},{attraction.longitude}")
                elif activity.latitude is not None and activity.longitude is not None:
                    locations.append({
                        "id": str(activity.id),
                        "name": activity.title or activity.location_name,
                        "lat": float(activity.latitude),
                        "lng": float(activity.longitude),
                        "type": "activity",
                        "marker_color": "green",
                        "start_time": activity.scheduled_start_time.isoformat() if activity.scheduled_start_time else None,
                        "sequence": activity.sequence_order,
                    })
                    route_waypoints.append(f"{activity.latitude},{activity.longitude}")

            # Calculate center point (average of all locations)
            if locations:
                center_lat = sum(loc["lat"] for loc in locations) / len(locations)
                center_lng = sum(loc["lng"] for loc in locations) / len(locations)
            elif itinerary.base_latitude and itinerary.base_longitude:
                center_lat = float(itinerary.base_latitude)
                center_lng = float(itinerary.base_longitude)
            else:
                # Default to Lovran
                center_lat = 45.2936
                center_lng = 14.2719
            
            # Build route information
            tpref = itinerary.transportation_preference
            mode_str = (
                tpref.value if hasattr(tpref, "value") else (tpref or "driving")
            )
            route = {
                "waypoints": route_waypoints,
                "optimize": True,
                "mode": mode_str,
            }
            
            return {
                "day_plan_id": str(day_plan_id),
                "locations": locations,
                "route": route,
                "center": {"lat": center_lat, "lng": center_lng},
                "zoom": 13 if len(locations) > 1 else 15,
                "bounds": self._calculate_bounds(locations) if locations else None
            }
            
        except Exception as e:
            logger.error(f"Error generating map view data for day plan {day_plan_id}: {e}")
            return {}
    
    def _calculate_bounds(self, locations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate map bounds from locations."""
        if not locations:
            return {}
        
        lats = [loc["lat"] for loc in locations]
        lngs = [loc["lng"] for loc in locations]
        
        return {
            "north": max(lats),
            "south": min(lats),
            "east": max(lngs),
            "west": min(lngs)
        }

    async def check_in_activity(self, activity_id: uuid.UUID, guest_group_id: uuid.UUID) -> Dict[str, Any]:
        """
        Check in to an activity, updating status and recording actual time.
        
        Args:
            activity_id: Activity UUID
            guest_group_id: Guest group UUID (for validation)
            
        Returns:
            Dict with check-in confirmation
        """
        try:
            # Get activity
            activity_stmt = select(ItineraryActivity).where(ItineraryActivity.id == activity_id)
            activity_result = await self.db.execute(activity_stmt)
            activity = activity_result.scalar_one_or_none()
            
            if not activity:
                raise ValueError("Activity not found")
            
            # Verify activity belongs to guest group's itinerary
            day_plan = await self._get_day_plan(activity.day_plan_id)
            if not day_plan:
                raise ValueError("Day plan not found")
            
            itinerary = await self._get_itinerary(day_plan.itinerary_id)
            if not itinerary or itinerary.guest_group_id != guest_group_id:
                raise ValueError("Activity does not belong to this guest group")
            
            # Update activity status
            from sqlalchemy import update
            from app.models.itinerary import ActivityStatus
            
            update_stmt = update(ItineraryActivity).where(
                ItineraryActivity.id == activity_id
            ).values(
                status=ActivityStatus.COMPLETED,
                actual_start_time=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(update_stmt)
            await self.db.commit()
            
            logger.info(f"Activity {activity_id} checked in by guest group {guest_group_id}")
            
            return {
                "success": True,
                "message": "Checked in to activity successfully",
                "activity_id": str(activity_id),
                "activity_name": activity.title,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error checking in activity {activity_id}: {e}")
            raise

    async def get_itinerary_with_details(self, itinerary_id: uuid.UUID, 
                                       include_activities: bool = True) -> Optional[ItineraryWithDetails]:
        """
        Get complete itinerary with day plans and activities.
        
        Args:
            itinerary_id: Itinerary ID
            include_activities: Whether to include activities in day plans
            
        Returns:
            ItineraryWithDetails: Complete itinerary or None
        """
        try:
            # Get itinerary
            stmt = select(Itinerary).where(Itinerary.id == itinerary_id)
            result = await self.db.execute(stmt)
            itinerary = result.scalar_one_or_none()
            
            if not itinerary:
                return None
            
            # Get day plans
            day_plans_stmt = select(DayPlan).where(
                DayPlan.itinerary_id == itinerary_id
            ).order_by(DayPlan.day_number)
            
            day_plans_result = await self.db.execute(day_plans_stmt)
            day_plans = day_plans_result.scalars().all()
            
            # Convert to response models
            itinerary_response = ItineraryResponse.model_validate(itinerary)
            day_plan_responses = []
            
            for day_plan in day_plans:
                if include_activities:
                    # Get activities for this day
                    activities_stmt = select(ItineraryActivity).where(
                        ItineraryActivity.day_plan_id == day_plan.id
                    ).order_by(ItineraryActivity.sequence_order)
                    
                    activities_result = await self.db.execute(activities_stmt)
                    activities = activities_result.scalars().all()
                    
                    day_plan_with_activities = DayPlanWithActivities(
                        **DayPlanResponse.model_validate(day_plan).model_dump(),
                        activities=[ActivityResponse.model_validate(activity) for activity in activities]
                    )
                    day_plan_responses.append(day_plan_with_activities)
                else:
                    day_plan_responses.append(DayPlanResponse.model_validate(day_plan))
            
            return ItineraryWithDetails(
                **itinerary_response.model_dump(),
                day_plans=day_plan_responses
            )
            
        except Exception as e:
            logger.error(f"Error getting itinerary with details {itinerary_id}: {e}")
            return None

    async def create_day_plan(self, itinerary_id: uuid.UUID, 
                            day_plan_data: DayPlanCreate) -> Optional[DayPlanResponse]:
        """
        Create a day plan within an itinerary.
        
        Args:
            itinerary_id: Parent itinerary ID
            day_plan_data: Day plan creation data
            
        Returns:
            DayPlanResponse: Created day plan or None
        """
        try:
            day_plan = DayPlan(
                itinerary_id=itinerary_id,
                day_number=day_plan_data.day_number,
                date=day_plan_data.date,
                title=day_plan_data.title,
                theme=day_plan_data.theme,
                start_time=day_plan_data.start_time,
                end_time=day_plan_data.end_time,
                description=day_plan_data.description,
                weather_dependent=day_plan_data.weather_dependent,
                main_transport_mode=day_plan_data.main_transport_mode,
                estimated_cost=day_plan_data.estimated_cost
            )
            
            self.db.add(day_plan)
            await self.db.commit()
            await self.db.refresh(day_plan)
            
            logger.info(f"Created day plan {day_plan.id} for itinerary {itinerary_id}")
            return DayPlanResponse.model_validate(day_plan)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating day plan: {e}")
            return None

    async def add_activity_to_day(self, day_plan_id: uuid.UUID, 
                                 activity_data: ActivityCreate) -> Optional[ActivityResponse]:
        """
        Add an activity to a day plan with Google Maps integration.
        
        Args:
            day_plan_id: Day plan ID
            activity_data: Activity creation data
            
        Returns:
            ActivityResponse: Created activity or None
        """
        try:
            # Get day plan to access itinerary and host info
            day_plan = await self._get_day_plan(day_plan_id)
            if not day_plan:
                return None
            
            itinerary = await self._get_itinerary(day_plan.itinerary_id)
            if not itinerary:
                return None
            
            # Get coordinates for the activity location
            coords = await self._geocode_address(itinerary.host_id, activity_data.address or activity_data.location_name)
            
            # Calculate travel information from previous activity
            travel_info = await self._calculate_travel_to_activity(
                day_plan_id, activity_data, coords, itinerary.host_id
            )
            
            # Generate Google Maps URL
            maps_url = await self._generate_google_maps_url(
                activity_data.location_name, 
                activity_data.address,
                coords,
                itinerary.host_id
            )
            
            # Get next sequence order
            next_order = await self._get_next_activity_sequence(day_plan_id)
            
            activity = ItineraryActivity(
                day_plan_id=day_plan_id,
                attraction_id=activity_data.attraction_id,
                title=activity_data.title,
                description=activity_data.description,
                activity_type=activity_data.activity_type,
                category=activity_data.category,
                sequence_order=next_order,
                scheduled_start_time=_naive_utc(activity_data.scheduled_start_time),
                scheduled_end_time=_naive_utc(activity_data.scheduled_end_time),
                estimated_duration=activity_data.estimated_duration,
                location_name=activity_data.location_name,
                address=activity_data.address,
                latitude=coords[0] if coords else activity_data.latitude,
                longitude=coords[1] if coords else activity_data.longitude,
                google_maps_url=maps_url,
                transport_from_previous=activity_data.transport_from_previous,
                travel_time_minutes=travel_info['time_minutes'],
                travel_distance_km=travel_info['distance_km'],
                transport_cost=travel_info['cost'],
                transport_instructions=travel_info['instructions'],
                cost_per_person=activity_data.cost_per_person,
                booking_required=activity_data.booking_required,
                priority_level=activity_data.priority_level,
                host_tip=activity_data.host_tip,
            )
            
            # Add host insights if this is linked to an attraction
            if activity_data.attraction_id:
                attraction = await self.attraction_service.get_attraction_by_id(activity_data.attraction_id)
                if attraction:
                    if not activity.host_tip:
                        activity.host_tip = attraction.host_personal_tip
                    activity.host_story = attraction.host_story
                    activity.insider_info = attraction.host_insider_info
                    activity.best_time_to_visit = attraction.host_favorite_time
                    activity.opening_hours = attraction.opening_hours
            
            self.db.add(activity)
            await self.db.commit()
            await self.db.refresh(activity)
            
            # Update day plan totals
            await self._update_day_plan_totals(day_plan_id)
            
            logger.info(f"Added activity {activity.id} to day plan {day_plan_id}")
            return ActivityResponse.model_validate(activity)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding activity to day plan: {e}")
            return None

    async def update_itinerary(
        self,
        itinerary_id: uuid.UUID,
        host_id: uuid.UUID,
        data: ItineraryUpdate,
    ) -> Optional[ItineraryResponse]:
        try:
            itinerary = await self._get_itinerary(itinerary_id)
            if not itinerary or itinerary.host_id != host_id:
                return None
            payload = data.model_dump(exclude_unset=True)
            for key, value in payload.items():
                setattr(itinerary, key, value)
            itinerary.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(itinerary)
            return ItineraryResponse.model_validate(itinerary)
        except Exception as e:
            await self.db.rollback()
            logger.error("Error updating itinerary %s: %s", itinerary_id, e)
            return None

    async def list_route_points(
        self, itinerary_id: uuid.UUID, host_id: uuid.UUID
    ) -> Optional[List[RoutePointResponse]]:
        itinerary = await self._get_itinerary(itinerary_id)
        if not itinerary or itinerary.host_id != host_id:
            return None
        stmt = (
            select(ItineraryActivity, DayPlan)
            .join(DayPlan, ItineraryActivity.day_plan_id == DayPlan.id)
            .where(DayPlan.itinerary_id == itinerary_id)
            .order_by(DayPlan.day_number, ItineraryActivity.sequence_order)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            RoutePointResponse(
                id=act.id,
                day_plan_id=act.day_plan_id,
                name=act.title,
                latitude=act.latitude,
                longitude=act.longitude,
                description=act.description,
                order_index=act.sequence_order,
                estimated_duration=act.estimated_duration,
            )
            for act, _dp in rows
        ]

    async def add_route_point(
        self,
        itinerary_id: uuid.UUID,
        host_id: uuid.UUID,
        data: RoutePointCreate,
    ) -> Optional[RoutePointResponse]:
        itinerary = await self._get_itinerary(itinerary_id)
        if not itinerary or itinerary.host_id != host_id:
            return None
        day_plan = await self._get_day_plan(data.day_plan_id)
        if not day_plan or day_plan.itinerary_id != itinerary_id:
            return None
        order = data.order_index or await self._get_next_activity_sequence(data.day_plan_id)
        start = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
        end = start + timedelta(minutes=data.estimated_duration)
        created = await self.add_activity_to_day(
            data.day_plan_id,
            ActivityCreate(
                title=data.name,
                description=data.description,
                activity_type="tnt_point",
                location_name=data.name,
                scheduled_start_time=start,
                scheduled_end_time=end,
                estimated_duration=data.estimated_duration,
                latitude=data.latitude,
                longitude=data.longitude,
            ),
        )
        if not created:
            return None
        act = await self._get_activity(created.id)
        if act and act.sequence_order != order:
            act.sequence_order = order
            await self.db.commit()
            await self.db.refresh(act)
        elif act:
            pass
        else:
            act = None
        row = act or await self._get_activity(created.id)
        if not row:
            return None
        return RoutePointResponse(
            id=row.id,
            day_plan_id=row.day_plan_id,
            name=row.title,
            latitude=row.latitude,
            longitude=row.longitude,
            description=row.description,
            order_index=row.sequence_order,
            estimated_duration=row.estimated_duration,
        )

    async def update_route_point(
        self,
        point_id: uuid.UUID,
        host_id: uuid.UUID,
        data: ActivityUpdate,
    ) -> Optional[RoutePointResponse]:
        act = await self._get_activity(point_id)
        if not act:
            return None
        day_plan = await self._get_day_plan(act.day_plan_id)
        itinerary = await self._get_itinerary(day_plan.itinerary_id) if day_plan else None
        if not itinerary or itinerary.host_id != host_id:
            return None
        payload = data.model_dump(exclude_unset=True)
        if "title" in payload:
            act.title = payload["title"]
            if "location_name" not in payload:
                act.location_name = payload["title"]
        if "location_name" in payload:
            act.location_name = payload["location_name"]
        for key in ("description", "address", "latitude", "longitude", "host_tip", "estimated_duration"):
            if key in payload:
                setattr(act, key, payload[key])
        if "sequence_order" in payload:
            act.sequence_order = payload["sequence_order"]
        if "scheduled_start_time" in payload:
            act.scheduled_start_time = _naive_utc(payload["scheduled_start_time"])
        if "scheduled_end_time" in payload:
            act.scheduled_end_time = _naive_utc(payload["scheduled_end_time"])
        act.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(act)
        return RoutePointResponse(
            id=act.id,
            day_plan_id=act.day_plan_id,
            name=act.title,
            latitude=act.latitude,
            longitude=act.longitude,
            description=act.description,
            order_index=act.sequence_order,
            estimated_duration=act.estimated_duration,
        )

    async def delete_route_point(self, point_id: uuid.UUID, host_id: uuid.UUID) -> bool:
        act = await self._get_activity(point_id)
        if not act:
            return False
        day_plan = await self._get_day_plan(act.day_plan_id)
        itinerary = await self._get_itinerary(day_plan.itinerary_id) if day_plan else None
        if not itinerary or itinerary.host_id != host_id:
            return False
        day_plan_id = act.day_plan_id
        await self.db.delete(act)
        await self.db.commit()
        await self._update_day_plan_totals(day_plan_id)
        return True

    async def reorder_route_points(
        self,
        itinerary_id: uuid.UUID,
        host_id: uuid.UUID,
        data: RoutePointReorder,
    ) -> bool:
        itinerary = await self._get_itinerary(itinerary_id)
        if not itinerary or itinerary.host_id != host_id:
            return False
        day_plan = await self._get_day_plan(data.day_plan_id)
        if not day_plan or day_plan.itinerary_id != itinerary_id:
            return False
        stmt = (
            select(ItineraryActivity)
            .where(ItineraryActivity.day_plan_id == data.day_plan_id)
            .order_by(ItineraryActivity.sequence_order, ItineraryActivity.created_at)
        )
        result = await self.db.execute(stmt)
        activities = list(result.scalars().all())
        activities_by_id = {act.id: act for act in activities}
        submitted_ids = list(data.ordered_activity_ids)
        if len(set(submitted_ids)) != len(submitted_ids):
            return False
        if any(act_id not in activities_by_id for act_id in submitted_ids):
            return False

        ordered_ids = submitted_ids + [act.id for act in activities if act.id not in submitted_ids]
        for idx, act_id in enumerate(ordered_ids, start=1):
            activities_by_id[act_id].sequence_order = idx
        await self.db.commit()
        return True

    async def _get_activity(self, activity_id: uuid.UUID) -> Optional[ItineraryActivity]:
        stmt = select(ItineraryActivity).where(ItineraryActivity.id == activity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # Google Maps Integration
    
    async def get_directions(self, host_id: uuid.UUID, 
                           directions_request: GoogleMapsDirectionsRequest) -> Optional[GoogleMapsDirectionsResponse]:
        """
        Get directions between two locations using Google Maps API.
        
        Args:
            host_id: Host ID for API key access
            directions_request: Direction request parameters
            
        Returns:
            GoogleMapsDirectionsResponse: Directions information or None
        """
        try:
            # Get Google Maps API key
            api_key = await self.settings_service.get_host_api_key(str(host_id), "google_maps")
            if not api_key:
                logger.warning(f"No Google Maps API key found for host {host_id}")
                return None
            
            # Build Google Directions API URL
            base_url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": directions_request.origin,
                "destination": directions_request.destination,
                "mode": directions_request.mode.lower(),
                "language": directions_request.language,
                "key": api_key
            }
            
            if directions_request.avoid:
                params["avoid"] = "|".join(directions_request.avoid)
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK" and data.get("routes"):
                            route = data["routes"][0]
                            leg = route["legs"][0]
                            
                            # Generate direct Google Maps URL
                            maps_url = self._create_google_maps_url(
                                directions_request.origin,
                                directions_request.destination,
                                directions_request.mode
                            )
                            
                            return GoogleMapsDirectionsResponse(
                                distance=leg["distance"]["text"],
                                duration=leg["duration"]["text"],
                                distance_value=leg["distance"]["value"],
                                duration_value=leg["duration"]["value"],
                                steps=leg.get("steps", []),
                                polyline=route.get("overview_polyline", {}).get("points"),
                                maps_url=maps_url
                            )
                        else:
                            logger.warning(f"Google Directions API error: {data.get('status')}")
                    else:
                        logger.error(f"Google Directions API request failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            
        return None

    async def optimize_day_plan_route(self, day_plan_id: uuid.UUID) -> bool:
        """
        Optimize the route for a day plan using Google Maps.
        
        Args:
            day_plan_id: Day plan to optimize
            
        Returns:
            bool: True if optimization was successful
        """
        try:
            # Get day plan with activities
            day_plan = await self._get_day_plan_with_activities(day_plan_id)
            if not day_plan or not day_plan.activities:
                return False
            
            itinerary = await self._get_itinerary(day_plan.itinerary_id)
            if not itinerary:
                return False
            
            # Get locations for optimization
            locations = []
            for activity in day_plan.activities:
                if activity.latitude and activity.longitude:
                    locations.append({
                        "id": activity.id,
                        "lat": activity.latitude,
                        "lng": activity.longitude,
                        "name": activity.location_name
                    })
            
            if len(locations) < 2:
                return False
            
            # Use Google Maps Distance Matrix to optimize route
            optimized_order = await self._optimize_route_with_google_maps(
                itinerary.host_id, locations, itinerary.base_latitude, itinerary.base_longitude
            )
            
            if optimized_order:
                # Update activity sequence orders
                for new_order, activity_id in enumerate(optimized_order, 1):
                    stmt = select(ItineraryActivity).where(ItineraryActivity.id == activity_id)
                    result = await self.db.execute(stmt)
                    activity = result.scalar_one_or_none()
                    
                    if activity:
                        activity.sequence_order = new_order
                
                await self.db.commit()
                
                # Recalculate travel times and distances
                await self._recalculate_day_plan_travel(day_plan_id)
                
                logger.info(f"Optimized route for day plan {day_plan_id}")
                return True
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error optimizing day plan route: {e}")
            
        return False

    # AI-Powered Itinerary Generation

    def _build_llm_itinerary_catalog(self, attractions: List[Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        catalog: List[Dict[str, Any]] = []
        for a in attractions:
            catalog.append(
                {
                    "id": str(a.id),
                    "name": getattr(a, "name", "") or "",
                    "type": str(getattr(a, "attraction_type", "") or ""),
                    "city": getattr(a, "city", "") or "",
                    "tags": list(getattr(a, "category_tags", None) or []),
                    "excerpt": ((getattr(a, "description", None) or "")[:240]),
                }
            )
        by_id = {str(x.id): x for x in attractions}
        return catalog, by_id

    def _build_llm_itinerary_user_prompt(
        self,
        catalog: List[Dict[str, Any]],
        request: ItinerarySuggestionRequest,
        guest_group: Optional[GuestGroup],
    ) -> str:
        theme = (request.theme_prompt or "").strip()
        must = [str(x) for x in (request.must_see_attractions or [])]
        avoid = request.avoid_activities or []
        guest_note = (
            f"Lead guest / group label: {guest_group.lead_guest_name or 'guests'}"
            if guest_group
            else "Generic reusable template (no specific guest yet)."
        )
        return f"""Plan a {request.duration_days}-day Croatian tourism itinerary for a holiday-rental host.

{guest_note}
Theme / brief: {theme or '(none — balanced highlights)'}
Interests (weight these): {json.dumps(request.interests, ensure_ascii=False)}
Pace: {request.pace!r}, budget: {request.budget_level!r}
Must include these attraction IDs on at least one day (use exact UUIDs): {json.dumps(must)}
Avoid or de-prioritize activity names/types like: {json.dumps(avoid, ensure_ascii=False)}

You may ONLY use attraction IDs from this catalog (do not invent UUIDs):
{json.dumps(catalog, ensure_ascii=False)}

Return JSON with this exact shape (no markdown fences):
{{
  "itinerary_title": "short compelling title",
  "itinerary_description": "2–5 sentences for guests",
  "reasoning_summary": "2–4 sentences why this flow works geographically and thematically",
  "days": [
    {{
      "day_number": 1,
      "day_title": "short",
      "day_theme": "e.g. coast | culture | food",
      "ordered_attraction_ids": ["uuid", "..."]
    }}
  ]
}}

Rules:
- "days" must have exactly {request.duration_days} objects with day_number 1 through {request.duration_days}.
- Each day: 2–5 stops when the catalog allows; order them for sensible geography and pacing.
- Every ordered_attraction_ids entry must be a string UUID present in the catalog.
- Spread must-see IDs across suitable days; avoid repeating the same attraction on multiple days unless the catalog is very small."""

    def _build_itinerary_from_llm_plan(
        self,
        host: Host,
        guest_group: Optional[GuestGroup],
        attractions_by_id: Dict[str, Any],
        plan: LLMItineraryPlanResult,
        request: ItinerarySuggestionRequest,
    ) -> Tuple[ItineraryCreate, List[DayPlanCreate], List[ActivityCreate]]:
        is_generic = guest_group is None
        theme = (request.theme_prompt or "").strip()
        title_core = (
            f"{request.duration_days}-Day {theme}"
            if theme
            else f"{request.duration_days}-Day Croatian Experience"
        )
        desc_fallback = (
            f"AI-generated route template themed around: {theme}. "
            "Assign to a guest group with a start date when ready."
            if is_generic
            else "AI-generated itinerary based on your preferences"
        )
        if is_generic:
            start_date = None
            end_date = None
            base_label = f"{host.city or 'Lovran'}, Croatia"
        else:
            start_date = date.today() + timedelta(days=1)
            end_date = start_date + timedelta(days=request.duration_days - 1)
            base_label = guest_group.lead_guest_name or "Lovran, Croatia"

        title = (plan.itinerary_title or title_core)[:200]
        desc = (plan.itinerary_description or desc_fallback)[:2000]

        suggested_itinerary = ItineraryCreate(
            title=title,
            description=desc if desc else None,
            start_date=start_date,
            end_date=end_date,
            base_location=base_label[:200],
            pace=request.pace,
            budget_level=request.budget_level,
            group_interests=request.interests,
            is_template=is_generic,
        )

        day_plans: List[DayPlanCreate] = []
        activities: List[ActivityCreate] = []
        template_epoch = date(2000, 1, 1)
        days_sorted = sorted(plan.days, key=lambda d: d.day_number)

        for day_plan_item in days_sorted:
            day_num = day_plan_item.day_number
            if is_generic:
                day_date = template_epoch + timedelta(days=day_num - 1)
            else:
                assert start_date is not None
                day_date = start_date + timedelta(days=day_num - 1)
            day_title = (day_plan_item.day_title or f"Day {day_num}")[:200]
            day_theme = (day_plan_item.day_theme or theme or "Exploration")[:100]
            day_plans.append(
                DayPlanCreate(
                    day_number=day_num,
                    date=day_date,
                    title=day_title,
                    theme=day_theme,
                )
            )
            for i, aid in enumerate(day_plan_item.ordered_attraction_ids):
                attraction = attractions_by_id.get(aid)
                if not attraction:
                    continue
                start_time = datetime.combine(day_date, time(9 + i * 2, 0))
                end_time = start_time + timedelta(hours=1, minutes=30)
                activities.append(
                    ActivityCreate(
                        title=(getattr(attraction, "name", None) or f"Activity {i + 1}")[:200],
                        description=getattr(attraction, "description", "") or "",
                        activity_type="attraction",
                        location_name=(getattr(attraction, "name", "") or "")[:200],
                        address=getattr(attraction, "address", None),
                        scheduled_start_time=start_time,
                        scheduled_end_time=end_time,
                        estimated_duration=90,
                        attraction_id=getattr(attraction, "id", None),
                        host_tip=getattr(attraction, "host_personal_tip", None),
                    )
                )

        return suggested_itinerary, day_plans, activities

    async def _try_llm_itinerary_plan(
        self,
        host_id: uuid.UUID,
        host: Host,
        guest_group: Optional[GuestGroup],
        attractions: List[Any],
        request: ItinerarySuggestionRequest,
    ) -> Optional[Tuple[ItineraryCreate, List[DayPlanCreate], List[ActivityCreate], str]]:
        flag = os.getenv("ITINERARY_USE_LLM", "1").strip().lower()
        if flag in ("0", "false", "no"):
            return None
        if not attractions:
            return None

        catalog, by_id = self._build_llm_itinerary_catalog(attractions)
        catalog_ids = set(by_id.keys())
        user_content = self._build_llm_itinerary_user_prompt(catalog, request, guest_group)
        ctx: Dict[str, Any] = {
            "location": "Croatia",
            "focus_area": host.city or "Istria",
            "task": "itinerary_json",
        }

        res = await self._ai_service.generate_structured_response(
            str(host_id),
            [{"role": "user", "content": user_content}],
            context=ctx,
            response_schema=LLMItineraryPlanResult,
        )
        plan: Optional[LLMItineraryPlanResult] = None
        if res.get("success") and res.get("structured_data"):
            try:
                plan = LLMItineraryPlanResult.model_validate(res["structured_data"])
            except Exception as e:
                logger.warning("LLM itinerary: structured_data validation failed: %s", e)
        if plan is None and res.get("success"):
            parsed = _parse_llm_itinerary_json(res.get("response") or "")
            if parsed:
                try:
                    plan = LLMItineraryPlanResult.model_validate(parsed)
                except Exception as e:
                    logger.warning("LLM itinerary: response JSON validation failed: %s", e)

        if plan is None:
            chat = await self._ai_service.generate_chat_response(
                str(host_id),
                [
                    {
                        "role": "user",
                        "content": user_content + "\n\nRespond with ONLY valid JSON, no other text.",
                    }
                ],
                context=ctx,
            )
            if chat.get("success"):
                parsed = _parse_llm_itinerary_json(chat.get("response") or "")
                if parsed:
                    try:
                        plan = LLMItineraryPlanResult.model_validate(parsed)
                    except Exception as e:
                        logger.warning("LLM itinerary: chat JSON validation failed: %s", e)

        if plan is None:
            return None
        if not _llm_plan_is_usable(
            plan,
            request.duration_days,
            catalog_ids,
            list(request.must_see_attractions or []),
        ):
            logger.info("LLM itinerary plan rejected by validation rules")
            return None

        payload = self._build_itinerary_from_llm_plan(host, guest_group, by_id, plan, request)
        reasoning = (plan.reasoning_summary or "").strip()
        return (*payload, reasoning)

    async def generate_itinerary_suggestions(self, host_id: uuid.UUID, 
                                           suggestion_request: ItinerarySuggestionRequest) -> Optional[ItinerarySuggestionResponse]:
        """
        Generate AI-powered itinerary suggestions for a guest group or a generic route template.
        """
        try:
            guest_group: Optional[GuestGroup] = None
            if suggestion_request.guest_group_id:
                guest_group = await self._get_guest_group(suggestion_request.guest_group_id)
                if not guest_group:
                    return None
                if not host_owns_guest_group(guest_group, host_id):
                    return None

            host = await self._get_host(host_id)
            if not host:
                return None

            region_filter = getattr(host, "county", None) or getattr(host, "region", None)
            attractions = await self.attraction_service.search_attractions(
                city=host.city,
                region=region_filter,
                only_approved=True,
                limit=50
            )

            suitable_attractions = self._filter_attractions_by_preferences(
                attractions, suggestion_request, guest_group
            )

            llm_out = await self._try_llm_itinerary_plan(
                host_id, host, guest_group, suitable_attractions, suggestion_request
            )
            if llm_out:
                suggested_itinerary, day_plans, activities, reasoning_llm = llm_out
                reasoning = reasoning_llm or await self._generate_itinerary_reasoning(
                    guest_group, suggestion_request, suitable_attractions
                )
            else:
                suggested_itinerary, day_plans, activities = await self._generate_optimized_itinerary(
                    host_id,
                    guest_group,
                    suitable_attractions,
                    suggestion_request,
                )
                reasoning = await self._generate_itinerary_reasoning(
                    guest_group, suggestion_request, suitable_attractions
                )

            return ItinerarySuggestionResponse(
                suggested_itinerary=suggested_itinerary,
                day_plans=day_plans,
                activities=activities,
                reasoning=reasoning,
                alternatives=await self._generate_alternative_suggestions(suggestion_request)
            )

        except Exception as e:
            logger.error(f"Error generating itinerary suggestions: {e}")
            return None

    # Collaborative Planning Features
    
    async def vote_on_activity(self, guest_group_id: uuid.UUID, activity_id: uuid.UUID,
                              vote_data: ActivityVoteCreate) -> Optional[ActivityVoteResponse]:
        """
        Allow guests to vote on activities.
        
        Args:
            guest_group_id: Guest group voting
            activity_id: Activity to vote on
            vote_data: Vote information
            
        Returns:
            ActivityVoteResponse: Created vote or None
        """
        try:
            # Check if guest already voted on this activity
            existing_vote_stmt = select(ActivityVote).where(
                and_(
                    ActivityVote.itinerary_activity_id == activity_id,
                    ActivityVote.guest_group_id == guest_group_id,
                    ActivityVote.guest_name == vote_data.guest_name
                )
            )
            
            existing_result = await self.db.execute(existing_vote_stmt)
            existing_vote = existing_result.scalar_one_or_none()
            
            if existing_vote:
                # Update existing vote
                existing_vote.vote = vote_data.vote
                existing_vote.priority = vote_data.priority
                existing_vote.reason = vote_data.reason
                existing_vote.updated_at = datetime.utcnow()
                
                await self.db.commit()
                await self.db.refresh(existing_vote)
                
                return ActivityVoteResponse.model_validate(existing_vote)
            else:
                # Create new vote
                vote = ActivityVote(
                    itinerary_activity_id=activity_id,
                    guest_group_id=guest_group_id,
                    guest_name=vote_data.guest_name,
                    vote=vote_data.vote,
                    priority=vote_data.priority,
                    reason=vote_data.reason
                )
                
                self.db.add(vote)
                await self.db.commit()
                await self.db.refresh(vote)
                
                logger.info(f"Guest voted on activity {activity_id}: {vote_data.vote}")
                return ActivityVoteResponse.model_validate(vote)
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error voting on activity: {e}")
            return None

    async def get_activity_votes(self, activity_id: uuid.UUID) -> List[ActivityVoteResponse]:
        """
        Get all votes for an activity.
        
        Args:
            activity_id: Activity ID
            
        Returns:
            List[ActivityVoteResponse]: List of votes
        """
        try:
            stmt = select(ActivityVote).where(
                ActivityVote.itinerary_activity_id == activity_id
            ).order_by(desc(ActivityVote.created_at))
            
            result = await self.db.execute(stmt)
            votes = result.scalars().all()
            
            return [ActivityVoteResponse.model_validate(vote) for vote in votes]
            
        except Exception as e:
            logger.error(f"Error getting activity votes: {e}")
            return []

    # Helper Methods
    
    async def _geocode_address(self, host_id: uuid.UUID, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address using Google Maps Geocoding API.
        
        Args:
            host_id: Host ID for API key access
            address: Address to geocode
            
        Returns:
            Tuple[float, float]: Latitude, longitude or None
        """
        try:
            api_key = await self.settings_service.get_host_api_key(str(host_id), "google_maps")
            if not api_key:
                return None
            
            base_url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": address,
                "key": api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "OK" and data.get("results"):
                            location = data["results"][0]["geometry"]["location"]
                            return (location["lat"], location["lng"])
                            
        except Exception as e:
            logger.error(f"Error geocoding address {address}: {e}")
            
        return None

    async def _calculate_travel_to_activity(self, day_plan_id: uuid.UUID, 
                                          activity_data: ActivityCreate,
                                          activity_coords: Optional[Tuple[float, float]],
                                          host_id: uuid.UUID) -> Dict[str, Any]:
        """Calculate travel information to an activity."""
        travel_info = {
            "time_minutes": 0,
            "distance_km": 0.0,
            "cost": 0.0,
            "instructions": ""
        }
        
        try:
            # Get previous activity in sequence
            previous_activity = await self._get_last_activity_in_day(day_plan_id)
            
            if previous_activity and activity_coords:
                # Calculate travel using Google Maps
                origin = f"{previous_activity.latitude},{previous_activity.longitude}"
                destination = f"{activity_coords[0]},{activity_coords[1]}"
                
                directions_request = GoogleMapsDirectionsRequest(
                    origin=origin,
                    destination=destination,
                    mode=activity_data.transport_from_previous
                )
                
                directions = await self.get_directions(host_id, directions_request)
                
                if directions:
                    travel_info["time_minutes"] = directions.duration_value // 60
                    travel_info["distance_km"] = directions.distance_value / 1000
                    travel_info["instructions"] = f"Travel {directions.distance} in {directions.duration}"
                    
                    # Estimate cost based on transport mode
                    if activity_data.transport_from_previous == TransportMode.DRIVING:
                        travel_info["cost"] = travel_info["distance_km"] * 0.5  # Rough estimate
                    elif activity_data.transport_from_previous == TransportMode.TRANSIT:
                        travel_info["cost"] = 2.0  # Rough public transport cost
                        
        except Exception as e:
            logger.error(f"Error calculating travel to activity: {e}")
            
        return travel_info

    async def _generate_google_maps_url(self, location_name: str, address: Optional[str],
                                      coords: Optional[Tuple[float, float]], host_id: uuid.UUID) -> Optional[str]:
        """Generate a direct Google Maps URL for a location."""
        try:
            if coords:
                # Use coordinates for precision
                query = f"{coords[0]},{coords[1]}"
            elif address:
                query = quote(address)
            else:
                query = quote(location_name)
            
            return f"https://www.google.com/maps/search/?api=1&query={query}"
            
        except Exception as e:
            logger.error(f"Error generating Google Maps URL: {e}")
            return None

    def _create_google_maps_url(self, origin: str, destination: str, mode: str) -> str:
        """Create a Google Maps URL for directions."""
        base_url = "https://www.google.com/maps/dir/"
        mode_param = ""
        
        if mode == TransportMode.WALKING:
            mode_param = "&dirflg=w"
        elif mode == TransportMode.TRANSIT:
            mode_param = "&dirflg=r"
        elif mode == TransportMode.CYCLING:
            mode_param = "&dirflg=b"
        
        return f"{base_url}{quote(origin)}/{quote(destination)}/{mode_param}"

    async def _get_day_plan(self, day_plan_id: uuid.UUID) -> Optional[DayPlan]:
        """Get a day plan by ID."""
        stmt = select(DayPlan).where(DayPlan.id == day_plan_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_itinerary(self, itinerary_id: uuid.UUID) -> Optional[Itinerary]:
        """Get an itinerary by ID."""
        stmt = select(Itinerary).where(Itinerary.id == itinerary_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_guest_group(self, guest_group_id: uuid.UUID) -> Optional[GuestGroup]:
        """Get a guest group by ID."""
        stmt = select(GuestGroup).where(GuestGroup.id == guest_group_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_host(self, host_id: uuid.UUID) -> Optional[Host]:
        """Get a host by ID."""
        stmt = select(Host).where(Host.id == host_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_next_activity_sequence(self, day_plan_id: uuid.UUID) -> int:
        """Get the next sequence order for activities in a day plan."""
        stmt = select(func.max(ItineraryActivity.sequence_order)).where(
            ItineraryActivity.day_plan_id == day_plan_id
        )
        result = await self.db.execute(stmt)
        max_order = result.scalar()
        return (max_order or 0) + 1

    async def _get_last_activity_in_day(self, day_plan_id: uuid.UUID) -> Optional[ItineraryActivity]:
        """Get the last activity in a day plan."""
        stmt = select(ItineraryActivity).where(
            ItineraryActivity.day_plan_id == day_plan_id
        ).order_by(desc(ItineraryActivity.sequence_order)).limit(1)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _update_day_plan_totals(self, day_plan_id: uuid.UUID):
        """Update day plan totals based on activities."""
        try:
            # Get all activities for the day
            stmt = select(ItineraryActivity).where(
                ItineraryActivity.day_plan_id == day_plan_id
            )
            result = await self.db.execute(stmt)
            activities = result.scalars().all()
            
            # Calculate totals
            total_distance = sum(activity.travel_distance_km for activity in activities)
            total_travel_time = sum(activity.travel_time_minutes for activity in activities)
            estimated_cost = sum(activity.cost_per_person or 0 for activity in activities)
            
            # Update day plan
            day_plan_stmt = select(DayPlan).where(DayPlan.id == day_plan_id)
            day_plan_result = await self.db.execute(day_plan_stmt)
            day_plan = day_plan_result.scalar_one_or_none()
            
            if day_plan:
                day_plan.total_distance = total_distance
                day_plan.total_travel_time = total_travel_time
                day_plan.estimated_cost = estimated_cost
                day_plan.updated_at = datetime.utcnow()
                
                await self.db.commit()
                
        except Exception as e:
            logger.error(f"Error updating day plan totals: {e}")

    def _filter_attractions_by_preferences(self, attractions: List[Any], 
                                         request: ItinerarySuggestionRequest,
                                         guest_group: Optional[GuestGroup]) -> List[Any]:
        """Filter attractions based on guest preferences."""
        suitable = []
        
        for attraction in attractions:
            if request.interests:
                attraction_tags = getattr(attraction, 'category_tags', [])
                if any(interest in attraction_tags for interest in request.interests):
                    suitable.append(attraction)
            else:
                suitable.append(attraction)
        
        return suitable[:20]  # Limit for performance

    async def _generate_optimized_itinerary(
        self,
        host_id: uuid.UUID,
        guest_group: Optional[GuestGroup],
        attractions: List[Any],
        request: ItinerarySuggestionRequest,
    ) -> Tuple[ItineraryCreate, List[DayPlanCreate], List[ActivityCreate]]:
        """Generate an optimized itinerary structure (guest-specific or generic template)."""
        is_generic = guest_group is None
        host_ref = await self._get_host(host_id)
        host_city = (host_ref.city if host_ref and host_ref.city else None) or "Lovran"

        if is_generic:
            start_date = None
            end_date = None
            base_label = f"{host_city}, Croatia"
        else:
            start_date = date.today() + timedelta(days=1)
            end_date = start_date + timedelta(days=request.duration_days - 1)
            base_label = guest_group.lead_guest_name or "Lovran, Croatia"

        theme = (request.theme_prompt or "").strip()
        title_core = (
            f"{request.duration_days}-Day {theme}"
            if theme
            else f"{request.duration_days}-Day Croatian Experience"
        )
        desc = (
            f"AI-generated route template themed around: {theme}. "
            "Assign to a guest group with a start date when ready."
            if is_generic
            else "AI-generated itinerary based on your preferences"
        )

        suggested_itinerary = ItineraryCreate(
            title=title_core[:200],
            description=desc[:2000] if desc else None,
            start_date=start_date,
            end_date=end_date,
            base_location=base_label[:200],
            pace=request.pace,
            budget_level=request.budget_level,
            group_interests=request.interests,
            is_template=is_generic,
        )
        
        # Create day plans
        day_plans = []
        activities = []
        
        attractions_per_day = len(attractions) // request.duration_days
        
        template_epoch = date(2000, 1, 1)
        for day_num in range(1, request.duration_days + 1):
            day_date = (
                template_epoch + timedelta(days=day_num - 1)
                if is_generic
                else start_date + timedelta(days=day_num - 1)
            )

            day_plan = DayPlanCreate(
                day_number=day_num,
                date=day_date,
                title=f"Day {day_num} - Croatian Discovery",
                theme=theme[:100] if theme else "Cultural & Natural Exploration",
            )
            day_plans.append(day_plan)

            start_idx = (day_num - 1) * attractions_per_day
            end_idx = start_idx + attractions_per_day
            day_attractions = attractions[start_idx:end_idx]

            for i, attraction in enumerate(day_attractions):
                start_time = datetime.combine(day_date, time(9 + i * 2, 0))
                end_time = start_time + timedelta(hours=1.5)

                activity = ActivityCreate(
                    title=getattr(attraction, 'name', f'Activity {i+1}'),
                    description=getattr(attraction, 'description', ''),
                    activity_type="attraction",
                    location_name=getattr(attraction, 'name', ''),
                    address=getattr(attraction, 'address', ''),
                    scheduled_start_time=start_time,
                    scheduled_end_time=end_time,
                    estimated_duration=90,
                    attraction_id=getattr(attraction, 'id', None),
                    host_tip=getattr(attraction, 'host_personal_tip', None),
                )
                activities.append(activity)

        return suggested_itinerary, day_plans, activities

    async def _generate_itinerary_reasoning(
        self,
        guest_group: Optional[GuestGroup],
        request: ItinerarySuggestionRequest,
        attractions: List[Any],
    ) -> str:
        """Generate reasoning for the suggested itinerary."""
        interests_txt = ", ".join(request.interests) if request.interests else "general discovery"
        theme_txt = (request.theme_prompt or "").strip()
        if guest_group is None:
            base = (
                f"This {request.duration_days}-day reusable route template highlights {len(attractions)} curated stops "
                f"with interests aligned to: {interests_txt}. "
            )
            if theme_txt:
                base += f"Theme: {theme_txt}. "
            base += (
                f"Pace: {request.pace}, budget: {request.budget_level}. "
                "Save as a template and assign to a guest group with a start date."
            )
            return base
        return f"""This {request.duration_days}-day itinerary was created based on your group's interests in {interests_txt}
        and your {request.budget_level} budget preference. The {request.pace} pace allows for comfortable exploration
        of Croatian culture and natural beauty. Each day includes a mix of activities
        that match your preferences while allowing time for spontaneous discoveries."""

    async def _generate_alternative_suggestions(self, request: ItinerarySuggestionRequest) -> List[str]:
        """Generate alternative suggestions."""
        alternatives = [
            "Focus more on coastal activities and beaches",
            "Include more cultural and historical sites",
            "Add wine tasting and culinary experiences",
            "Include day trips to nearby cities like Pula or Rovinj"
        ]
        return alternatives[:3]  # Return top 3 alternatives 