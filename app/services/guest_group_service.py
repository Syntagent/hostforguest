"""
Guest group service layer for the Croatian tourist host platform.

Handles guest group management, access code generation/validation,
and preference collection for the B2B SaaS platform.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.exc import IntegrityError

from app.models.guest_group import (
    GuestGroup,
    AccessCode,
    GuestPreference,
    GuestEVisitorData,
    GuestGroupStatus,
    AccessCodeStatus,
    GuestGroupCreate,
    GuestGroupUpdate,
    GuestGroupResponse,
    GuestGroupAccommodationSummary,
    HostGuestExperienceResponse,
    AccessCodeCreate,
    AccessCodeResponse,
    AccessCodeActivation,
    GuestPreferenceCreate,
    GuestPreferenceResponse,
    GuestEVisitorDataCreate,
    GuestEVisitorDataUpdate,
    GuestEVisitorDataResponse,
    generate_access_code,
    is_access_code_valid,
)
from app.models.host import HostProfile
from app.core.config import settings

logger = logging.getLogger(__name__)

# New guest-group codes: shared link, multiple devices / retries (within cap)
DEFAULT_GUEST_GROUP_CODE_EXPIRE_HOURS = 720  # 30d (AccessCodeCreate max)
DEFAULT_GUEST_GROUP_CODE_MAX_USAGE = 10  # AccessCodeCreate allows max 10


def _accommodation_summary_from_profile(profile: HostProfile) -> GuestGroupAccommodationSummary:
    return GuestGroupAccommodationSummary(
        host_profile_id=profile.id,
        property_name=profile.property_name,
        property_type=profile.property_type,
        address=profile.address,
        city=profile.city,
        county=profile.county,
        latitude=profile.latitude,
        longitude=profile.longitude,
    )


def host_owns_guest_group(group: Optional[GuestGroup], host_id: object) -> bool:
    """True if group belongs to host (UUID-safe across asyncpg / SQLAlchemy / str)."""
    if group is None or host_id is None:
        return False
    try:
        return uuid.UUID(str(group.host_id)) == uuid.UUID(str(host_id))
    except (ValueError, TypeError, AttributeError):
        return False


def _access_code_status_equals(status: object, expected: AccessCodeStatus) -> bool:
    """DB may return plain str; avoid `str != Enum` false negatives in Python."""
    if status is None:
        return False
    if isinstance(status, AccessCodeStatus):
        return status == expected
    return str(status).lower() == expected.value


class GuestGroupService:
    """
    Service class for guest group management operations.
    
    Handles guest group creation, access code management, and preference
    collection for the Croatian tourist platform.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the guest group service.
        
        Args:
            db: Database session
        """
        self.db = db

    async def get_by_id(self, group_id: uuid.UUID) -> Optional[GuestGroup]:
        """Alias used by API routes; returns ORM row."""
        return await self.get_guest_group_by_id(group_id)

    async def _active_access_code_row(self, guest_group_id: uuid.UUID) -> Optional[AccessCode]:
        """Newest usable AccessCode row for a group, or None."""
        now = datetime.utcnow()
        stmt = (
            select(AccessCode)
            .where(
                AccessCode.guest_group_id == guest_group_id,
                AccessCode.status == AccessCodeStatus.ACTIVE.value,
                AccessCode.expires_at > now,
                AccessCode.usage_count < AccessCode.max_usage_count,
            )
            .order_by(AccessCode.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _usable_access_code_for_group(self, guest_group_id: uuid.UUID) -> Optional[str]:
        ac = await self._active_access_code_row(guest_group_id)
        return ac.code if ac else None

    async def _profile_for_host_id(self, host_id: uuid.UUID) -> Optional[HostProfile]:
        stmt = select(HostProfile).where(HostProfile.host_id == host_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _profile_for_guest_group(
        self,
        group: GuestGroup,
        profile_hint: Optional[HostProfile] = None,
    ) -> Optional[HostProfile]:
        if profile_hint is not None:
            return profile_hint
        if group.host_profile_id:
            r = await self.db.execute(
                select(HostProfile).where(HostProfile.id == group.host_profile_id)
            )
            prof = r.scalar_one_or_none()
            if prof is not None:
                return prof
        return await self._profile_for_host_id(group.host_id)

    async def guest_group_to_response(
        self,
        group: GuestGroup,
        *,
        profile: Optional[HostProfile] = None,
    ) -> GuestGroupResponse:
        """Build API response including access_code and linked accommodation (host_profiles)."""
        code = await self._usable_access_code_for_group(group.id)
        prof = await self._profile_for_guest_group(group, profile)
        acc = _accommodation_summary_from_profile(prof) if prof else None
        base = GuestGroupResponse.model_validate(group)
        return base.model_copy(update={"access_code": code, "accommodation": acc})
    
    # Guest Group CRUD Operations
    async def create_guest_group(self, host_id: uuid.UUID, group_data: GuestGroupCreate) -> Optional[GuestGroupResponse]:
        """
        Create a new guest group for a host.
        
        Args:
            host_id: Host UUID who owns this group
            group_data: Guest group creation data
            
        Returns:
            GuestGroupResponse: Created guest group or None if failed
        """
        try:
            prof = await self._profile_for_host_id(host_id)
            # Create guest group
            guest_group = GuestGroup(
                host_id=host_id,
                host_profile_id=prof.id if prof else None,
                group_name=group_data.group_name,
                group_size=group_data.group_size,
                check_in_date=group_data.check_in_date,
                check_out_date=group_data.check_out_date,
                lead_guest_name=group_data.lead_guest_name,
                lead_guest_email=group_data.lead_guest_email,
                lead_guest_phone=group_data.lead_guest_phone,
                preferred_language=group_data.preferred_language,
                supported_languages=group_data.supported_languages,
                age_groups=group_data.age_groups,
                interests=group_data.interests,
                mobility_requirements=group_data.mobility_requirements,
                dietary_restrictions=group_data.dietary_restrictions,
                budget_level=group_data.budget_level,
                preferred_activities=group_data.preferred_activities,
                avoided_activities=group_data.avoided_activities,
                previous_visits_croatia=group_data.previous_visits_croatia,
                travel_style=group_data.travel_style,
                group_dynamics=group_data.group_dynamics,
                interested_regions=group_data.interested_regions,
                seasonal_preferences=group_data.seasonal_preferences
            )
            
            self.db.add(guest_group)
            await self.db.commit()
            await self.db.refresh(guest_group)

            issued = await self.generate_access_code_for_group(
                host_id,
                AccessCodeCreate(
                    guest_group_id=guest_group.id,
                    expires_in_hours=DEFAULT_GUEST_GROUP_CODE_EXPIRE_HOURS,
                    max_usage_count=DEFAULT_GUEST_GROUP_CODE_MAX_USAGE,
                ),
            )
            if not issued:
                logger.warning(
                    "Guest group %s created but initial access code failed for host %s",
                    guest_group.id,
                    host_id,
                )

            logger.info(f"Guest group created successfully: {guest_group.id} for host {host_id}")
            return await self.guest_group_to_response(guest_group, profile=prof)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating guest group for host {host_id}: {e}")
            return None
    
    async def get_guest_group_by_id(self, group_id: uuid.UUID) -> Optional[GuestGroup]:
        """
        Get guest group by ID.
        
        Args:
            group_id: Guest group UUID
            
        Returns:
            GuestGroup: Guest group object or None
        """
        try:
            stmt = select(GuestGroup).where(GuestGroup.id == group_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting guest group by ID {group_id}: {e}")
            return None

    async def get_host_guest_experience(
        self,
        host_id: uuid.UUID,
        guest_group_id: uuid.UUID,
    ) -> Optional[HostGuestExperienceResponse]:
        """
        Host-only: guest group plus latest usable access code for opening the guest app.

        Read-only; does not increment access code usage.
        """
        group = await self.get_guest_group_by_id(guest_group_id)
        if not host_owns_guest_group(group, host_id):
            return None
        ac = await self._active_access_code_row(guest_group_id)
        code_str = ac.code if ac else None
        expires = ac.expires_at if ac else None
        guest_app_path = f"/guest/{code_str}" if code_str else ""
        prof = await self._profile_for_host_id(host_id)
        gg = await self.guest_group_to_response(group, profile=prof)
        return HostGuestExperienceResponse(
            guest_group=gg,
            access_code=code_str,
            access_code_expires_at=expires,
            guest_app_path=guest_app_path,
            guest_join_path="/guest/join",
        )

    async def get_host_guest_groups(self, host_id: uuid.UUID, include_completed: bool = False) -> List[GuestGroupResponse]:
        """
        Get all guest groups for a host.
        
        Args:
            host_id: Host UUID
            include_completed: Whether to include completed groups
            
        Returns:
            List[GuestGroupResponse]: List of guest groups
        """
        try:
            stmt = select(GuestGroup).where(GuestGroup.host_id == host_id)
            
            if not include_completed:
                stmt = stmt.where(GuestGroup.status.in_([
                    GuestGroupStatus.PENDING,
                    GuestGroupStatus.ACTIVE
                ]))
            
            stmt = stmt.order_by(GuestGroup.created_at.desc())
            result = await self.db.execute(stmt)
            groups = result.scalars().all()

            prof = await self._profile_for_host_id(host_id)
            return [await self.guest_group_to_response(g, profile=prof) for g in groups]
            
        except Exception as e:
            logger.error(f"Error getting guest groups for host {host_id}: {e}")
            return []
    
    async def update_guest_group(self, group_id: uuid.UUID, group_data: GuestGroupUpdate) -> Optional[GuestGroupResponse]:
        """
        Update guest group information.
        
        Args:
            group_id: Guest group UUID
            group_data: Updated group data
            
        Returns:
            GuestGroupResponse: Updated guest group or None
        """
        try:
            # Get existing group
            group = await self.get_guest_group_by_id(group_id)
            if not group:
                logger.warning(f"Guest group update failed: Group not found {group_id}")
                return None
            
            # Update only provided fields
            update_data = group_data.model_dump(exclude_unset=True)
            if update_data:
                update_data['updated_at'] = datetime.utcnow()
                
                stmt = update(GuestGroup).where(GuestGroup.id == group_id).values(**update_data)
                await self.db.execute(stmt)
                await self.db.commit()
                
                # Refresh group data
                await self.db.refresh(group)
                
                logger.info(f"Guest group updated successfully: {group_id}")
                prof = await self._profile_for_host_id(group.host_id)
                return await self.guest_group_to_response(group, profile=prof)

            prof = await self._profile_for_host_id(group.host_id)
            return await self.guest_group_to_response(group, profile=prof)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating guest group {group_id}: {e}")
            return None
    
    async def delete_guest_group(self, group_id: uuid.UUID) -> bool:
        """
        Delete a guest group and associated access codes.
        
        Args:
            group_id: Guest group UUID
            
        Returns:
            bool: True if successful
        """
        try:
            # First revoke all access codes for this group
            await self._revoke_group_access_codes(group_id)
            
            # Delete the group
            stmt = delete(GuestGroup).where(GuestGroup.id == group_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Guest group deleted successfully: {group_id}")
                return True
            else:
                logger.warning(f"Guest group not found for deletion: {group_id}")
                return False
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting guest group {group_id}: {e}")
            return False
    
    # Access Code Management
    async def generate_access_code_for_group(
        self,
        host_id: uuid.UUID,
        code_data: AccessCodeCreate,
        client_ip: Optional[str] = None,
        *,
        raise_on_failure: bool = False,
    ) -> Optional[AccessCodeResponse]:
        """
        Generate an access code for a guest group.
        
        Args:
            host_id: Host UUID creating the code
            code_data: Access code creation data
            client_ip: IP address of the client creating the code
            
        Returns:
            AccessCodeResponse: Created access code or None
        """
        try:
            # Verify the guest group belongs to the host
            group = await self.get_guest_group_by_id(code_data.guest_group_id)
            if not host_owns_guest_group(group, host_id):
                msg = (
                    f"Access code creation failed: Group {code_data.guest_group_id} "
                    f"not found or not owned by host {host_id}"
                )
                logger.warning(msg)
                if raise_on_failure:
                    raise ValueError(msg)
                return None

            # Generate unique access code
            max_attempts = 10
            code = None
            for _ in range(max_attempts):
                code = generate_access_code()
                if await self._is_code_unique(code):
                    break
                code = None
            
            if not code:
                msg = "Failed to generate unique access code after maximum attempts"
                logger.error(msg)
                if raise_on_failure:
                    raise RuntimeError(msg)
                return None

            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(hours=code_data.expires_in_hours)
            
            # Create access code
            access_code = AccessCode(
                code=code,
                host_id=host_id,
                guest_group_id=code_data.guest_group_id,
                expires_at=expires_at,
                max_usage_count=code_data.max_usage_count,
                created_by_ip=client_ip,
                status=AccessCodeStatus.ACTIVE.value,
            )
            
            self.db.add(access_code)
            await self.db.commit()
            await self.db.refresh(access_code)
            
            logger.info(f"Access code generated successfully: {code} for group {code_data.guest_group_id}")
            return AccessCodeResponse.model_validate(access_code)

        except IntegrityError:
            await self.db.rollback()
            logger.warning(
                "Integrity error generating access code for group %s (likely duplicate code race)",
                code_data.guest_group_id,
            )
            if raise_on_failure:
                raise
            return None
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Error generating access code for group %s",
                code_data.guest_group_id,
            )
            if raise_on_failure:
                raise
            return None

    async def regenerate_access_code(self, guest_group_id: uuid.UUID) -> Optional[AccessCodeResponse]:
        """
        Revoke existing codes for the group and create a new active access code.

        Used by POST /guest-groups/{id}/regenerate-code so hosts can share/copy a code.
        """
        group = await self.get_guest_group_by_id(guest_group_id)
        if not group:
            return None
        last_integrity: Optional[IntegrityError] = None
        for _ in range(5):
            try:
                await self._revoke_group_access_codes(guest_group_id)
                await self.db.flush()
                return await self.generate_access_code_for_group(
                    group.host_id,
                    AccessCodeCreate(
                        guest_group_id=guest_group_id,
                        expires_in_hours=DEFAULT_GUEST_GROUP_CODE_EXPIRE_HOURS,
                        max_usage_count=DEFAULT_GUEST_GROUP_CODE_MAX_USAGE,
                    ),
                    raise_on_failure=True,
                )
            except IntegrityError as e:
                last_integrity = e
                await self.db.rollback()
                logger.warning(
                    "Regenerate integrity error for group %s, retrying: %s",
                    guest_group_id,
                    e,
                )
        if last_integrity:
            raise last_integrity
        return None

    async def validate_access_code(self, access_code: str) -> Optional[GuestGroup]:
        """
        Validate an access code and return the associated guest group.
        
        Args:
            access_code: Access code to validate
            
        Returns:
            GuestGroup: Associated guest group or None if invalid
        """
        try:
            # Validate code format
            if not is_access_code_valid(access_code):
                logger.warning(f"Invalid access code format: {access_code}")
                return None
            
            # Get access code
            code_upper = access_code.upper()
            stmt = select(AccessCode).where(AccessCode.code == code_upper)
            result = await self.db.execute(stmt)
            access_code_obj = result.scalar_one_or_none()
            
            if not access_code_obj:
                logger.warning(f"Access code not found: {access_code}")
                return None
            
            # Check if code is still valid
            if not _access_code_status_equals(access_code_obj.status, AccessCodeStatus.ACTIVE):
                logger.warning(f"Access code not active: {access_code} (status: {access_code_obj.status})")
                return None

            if access_code_obj.expires_at < datetime.utcnow():
                # Auto-expire the code
                await self._expire_access_code(access_code_obj.id)
                logger.warning(f"Access code expired: {access_code}")
                return None
            
            if access_code_obj.usage_count >= access_code_obj.max_usage_count:
                logger.warning(f"Access code usage limit exceeded: {access_code}")
                return None
            
            # Get the associated guest group
            group = await self.get_guest_group_by_id(access_code_obj.guest_group_id)
            
            logger.info(f"Access code validated successfully: {access_code} for group {access_code_obj.guest_group_id}")
            
            return group
            
        except Exception as e:
            logger.error(f"Error validating access code {access_code}: {e}")
            return None

    async def activate_access_code(self, activation_data: AccessCodeActivation, 
                                 client_ip: Optional[str] = None, 
                                 user_agent: Optional[str] = None) -> Optional[GuestGroupResponse]:
        """
        Activate an access code and return the associated guest group.
        
        Args:
            activation_data: Access code activation data
            client_ip: IP address of the client using the code
            user_agent: User agent string
            
        Returns:
            GuestGroupResponse: Associated guest group or None
        """
        try:
            # Validate code format
            if not is_access_code_valid(activation_data.code):
                logger.warning(f"Invalid access code format: {activation_data.code}")
                return None
            
            # Get access code
            code_upper = activation_data.code.upper()
            stmt = select(AccessCode).where(AccessCode.code == code_upper)
            result = await self.db.execute(stmt)
            access_code = result.scalar_one_or_none()
            
            if not access_code:
                logger.warning(f"Access code not found: {activation_data.code}")
                return None
            
            # Check if code is still valid
            if not _access_code_status_equals(access_code.status, AccessCodeStatus.ACTIVE):
                logger.warning(f"Access code not active: {activation_data.code} (status: {access_code.status})")
                return None

            if access_code.expires_at < datetime.utcnow():
                # Auto-expire the code
                await self._expire_access_code(access_code.id)
                logger.warning(f"Access code expired: {activation_data.code}")
                return None

            if access_code.usage_count >= access_code.max_usage_count:
                logger.warning(f"Access code usage limit exceeded: {activation_data.code}")
                return None

            # Update access code usage
            access_code.usage_count += 1
            access_code.used_at = datetime.utcnow()
            access_code.used_from_ip = client_ip
            access_code.user_agent = user_agent
            
            # Mark as used if reached max usage
            if access_code.usage_count >= access_code.max_usage_count:
                access_code.status = AccessCodeStatus.USED.value

            # Update guest group status to active if it was pending
            group = await self.get_guest_group_by_id(access_code.guest_group_id)
            if group and group.status == GuestGroupStatus.PENDING:
                group.status = GuestGroupStatus.ACTIVE
                group.activated_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Access code activated successfully: {activation_data.code} for group {access_code.guest_group_id}")
            
            if group:
                prof = await self._profile_for_host_id(group.host_id)
                return await self.guest_group_to_response(group, profile=prof)
            
            return None
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error activating access code {activation_data.code}: {e}")
            return None
    
    async def get_host_access_codes(self, host_id: uuid.UUID, include_expired: bool = False) -> List[AccessCodeResponse]:
        """
        Get all access codes for a host.
        
        Args:
            host_id: Host UUID
            include_expired: Whether to include expired codes
            
        Returns:
            List[AccessCodeResponse]: List of access codes
        """
        try:
            stmt = select(AccessCode).where(AccessCode.host_id == host_id)
            
            if not include_expired:
                stmt = stmt.where(
                    and_(
                        AccessCode.status.in_(
                            [AccessCodeStatus.ACTIVE.value, AccessCodeStatus.USED.value]
                        ),
                        AccessCode.expires_at > datetime.utcnow()
                    )
                )
            
            stmt = stmt.order_by(AccessCode.created_at.desc())
            result = await self.db.execute(stmt)
            codes = result.scalars().all()
            
            return [AccessCodeResponse.model_validate(code) for code in codes]
            
        except Exception as e:
            logger.error(f"Error getting access codes for host {host_id}: {e}")
            return []
    
    async def revoke_access_code(self, host_id: uuid.UUID, code_id: uuid.UUID) -> bool:
        """
        Revoke an access code.
        
        Args:
            host_id: Host UUID (for authorization)
            code_id: Access code UUID to revoke
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(AccessCode).where(
                and_(
                    AccessCode.id == code_id,
                    AccessCode.host_id == host_id
                )
            ).values(
                status=AccessCodeStatus.REVOKED.value,
                updated_at=datetime.utcnow(),
            )

            result = await self.db.execute(stmt)
            await self.db.commit()

            if result.rowcount > 0:
                logger.info(f"Access code revoked successfully: {code_id}")
                return True
            else:
                logger.warning(f"Access code not found or not owned by host: {code_id}")
                return False
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error revoking access code {code_id}: {e}")
            return False
    
    # Guest Preferences Management
    async def add_guest_preference(self, guest_group_id: uuid.UUID, preference_data: GuestPreferenceCreate) -> Optional[GuestPreferenceResponse]:
        """
        Add a single guest preference to a group.
        
        Args:
            guest_group_id: Guest group UUID
            preference_data: Guest preference data
            
        Returns:
            GuestPreferenceResponse: Created preference or None
        """
        try:
            preference = GuestPreference(
                guest_group_id=guest_group_id,
                guest_name=preference_data.guest_name,
                age_category=preference_data.age_category,
                personal_interests=preference_data.personal_interests,
                dietary_needs=preference_data.dietary_needs,
                mobility_notes=preference_data.mobility_notes,
                language_preference=preference_data.language_preference,
                cultural_interests=preference_data.cultural_interests,
                food_interests=preference_data.food_interests
            )
            
            self.db.add(preference)
            await self.db.commit()
            await self.db.refresh(preference)
            
            logger.info(f"Added guest preference for group {guest_group_id}")
            return GuestPreferenceResponse.model_validate(preference)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding guest preference for group {guest_group_id}: {e}")
            return None

    async def add_guest_preferences(self, group_id: uuid.UUID, preferences: List[GuestPreferenceCreate]) -> List[GuestPreferenceResponse]:
        """
        Add individual guest preferences to a group.
        
        Args:
            group_id: Guest group UUID
            preferences: List of guest preferences
            
        Returns:
            List[GuestPreferenceResponse]: Created preferences
        """
        try:
            created_preferences = []
            
            for pref_data in preferences:
                preference = GuestPreference(
                    guest_group_id=group_id,
                    guest_name=pref_data.guest_name,
                    age_category=pref_data.age_category,
                    personal_interests=pref_data.personal_interests,
                    dietary_needs=pref_data.dietary_needs,
                    mobility_notes=pref_data.mobility_notes,
                    language_preference=pref_data.language_preference,
                    cultural_interests=pref_data.cultural_interests,
                    food_interests=pref_data.food_interests
                )
                
                self.db.add(preference)
                created_preferences.append(preference)
            
            await self.db.commit()
            
            # Refresh all preferences
            for pref in created_preferences:
                await self.db.refresh(pref)
            
            logger.info(f"Added {len(created_preferences)} guest preferences for group {group_id}")
            return [GuestPreferenceResponse.model_validate(pref) for pref in created_preferences]
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding guest preferences for group {group_id}: {e}")
            return []
    
    async def get_guest_preferences(self, group_id: uuid.UUID) -> List[GuestPreferenceResponse]:
        """
        Get all guest preferences for a group.
        
        Args:
            group_id: Guest group UUID
            
        Returns:
            List[GuestPreferenceResponse]: List of guest preferences
        """
        try:
            stmt = select(GuestPreference).where(GuestPreference.guest_group_id == group_id)
            result = await self.db.execute(stmt)
            preferences = result.scalars().all()
            
            return [GuestPreferenceResponse.model_validate(pref) for pref in preferences]
            
        except Exception as e:
            logger.error(f"Error getting guest preferences for group {group_id}: {e}")
            return []
    
    # Analytics and Reporting
    async def update_recommendation_stats(self, group_id: uuid.UUID, given: int = 0, accepted: int = 0) -> bool:
        """
        Update recommendation statistics for a guest group.
        
        Args:
            group_id: Guest group UUID
            given: Number of recommendations given
            accepted: Number of recommendations accepted
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(GuestGroup).where(GuestGroup.id == group_id).values(
                recommendations_given=GuestGroup.recommendations_given + given,
                recommendations_accepted=GuestGroup.recommendations_accepted + accepted,
                updated_at=datetime.utcnow()
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating recommendation stats for group {group_id}: {e}")
            return False
    
    # Private Helper Methods
    async def _is_code_unique(self, code: str) -> bool:
        """Check if access code is unique."""
        stmt = select(AccessCode).where(AccessCode.code == code.upper())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is None
    
    async def _expire_access_code(self, code_id: uuid.UUID) -> None:
        """Mark an access code as expired."""
        try:
            stmt = update(AccessCode).where(AccessCode.id == code_id).values(
                status=AccessCodeStatus.EXPIRED.value,
                updated_at=datetime.utcnow(),
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error expiring access code {code_id}: {e}")
    
    async def _revoke_group_access_codes(self, group_id: uuid.UUID) -> None:
        """Revoke all access codes for a guest group."""
        stmt = update(AccessCode).where(AccessCode.guest_group_id == group_id).values(
            status=AccessCodeStatus.REVOKED.value,
            updated_at=datetime.utcnow(),
        )
        await self.db.execute(stmt)
    
    async def cleanup_expired_codes(self) -> int:
        """
        Clean up expired access codes (background task).
        
        Returns:
            int: Number of codes cleaned up
        """
        try:
            stmt = update(AccessCode).where(
                and_(
                    AccessCode.status == AccessCodeStatus.ACTIVE.value,
                    AccessCode.expires_at < datetime.utcnow(),
                )
            ).values(
                status=AccessCodeStatus.EXPIRED.value,
                updated_at=datetime.utcnow(),
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            count = result.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} expired access codes")
            
            return count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error cleaning up expired access codes: {e}")
            return 0
    
    # E-visitor Data Management
    async def create_guest_evisitor_data(
        self, 
        guest_group_id: uuid.UUID, 
        evisitor_data: GuestEVisitorDataCreate
    ) -> Optional[GuestEVisitorDataResponse]:
        """
        Create e-visitor data for a guest in a group.
        
        Args:
            guest_group_id: Guest group UUID
            evisitor_data: E-visitor data creation model
            
        Returns:
            GuestEVisitorDataResponse: Created e-visitor data or None if failed
        """
        try:
            # Verify guest group exists
            guest_group = await self.get_guest_group_by_id(guest_group_id)
            if not guest_group:
                logger.error(f"Guest group {guest_group_id} not found")
                return None
            
            # Create e-visitor data
            guest_evisitor = GuestEVisitorData(
                guest_group_id=guest_group_id,
                first_name=evisitor_data.first_name,
                last_name=evisitor_data.last_name,
                date_of_birth=evisitor_data.date_of_birth,
                nationality=evisitor_data.nationality,
                id_type=evisitor_data.id_type,
                id_number=evisitor_data.id_number,
                id_issuing_country=evisitor_data.id_issuing_country,
                id_expiry_date=evisitor_data.id_expiry_date,
                address_line1=evisitor_data.address_line1,
                address_line2=evisitor_data.address_line2,
                city=evisitor_data.city,
                state_province=evisitor_data.state_province,
                postal_code=evisitor_data.postal_code,
                country=evisitor_data.country,
                arrival_date=evisitor_data.arrival_date,
                departure_date=evisitor_data.departure_date,
                email=evisitor_data.email,
                phone=evisitor_data.phone
            )
            
            self.db.add(guest_evisitor)
            await self.db.commit()
            await self.db.refresh(guest_evisitor)
            
            logger.info(f"E-visitor data created for guest {guest_evisitor.id} in group {guest_group_id}")
            return GuestEVisitorDataResponse.model_validate(guest_evisitor)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating e-visitor data for group {guest_group_id}: {e}")
            return None
    
    async def get_guest_evisitor_data(
        self, 
        guest_group_id: uuid.UUID
    ) -> List[GuestEVisitorDataResponse]:
        """
        Get all e-visitor data for a guest group.
        
        Args:
            guest_group_id: Guest group UUID
            
        Returns:
            List[GuestEVisitorDataResponse]: List of e-visitor data
        """
        try:
            stmt = select(GuestEVisitorData).where(
                GuestEVisitorData.guest_group_id == guest_group_id
            )
            result = await self.db.execute(stmt)
            evisitor_data = result.scalars().all()
            
            return [GuestEVisitorDataResponse.model_validate(data) for data in evisitor_data]
            
        except Exception as e:
            logger.error(f"Error getting e-visitor data for group {guest_group_id}: {e}")
            return []
    
    async def update_guest_evisitor_data(
        self, 
        evisitor_id: uuid.UUID, 
        update_data: GuestEVisitorDataUpdate
    ) -> Optional[GuestEVisitorDataResponse]:
        """
        Update e-visitor data for a guest.
        
        Args:
            evisitor_id: E-visitor data UUID
            update_data: Update data model
            
        Returns:
            GuestEVisitorDataResponse: Updated e-visitor data or None if failed
        """
        try:
            # Get existing e-visitor data
            stmt = select(GuestEVisitorData).where(GuestEVisitorData.id == evisitor_id)
            result = await self.db.execute(stmt)
            evisitor_data = result.scalar_one_or_none()
            
            if not evisitor_data:
                logger.error(f"E-visitor data {evisitor_id} not found")
                return None
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            if update_dict:
                update_dict['updated_at'] = datetime.utcnow()
                
                stmt = update(GuestEVisitorData).where(
                    GuestEVisitorData.id == evisitor_id
                ).values(**update_dict)
                
                await self.db.execute(stmt)
                await self.db.commit()
                
                # Refresh the object
                await self.db.refresh(evisitor_data)
            
            logger.info(f"E-visitor data {evisitor_id} updated successfully")
            return GuestEVisitorDataResponse.model_validate(evisitor_data)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating e-visitor data {evisitor_id}: {e}")
            return None
    
    async def mark_evisitor_registered(
        self, 
        evisitor_id: uuid.UUID, 
        confirmation_number: str
    ) -> bool:
        """
        Mark e-visitor data as registered with Croatian authorities.
        
        Args:
            evisitor_id: E-visitor data UUID
            confirmation_number: E-visitor confirmation number
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(GuestEVisitorData).where(
                GuestEVisitorData.id == evisitor_id
            ).values(
                evisitor_registered=True,
                evisitor_registration_date=datetime.utcnow(),
                evisitor_confirmation_number=confirmation_number,
                updated_at=datetime.utcnow()
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            success = result.rowcount > 0
            if success:
                logger.info(f"E-visitor data {evisitor_id} marked as registered")
            
            return success
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking e-visitor data {evisitor_id} as registered: {e}")
            return False
    
    async def delete_guest_evisitor_data(self, evisitor_id: uuid.UUID) -> bool:
        """
        Delete e-visitor data for a guest.
        
        Args:
            evisitor_id: E-visitor data UUID
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = delete(GuestEVisitorData).where(GuestEVisitorData.id == evisitor_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            success = result.rowcount > 0
            if success:
                logger.info(f"E-visitor data {evisitor_id} deleted successfully")
            
            return success
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting e-visitor data {evisitor_id}: {e}")
            return False 