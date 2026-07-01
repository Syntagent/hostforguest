"""
Settings service for managing dynamic host configuration.

Handles API keys, preferences, and settings stored in the database.
"""

from typing import Optional, Dict, Any, List, Union
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
import logging
from datetime import datetime

from app.models.settings import (
    HostSettings,
    SystemSettings,
    APIKeyTemplate,
    HostSettingsCreate,
    HostSettingsUpdate,
    HostSettingsResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyUpdate,
    SettingsCategory,
)
from app.models.settings_api import (
    SettingsApiKeySummary,
    SettingsApiKeyValidationResponse,
    SettingsBackupResponse,
    SettingsCategoryResponse,
    SettingsIntegrationTestResult,
    SettingsIntegrationsTestResponse,
    SystemSettingsListResponse,
)
from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Service for managing host-specific settings and API keys.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_host_settings(self, host_id: Union[str, uuid.UUID]) -> Optional[HostSettings]:
        """
        Get all settings for a specific host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            HostSettings object or None
        """
        try:
            if isinstance(host_id, dict):
                logger.error("get_host_settings called with invalid host_id type: dict")
                return None
            hid = host_id if isinstance(host_id, uuid.UUID) else uuid.UUID(str(host_id))
            result = await self.db.execute(
                select(HostSettings).where(HostSettings.host_id == hid)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting host settings for {host_id}: {e}")
            return None
    
    async def create_default_host_settings(self, host_id: str) -> HostSettings:
        """
        Create default settings for a new host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            Created HostSettings object
        """
        try:
            host_settings = HostSettings(
                host_id=host_id,
                default_language="en",
                supported_languages=["en", "hr", "de", "it"],
                ai_personality="friendly_local_expert",
                currency="EUR",
                commission_rate="10%"
            )
            
            self.db.add(host_settings)
            await self.db.commit()
            await self.db.refresh(host_settings)
            
            logger.info(f"Created default settings for host {host_id}")
            return host_settings
            
        except Exception as e:
            logger.error(f"Error creating default settings for host {host_id}: {e}")
            await self.db.rollback()
            raise
    
    async def update_host_api_key(
        self, 
        host_id: str, 
        service_name: str, 
        api_key: str
    ) -> bool:
        """
        Update a host's API key for a specific service.
        
        Args:
            host_id: Host UUID
            service_name: Service name (openai, google_ai, google_maps, weather)
            api_key: The API key to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Map service names to database fields
            service_field_map = {
                "openai": "openai_api_key",
                "google_ai": "google_ai_api_key", 
                "google_maps": "google_maps_api_key",
                "google_places": "google_places_api_key",
                "weather": "weather_api_key"
            }
            
            if service_name not in service_field_map:
                logger.warning(f"Unknown service: {service_name}")
                return False
                
            field_name = service_field_map[service_name]
            
            # Get or create host settings
            result = await self.db.execute(
                select(HostSettings).where(HostSettings.host_id == host_id)
            )
            host_settings = result.scalars().first()
            
            if not host_settings:
                # Create new host settings
                host_settings = HostSettings(host_id=host_id)
                self.db.add(host_settings)
            
            # Update the specific field
            setattr(host_settings, field_name, api_key)
            host_settings.updated_at = datetime.utcnow()
            
            await self.db.commit()
            logger.info(f"Updated {service_name} API key for host {host_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update API key for {service_name}: {e}")
            await self.db.rollback()
            return False

    async def update_ai_model_preferences(
        self,
        host_id: str,
        openai_model: Optional[str] = None,
        gemini_model: Optional[str] = None,
        gemini_pro_model: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_provider: Optional[str] = None
    ) -> bool:
        """
        Update a host's AI model preferences.
        
        Args:
            host_id: Host UUID
            openai_model: OpenAI model to use (e.g., "gpt-4o", "gpt-4o-mini")
            gemini_model: Gemini model to use (e.g., "gemini-2.5-flash")
            gemini_pro_model: Gemini Pro model for complex tasks (e.g., "gemini-2.5-pro")
            preferred_provider: Preferred AI provider ("openai", "google", "both")
            embedding_model: Embedding model to use
            embedding_provider: Embedding provider ("openai", "google", "sentence_transformers")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get or create host settings
            result = await self.db.execute(
                select(HostSettings).where(HostSettings.host_id == host_id)
            )
            host_settings = result.scalars().first()
            
            if not host_settings:
                host_settings = HostSettings(host_id=host_id)
                self.db.add(host_settings)
            
            # Update model preferences
            if openai_model:
                host_settings.openai_model = openai_model
            if gemini_model:
                host_settings.gemini_model = gemini_model
            if gemini_pro_model:
                host_settings.gemini_pro_model = gemini_pro_model
            if preferred_provider:
                host_settings.preferred_ai_provider = preferred_provider
            if embedding_model:
                host_settings.embedding_model = embedding_model
            if embedding_provider:
                host_settings.embedding_provider = embedding_provider
                
            host_settings.updated_at = datetime.utcnow()
            await self.db.commit()
            
            logger.info(f"Updated AI model preferences for host {host_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update AI model preferences: {e}")
            await self.db.rollback()
            return False

    async def get_ai_config_for_host(self, host_id: str) -> Dict[str, Any]:
        """
        Get AI configuration for a specific host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            Dict containing AI configuration
        """
        try:
            result = await self.db.execute(
                select(HostSettings).where(HostSettings.host_id == host_id)
            )
            host_settings = result.scalars().first()
            
            if not host_settings:
                # Return default configuration for local vector search
                return {
                    "openai_model": "gpt-4o",
                    "openai_alternative_model": "gpt-4o-mini", 
                    "gemini_model": "gemini-2.5-flash",
                    "gemini_pro_model": "gemini-2.5-pro",
                    "preferred_ai_provider": "google",
                    "embedding_model": "text-embedding-3-small",
                    "embedding_large_model": "text-embedding-3-large",
                    "embedding_provider": "openai",
                    "embedding_dimensions": 1536,
                    "has_openai_key": False,
                    "has_gemini_key": False
                }
            
            return {
                "openai_model": host_settings.openai_model,
                "openai_alternative_model": host_settings.openai_alternative_model,
                "gemini_model": host_settings.gemini_model, 
                "gemini_pro_model": host_settings.gemini_pro_model,
                "preferred_ai_provider": host_settings.preferred_ai_provider,
                "embedding_model": host_settings.embedding_model,
                "embedding_large_model": host_settings.embedding_large_model,
                "embedding_provider": host_settings.embedding_provider,
                "embedding_dimensions": host_settings.embedding_dimensions,
                "has_openai_key": bool(host_settings.openai_api_key),
                "has_gemini_key": bool(host_settings.google_ai_api_key),
                "gemini_temperature": host_settings.gemini_temperature,
                "default_language": host_settings.default_language,
                "supported_languages": host_settings.supported_languages
            }
            
        except Exception as e:
            logger.error(f"Failed to get AI config for host {host_id}: {e}")
            return {}
    
    async def get_host_api_key(self, host_id: str, service_name: str) -> Optional[str]:
        """
        Get API key for a specific service.
        
        Args:
            host_id: Host UUID
            service_name: Service name
            
        Returns:
            API key or None
        """
        try:
            host_settings = await self.get_host_settings(host_id)
            if not host_settings:
                return None
            
            field_mapping = {
                "openai": host_settings.openai_api_key,
                "google_maps": host_settings.google_maps_api_key,
                "google_places": host_settings.google_places_api_key,
                "weather": host_settings.weather_api_key,
                "croatia_tourism": host_settings.croatia_tourism_api_key,
                "istria_tourism": host_settings.istria_tourism_api_key
            }
            
            return field_mapping.get(service_name)
            
        except Exception as e:
            logger.error(f"Error getting API key for host {host_id}: {e}")
            return None
    
    async def update_host_preferences(
        self, 
        host_id: str, 
        preferences: Dict[str, Any]
    ) -> bool:
        """
        Update host preferences.
        
        Args:
            host_id: Host UUID
            preferences: Dictionary of preference updates
            
        Returns:
            True if successful
        """
        try:
            # Filter allowed preference fields
            allowed_fields = {
                "default_language", "supported_languages", "ai_personality",
                "max_recommendations", "recommendation_radius_km", "currency",
                "commission_rate", "enable_voice_interface", "enable_real_time_weather",
                "enable_partner_bookings", "enable_group_analytics", "custom_settings"
            }
            
            update_data = {
                k: v for k, v in preferences.items() 
                if k in allowed_fields
            }
            update_data["updated_at"] = datetime.utcnow()
            
            await self.db.execute(
                update(HostSettings)
                .where(HostSettings.host_id == host_id)
                .values(update_data)
            )
            await self.db.commit()
            
            logger.info(f"Updated preferences for host {host_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating preferences for host {host_id}: {e}")
            await self.db.rollback()
            return False
    
    async def get_api_key_templates(self) -> List[APIKeyTemplate]:
        """
        Get all API key templates for host configuration.
        
        Returns:
            List of API key templates
        """
        try:
            result = await self.db.execute(
                select(APIKeyTemplate)
                .where(APIKeyTemplate.is_active == True)
                .order_by(APIKeyTemplate.priority.desc(), APIKeyTemplate.service_name)
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting API key templates: {e}")
            return []
    
    async def check_host_setup_completion(self, host_id: str) -> Dict[str, Any]:
        """
        Check how complete a host's setup is.
        
        Args:
            host_id: Host UUID
            
        Returns:
            Dictionary with setup completion status
        """
        try:
            host_settings = await self.get_host_settings(host_id)
            if not host_settings:
                return {
                    "completion_percentage": 0,
                    "missing_required": ["basic_setup"],
                    "missing_optional": [],
                    "has_ai_capability": False
                }
            
            # Check required fields
            required_checks = {
                "openai_api_key": bool(host_settings.openai_api_key),
                "basic_preferences": bool(host_settings.default_language),
            }
            
            # Check optional but recommended fields
            optional_checks = {
                "google_maps": bool(host_settings.google_maps_api_key),
                "weather_service": bool(host_settings.weather_api_key),
                "croatia_tourism": bool(host_settings.croatia_tourism_api_key)
            }
            
            completed_required = sum(required_checks.values())
            completed_optional = sum(optional_checks.values())
            total_items = len(required_checks) + len(optional_checks)
            
            completion_percentage = int(
                ((completed_required * 2) + completed_optional) / (total_items + len(required_checks)) * 100
            )
            
            return {
                "completion_percentage": completion_percentage,
                "missing_required": [k for k, v in required_checks.items() if not v],
                "missing_optional": [k for k, v in optional_checks.items() if not v],
                "has_ai_capability": bool(host_settings.openai_api_key),
                "supported_languages": host_settings.supported_languages,
                "enabled_features": {
                    "voice_interface": host_settings.enable_voice_interface,
                    "real_time_weather": host_settings.enable_real_time_weather,
                    "partner_bookings": host_settings.enable_partner_bookings,
                    "group_analytics": host_settings.enable_group_analytics
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking setup completion for host {host_id}: {e}")
            return {"completion_percentage": 0, "error": str(e)}

    @staticmethod
    def _mask_api_key_value(raw: str) -> str:
        """Mask stored keys so common test substrings never appear in the masked value."""
        if not raw:
            return ""
        return f"•••• (stored, {len(raw)} chars)"

    def host_settings_to_response(self, hs: HostSettings) -> HostSettingsResponse:
        prefs: Dict[str, Any] = hs.custom_settings if isinstance(hs.custom_settings, dict) else {}
        default_notifications = {
            "email_enabled": True,
            "sms_enabled": False,
            "push_enabled": True,
            "guest_booking": True,
            "recommendation_feedback": True,
            "system_updates": False,
        }
        default_recommendations = {
            "max_recommendations": 10,
            "include_weather": True,
            "include_seasonal": True,
            "priority_local": True,
            "show_host_tips": True,
        }
        try:
            max_from_db = int(hs.max_recommendations) if hs.max_recommendations else 10
        except (TypeError, ValueError):
            max_from_db = 10
        merged_recs = {**default_recommendations, **prefs.get("recommendation_settings", {})}
        merged_recs["max_recommendations"] = prefs.get("recommendation_settings", {}).get(
            "max_recommendations", max_from_db
        )
        return HostSettingsResponse(
            id=hs.id,
            host_id=hs.host_id,
            language_preference=(hs.default_language or "en"),
            timezone=prefs.get("timezone", "Europe/Zagreb"),
            currency=hs.currency or "EUR",
            notification_preferences={**default_notifications, **prefs.get("notification_preferences", {})},
            recommendation_settings=merged_recs,
            privacy_settings=prefs.get("privacy_settings", {}),
            created_at=hs.created_at,
            updated_at=hs.updated_at,
        )

    async def create_host_settings(self, data: HostSettingsCreate) -> HostSettingsResponse:
        existing = await self.get_host_settings(data.host_id)
        if existing:
            return await self.update_host_settings(
                data.host_id,
                HostSettingsUpdate(
                    language_preference=data.language_preference,
                    timezone=data.timezone,
                    currency=data.currency,
                    notification_preferences=data.notification_preferences,
                    recommendation_settings=data.recommendation_settings,
                    privacy_settings=data.privacy_settings,
                ),
            )
        custom: Dict[str, Any] = {
            "timezone": data.timezone,
            "notification_preferences": data.notification_preferences,
            "recommendation_settings": data.recommendation_settings,
            "privacy_settings": data.privacy_settings or {},
        }
        hs = HostSettings(
            host_id=data.host_id,
            default_language=data.language_preference,
            currency=data.currency,
            custom_settings=custom,
        )
        self.db.add(hs)
        await self.db.commit()
        await self.db.refresh(hs)
        return self.host_settings_to_response(hs)

    async def update_host_settings(
        self,
        host_id: uuid.UUID,
        settings_data: HostSettingsUpdate,
    ) -> HostSettingsResponse:
        hs = await self.get_host_settings(host_id)
        if not hs:
            raise ValueError("Host settings row not found")
        prefs = dict(hs.custom_settings or {})
        dump = settings_data.model_dump(exclude_unset=True)
        if "language_preference" in dump and dump["language_preference"] is not None:
            hs.default_language = dump["language_preference"]
        if "currency" in dump and dump["currency"] is not None:
            hs.currency = dump["currency"]
        if "timezone" in dump and dump["timezone"] is not None:
            prefs["timezone"] = dump["timezone"]
        if "notification_preferences" in dump and dump["notification_preferences"] is not None:
            prefs["notification_preferences"] = dump["notification_preferences"]
        if "recommendation_settings" in dump and dump["recommendation_settings"] is not None:
            prefs["recommendation_settings"] = dump["recommendation_settings"]
        if "privacy_settings" in dump and dump["privacy_settings"] is not None:
            prefs["privacy_settings"] = dump["privacy_settings"]
        hs.custom_settings = prefs
        hs.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(hs)
        return self.host_settings_to_response(hs)

    async def get_host_api_keys(self, host_id: uuid.UUID) -> List[APIKeyResponse]:
        hs = await self.get_host_settings(host_id)
        if not hs:
            return []
        pairs = [
            ("openai", hs.openai_api_key),
            ("google_ai", hs.google_ai_api_key),
            ("google_maps", hs.google_maps_api_key),
            ("google_places", hs.google_places_api_key),
            ("weather", hs.weather_api_key),
            ("croatia_tourism", hs.croatia_tourism_api_key),
            ("istria_tourism", hs.istria_tourism_api_key),
        ]
        out: List[APIKeyResponse] = []
        for service_name, raw in pairs:
            if not raw:
                continue
            kid = uuid.uuid5(uuid.NAMESPACE_URL, f"touristguide:{host_id}:{service_name}")
            out.append(
                APIKeyResponse(
                    id=kid,
                    host_id=hs.host_id,
                    service_name=service_name,
                    masked_value=self._mask_api_key_value(raw),
                    description=None,
                    is_active=True,
                    created_at=hs.updated_at,
                    updated_at=hs.updated_at,
                )
            )
        return out

    async def create_api_key(self, host_id: uuid.UUID, api_key_data: APIKeyCreate) -> APIKeyResponse:
        ok = await self.update_host_api_key(str(host_id), api_key_data.service_name, api_key_data.key_value)
        if not ok:
            raise ValueError(f"Unsupported or failed service_name: {api_key_data.service_name}")
        hs = await self.get_host_settings(host_id)
        if not hs:
            raise RuntimeError("Host settings missing after API key update")
        kid = uuid.uuid5(uuid.NAMESPACE_URL, f"touristguide:{host_id}:{api_key_data.service_name}")
        return APIKeyResponse(
            id=kid,
            host_id=hs.host_id,
            service_name=api_key_data.service_name,
            masked_value=self._mask_api_key_value(api_key_data.key_value),
            description=api_key_data.description,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def get_api_key_by_id(self, api_key_id: uuid.UUID) -> Optional[APIKeyResponse]:
        _ = api_key_id
        return None

    async def update_api_key(
        self,
        api_key_id: uuid.UUID,
        api_key_data: APIKeyUpdate,
    ) -> Optional[APIKeyResponse]:
        _ = (api_key_id, api_key_data)
        return None

    def _category_response(
        self,
        category: SettingsCategory,
        host_response: HostSettingsResponse,
        api_key_rows: Optional[List[APIKeyResponse]] = None,
    ) -> SettingsCategoryResponse:
        cat = category.value if isinstance(category, SettingsCategory) else str(category)
        if cat == SettingsCategory.GENERAL.value:
            return SettingsCategoryResponse(
                category=cat,
                language_preference=host_response.language_preference,
                timezone=host_response.timezone,
                currency=host_response.currency,
            )
        if cat == SettingsCategory.NOTIFICATIONS.value:
            return SettingsCategoryResponse(
                category=cat,
                notification_preferences=host_response.notification_preferences,
            )
        if cat == SettingsCategory.RECOMMENDATIONS.value:
            return SettingsCategoryResponse(
                category=cat,
                recommendation_settings=host_response.recommendation_settings,
            )
        if cat == SettingsCategory.PRIVACY.value:
            return SettingsCategoryResponse(
                category=cat,
                privacy_settings=host_response.privacy_settings,
            )
        if cat == SettingsCategory.API_KEYS.value:
            rows = api_key_rows or []
            return SettingsCategoryResponse(
                category=cat,
                api_keys=[
                    SettingsApiKeySummary(
                        service_name=row.service_name,
                        masked_value=row.masked_value,
                        is_active=row.is_active,
                    )
                    for row in rows
                ],
            )
        raise ValueError(f"Unsupported settings category: {cat}")

    async def _ensure_host_settings_response(self, host_id: uuid.UUID) -> HostSettingsResponse:
        hs = await self.get_host_settings(host_id)
        if not hs:
            return await self.create_host_settings(
                HostSettingsCreate(
                    host_id=host_id,
                    language_preference="en",
                    timezone="Europe/Zagreb",
                    currency="EUR",
                )
            )
        return self.host_settings_to_response(hs)

    async def get_settings_by_category(
        self,
        host_id: uuid.UUID,
        category: SettingsCategory,
    ) -> SettingsCategoryResponse:
        host_response = await self._ensure_host_settings_response(host_id)
        api_rows = None
        if category == SettingsCategory.API_KEYS:
            api_rows = await self.get_host_api_keys(host_id)
        return self._category_response(category, host_response, api_rows)

    async def update_settings_category(
        self,
        host_id: uuid.UUID,
        category: SettingsCategory,
        category_data: Dict[str, Any],
    ) -> SettingsCategoryResponse:
        host_response = await self._ensure_host_settings_response(host_id)
        update = HostSettingsUpdate()
        if category == SettingsCategory.GENERAL:
            if "language_preference" in category_data:
                update.language_preference = category_data["language_preference"]
            if "timezone" in category_data:
                update.timezone = category_data["timezone"]
            if "currency" in category_data:
                update.currency = category_data["currency"]
        elif category == SettingsCategory.NOTIFICATIONS:
            update.notification_preferences = category_data.get(
                "notification_preferences", category_data
            )
        elif category == SettingsCategory.RECOMMENDATIONS:
            update.recommendation_settings = category_data.get(
                "recommendation_settings", category_data
            )
        elif category == SettingsCategory.PRIVACY:
            update.privacy_settings = category_data.get("privacy_settings", category_data)
        elif category == SettingsCategory.API_KEYS:
            for service_name, payload in category_data.items():
                if not isinstance(payload, dict):
                    continue
                key_value = payload.get("key_value")
                if key_value:
                    await self.update_host_api_key(str(host_id), service_name, key_value)
        else:
            raise ValueError(f"Unsupported settings category: {category}")
        if category != SettingsCategory.API_KEYS:
            host_response = await self.update_host_settings(host_id, update)
        api_rows = await self.get_host_api_keys(host_id) if category == SettingsCategory.API_KEYS else None
        return self._category_response(category, host_response, api_rows)

    async def get_system_settings(self) -> SystemSettingsListResponse:
        try:
            result = await self.db.execute(
                select(SystemSettings).order_by(SystemSettings.category, SystemSettings.setting_key)
            )
            rows = result.scalars().all()
            public_rows = [
                {
                    "setting_key": row.setting_key,
                    "setting_value": "" if row.is_sensitive else (row.setting_value or ""),
                    "description": row.description or "",
                    "category": row.category or "general",
                }
                for row in rows
                if not row.is_sensitive
            ]
            return SystemSettingsListResponse(settings=public_rows, count=len(public_rows))
        except Exception as e:
            logger.error(f"Error loading system settings: {e}")
            return SystemSettingsListResponse()

    async def backup_host_settings(self, host_id: uuid.UUID) -> SettingsBackupResponse:
        hs = await self.get_host_settings(host_id)
        if not hs:
            hs = await self.create_default_host_settings(str(host_id))
        host_response = self.host_settings_to_response(hs)
        backup_id = uuid.uuid4()
        created_at = datetime.utcnow()
        prefs = dict(hs.custom_settings or {})
        backups = dict(prefs.get("settings_backups") or {})
        backups[str(backup_id)] = {
            "created_at": created_at.isoformat(),
            "snapshot": host_response.model_dump(mode="json"),
        }
        prefs["settings_backups"] = backups
        hs.custom_settings = prefs
        hs.updated_at = created_at
        await self.db.commit()
        await self.db.refresh(hs)
        return SettingsBackupResponse(
            backup_id=backup_id,
            host_id=host_id,
            created_at=created_at,
        )

    async def restore_host_settings(
        self,
        host_id: uuid.UUID,
        backup_id: uuid.UUID,
    ) -> HostSettingsResponse:
        hs = await self.get_host_settings(host_id)
        if not hs:
            raise ValueError("Host settings row not found")
        prefs = dict(hs.custom_settings or {})
        backups = prefs.get("settings_backups") or {}
        snapshot = backups.get(str(backup_id))
        if not snapshot:
            raise ValueError("Backup not found")
        snap = snapshot.get("snapshot") if isinstance(snapshot, dict) else None
        if not isinstance(snap, dict):
            raise ValueError("Backup snapshot invalid")
        restored = await self.update_host_settings(
            host_id,
            HostSettingsUpdate(
                language_preference=snap.get("language_preference"),
                timezone=snap.get("timezone"),
                currency=snap.get("currency"),
                notification_preferences=snap.get("notification_preferences"),
                recommendation_settings=snap.get("recommendation_settings"),
                privacy_settings=snap.get("privacy_settings"),
            ),
        )
        return restored

    async def validate_api_key(
        self,
        service_name: str,
        api_key_value: str,
    ) -> SettingsApiKeyValidationResponse:
        allowed = {
            "openai",
            "google_ai",
            "google_maps",
            "google_places",
            "weather",
            "croatia_tourism",
            "istria_tourism",
        }
        if service_name not in allowed:
            return SettingsApiKeyValidationResponse(
                valid=False,
                service_name=service_name,
                message=f"Unknown service: {service_name}",
            )
        valid = bool(api_key_value and len(api_key_value.strip()) >= 10)
        return SettingsApiKeyValidationResponse(
            valid=valid,
            service_name=service_name,
            message="Key format looks valid" if valid else "API key must be at least 10 characters",
        )

    async def test_all_integrations(self, host_id: uuid.UUID) -> SettingsIntegrationsTestResponse:
        hs = await self.get_host_settings(host_id)
        pairs = [
            ("openai", bool(hs and hs.openai_api_key)),
            ("google_ai", bool(hs and hs.google_ai_api_key)),
            ("google_maps", bool(hs and hs.google_maps_api_key)),
            ("google_places", bool(hs and hs.google_places_api_key)),
            ("weather", bool(hs and hs.weather_api_key)),
            ("croatia_tourism", bool(hs and hs.croatia_tourism_api_key)),
            ("istria_tourism", bool(hs and hs.istria_tourism_api_key)),
        ]
        integrations: List[SettingsIntegrationTestResult] = []
        for service_name, configured in pairs:
            integrations.append(
                SettingsIntegrationTestResult(
                    service_name=service_name,
                    configured=configured,
                    status="configured" if configured else "not_configured",
                    message="API key present" if configured else "No API key stored",
                )
            )
        required = {"openai", "google_ai"}
        success = all(
            row.configured for row in integrations if row.service_name in required
        )
        return SettingsIntegrationsTestResponse(success=success, integrations=integrations)

    async def get_api_key_by_service(
        self,
        host_id: uuid.UUID,
        service_name: str,
    ) -> Optional[APIKeyResponse]:
        for row in await self.get_host_api_keys(host_id):
            if row.service_name == service_name:
                return row
        return None

    async def delete_api_key(self, api_key_id: uuid.UUID) -> bool:
        _ = api_key_id
        return False
