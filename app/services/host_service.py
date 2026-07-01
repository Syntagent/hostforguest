"""
Host service layer for the Croatian tourist host platform.

Handles all business logic related to host management including
authentication, registration, profile management, and CRUD operations.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.models.host import (
    Host, 
    HostProfile,
    HostCreate, 
    HostUpdate, 
    HostResponse,
    HostLogin,
    HostProfileCreate,
    HostProfileUpdate,
    HostProfileResponse
)
from app.models.settings import HostSettings
from app.services.rls_service import RLSService
from app.core.config import settings
from app.services.session_service import SessionService
from app.services.geocoding_service import GeocodingService
from app.services.maintenance_service import haversine_km

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _coerce_placeholder_gps_to_none(
    lat: Optional[float], lng: Optional[float]
) -> tuple[Optional[float], Optional[float]]:
    """Store NULL instead of (0, 0) — common placeholder when GPS was never set."""
    if lat is None or lng is None:
        return lat, lng
    try:
        a, b = float(lat), float(lng)
        if abs(a) < 1e-6 and abs(b) < 1e-6:
            return None, None
    except (TypeError, ValueError):
        pass
    return lat, lng


def _apply_geocode_if_needed(profile: HostProfile) -> None:
    """Fill or refresh latitude/longitude from address when GPS missing or stale."""
    clat, clng = _coerce_placeholder_gps_to_none(profile.latitude, profile.longitude)
    profile.latitude, profile.longitude = clat, clng

    if not ((profile.address or "").strip() or (profile.city or "").strip()):
        return

    result = GeocodingService.geocode(
        address=profile.address,
        city=profile.city,
        county=profile.county,
    )
    if not result:
        return

    if clat is None or clng is None:
        profile.latitude = result.latitude
        profile.longitude = result.longitude
        logger.info(
            "Geocoded host profile via %s (%s)",
            result.matched_query,
            result.precision,
        )
        return

    drift_km = haversine_km(clat, clng, result.latitude, result.longitude)
    if drift_km > 1.5:
        profile.latitude = result.latitude
        profile.longitude = result.longitude
        logger.info(
            "Refreshed host GPS by %.1f km using %s (%s)",
            drift_km,
            result.matched_query,
            result.precision,
        )


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


class HostService:
    """
    Service class for host management operations.
    
    Handles authentication, registration, and CRUD operations for hosts
    in the Croatian tourist platform.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the host service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.session_service = SessionService(db)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            bool: True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a password.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token for host authentication.
        
        Args:
            data: Data to encode in token
            expires_delta: Token expiration time
            
        Returns:
            str: JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    async def authenticate_host(
        self, 
        email: str, 
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a host with email and password and create session.
        
        Args:
            email: Host email address
            password: Plain text password
            user_agent: User agent string
            ip_address: Client IP address
            
        Returns:
            Dict with host data and session tokens, or None
        """
        try:
            rls = RLSService(self.db)
            async with rls.login_bypass(email):
                host = await self.get_host_by_email(email)
            if not host:
                logger.warning(f"Authentication failed: Host not found for email {email}")
                return None

            if not self.verify_password(password, host.hashed_password):
                logger.warning(f"Authentication failed: Invalid password for email {email}")
                return None

            await rls.set_host_context(host.id)

            # Create session
            session_data = await self.session_service.create_session(
                host_id=host.id,
                user_agent=user_agent,
                ip_address=ip_address
            )

            if not session_data:
                logger.error(f"Failed to create session for host {host.id}")
                return None

            await rls.set_host_context(host.id)

            # Update last login
            await self.update_last_login(host.id)
            
            logger.info(f"Host authenticated successfully: {email}")
            
            return {
                "host": host,
                "session_token": session_data["session_token"],
                "refresh_token": session_data["refresh_token"],
                "expires_at": session_data["expires_at"],
                "refresh_expires_at": session_data["refresh_expires_at"]
            }
            
        except Exception as e:
            logger.error(f"Error during host authentication: {e}")
            return None
    
    async def create_host(self, host_data: HostCreate) -> Optional[HostResponse]:
        """
        Create a new host account.
        
        Args:
            host_data: Host creation data
            
        Returns:
            HostResponse: Created host data or None if failed
        """
        try:
            email_lc = _normalize_email(host_data.email)
            if not email_lc:
                logger.warning("Host creation failed: empty email")
                return None

            rls = RLSService(self.db)
            # Email lookup uses login bypass; keep it outside register_bypass so nested
            # bypass exit does not drop register mode before INSERT (RLS production).
            async with rls.login_bypass(email_lc):
                existing_host = await self.get_host_by_email(email_lc)
            if existing_host:
                logger.warning(f"Host creation failed: Email already exists {email_lc}")
                return None

            async with rls.register_bypass():
                # Create new host
                hashed_password = self.get_password_hash(host_data.password)

                # Create host record
                host = Host(
                email=email_lc,
                hashed_password=hashed_password,
                first_name=host_data.first_name,
                last_name=host_data.last_name,
                phone=host_data.phone,
                business_name=host_data.business_name,
                business_type=host_data.business_type,
                address=host_data.address,
                city=host_data.city,
                county=host_data.county,
                postal_code=host_data.postal_code,
                country=host_data.country,
                latitude=host_data.latitude,
                longitude=host_data.longitude,
                local_specialties=host_data.local_specialties,
                languages=host_data.languages,
                max_group_size=host_data.max_group_size,
                description=host_data.description,
                    welcome_message=host_data.welcome_message
                )

                self.db.add(host)
                await self.db.commit()

            # register_bypass allows INSERT only — set tenant context before follow-up reads.
            await rls.set_host_context(host.id)
            host_for_response = await self.get_host_by_id(host.id) or host

            # Create default host settings
            await self._create_default_host_settings(host.id)

            logger.info(f"Host created successfully: {host.email}")
            return HostResponse.model_validate(host_for_response)
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating host: {e}")
            return None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating host: {e}")
            return None
    
    async def get_host_by_id(self, host_id: uuid.UUID) -> Optional[Host]:
        """
        Get host by ID.
        
        Args:
            host_id: Host UUID
            
        Returns:
            Host: Host object or None
        """
        try:
            stmt = select(Host).where(Host.id == host_id, Host.is_active == True)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting host by ID {host_id}: {e}")
            return None
    
    async def get_host_by_email(self, email: str) -> Optional[Host]:
        """
        Get host by email address.
        
        Args:
            email: Host email address
            
        Returns:
            Host: Host object or None
        """
        try:
            email_norm = _normalize_email(email)
            if not email_norm:
                return None
            stmt = select(Host).where(
                func.lower(Host.email) == email_norm,
                Host.is_active == True,
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting host by email {email}: {e}")
            return None

    async def set_password_for_email_normalized(self, email_norm: str, new_plain_password: str) -> bool:
        """Set password hash by case-insensitive email (dev seed when DEV_LOGIN_SEED_FORCE)."""
        try:
            email_lc = _normalize_email(email_norm)
            if not email_lc:
                return False
            hashed = self.get_password_hash(new_plain_password)
            stmt = (
                update(Host)
                .where(func.lower(Host.email) == email_lc)
                .values(hashed_password=hashed, updated_at=datetime.utcnow())
            )
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error("Error setting password for email %s: %s", email_norm, e)
            return False

    async def update_host(self, host_id: uuid.UUID, host_data: HostUpdate) -> Optional[HostResponse]:
        """
        Update host information.
        
        Args:
            host_id: Host UUID
            host_data: Updated host data
            
        Returns:
            HostResponse: Updated host data or None
        """
        try:
            # Get existing host
            host = await self.get_host_by_id(host_id)
            if not host:
                logger.warning(f"Host update failed: Host not found {host_id}")
                return None
            
            # Update only provided fields
            update_data = host_data.model_dump(exclude_unset=True)
            if update_data:
                update_data['updated_at'] = datetime.utcnow()
                
                stmt = update(Host).where(Host.id == host_id).values(**update_data)
                await self.db.execute(stmt)
                await self.db.commit()
                
                # Refresh host data
                await self.db.refresh(host)
                
                logger.info(f"Host updated successfully: {host_id}")
                return HostResponse.model_validate(host)
            
            return HostResponse.model_validate(host)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating host {host_id}: {e}")
            return None

    async def change_password(
        self,
        host_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Verify current password and persist a new hash."""
        try:
            host = await self.get_host_by_id(host_id)
            if not host:
                return False
            if not self.verify_password(current_password, host.hashed_password):
                return False
            hashed = self.get_password_hash(new_password)
            stmt = (
                update(Host)
                .where(Host.id == host_id)
                .values(hashed_password=hashed, updated_at=datetime.utcnow())
            )
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info("Password changed for host %s", host_id)
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error("Error changing password for host %s: %s", host_id, e)
            return False
    
    async def delete_host(self, host_id: uuid.UUID) -> bool:
        """
        Soft delete a host (mark as inactive).
        
        Args:
            host_id: Host UUID
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(Host).where(Host.id == host_id).values(
                is_active=False,
                updated_at=datetime.utcnow()
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Host soft deleted successfully: {host_id}")
                return True
            else:
                logger.warning(f"Host not found for deletion: {host_id}")
                return False
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting host {host_id}: {e}")
            return False
    
    async def list_hosts(self, skip: int = 0, limit: int = 100) -> List[HostResponse]:
        """
        List all active hosts with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[HostResponse]: List of hosts
        """
        try:
            stmt = select(Host).where(Host.is_active == True).offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            hosts = result.scalars().all()
            
            return [HostResponse.model_validate(host) for host in hosts]
            
        except Exception as e:
            logger.error(f"Error listing hosts: {e}")
            return []
    
    async def update_last_login(self, host_id: uuid.UUID) -> None:
        """
        Update host's last login timestamp.
        
        Args:
            host_id: Host UUID
        """
        try:
            stmt = update(Host).where(Host.id == host_id).values(
                last_login=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating last login for host {host_id}: {e}")
    
    async def create_host_profile(self, host_id: uuid.UUID, profile_data: HostProfileCreate) -> Optional[HostProfileResponse]:
        """
        Create extended host profile.
        
        Args:
            host_id: Host UUID
            profile_data: Profile creation data
            
        Returns:
            HostProfileResponse: Created profile or None
        """
        try:
            # Check if host exists
            host = await self.get_host_by_id(host_id)
            if not host:
                logger.warning(f"Profile creation failed: Host not found {host_id}")
                return None
            
            # Check if profile already exists
            existing_profile = await self.get_host_profile(host_id)
            if existing_profile:
                logger.warning(f"Profile creation failed: Profile already exists for host {host_id}")
                return None
            
            # Create profile
            profile = HostProfile(
                host_id=host_id,
                property_name=profile_data.property_name,
                property_type=profile_data.property_type,
                number_of_rooms=profile_data.number_of_rooms,
                max_guests=profile_data.max_guests,
                services_offered=profile_data.services_offered,
                amenities=profile_data.amenities,
                expertise_areas=profile_data.expertise_areas,
                favorite_local_spots=profile_data.favorite_local_spots,
                location_story=profile_data.location_story,
            )
            
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
            
            logger.info(f"Host profile created successfully for host: {host_id}")
            return HostProfileResponse.model_validate(profile)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating host profile for {host_id}: {e}")
            return None
    
    async def update_host_profile(self, host_id: uuid.UUID, profile_data: HostProfileUpdate) -> Optional[HostProfileResponse]:
        """
        Update extended host profile.
        
        Args:
            host_id: Host UUID
            profile_data: Profile update data
            
        Returns:
            HostProfileResponse: Updated profile or None
        """
        try:
            # Check if host exists
            host = await self.get_host_by_id(host_id)
            if not host:
                logger.warning(f"Profile update failed: Host not found {host_id}")
                return None
            
            update_data = profile_data.model_dump(exclude_unset=True)
            existing_profile = await self.get_host_profile(host_id)

            if not existing_profile:
                create_fields = {
                    field: value
                    for field, value in update_data.items()
                    if hasattr(HostProfile, field)
                }
                profile = HostProfile(host_id=host_id, **create_fields)
                _apply_geocode_if_needed(profile)
                self.db.add(profile)
                await self.db.commit()
                await self.db.refresh(profile)
                logger.info(f"Host profile created via upsert for host: {host_id}")
                return HostProfileResponse.model_validate(profile)

            for field, value in update_data.items():
                if hasattr(existing_profile, field):
                    setattr(existing_profile, field, value)

            _apply_geocode_if_needed(existing_profile)
            existing_profile.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(existing_profile)

            logger.info(f"Host profile updated successfully for host: {host_id}")
            return HostProfileResponse.model_validate(existing_profile)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating host profile for {host_id}: {e}")
            return None
    
    async def get_host_profile(self, host_id: uuid.UUID) -> Optional[HostProfile]:
        """
        Get host profile by host ID.
        
        Args:
            host_id: Host UUID
            
        Returns:
            HostProfile: Host profile or None
        """
        try:
            stmt = select(HostProfile).where(HostProfile.host_id == host_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting host profile for {host_id}: {e}")
            return None
    
    async def _create_default_host_settings(self, host_id: uuid.UUID) -> None:
        """
        Create default settings for a new host.
        
        Args:
            host_id: Host UUID
        """
        try:
            settings = HostSettings(host_id=host_id)
            self.db.add(settings)
            await self.db.commit()
            logger.info(f"Default settings created for host: {host_id}")
        except Exception as e:
            logger.error(f"Error creating default settings for host {host_id}: {e}")
    
    async def search_hosts_by_location(self, city: str, county: Optional[str] = None) -> List[HostResponse]:
        """
        Search hosts by location (Croatian cities/counties).
        
        Args:
            city: City name
            county: Optional county name
            
        Returns:
            List[HostResponse]: Matching hosts
        """
        try:
            stmt = select(Host).where(
                Host.is_active == True,
                Host.city.ilike(f"%{city}%")
            )
            
            if county:
                stmt = stmt.where(Host.county.ilike(f"%{county}%"))
            
            result = await self.db.execute(stmt)
            hosts = result.scalars().all()
            
            return [HostResponse.model_validate(host) for host in hosts]
            
        except Exception as e:
            logger.error(f"Error searching hosts by location: {e}")
            return [] 

    async def get_current_host_from_session(self, session_token: str) -> Optional[Host]:
        """
        Get current host from session token.
        
        Args:
            session_token: Session token
            
        Returns:
            Host if valid session, None otherwise
        """
        try:
            rls = RLSService(self.db)
            async with rls.session_bypass():
                session = await self.session_service.validate_session(session_token)
            if not session:
                return None

            await rls.set_host_context(session.host_id)

            # Get host data
            stmt = select(Host).where(Host.id == session.host_id, Host.is_active == True)
            result = await self.db.execute(stmt)
            host = result.scalar_one_or_none()

            return host
            
        except Exception as e:
            logger.error(f"Error getting host from session: {e}")
            return None
    
    async def logout_host(self, session_token: str) -> bool:
        """
        Logout host by invalidating session.
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            bool: True if successful
        """
        async with RLSService(self.db).session_bypass():
            return await self.session_service.invalidate_session(session_token)
    
    async def logout_all_devices(self, host_id: uuid.UUID) -> bool:
        """
        Logout host from all devices.
        
        Args:
            host_id: Host UUID
            
        Returns:
            bool: True if successful
        """
        return await self.session_service.invalidate_all_host_sessions(host_id)
    
    async def refresh_host_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh host session using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new session data or None
        """
        rls = RLSService(self.db)
        async with rls.session_bypass():
            return await self.session_service.refresh_session(refresh_token)
    
    async def get_host_sessions(self, host_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            List of session data
        """
        sessions = await self.session_service.get_active_sessions(host_id)
        return [
            {
                "id": str(session.id),
                "user_agent": session.user_agent,
                "ip_address": session.ip_address,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "expires_at": session.expires_at
            }
            for session in sessions
        ] 