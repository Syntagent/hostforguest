"""
Settings management API endpoints for the Croatian tourist host platform.

Provides REST API endpoints for host settings management, API key configuration,
and system preferences.
"""

import logging
from typing import List, Optional, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import get_current_host
from app.services.settings_service import SettingsService
from app.services.host_service import HostService
from app.models.settings import (
    HostSettingsCreate,
    HostSettingsUpdate,
    HostSettingsResponse,
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyResponse,
    SystemSettingsResponse,
    SettingsCategory,
    HostSettings
)
from app.models.settings_api import (
    SettingsBackupResponse,
    SettingsApiKeyValidationResponse,
    SettingsCategoryResponse,
    SettingsIntegrationsTestResponse,
    SystemSettingsListResponse,
)
from app.models.host import Host

logger = logging.getLogger(__name__)
router = APIRouter()


# Host settings endpoints
@router.get("/", response_model=HostSettingsResponse)
async def get_host_settings(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all settings for the current host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostSettingsResponse: Host settings
    """
    try:
        settings_service = SettingsService(db)
        host_settings = await settings_service.get_host_settings(current_host.id)
        
        if not host_settings:
            # Create default settings if they don't exist
            default_settings = HostSettingsCreate(
                host_id=current_host.id,
                language_preference="en",
                timezone="Europe/Zagreb",
                currency="EUR",
                notification_preferences={
                    "email_enabled": True,
                    "sms_enabled": False,
                    "push_enabled": True,
                    "guest_booking": True,
                    "recommendation_feedback": True,
                    "system_updates": False
                },
                recommendation_settings={
                    "max_recommendations": 10,
                    "include_weather": True,
                    "include_seasonal": True,
                    "priority_local": True,
                    "show_host_tips": True
                }
            )
            host_settings = await settings_service.create_host_settings(default_settings)
        else:
            host_settings = settings_service.host_settings_to_response(host_settings)

        logger.info(f"Retrieved settings for host {current_host.id}")
        return host_settings
        
    except Exception as e:
        logger.error(f"Failed to retrieve host settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve host settings"
        )


@router.put("/", response_model=HostSettingsResponse)
async def update_host_settings(
    settings_data: HostSettingsUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update host settings.
    
    Args:
        settings_data: Updated settings data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostSettingsResponse: Updated host settings
    """
    try:
        settings_service = SettingsService(db)
        updated_settings = await settings_service.update_host_settings(
            host_id=current_host.id,
            settings_data=settings_data
        )
        
        logger.info(f"Updated settings for host {current_host.id}")
        return updated_settings
        
    except Exception as e:
        logger.error(f"Failed to update host settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update host settings"
        )


@router.get("/category/{category}", response_model=SettingsCategoryResponse)
async def get_settings_by_category(
    category: SettingsCategory,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get settings for a specific category.
    
    Args:
        category: Settings category
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Category-specific settings
    """
    try:
        settings_service = SettingsService(db)
        category_settings = await settings_service.get_settings_by_category(
            host_id=current_host.id,
            category=category
        )
        
        logger.info(f"Retrieved {category} settings for host {current_host.id}")
        return category_settings
        
    except Exception as e:
        logger.error(f"Failed to retrieve category settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category settings"
        )


@router.put("/category/{category}", response_model=SettingsCategoryResponse)
async def update_settings_category(
    category: SettingsCategory,
    category_data: Dict[str, Any],
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update settings for a specific category.
    
    Args:
        category: Settings category
        category_data: Updated category data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Updated category settings
    """
    try:
        settings_service = SettingsService(db)
        updated_settings = await settings_service.update_settings_category(
            host_id=current_host.id,
            category=category,
            category_data=category_data
        )
        
        logger.info(f"Updated {category} settings for host {current_host.id}")
        return updated_settings
        
    except Exception as e:
        logger.error(f"Failed to update category settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category settings"
        )


# API Key management endpoints
@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all API keys for the current host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        List[APIKeyResponse]: List of API keys (values masked)
    """
    try:
        settings_service = SettingsService(db)
        api_keys = await settings_service.get_host_api_keys(current_host.id)
        
        logger.info(f"Retrieved {len(api_keys)} API keys for host {current_host.id}")
        return api_keys
        
    except Exception as e:
        logger.error(f"Failed to retrieve API keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys"
        )


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key for the host.
    
    Args:
        api_key_data: API key creation data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        APIKeyResponse: Created API key (value masked)
    """
    try:
        settings_service = SettingsService(db)
        api_key = await settings_service.create_api_key(
            host_id=current_host.id,
            api_key_data=api_key_data
        )
        
        logger.info(f"Created {api_key_data.service_name} API key for host {current_host.id}")
        return api_key
        
    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.put("/api-keys/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: uuid.UUID,
    api_key_data: APIKeyUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an API key.
    
    Args:
        api_key_id: API key ID
        api_key_data: Updated API key data
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        APIKeyResponse: Updated API key (value masked)
    """
    try:
        settings_service = SettingsService(db)
        
        # Verify API key belongs to this host
        existing_key = await settings_service.get_api_key_by_id(api_key_id)
        if not existing_key or existing_key.host_id != current_host.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        updated_key = await settings_service.update_api_key(
            api_key_id=api_key_id,
            api_key_data=api_key_data
        )
        
        logger.info(f"Updated API key {api_key_id} for host {current_host.id}")
        return updated_key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an API key.
    
    Args:
        api_key_id: API key ID
        current_host: Current authenticated host
        db: Database session
    """
    try:
        settings_service = SettingsService(db)
        
        # Verify API key belongs to this host
        existing_key = await settings_service.get_api_key_by_id(api_key_id)
        if not existing_key or existing_key.host_id != current_host.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        await settings_service.delete_api_key(api_key_id)
        
        logger.info(f"Deleted API key {api_key_id} for host {current_host.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )


@router.get("/api-keys/service/{service_name}", response_model=APIKeyResponse)
async def get_api_key_by_service(
    service_name: str,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get API key for a specific service.
    
    Args:
        service_name: Service name (e.g., 'openai', 'google_maps', 'weather')
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        APIKeyResponse: API key for the service (value masked)
    """
    try:
        settings_service = SettingsService(db)
        api_key = await settings_service.get_api_key_by_service(
            host_id=current_host.id,
            service_name=service_name
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key for {service_name} not found"
            )
        
        logger.info(f"Retrieved {service_name} API key for host {current_host.id}")
        return api_key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve API key for {service_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve API key for {service_name}"
        )


# System settings endpoints (read-only for hosts)
@router.get("/system", response_model=SystemSettingsListResponse)
async def get_system_settings(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system-wide settings (read-only for hosts).
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        SystemSettingsResponse: System settings
    """
    try:
        settings_service = SettingsService(db)
        system_settings = await settings_service.get_system_settings()
        
        logger.info(f"Retrieved system settings for host {current_host.id}")
        return system_settings
        
    except Exception as e:
        logger.error(f"Failed to retrieve system settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system settings"
        )


# Backup and restore endpoints
@router.post("/backup", response_model=SettingsBackupResponse)
async def backup_host_settings(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a backup of all host settings and API keys.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Backup metadata
    """
    try:
        settings_service = SettingsService(db)
        backup_info = await settings_service.backup_host_settings(current_host.id)
        
        logger.info(f"Created settings backup for host {current_host.id}")
        return backup_info
        
    except Exception as e:
        logger.error(f"Failed to backup host settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to backup host settings"
        )


@router.post("/restore/{backup_id}", response_model=HostSettingsResponse)
async def restore_host_settings(
    backup_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore host settings from a backup.
    
    Args:
        backup_id: Backup ID
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        HostSettingsResponse: Restored host settings
    """
    try:
        settings_service = SettingsService(db)
        restored_settings = await settings_service.restore_host_settings(
            host_id=current_host.id,
            backup_id=backup_id
        )
        
        logger.info(f"Restored settings from backup {backup_id} for host {current_host.id}")
        return restored_settings
        
    except Exception as e:
        logger.error(f"Failed to restore host settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore host settings"
        )


# Validation endpoints
@router.post("/validate/api-key", response_model=SettingsApiKeyValidationResponse)
async def validate_api_key(
    service_name: str,
    api_key_value: str,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate an API key before saving it.
    
    Args:
        service_name: Service name
        api_key_value: API key value to validate
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Validation results
    """
    try:
        settings_service = SettingsService(db)
        validation_result = await settings_service.validate_api_key(
            service_name=service_name,
            api_key_value=api_key_value
        )
        
        logger.info(f"Validated {service_name} API key for host {current_host.id}")
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate API key"
        )


@router.get("/test/integrations", response_model=SettingsIntegrationsTestResponse)
async def test_integrations(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Test all configured integrations for the host.
    
    Args:
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        Dict[str, Any]: Integration test results
    """
    try:
        settings_service = SettingsService(db)
        test_results = await settings_service.test_all_integrations(current_host.id)
        
        logger.info(f"Tested integrations for host {current_host.id}")
        return test_results
        
    except Exception as e:
        logger.error(f"Failed to test integrations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test integrations"
        ) 