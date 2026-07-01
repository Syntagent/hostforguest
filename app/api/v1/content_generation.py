"""
Content generation API endpoints.

Provides REST API for AI-powered content generation including
attraction descriptions, local tips, translations, and social media posts.
"""

import logging
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.v1.hosts import get_current_host
from app.models.host import Host
from app.services.content_generation_service import ContentGenerationService
from app.services.ai_service import AIService
from app.services.settings_service import SettingsService
from app.services.attraction_service import AttractionService
from app.services.guest_group_service import GuestGroupService, host_owns_guest_group

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class GenerateDescriptionRequest(BaseModel):
    """Request for generating attraction description."""
    attraction_id: str
    language: str = "en"
    include_seo: bool = False


class GenerateDescriptionResponse(BaseModel):
    """Response with generated description."""
    description: str
    seo_description: Optional[str] = None
    language: str


class GenerateTipsRequest(BaseModel):
    """Request for generating local tips."""
    host_id: str
    attraction_id: Optional[str] = None
    language: str = "en"
    count: int = 5


class GenerateTipsResponse(BaseModel):
    """Response with generated tips."""
    tips: List[str]
    language: str


class TranslateContentRequest(BaseModel):
    """Request for translating content."""
    source_text: str
    source_language: str
    target_languages: List[str]


class TranslateContentResponse(BaseModel):
    """Response with translations."""
    translations: dict
    source_language: str


class GenerateSocialMediaRequest(BaseModel):
    """Request for generating social media post."""
    attraction_id: str
    post_type: str = "instagram"  # instagram, facebook, twitter
    language: str = "en"


class GenerateSocialMediaResponse(BaseModel):
    """Response with social media post."""
    post: str
    post_type: str
    language: str


class GenerateEmailRequest(BaseModel):
    """Request for generating email template."""
    template_type: str  # welcome, pre_arrival, follow_up
    host_id: str
    guest_group_id: Optional[str] = None
    language: str = "en"


class GenerateEmailResponse(BaseModel):
    """Response with email template."""
    email_content: str
    template_type: str
    language: str


@router.post("/attractions/description", response_model=GenerateDescriptionResponse)
async def generate_attraction_description(
    request: GenerateDescriptionRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered description for an attraction.
    
    Args:
        request: Description generation request
        db: Database session
        
    Returns:
        Generated description
    """
    try:
        settings_service = SettingsService(db)
        ai_service = AIService(settings_service)
        content_service = ContentGenerationService(ai_service=ai_service, settings_service=settings_service)
        attraction_service = AttractionService(db)
        
        attraction = await attraction_service.get_attraction_by_id(uuid.UUID(request.attraction_id))
        if not attraction or attraction.created_by_host_id != current_host.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        description = await content_service.generate_attraction_description(
            attraction=attraction,
            host=current_host,
            language=request.language
        )
        
        if not description:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate description"
            )
        
        # Generate SEO description if requested
        seo_description = None
        if request.include_seo:
            seo_description = await content_service.generate_seo_description(attraction)
        
        return GenerateDescriptionResponse(
            description=description,
            seo_description=seo_description,
            language=request.language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating description: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        )


@router.post("/tips", response_model=GenerateTipsResponse)
async def generate_local_tips(
    request: GenerateTipsRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate local tips for a host location.
    
    Args:
        request: Tips generation request
        db: Database session
        
    Returns:
        Generated tips
    """
    try:
        settings_service = SettingsService(db)
        ai_service = AIService(settings_service)
        content_service = ContentGenerationService(ai_service=ai_service, settings_service=settings_service)
        attraction_service = AttractionService(db)
        
        if str(current_host.id) != request.host_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden"
            )
        
        attraction = None
        if request.attraction_id:
            attraction = await attraction_service.get_attraction_by_id(uuid.UUID(request.attraction_id))
            if not attraction or attraction.created_by_host_id != current_host.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Attraction not found"
                )
        
        tips = await content_service.generate_local_tips(
            host=current_host,
            attraction=attraction,
            language=request.language
        )
        
        # Limit to requested count
        tips = tips[:request.count]
        
        return GenerateTipsResponse(
            tips=tips,
            language=request.language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tips: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tips: {str(e)}"
        )


@router.post("/translate", response_model=TranslateContentResponse)
async def translate_content(
    request: TranslateContentRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Translate content to multiple languages.
    
    Args:
        request: Translation request
        db: Database session
        
    Returns:
        Translations dictionary
    """
    try:
        settings_service = SettingsService(db)
        ai_service = AIService(settings_service)
        content_service = ContentGenerationService(ai_service=ai_service, settings_service=settings_service)
        
        translations = await content_service.generate_multi_language_content(
            source_text=request.source_text,
            source_language=request.source_language,
            target_languages=request.target_languages
        )
        
        return TranslateContentResponse(
            translations=translations,
            source_language=request.source_language
        )
        
    except Exception as e:
        logger.error(f"Error translating content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to translate content: {str(e)}"
        )


@router.post("/social-media", response_model=GenerateSocialMediaResponse)
async def generate_social_media_post(
    request: GenerateSocialMediaRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate social media post for an attraction.
    
    Args:
        request: Social media generation request
        db: Database session
        
    Returns:
        Generated social media post
    """
    try:
        settings_service = SettingsService(db)
        ai_service = AIService(settings_service)
        content_service = ContentGenerationService(ai_service=ai_service, settings_service=settings_service)
        attraction_service = AttractionService(db)
        
        # Get attraction
        attraction = await attraction_service.get_attraction_by_id(uuid.UUID(request.attraction_id))
        if not attraction or attraction.created_by_host_id != current_host.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attraction not found"
            )
        
        # Generate post
        post = await content_service.generate_social_media_post(
            attraction=attraction,
            post_type=request.post_type,
            language=request.language
        )
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate social media post"
            )
        
        return GenerateSocialMediaResponse(
            post=post,
            post_type=request.post_type,
            language=request.language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating social media post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate post: {str(e)}"
        )


@router.post("/email", response_model=GenerateEmailResponse)
async def generate_email_template(
    request: GenerateEmailRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate email template for guest communications.
    
    Args:
        request: Email generation request
        db: Database session
        
    Returns:
        Generated email template
    """
    try:
        settings_service = SettingsService(db)
        ai_service = AIService(settings_service)
        content_service = ContentGenerationService(ai_service=ai_service, settings_service=settings_service)
        if str(current_host.id) != request.host_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden"
            )
        
        guest_group = None
        if request.guest_group_id:
            guest_group_service = GuestGroupService(db)
            guest_group_obj = await guest_group_service.get_guest_group_by_id(
                uuid.UUID(request.guest_group_id)
            )
            if not guest_group_obj or not host_owns_guest_group(guest_group_obj, current_host.id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Guest group not found"
                )
            guest_group = {"group": guest_group_obj}
        
        email_content = await content_service.generate_email_template(
            template_type=request.template_type,
            host=current_host,
            guest_group=guest_group,
            language=request.language
        )
        
        if not email_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate email template"
            )
        
        return GenerateEmailResponse(
            email_content=email_content,
            template_type=request.template_type,
            language=request.language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating email template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate email: {str(e)}"
        )

