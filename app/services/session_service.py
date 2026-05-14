"""
Session management service for database-based token storage.

Handles session creation, validation, refresh, and cleanup for the Croatian tourist host platform.
"""

import logging
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.exc import IntegrityError
from jose import JWTError, jwt

from app.models.host import UserSession, Host
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service class for session management operations.
    
    Handles database-based token storage, session validation, and cleanup.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the session service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def _generate_session_token(self) -> str:
        """
        Generate a secure random session token.
        
        Returns:
            str: Secure random token
        """
        return secrets.token_urlsafe(32)
    
    def _generate_refresh_token(self) -> str:
        """
        Generate a secure random refresh token.
        
        Returns:
            str: Secure random refresh token
        """
        return secrets.token_urlsafe(32)
    
    async def create_session(
        self, 
        host_id: uuid.UUID, 
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        session_duration_minutes: int = 30,
        refresh_duration_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new user session with tokens.
        
        Args:
            host_id: Host UUID
            user_agent: User agent string
            ip_address: Client IP address
            session_duration_minutes: Session token duration in minutes
            refresh_duration_days: Refresh token duration in days
            
        Returns:
            Dict with session_token, refresh_token, and expiry info
        """
        try:
            # Generate tokens
            session_token = self._generate_session_token()
            refresh_token = self._generate_refresh_token()
            
            # Calculate expiry times
            expires_at = datetime.utcnow() + timedelta(minutes=session_duration_minutes)
            refresh_expires_at = datetime.utcnow() + timedelta(days=refresh_duration_days)
            
            # Create session record
            session = UserSession(
                host_id=host_id,
                session_token=session_token,
                refresh_token=refresh_token,
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                is_active=True
            )
            
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
            logger.info(f"Created session for host {host_id}")
            
            return {
                "session_token": session_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "refresh_expires_at": refresh_expires_at,
                "session_id": session.id
            }
            
        except Exception as e:
            logger.error(f"Error creating session for host {host_id}: {e}")
            await self.db.rollback()
            return None
    
    async def validate_session(self, session_token: str) -> Optional[UserSession]:
        """
        Validate a session token and return session if valid.
        
        Args:
            session_token: Session token to validate
            
        Returns:
            UserSession if valid, None otherwise
        """
        try:
            # Find active session
            stmt = select(UserSession).where(
                and_(
                    UserSession.session_token == session_token,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
            
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                logger.warning(f"Invalid or expired session token: {session_token[:10]}...")
                return None
            
            # Update last activity
            session.last_activity = datetime.utcnow()
            await self.db.commit()
            
            logger.debug(f"Validated session {session.id} for host {session.host_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error validating session token: {e}")
            return None
    
    async def refresh_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh a session using refresh token.
        
        Args:
            refresh_token: Refresh token to use
            
        Returns:
            Dict with new session_token and expiry info
        """
        try:
            # Find active session with valid refresh token
            stmt = select(UserSession).where(
                and_(
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == True,
                    UserSession.refresh_expires_at > datetime.utcnow()
                )
            )
            
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                logger.warning(f"Invalid or expired refresh token: {refresh_token[:10]}...")
                return None
            
            # Generate new session token
            new_session_token = self._generate_session_token()
            expires_at = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
            
            # Update session
            session.session_token = new_session_token
            session.expires_at = expires_at
            session.last_activity = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Refreshed session {session.id} for host {session.host_id}")
            
            return {
                "session_token": new_session_token,
                "expires_at": expires_at,
                "session_id": session.id
            }
            
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            await self.db.rollback()
            return None
    
    async def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate a session (logout).
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(UserSession).where(
                UserSession.session_token == session_token
            ).values(is_active=False)
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Invalidated session: {session_token[:10]}...")
                return True
            else:
                logger.warning(f"Session not found for invalidation: {session_token[:10]}...")
                return False
                
        except Exception as e:
            logger.error(f"Error invalidating session: {e}")
            await self.db.rollback()
            return False
    
    async def invalidate_all_host_sessions(self, host_id: uuid.UUID) -> bool:
        """
        Invalidate all sessions for a host (logout from all devices).
        
        Args:
            host_id: Host UUID
            
        Returns:
            bool: True if successful
        """
        try:
            stmt = update(UserSession).where(
                and_(
                    UserSession.host_id == host_id,
                    UserSession.is_active == True
                )
            ).values(is_active=False)
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info(f"Invalidated all sessions for host {host_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating all sessions for host {host_id}: {e}")
            await self.db.rollback()
            return False
    
    async def get_active_sessions(self, host_id: uuid.UUID) -> List[UserSession]:
        """
        Get all active sessions for a host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            List of active UserSession objects
        """
        try:
            stmt = select(UserSession).where(
                and_(
                    UserSession.host_id == host_id,
                    UserSession.is_active == True
                )
            ).order_by(UserSession.created_at.desc())
            
            result = await self.db.execute(stmt)
            sessions = result.scalars().all()
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting active sessions for host {host_id}: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from database.
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            stmt = delete(UserSession).where(
                and_(
                    UserSession.is_active == False,
                    UserSession.expires_at < datetime.utcnow() - timedelta(days=1)
                )
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            cleaned_count = result.rowcount
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            await self.db.rollback()
            return 0
