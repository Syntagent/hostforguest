"""
Host onboarding API endpoints with AI-powered profile generation.

Provides endpoints for hosts to create authentic profiles with AI assistance,
designed to work with beautiful Aceternity UI components.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import uuid
import logging
from datetime import datetime, timezone
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.models import Host, HostCreate, HostResponse
from app.services.host_onboarding_service import HostOnboardingService
from app.services.host_service import HostService
from app.services.onboarding_analytics_service import OnboardingAnalyticsService
from app.api.v1.hosts import get_current_host

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


# Import models from separate module
from app.api.v1.host_onboarding_models import (
    PropertyType,
    CroatianRegion,
    LocalExperience,
    KnowledgeLevel,
    AttractionCategory,
    AuthenticityLevel,
    CostEstimate,
    BestTime,
    Difficulty,
    GooglePlaceLocation,
    GooglePlaceInfo,
    AttractionSuggestion,
    EnhancedAttractionSuggestionsRequest,
    AttractionSuggestionsResponse,
    GooglePlacesResponse,
    OnboardingBasicInfo,
    ProfileSuggestionsResponse,
    WelcomeMessageResponse,
    ProfileValidationResponse,
    OnboardingStepResponse,
    EditSuggestionRequest,
    CoWriteRequest,
    AttractionSuggestionsRequest,
    AIEnhancementResponse
)

# Import helper functions
from app.api.v1.host_onboarding_helpers import (
    calculate_experience_score,
    analyze_guest_alignment,
    analyze_story_quality,
    extract_authenticity_indicators,
    generate_improvement_suggestions,
    identify_marketing_angles,
    identify_competitive_advantages,
    calculate_confidence_score,
    generate_guest_recommendations,
    generate_story_suggestions,
    generate_actionable_insights,
    suggest_next_steps
)

# Import Google Places functions
from app.api.v1.host_onboarding_google import (
    get_google_places_info,
    get_nearby_google_places
)


# Helper function to get current host (if authenticated)
async def get_current_host_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[Host]:
    """Get current host if authenticated, otherwise return None."""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        host_id: str = payload.get("sub")
        if not host_id:
            return None

        host_service = HostService(db)
        return await host_service.get_by_id(uuid.UUID(host_id))
    except:
        return None


# Onboarding API Endpoints

@router.post("/generate-profile-suggestions", response_model=ProfileSuggestionsResponse)
async def generate_profile_suggestions(
    basic_info: OnboardingBasicInfo,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Generate AI-powered profile suggestions for hosts.

    This endpoint helps hosts create authentic profiles using AI assistance
    based on their location, property type, and personal interests.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Convert to dict for service
        basic_info_dict = basic_info.model_dump()

        # Generate AI suggestions
        result = await onboarding_service.generate_host_profile_suggestions(
            basic_info=basic_info_dict,
            ai_preferences={"style": basic_info.profile_style, "target_guests": basic_info.target_guests}
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate profile suggestions"
            )

        # Create UI components for Aceternity UI
        ui_components = {
            "hero_section": {
                "component": "HeroSection",
                "props": {
                    "title": "Your AI-Generated Profile",
                    "subtitle": "Review and customize your profile suggestions",
                    "background_gradient": "from-blue-600 via-purple-600 to-pink-600"
                }
            },
            "suggestion_cards": {
                "component": "BentoGrid",
                "props": {
                    "className": "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
                    "items": [
                        {
                            "title": category.replace("_", " ").title(),
                            "description": suggestions[0] if suggestions else "No suggestions",
                            "suggestions": suggestions,
                            "className": "hover:scale-105 transition-transform"
                        }
                        for category, suggestions in result["suggestions"].items()
                    ]
                }
            }
        }

        return ProfileSuggestionsResponse(
            success=True,
            suggestions=result["suggestions"],
            reasoning=result["reasoning"],
            alternatives=result["alternatives"],
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating profile suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate profile suggestions"
        )


@router.post("/generate-attraction-suggestions", response_model=AttractionSuggestionsResponse)
async def generate_attraction_suggestions(
    request: EnhancedAttractionSuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate REAL Croatian tourism attraction suggestions for hosts.

    Uses curated Croatian tourism data and official source analysis,
    enhanced with AI personalization based on host's interests and location.
    """
    try:
        logger.info(f"🎯 Generating REAL Croatian attractions for {request.city} with interests: {request.interests}")

        onboarding_service = HostOnboardingService(db)

        # Build location info from request
        location_info = {}
        if request.city:
            location_info["city"] = request.city
        if request.address:
            location_info["address"] = request.address
        if request.region:
            location_info["region"] = request.region.value if hasattr(request.region, 'value') else request.region

        # Generate attractions using REAL Croatian tourism data
        result = await onboarding_service.generate_local_attraction_suggestions(
            host_location=location_info,
            host_interests=request.interests,
            local_knowledge_level=request.knowledge_level.value if hasattr(request.knowledge_level, 'value') else request.knowledge_level
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate attraction suggestions")
            )

        # Log the real data results
        data_source = result.get("data_source", "unknown")
        sources_used = result.get("sources_used", 0)
        personalization_level = result.get("personalization_level", "unknown")

        logger.info(f"✅ Generated {len(result['attractions'])} attractions using {data_source}")
        logger.info(f"📊 Data sources: {sources_used}, Personalization: {personalization_level}")

        # Create enhanced UI components with real data indicators
        ui_components = {
            "hero_section": {
                "component": "HeroSection",
                "props": {
                    "title": f"Real Croatian Attractions in {location_info.get('city', 'Your Area')}",
                    "subtitle": f"Curated from {sources_used} real Croatian tourism sources • Personalized for your expertise",
                    "background_gradient": "from-green-600 via-blue-600 to-purple-800",
                    "data_badge": {
                        "text": f"Real Data • {data_source}",
                        "color": "green" if "real" in data_source else "orange"
                    }
                }
            },
            "attraction_grid": {
                "component": "BentoGrid",
                "props": {
                    "className": "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
                    "items": [
                        {
                            "title": attraction["name"],
                            "description": attraction["description"],
                            "category": attraction.get("category", "experience"),
                            "cost": attraction.get("cost_estimate", "varies"),
                            "authenticity": attraction.get("authenticity_level", "high"),
                            "best_time": attraction.get("best_time", "anytime"),
                            "className": "hover:scale-105 transition-transform",
                            "data_source": attraction.get("data_source", "unknown"),
                            "enhanced": attraction.get("enhanced", False),
                            "relevance_score": attraction.get("relevance_score", 0.5)
                        }
                        for attraction in result["attractions"]
                    ]
                }
            }
        }

        return AttractionSuggestionsResponse(
            success=True,
            attractions=result["attractions"],
            categories=result.get("categories", {}),
            reasoning=result.get("reasoning", ""),
            ui_components=ui_components,
            metadata={
                "data_source": data_source,
                "sources_used": sources_used,
                "personalization_level": personalization_level,
                "total_attractions": len(result["attractions"])
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating attraction suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate attraction suggestions"
        )


@router.post("/generate-welcome-messages", response_model=WelcomeMessageResponse)
async def generate_welcome_messages(
    basic_info: OnboardingBasicInfo,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered welcome message suggestions.

    Creates multiple welcome message options in different styles
    for hosts to choose from or customize.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        result = await onboarding_service.generate_welcome_message_suggestions(
            basic_info=basic_info.model_dump()
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate welcome messages"
            )

        # Create UI components
        ui_components = {
            "message_cards": {
                "component": "CardGrid",
                "props": {
                    "items": [
                        {
                            "title": "Warm & Friendly",
                            "description": "Emphasizes hospitality and warmth",
                            "content": result["welcome_messages"]["warm_friendly"],
                            "icon": "👋",
                            "gradient": "from-yellow-400 to-orange-500"
                        },
                        {
                            "title": "Local & Authentic",
                            "description": "Emphasizes Croatian culture and traditions",
                            "content": result["welcome_messages"]["local_authentic"],
                            "icon": "🇭🇷",
                            "gradient": "from-red-500 to-blue-500"
                        }
                    ]
                }
            },
            "tips_section": {
                "component": "FeatureList",
                "props": {
                    "title": "Welcome Message Tips",
                    "items": [
                        {"text": tip, "icon": "💡"}
                        for tip in result["tips"]
                    ]
                }
            }
        }

        return WelcomeMessageResponse(
            success=True,
            welcome_messages=result["welcome_messages"],
            tips=result["tips"],
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating welcome messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate welcome messages"
        )


@router.post("/validate-profile", response_model=ProfileValidationResponse)
async def validate_and_enhance_profile(
    profile_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Validate host profile data and suggest AI-powered enhancements.

    Analyzes profile completeness and authenticity, providing actionable
    suggestions for improvement.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        result = await onboarding_service.validate_and_enhance_profile(profile_data)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile validation failed"
            )

        # Create progress and enhancement UI
        completeness_score = result["completeness_score"]
        ui_components = {
            "progress_section": {
                "component": "ProgressCard",
                "props": {
                    "title": "Profile Completeness",
                    "progress": completeness_score,
                    "color": "green" if completeness_score > 80 else "yellow" if completeness_score > 60 else "red",
                    "description": f"Your profile is {completeness_score:.0f}% complete"
                }
            },
            "enhancement_cards": {
                "component": "EnhancementGrid",
                "props": {
                    "enhancements": [
                        {
                            "category": enhancement["category"],
                            "suggestion": enhancement["suggestion"],
                            "priority": enhancement["priority"],
                            "difficulty": enhancement["implementation"],
                            "icon": "🔧" if enhancement["priority"] == "high" else "💡"
                        }
                        for enhancement in result["enhancements"]
                    ]
                }
            },
            "validation_status": {
                "component": "StatusBanner",
                "props": {
                    "status": "success" if result["validation"]["is_valid"] else "warning",
                    "message": "Profile is ready!" if result["validation"]["is_valid"] else "Some required fields are missing",
                    "missing_fields": result["validation"].get("missing_fields", [])
                }
            }
        }

        return ProfileValidationResponse(
            success=True,
            validation=result["validation"],
            enhancements=result["enhancements"],
            completeness_score=completeness_score,
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate profile"
        )


@router.get("/onboarding-flow/{step}", response_model=OnboardingStepResponse)
async def get_onboarding_step(
    step: int,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Get specific step in the multi-step onboarding flow with Aceternity UI components.

    Provides structured onboarding experience with beautiful UI components
    for each step of the host registration process.
    """
    try:
        total_steps = 5

        if step < 1 or step > total_steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step. Must be between 1 and {total_steps}"
            )

        # Define onboarding steps with Aceternity UI components
        steps = {
            1: {
                "step_name": "Welcome & Introduction",
                "content": {
                    "title": "Welcome to TouristGuideLocal",
                    "description": "Let's help you create an amazing experience for your guests",
                    "features": [
                        "AI-powered profile creation",
                        "Local attraction suggestions",
                        "Personalized recommendations"
                    ]
                },
                "ui_components": {
                    "welcome_card": {
                        "component": "WelcomeCard",
                        "props": {
                            "title": "Welcome!",
                            "description": "We'll guide you through creating your host profile",
                            "progress": 20
                        }
                    }
                }
            },
            2: {
                "step_name": "Property Details",
                "content": {
                    "title": "Tell us about your property",
                    "description": "Let's start with the basics about your Croatian property",
                    "fields": [
                        {
                            "name": "city",
                            "label": "City",
                            "type": "text",
                            "placeholder": "e.g., Lovran, Split, Dubrovnik",
                            "required": True,
                            "icon": "🏙️"
                        },
                        {
                            "name": "address",
                            "label": "Property Address",
                            "type": "textarea",
                            "placeholder": "Full address of your property",
                            "required": True,
                            "icon": "📍"
                        },
                        {
                            "name": "business_type",
                            "label": "Accommodation Type",
                            "type": "select",
                            "options": [
                                {"value": "apartment", "label": "Apartment"},
                                {"value": "villa", "label": "Villa"},
                                {"value": "house", "label": "House"},
                                {"value": "room", "label": "Private Room"}
                            ],
                            "icon": "🏠"
                        }
                    ],
                    "progress": 40
                },
                "ui_components": {
                    "form": {
                        "component": "OnboardingForm",
                        "props": {
                            "step": 2,
                            "title": "Property Details",
                            "description": "Let's start with the basics about your Croatian property",
                            "fields": [
                                {
                                    "name": "city",
                                    "label": "City",
                                    "type": "text",
                                    "placeholder": "e.g., Lovran, Split, Dubrovnik",
                                    "required": True,
                                    "icon": "🏙️"
                                },
                                {
                                    "name": "address",
                                    "label": "Property Address",
                                    "type": "textarea",
                                    "placeholder": "Full address of your property",
                                    "required": True,
                                    "icon": "📍"
                                },
                                {
                                    "name": "business_type",
                                    "label": "Accommodation Type",
                                    "type": "select",
                                    "options": [
                                        {"value": "apartment", "label": "Apartment"},
                                        {"value": "villa", "label": "Villa"},
                                        {"value": "house", "label": "House"},
                                        {"value": "room", "label": "Private Room"}
                                    ],
                                    "icon": "🏠"
                                }
                            ],
                            "progress": 40
                        }
                    }
                }
            },
            3: {
                "step_name": "AI Profile Generation",
                "content": {
                    "title": "Create Your Authentic Profile",
                    "description": "Let our AI help you create a compelling host profile that showcases your Croatian hospitality.",
                    "ai_features": [
                        "Authentic business descriptions",
                        "Warm welcome messages",
                        "Local specialty highlights",
                        "Personal host stories"
                    ]
                },
                "ui_components": {
                    "ai_generator": {
                        "component": "AIProfileGenerator",
                        "props": {
                            "title": "AI-Powered Profile Creation",
                            "description": "Answer a few questions and watch AI create your authentic Croatian host profile",
                            "steps": [
                                {
                                    "title": "Personality & Style",
                                    "questions": [
                                        "What's your hosting style?",
                                        "What makes your location special?",
                                        "What are your local interests?"
                                    ]
                                },
                                {
                                    "title": "Generate Profile",
                                    "description": "AI creates multiple profile options"
                                },
                                {
                                    "title": "Review & Customize",
                                    "description": "Choose and personalize your favorite"
                                }
                            ]
                        }
                    }
                }
            },
            4: {
                "step_name": "Local Attractions",
                "content": {
                    "title": "Share Your Local Knowledge",
                    "description": "Help guests discover the best of your area with AI-suggested attractions and your personal insights.",
                    "categories": ["Hidden Gems", "Local Favorites", "Cultural Sites", "Natural Beauty", "Food & Drink"]
                },
                "ui_components": {
                    "attraction_builder": {
                        "component": "AttractionBuilder",
                        "props": {
                            "title": "Build Your Local Guide",
                            "description": "AI will suggest attractions, you add your personal touch",
                            "features": [
                                {
                                    "icon": "🔍",
                                    "title": "AI Discovery",
                                    "description": "Find hidden gems and local favorites"
                                },
                                {
                                    "icon": "✏️",
                                    "title": "Personal Touch",
                                    "description": "Add your own insights and recommendations"
                                },
                                {
                                    "icon": "📸",
                                    "title": "Visual Content",
                                    "description": "Upload photos to make it personal"
                                }
                            ]
                        }
                    }
                }
            },
            5: {
                "step_name": "Review & Complete",
                "content": {
                    "title": "Review Your Profile",
                    "description": "Review everything and complete your onboarding",
                    "checklist": [
                        "Profile information complete",
                        "Attractions added",
                        "Welcome messages ready",
                        "Access code generated"
                    ]
                },
                "ui_components": {
                    "review_card": {
                        "component": "ReviewCard",
                        "props": {
                            "title": "Almost Done!",
                            "description": "Review your profile and complete onboarding",
                            "checklist": [
                                "Profile information complete",
                                "Attractions added",
                                "Welcome messages ready",
                                "Access code generated"
                            ]
                        }
                    }
                }
            }
        }

        step_data = steps.get(step, {})

        return OnboardingStepResponse(
            step=step,
            total_steps=total_steps,
            step_name=step_data.get("step_name", ""),
            content=step_data.get("content", {}),
            ui_components=step_data.get("ui_components", {}),
            next_step_available=step < total_steps
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting onboarding step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get onboarding step"
        )


@router.post("/edit-suggestion")
async def edit_profile_suggestion(
    edit_request: EditSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Edit or co-write a profile suggestion with AI assistance.

    Allows hosts to customize AI-generated suggestions with their personal touch,
    with optional AI collaboration for improvement.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        if edit_request.is_collaborative:
            # Use AI to improve the user's edit
            collaboration_context = {
                "category": edit_request.category,
                "original": edit_request.original_text,
                "user_edit": edit_request.user_edit,
                "collaboration_prompt": edit_request.collaboration_prompt
            }

            messages = [
                {
                    "role": "system",
                    "content": """You are helping a Croatian host improve their profile content.
                    Your role is to enhance their personal edits while maintaining their authentic voice.
                    Keep it warm, genuine, and true to Croatian hospitality."""
                },
                {
                    "role": "user",
                    "content": f"""
Original AI suggestion: "{edit_request.original_text}"

User's edit: "{edit_request.user_edit}"

User's request: "{edit_request.collaboration_prompt}"

Please help improve the user's edit while:
1. Preserving their personal voice and intent
2. Maintaining authentic Croatian hospitality tone
3. Keeping it natural and genuine
4. Making it more compelling for guests

Return only the improved version, no additional text.
"""
                }
            ]

            ai_response = await onboarding_service.ai_service.generate_chat_response(
                host_id="onboarding",
                messages=messages,
                context=collaboration_context
            )

            if ai_response.get("success"):
                improved_text = ai_response.get("response", "").strip()
                return {
                    "success": True,
                    "original": edit_request.original_text,
                    "user_edit": edit_request.user_edit,
                    "ai_improved": improved_text,
                    "final_suggestion": improved_text,
                    "collaboration_used": True
                }

        # No collaboration requested, just return the user's edit
        return {
            "success": True,
            "original": edit_request.original_text,
            "user_edit": edit_request.user_edit,
            "final_suggestion": edit_request.user_edit,
            "collaboration_used": False
        }

    except Exception as e:
        logger.error(f"Error editing suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit suggestion"
        )


@router.post("/co-write")
async def co_write_content(
    cowrite_request: CoWriteRequest,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Co-write content with AI assistance.

    Helps hosts create content from scratch or expand their initial ideas with AI collaboration.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Build context for co-writing
        context = {
            "category": cowrite_request.category,
            "style": cowrite_request.style_preference,
            "user_input": cowrite_request.user_input,
            "additional_context": cowrite_request.context
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are co-writing {cowrite_request.category} content with a Croatian host. Your role is to help them expand and improve their ideas while maintaining their authentic voice.

Style: {cowrite_request.style_preference}
Focus: Croatian hospitality, authenticity, local knowledge

Guidelines:
- Build upon the user's input, don't replace it
- Maintain their personal voice and perspective
- Add Croatian cultural elements naturally
- Keep it genuine and warm
- Make it compelling for guests"""
            },
            {
                "role": "user",
                "content": f"""I want to write {cowrite_request.category} content. Here's what I have so far:

"{cowrite_request.user_input}"

Please help me expand this into a complete, compelling piece that maintains my voice but makes it more engaging for potential guests. Keep the authentic Croatian hospitality feel.

Return only the improved content, no additional text."""
            }
        ]

        ai_response = await onboarding_service.ai_service.generate_chat_response(
            host_id="onboarding",
            messages=messages,
            context=context
        )

        if ai_response.get("success"):
            co_written_content = ai_response.get("response", "").strip()
            return {
                "success": True,
                "user_input": cowrite_request.user_input,
                "co_written": co_written_content,
                "category": cowrite_request.category
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to co-write content"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error co-writing content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to co-write content"
        )


@router.post("/analyze-location", response_model=Dict[str, Any])
async def analyze_location_potential(
    request: EnhancedAttractionSuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze location potential using Croatian tourism hosting best practices.

    Provides comprehensive analysis of a location's tourism potential,
    including market analysis, competitive landscape, and recommendations.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Enhanced analysis with multiple data sources
        analysis_results = {
            "location_analysis": {
                "city": request.city,
                "region": request.region.value if request.region else None,
                "coordinates": request.coordinates.model_dump() if request.coordinates else None,
                "local_experience_score": calculate_experience_score(request.local_experience),
                "knowledge_level": request.knowledge_level.value if hasattr(request.knowledge_level, 'value') else request.knowledge_level
            },
            "market_potential": {
                "guest_alignment": analyze_guest_alignment(request.preferred_guests),
                "interest_diversity": len(request.interests),
                "location_story_quality": analyze_story_quality(request.location_story),
                "authenticity_indicators": extract_authenticity_indicators(request.location_story)
            },
            "recommendations": {
                "suggested_improvements": generate_improvement_suggestions(request),
                "marketing_angles": identify_marketing_angles(request),
                "competitive_advantages": identify_competitive_advantages(request)
            },
            "metadata": {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "data_sources": ["user_input", "ai_analysis", "tourism_guidelines"],
                "confidence_score": calculate_confidence_score(request)
            }
        }

        return {
            "success": True,
            "analysis": analysis_results,
            "insights": generate_actionable_insights(analysis_results),
            "next_steps": suggest_next_steps(analysis_results)
        }

    except Exception as e:
        logger.error(f"Location analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze location potential"
        )


# All models are imported from host_onboarding_models module
# Helper functions are imported from host_onboarding_helpers module
# Google Places functions are imported from host_onboarding_google module


# Helper function to get current host (if authenticated)
async def get_current_host_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[Host]:
    """Get current host if authenticated, otherwise return None."""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        host_id: str = payload.get("sub")
        if not host_id:
            return None

        host_service = HostService(db)
        return await host_service.get_by_id(uuid.UUID(host_id))
    except:
        return None


# Onboarding API Endpoints

@router.post("/generate-profile-suggestions", response_model=ProfileSuggestionsResponse)
async def generate_profile_suggestions(
    basic_info: OnboardingBasicInfo,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Generate AI-powered profile suggestions for hosts.

    This endpoint helps hosts create authentic profiles using AI assistance
    based on their location, property type, and personal interests.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Convert to dict for service
        basic_info_dict = basic_info.model_dump()

        # Generate AI suggestions
        result = await onboarding_service.generate_host_profile_suggestions(
            basic_info=basic_info_dict,
            ai_preferences={"style": basic_info.profile_style, "target_guests": basic_info.target_guests}
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate profile suggestions")
            )

        # Create UI components for Aceternity UI
        ui_components = {
            "hero_section": {
                "component": "HeroSection",
                "props": {
                    "title": "Your AI-Generated Profile",
                    "subtitle": "Review and customize your profile suggestions",
                    "background_gradient": "from-blue-600 via-purple-600 to-pink-600"
                }
            },
            "suggestion_cards": {
                "component": "BentoGrid",
                "props": {
                    "className": "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
                    "items": [
                        {
                            "title": category.replace("_", " ").title(),
                            "description": suggestions[0] if suggestions else "No suggestions",
                            "suggestions": suggestions,
                            "className": "hover:scale-105 transition-transform"
                        }
                        for category, suggestions in result["suggestions"].items()
                    ]
                }
            }
        }

        return ProfileSuggestionsResponse(
            success=True,
            suggestions=result["suggestions"],
            reasoning=result["reasoning"],
            alternatives=result["alternatives"],
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating profile suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate profile suggestions"
        )


@router.post("/generate-attraction-suggestions", response_model=AttractionSuggestionsResponse)
async def generate_attraction_suggestions(
    request: EnhancedAttractionSuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate REAL Croatian tourism attraction suggestions for hosts.

    Uses curated Croatian tourism data and official source analysis,
    enhanced with AI personalization based on host's interests and location.
    """
    try:
        logger.info(f"🎯 Generating REAL Croatian attractions for {request.city} with interests: {request.interests}")

        onboarding_service = HostOnboardingService(db)

        # Build location info from request
        location_info = {}
        if request.city:
            location_info["city"] = request.city
        if request.address:
            location_info["address"] = request.address
        if request.region:
            location_info["region"] = request.region.value if hasattr(request.region, 'value') else request.region

        # Generate attractions using REAL Croatian tourism data
        result = await onboarding_service.generate_local_attraction_suggestions(
            host_location=location_info,
            host_interests=request.interests,
            local_knowledge_level=request.knowledge_level.value if hasattr(request.knowledge_level, 'value') else request.knowledge_level
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate attraction suggestions")
            )

        # Log the real data results
        data_source = result.get("data_source", "unknown")
        sources_used = result.get("sources_used", 0)
        personalization_level = result.get("personalization_level", "unknown")

        logger.info(f"✅ Generated {len(result['attractions'])} attractions using {data_source}")
        logger.info(f"📊 Data sources: {sources_used}, Personalization: {personalization_level}")

        # Create enhanced UI components with real data indicators
        ui_components = {
            "hero_section": {
                "component": "HeroSection",
                "props": {
                    "title": f"Real Croatian Attractions in {location_info.get('city', 'Your Area')}",
                    "subtitle": f"Curated from {sources_used} real Croatian tourism sources • Personalized for your expertise",
                    "background_gradient": "from-green-600 via-blue-600 to-purple-800",
                    "data_badge": {
                        "text": f"Real Data • {data_source}",
                        "color": "green" if "real" in data_source else "orange"
                    }
                }
            },
            "attraction_grid": {
                "component": "BentoGrid",
                "props": {
                    "className": "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
                    "items": [
                        {
                            "title": attraction["name"],
                            "description": attraction["description"],
                            "category": attraction.get("category", "experience"),
                            "cost": attraction.get("cost_estimate", "varies"),
                            "authenticity": attraction.get("authenticity_level", "high"),
                            "best_time": attraction.get("best_time", "anytime"),
                            "className": "hover:scale-105 transition-transform",
                            "data_source": attraction.get("data_source", "unknown"),
                            "enhanced": attraction.get("enhanced", False),
                            "relevance_score": attraction.get("relevance_score", 0.5)
                        }
                        for attraction in result["attractions"]
                    ]
                }
            }
        }

        return AttractionSuggestionsResponse(
            success=True,
            attractions=result["attractions"],
            categories=result.get("categories", {}),
            reasoning=result.get("reasoning", ""),
            ui_components=ui_components,
            metadata={
                "data_source": data_source,
                "sources_used": sources_used,
                "personalization_level": personalization_level,
                "total_attractions": len(result["attractions"])
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating attraction suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate attraction suggestions"
        )


@router.post("/generate-welcome-messages", response_model=WelcomeMessageResponse)
async def generate_welcome_messages(
    basic_info: OnboardingBasicInfo,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered welcome message suggestions.

    Creates multiple welcome message options in different styles
    for hosts to choose from or customize.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        result = await onboarding_service.generate_welcome_message_suggestions(
            basic_info=basic_info.model_dump()
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate welcome messages"
            )

        # Create UI components
        ui_components = {
            "message_cards": {
                "component": "CardGrid",
                "props": {
                    "items": [
                        {
                            "title": "Warm & Friendly",
                            "description": "Emphasizes hospitality and warmth",
                            "content": result["welcome_messages"]["warm_friendly"],
                            "icon": "👋",
                            "gradient": "from-yellow-400 to-orange-500"
                        },
                        {
                            "title": "Local & Authentic",
                            "description": "Emphasizes Croatian culture and traditions",
                            "content": result["welcome_messages"]["local_authentic"],
                            "icon": "🇭🇷",
                            "gradient": "from-red-500 to-blue-500"
                        }
                    ]
                }
            },
            "tips_section": {
                "component": "FeatureList",
                "props": {
                    "title": "Welcome Message Tips",
                    "items": [
                        {"text": tip, "icon": "💡"}
                        for tip in result["tips"]
                    ]
                }
            }
        }

        return WelcomeMessageResponse(
            success=True,
            welcome_messages=result["welcome_messages"],
            tips=result["tips"],
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating welcome messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate welcome messages"
        )


@router.post("/validate-profile", response_model=ProfileValidationResponse)
async def validate_and_enhance_profile(
    profile_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Validate host profile data and suggest AI-powered enhancements.

    Analyzes profile completeness and authenticity, providing actionable
    suggestions for improvement.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        result = await onboarding_service.validate_and_enhance_profile(profile_data)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile validation failed"
            )

        # Create progress and enhancement UI
        completeness_score = result["completeness_score"]
        ui_components = {
            "progress_section": {
                "component": "ProgressCard",
                "props": {
                    "title": "Profile Completeness",
                    "progress": completeness_score,
                    "color": "green" if completeness_score > 80 else "yellow" if completeness_score > 60 else "red",
                    "description": f"Your profile is {completeness_score:.0f}% complete"
                }
            },
            "enhancement_cards": {
                "component": "EnhancementGrid",
                "props": {
                    "enhancements": [
                        {
                            "category": enhancement["category"],
                            "suggestion": enhancement["suggestion"],
                            "priority": enhancement["priority"],
                            "difficulty": enhancement["implementation"],
                            "icon": "🔧" if enhancement["priority"] == "high" else "💡"
                        }
                        for enhancement in result["enhancements"]
                    ]
                }
            },
            "validation_status": {
                "component": "StatusBanner",
                "props": {
                    "status": "success" if result["validation"]["is_valid"] else "warning",
                    "message": "Profile is ready!" if result["validation"]["is_valid"] else "Some required fields are missing",
                    "missing_fields": result["validation"].get("missing_fields", [])
                }
            }
        }

        return ProfileValidationResponse(
            success=True,
            validation=result["validation"],
            enhancements=result["enhancements"],
            completeness_score=completeness_score,
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate profile"
        )


@router.get("/onboarding-flow/{step}", response_model=OnboardingStepResponse)
async def get_onboarding_step(
    step: int,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Get specific step in the multi-step onboarding flow with Aceternity UI components.

    Provides structured onboarding experience with beautiful UI components
    for each step of the host registration process.
    """
    try:
        total_steps = 5

        if step < 1 or step > total_steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step. Must be between 1 and {total_steps}"
            )

        # Define onboarding steps with Aceternity UI components
        steps = {
            1: {
                "step_name": "Welcome & Introduction",
                "content": {
                    "title": "Welcome to TouristGuideLocal",
                    "description": "Let's help you create an amazing experience for your guests",
                    "features": [
                        "AI-powered profile creation",
                        "Local attraction suggestions",
                        "Personalized recommendations"
                    ]
                },
                "ui_components": {
                    "welcome_card": {
                        "component": "WelcomeCard",
                        "props": {
                            "title": "Welcome!",
                            "description": "We'll guide you through creating your host profile",
                            "progress": 20
                        }
                    }
                }
            },
            2: {
                "step_name": "Property Details",
                "content": {
                    "title": "Tell us about your property",
                    "description": "Let's start with the basics about your Croatian property",
                    "fields": [
                        {
                            "name": "city",
                            "label": "City",
                            "type": "text",
                            "placeholder": "e.g., Lovran, Split, Dubrovnik",
                            "required": True,
                            "icon": "🏙️"
                        },
                        {
                            "name": "address",
                            "label": "Property Address",
                            "type": "textarea",
                            "placeholder": "Full address of your property",
                            "required": True,
                            "icon": "📍"
                        },
                        {
                            "name": "business_type",
                            "label": "Accommodation Type",
                            "type": "select",
                            "options": [
                                {"value": "apartment", "label": "Apartment"},
                                {"value": "villa", "label": "Villa"},
                                {"value": "house", "label": "House"},
                                {"value": "room", "label": "Private Room"}
                            ],
                            "icon": "🏠"
                        }
                    ],
                    "progress": 40
                },
                "ui_components": {
                    "form": {
                        "component": "OnboardingForm",
                        "props": {
                            "step": 2,
                            "title": "Property Details",
                            "description": "Let's start with the basics about your Croatian property",
                            "fields": [
                                {
                                    "name": "city",
                                    "label": "City",
                                    "type": "text",
                                    "placeholder": "e.g., Lovran, Split, Dubrovnik",
                                    "required": True,
                                    "icon": "🏙️"
                                },
                                {
                                    "name": "address",
                                    "label": "Property Address",
                                    "type": "textarea",
                                    "placeholder": "Full address of your property",
                                    "required": True,
                                    "icon": "📍"
                                },
                                {
                                    "name": "business_type",
                                    "label": "Accommodation Type",
                                    "type": "select",
                                    "options": [
                                        {"value": "apartment", "label": "Apartment"},
                                        {"value": "villa", "label": "Villa"},
                                        {"value": "house", "label": "House"},
                                        {"value": "room", "label": "Private Room"}
                                    ],
                                    "icon": "🏠"
                                }
                            ],
                            "progress": 40
                        }
                    }
                }
            },
            3: {
                "step_name": "AI Profile Generation",
                "content": {
                    "title": "Create Your Authentic Profile",
                    "description": "Let our AI help you create a compelling host profile that showcases your Croatian hospitality.",
                    "ai_features": [
                        "Authentic business descriptions",
                        "Warm welcome messages",
                        "Local specialty highlights",
                        "Personal host stories"
                    ]
                },
                "ui_components": {
                    "ai_generator": {
                        "component": "AIProfileGenerator",
                        "props": {
                            "title": "AI-Powered Profile Creation",
                            "description": "Answer a few questions and watch AI create your authentic Croatian host profile",
                            "steps": [
                                {
                                    "title": "Personality & Style",
                                    "questions": [
                                        "What's your hosting style?",
                                        "What makes your location special?",
                                        "What are your local interests?"
                                    ]
                                },
                                {
                                    "title": "Generate Profile",
                                    "description": "AI creates multiple profile options"
                                },
                                {
                                    "title": "Review & Customize",
                                    "description": "Choose and personalize your favorite"
                                }
                            ]
                        }
                    }
                }
            },
            4: {
                "step_name": "Local Attractions",
                "content": {
                    "title": "Share Your Local Knowledge",
                    "description": "Help guests discover the best of your area with AI-suggested attractions and your personal insights.",
                    "categories": ["Hidden Gems", "Local Favorites", "Cultural Sites", "Natural Beauty", "Food & Drink"]
                },
                "ui_components": {
                    "attraction_builder": {
                        "component": "AttractionBuilder",
                        "props": {
                            "title": "Build Your Local Guide",
                            "description": "AI will suggest attractions, you add your personal touch",
                            "features": [
                                {
                                    "icon": "🔍",
                                    "title": "AI Discovery",
                                    "description": "Find hidden gems and local favorites"
                                },
                                {
                                    "icon": "✏️",
                                    "title": "Personal Touch",
                                    "description": "Add your own insights and recommendations"
                                },
                                {
                                    "icon": "📸",
                                    "title": "Visual Content",
                                    "description": "Upload photos to make it personal"
                                }
                            ]
                        }
                    }
                }
            },
            5: {
                "step_name": "Review & Complete",
                "content": {
                    "title": "Review Your Profile",
                    "description": "Review everything and complete your onboarding",
                    "checklist": [
                        "Profile information complete",
                        "Attractions added",
                        "Welcome messages ready",
                        "Access code generated"
                    ]
                },
                "ui_components": {
                    "review_card": {
                        "component": "ReviewCard",
                        "props": {
                            "title": "Almost Done!",
                            "description": "Review your profile and complete onboarding",
                            "checklist": [
                                "Profile information complete",
                                "Attractions added",
                                "Welcome messages ready",
                                "Access code generated"
                            ]
                        }
                    }
                }
            }
        }

        step_data = steps.get(step, {})

        return OnboardingStepResponse(
            step=step,
            total_steps=total_steps,
            step_name=step_data.get("step_name", ""),
            content=step_data.get("content", {}),
            ui_components=step_data.get("ui_components", {}),
            next_step_available=step < total_steps
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting onboarding step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get onboarding step"
        )


@router.post("/edit-suggestion")
async def edit_profile_suggestion(
    edit_request: EditSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Edit or co-write a profile suggestion with AI assistance.

    Allows hosts to customize AI-generated suggestions with their personal touch,
    with optional AI collaboration for improvement.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        if edit_request.is_collaborative:
            # Use AI to improve the user's edit
            collaboration_context = {
                "category": edit_request.category,
                "original": edit_request.original_text,
                "user_edit": edit_request.user_edit,
                "collaboration_prompt": edit_request.collaboration_prompt
            }

            messages = [
                {
                    "role": "system",
                    "content": """You are helping a Croatian host improve their profile content.
                    Your role is to enhance their personal edits while maintaining their authentic voice.
                    Keep it warm, genuine, and true to Croatian hospitality."""
                },
                {
                    "role": "user",
                    "content": f"""
Original AI suggestion: "{edit_request.original_text}"

User's edit: "{edit_request.user_edit}"

User's request: "{edit_request.collaboration_prompt}"

Please help improve the user's edit while:
1. Preserving their personal voice and intent
2. Maintaining authentic Croatian hospitality tone
3. Keeping it natural and genuine
4. Making it more compelling for guests

Return only the improved version, no additional text.
"""
                }
            ]

            ai_response = await onboarding_service.ai_service.generate_chat_response(
                host_id="onboarding",
                messages=messages,
                context=collaboration_context
            )

            if ai_response.get("success"):
                improved_text = ai_response.get("response", "").strip()
                return {
                    "success": True,
                    "original": edit_request.original_text,
                    "user_edit": edit_request.user_edit,
                    "ai_improved": improved_text,
                    "final_suggestion": improved_text,
                    "collaboration_used": True
                }

        # No collaboration requested, just return the user's edit
        return {
            "success": True,
            "original": edit_request.original_text,
            "user_edit": edit_request.user_edit,
            "final_suggestion": edit_request.user_edit,
            "collaboration_used": False
        }

    except Exception as e:
        logger.error(f"Error editing suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit suggestion"
        )


@router.post("/co-write")
async def co_write_content(
    cowrite_request: CoWriteRequest,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Co-write content with AI assistance.

    Helps hosts create content from scratch or expand their initial ideas with AI collaboration.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Build context for co-writing
        context = {
            "category": cowrite_request.category,
            "style": cowrite_request.style_preference,
            "user_input": cowrite_request.user_input,
            "additional_context": cowrite_request.context
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are co-writing {cowrite_request.category} content with a Croatian host. Your role is to help them expand and improve their ideas while maintaining their authentic voice.

Style: {cowrite_request.style_preference}
Focus: Croatian hospitality, authenticity, local knowledge

Guidelines:
- Build upon the user's input, don't replace it
- Maintain their personal voice and perspective
- Add Croatian cultural elements naturally
- Keep it genuine and warm
- Make it compelling for guests"""
            },
            {
                "role": "user",
                "content": f"""I want to write {cowrite_request.category} content. Here's what I have so far:

"{cowrite_request.user_input}"

Please help me expand this into a complete, compelling piece that maintains my voice but makes it more engaging for potential guests. Keep the authentic Croatian hospitality feel.

Return only the improved content, no additional text."""
            }
        ]

        ai_response = await onboarding_service.ai_service.generate_chat_response(
            host_id="onboarding",
            messages=messages,
            context=context
        )

        if ai_response.get("success"):
            co_written_content = ai_response.get("response", "").strip()
            return {
                "success": True,
                "user_input": cowrite_request.user_input,
                "co_written": co_written_content,
                "category": cowrite_request.category
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to co-write content"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error co-writing content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to co-write content"
        )


@router.post("/analyze-location", response_model=Dict[str, Any])
async def analyze_location_potential(
    request: EnhancedAttractionSuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze location potential using Croatian tourism hosting best practices.

    Provides comprehensive analysis of a location's tourism potential,
    including market analysis, competitive landscape, and recommendations.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Enhanced analysis with multiple data sources
        analysis_results = {
            "location_analysis": {
                "city": request.city,
                "region": request.region.value if request.region else None,
                "coordinates": request.coordinates.model_dump() if request.coordinates else None,
                "local_experience_score": calculate_experience_score(request.local_experience),
                "knowledge_level": request.knowledge_level.value if hasattr(request.knowledge_level, 'value') else request.knowledge_level
            },
            "market_potential": {
                "guest_alignment": analyze_guest_alignment(request.preferred_guests),
                "interest_diversity": len(request.interests),
                "location_story_quality": analyze_story_quality(request.location_story),
                "authenticity_indicators": extract_authenticity_indicators(request.location_story)
            },
            "recommendations": {
                "suggested_improvements": generate_improvement_suggestions(request),
                "marketing_angles": identify_marketing_angles(request),
                "competitive_advantages": identify_competitive_advantages(request)
            },
            "metadata": {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "data_sources": ["user_input", "ai_analysis", "tourism_guidelines"],
                "confidence_score": calculate_confidence_score(request)
            }
        }

        return {
            "success": True,
            "analysis": analysis_results,
            "insights": generate_actionable_insights(analysis_results),
            "next_steps": suggest_next_steps(analysis_results)
        }

    except Exception as e:
        logger.error(f"Location analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze location potential"
        )


# Duplicate model definitions removed - all models are imported from host_onboarding_models module


# Helper function to get current host (if authenticated)
async def get_current_host_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[Host]:
    """Get current host if authenticated, otherwise return None."""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        host_id: str = payload.get("sub")
        if not host_id:
            return None

        host_service = HostService(db)
        return await host_service.get_by_id(uuid.UUID(host_id))
    except:
        return None


# Onboarding API Endpoints

@router.post("/generate-profile-suggestions", response_model=ProfileSuggestionsResponse)
async def generate_profile_suggestions(
    basic_info: OnboardingBasicInfo,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Generate AI-powered profile suggestions for hosts.

    This endpoint helps hosts create authentic profiles using AI assistance
    based on their location, property type, and personal interests.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Convert to dict for service
        basic_info_dict = basic_info.model_dump()

        # Generate AI suggestions
        result = await onboarding_service.generate_host_profile_suggestions(
            basic_info=basic_info_dict,
            ai_preferences={"style": basic_info.profile_style, "target_guests": basic_info.target_guests}
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate profile suggestions")
            )

        # Create beautiful UI components for Aceternity
        ui_components = {
            "hero_section": {
                "component": "HeroSection",
                "props": {
                    "title": f"Welcome to Croatian Hospitality in {basic_info.city}",
                    "subtitle": "Let AI help you create an authentic host profile that showcases your local expertise",
                    "background_gradient": "from-blue-600 via-purple-600 to-indigo-800",
                    "cta_text": "Continue Setup"
                }
            },
            "bento_grid": {
                "component": "BentoGrid",
                "props": {
                    "items": [
                        {
                            "title": "Business Description",
                            "description": "AI-generated authentic descriptions",
                            "icon": "🏠",
                            "suggestions": list(result["suggestions"].get("business_description", [])),
                            "className": "md:col-span-2"
                        },
                        {
                            "title": "Welcome Messages",
                            "description": "Warm Croatian hospitality greetings",
                            "icon": "👋",
                            "suggestions": list(result["suggestions"].get("welcome_message", [])),
                            "className": "md:col-span-1"
                        },
                        {
                            "title": "Local Specialties",
                            "description": "Unique local experiences to highlight",
                            "icon": "🌟",
                            "suggestions": list(result["suggestions"].get("local_specialties", [])),
                            "className": "md:col-span-1"
                        },
                        {
                            "title": "Host Story",
                            "description": "Personal connection to your area",
                            "icon": "📖",
                            "suggestions": list(result["suggestions"].get("host_story", [])),
                            "className": "md:col-span-2"
                        }
                    ]
                }
            },
            "feature_section": {
                "component": "FeatureSection",
                "props": {
                    "features": [
                        {
                            "title": "AI-Powered Authenticity",
                            "description": "Generate genuine profiles that reflect Croatian culture",
                            "icon": "🤖"
                        },
                        {
                            "title": "Local Expertise",
                            "description": "Showcase your unique knowledge of the area",
                            "icon": "🗺️"
                        },
                        {
                            "title": "Guest Appeal",
                            "description": "Create compelling profiles that attract the right guests",
                            "icon": "✨"
                        }
                    ]
                }
            }
        }

        return ProfileSuggestionsResponse(
            success=True,
            suggestions=result["suggestions"],
            reasoning=result["reasoning"],
            alternatives=result["alternatives"],
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating profile suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate profile suggestions"
        )


@router.post("/generate-attraction-suggestions", response_model=AttractionSuggestionsResponse)
async def generate_attraction_suggestions(
    request: EnhancedAttractionSuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate REAL Croatian tourism attraction suggestions for hosts.

    Uses curated Croatian tourism data and official source analysis,
    enhanced with AI personalization based on host's interests and location.
    """
    try:
        logger.info(f"🎯 Generating REAL Croatian attractions for {request.city} with interests: {request.interests}")

        onboarding_service = HostOnboardingService(db)

        # Build location info from request
        location_info = {}
        if request.city:
            location_info["city"] = request.city
        if request.address:
            location_info["address"] = request.address
        if request.region:
            location_info["region"] = request.region

        # Generate attractions using REAL Croatian tourism data
        result = await onboarding_service.generate_local_attraction_suggestions(
            host_location=location_info,
            host_interests=request.interests,
            local_knowledge_level=request.knowledge_level
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate attraction suggestions")
            )

        # Log the real data results
        data_source = result.get("data_source", "unknown")
        sources_used = result.get("sources_used", 0)
        personalization_level = result.get("personalization_level", "unknown")

        logger.info(f"✅ Generated {len(result['attractions'])} attractions using {data_source}")
        logger.info(f"📊 Data sources: {sources_used}, Personalization: {personalization_level}")

        # Create enhanced UI components with real data indicators
        ui_components = {
            "hero_section": {
                "component": "HeroSection",
                "props": {
                    "title": f"Real Croatian Attractions in {location_info.get('city', 'Your Area')}",
                    "subtitle": f"Curated from {sources_used} real Croatian tourism sources • Personalized for your expertise",
                    "background_gradient": "from-green-600 via-blue-600 to-purple-800",
                    "data_badge": {
                        "text": f"Real Data • {data_source}",
                        "color": "green" if "real" in data_source else "orange"
                    }
                }
            },
            "attraction_grid": {
                "component": "BentoGrid",
                "props": {
                    "className": "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
                    "items": [
                        {
                            "title": attraction["name"],
                            "description": attraction["description"],
                            "category": attraction.get("category", "experience"),
                            "cost": attraction.get("cost_estimate", "varies"),
                            "authenticity": attraction.get("authenticity_level", "high"),
                            "best_time": attraction.get("best_time", "anytime"),
                            "className": "hover:scale-105 transition-transform",
                            "data_source": attraction.get("data_source", "unknown"),
                            "enhanced": attraction.get("enhanced", False),
                            "relevance_score": attraction.get("relevance_score", 0.5)
                        }
                        for attraction in result["attractions"]
                    ]
                }
            },
            "category_tabs": {
                "component": "Tabs",
                "props": {
                    "tabs": [
                        {
                            "title": category.title(),
                            "value": category,
                            "content": attractions
                        }
                        for category, attractions in result["categories"].items()
                    ]
                }
            },
            "data_summary": {
                "component": "DataSummary",
                "props": {
                    "data_source": data_source,
                    "sources_used": sources_used,
                    "personalization_level": personalization_level,
                    "reasoning": result.get("reasoning", ""),
                    "attraction_count": len(result["attractions"])
                }
            }
        }

        return AttractionSuggestionsResponse(
            success=True,
            attractions=result["attractions"],
            categories=result["categories"],
            reasoning=result["reasoning"],
            ui_components=ui_components,
            metadata={
                "data_source": data_source,
                "sources_used": sources_used,
                "personalization_level": personalization_level,
                "generation_method": "real_croatian_tourism_data"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating real attraction suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate attraction suggestions: {str(e)}"
        )


@router.post("/generate-welcome-messages", response_model=WelcomeMessageResponse)
async def generate_welcome_messages(
    personality_info: Dict[str, Any],
    guest_types: List[str],
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered welcome message suggestions for different guest types.

    Creates warm, authentic welcome messages that reflect Croatian hospitality.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        result = await onboarding_service.generate_welcome_message_suggestions(
            host_personality=personality_info,
            guest_types=guest_types
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to generate welcome messages")
            )

        # Create beautiful UI components
        ui_components = {
            "message_cards": {
                "component": "CardGrid",
                "props": {
                    "cards": [
                        {
                            "title": "Warm & Personal",
                            "description": "Family-like approach with personal touch",
                            "content": result["welcome_messages"]["warm_personal"],
                            "icon": "❤️",
                            "gradient": "from-pink-500 to-rose-500"
                        },
                        {
                            "title": "Professional & Helpful",
                            "description": "Informative yet welcoming style",
                            "content": result["welcome_messages"]["professional_helpful"],
                            "icon": "🤝",
                            "gradient": "from-blue-500 to-indigo-500"
                        },
                        {
                            "title": "Local & Authentic",
                            "description": "Emphasizes Croatian culture and traditions",
                            "content": result["welcome_messages"]["local_authentic"],
                            "icon": "🇭🇷",
                            "gradient": "from-red-500 to-blue-500"
                        }
                    ]
                }
            },
            "tips_section": {
                "component": "FeatureList",
                "props": {
                    "title": "Welcome Message Tips",
                    "items": [
                        {"text": tip, "icon": "💡"}
                        for tip in result["tips"]
                    ]
                }
            }
        }

        return WelcomeMessageResponse(
            success=True,
            welcome_messages=result["welcome_messages"],
            tips=result["tips"],
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating welcome messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate welcome messages"
        )


@router.post("/validate-profile", response_model=ProfileValidationResponse)
async def validate_and_enhance_profile(
    profile_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Validate host profile data and suggest AI-powered enhancements.

    Analyzes profile completeness and authenticity, providing actionable
    suggestions for improvement.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        result = await onboarding_service.validate_and_enhance_profile(profile_data)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile validation failed"
            )

        # Create progress and enhancement UI
        completeness_score = result["completeness_score"]
        ui_components = {
            "progress_section": {
                "component": "ProgressCard",
                "props": {
                    "title": "Profile Completeness",
                    "progress": completeness_score,
                    "color": "green" if completeness_score > 80 else "yellow" if completeness_score > 60 else "red",
                    "description": f"Your profile is {completeness_score:.0f}% complete"
                }
            },
            "enhancement_cards": {
                "component": "EnhancementGrid",
                "props": {
                    "enhancements": [
                        {
                            "category": enhancement["category"],
                            "suggestion": enhancement["suggestion"],
                            "priority": enhancement["priority"],
                            "difficulty": enhancement["implementation"],
                            "icon": "🔧" if enhancement["priority"] == "high" else "💡"
                        }
                        for enhancement in result["enhancements"]
                    ]
                }
            },
            "validation_status": {
                "component": "StatusBanner",
                "props": {
                    "status": "success" if result["validation"]["is_valid"] else "warning",
                    "message": "Profile is ready!" if result["validation"]["is_valid"] else "Some required fields are missing",
                    "missing_fields": result["validation"].get("missing_fields", [])
                }
            }
        }

        return ProfileValidationResponse(
            success=True,
            validation=result["validation"],
            enhancements=result["enhancements"],
            completeness_score=completeness_score,
            ui_components=ui_components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate profile"
        )


@router.get("/onboarding-flow/{step}", response_model=OnboardingStepResponse)
async def get_onboarding_step(
    step: int,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Get specific step in the multi-step onboarding flow with Aceternity UI components.

    Provides structured onboarding experience with beautiful UI components
    for each step of the host registration process.
    """
    try:
        total_steps = 5

        if step < 1 or step > total_steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step. Must be between 1 and {total_steps}"
            )

        # Define onboarding steps with Aceternity UI components
        steps = {
            1: {
                "step_name": "Welcome & Introduction",
                "content": {
                    "title": "Welcome to Croatian Tourism Hosting",
                    "description": "Join the community of authentic Croatian hosts and create unforgettable experiences for your guests.",
                    "benefits": [
                        "AI-powered profile creation",
                        "Local attraction recommendations",
                        "Guest management tools",
                        "Croatian hospitality expertise"
                    ]
                },
                "ui_components": {
                    "hero": {
                        "component": "HeroSection",
                        "props": {
                            "title": "Transform Your Croatian Property into an Experience",
                            "subtitle": "Join hosts across Croatia who are creating authentic local experiences",
                            "cta_primary": "Start Your Journey",
                            "cta_secondary": "Learn More",
                            "background_image": "/images/croatian-coast.jpg",
                            "overlay_gradient": "from-blue-900/70 to-transparent"
                        }
                    },
                    "features": {
                        "component": "FeatureGrid",
                        "props": {
                            "features": [
                                {
                                    "icon": "🤖",
                                    "title": "AI-Powered Setup",
                                    "description": "Let AI help create your authentic host profile"
                                },
                                {
                                    "icon": "🏖️",
                                    "title": "Local Expertise",
                                    "description": "Showcase your unique Croatian knowledge"
                                },
                                {
                                    "icon": "👥",
                                    "title": "Guest Management",
                                    "description": "Tools to create memorable experiences"
                                }
                            ]
                        }
                    }
                }
            },
            2: {
                "step_name": "Basic Information",
                "content": {
                    "title": "Tell Us About Your Property",
                    "description": "Help us understand your location and accommodation type.",
                    "form_fields": [
                        {"name": "city", "label": "City", "type": "text", "required": True},
                        {"name": "address", "label": "Property Address", "type": "textarea", "required": True},
                        {"name": "business_type", "label": "Accommodation Type", "type": "select", "options": ["apartment", "villa", "house", "room"]},
                        {"name": "max_group_size", "label": "Maximum Guests", "type": "number", "min": 1, "max": 20}
                    ]
                },
                "ui_components": {
                    "form": {
                        "component": "OnboardingForm",
                        "props": {
                            "step": 2,
                            "title": "Property Details",
                            "description": "Let's start with the basics about your Croatian property",
                            "fields": [
                                {
                                    "name": "city",
                                    "label": "City",
                                    "type": "text",
                                    "placeholder": "e.g., Lovran, Split, Dubrovnik",
                                    "required": True,
                                    "icon": "🏙️"
                                },
                                {
                                    "name": "address",
                                    "label": "Property Address",
                                    "type": "textarea",
                                    "placeholder": "Full address of your property",
                                    "required": True,
                                    "icon": "📍"
                                },
                                {
                                    "name": "business_type",
                                    "label": "Accommodation Type",
                                    "type": "select",
                                    "options": [
                                        {"value": "apartment", "label": "Apartment"},
                                        {"value": "villa", "label": "Villa"},
                                        {"value": "house", "label": "House"},
                                        {"value": "room", "label": "Private Room"}
                                    ],
                                    "icon": "🏠"
                                }
                            ],
                            "progress": 40
                        }
                    }
                }
            },
            3: {
                "step_name": "AI Profile Generation",
                "content": {
                    "title": "Create Your Authentic Profile",
                    "description": "Let our AI help you create a compelling host profile that showcases your Croatian hospitality.",
                    "ai_features": [
                        "Authentic business descriptions",
                        "Warm welcome messages",
                        "Local specialty highlights",
                        "Personal host stories"
                    ]
                },
                "ui_components": {
                    "ai_generator": {
                        "component": "AIProfileGenerator",
                        "props": {
                            "title": "AI-Powered Profile Creation",
                            "description": "Answer a few questions and watch AI create your authentic Croatian host profile",
                            "steps": [
                                {
                                    "title": "Personality & Style",
                                    "questions": [
                                        "What's your hosting style?",
                                        "What makes your location special?",
                                        "What are your local interests?"
                                    ]
                                },
                                {
                                    "title": "Generate Profile",
                                    "description": "AI creates multiple profile options"
                                },
                                {
                                    "title": "Review & Customize",
                                    "description": "Choose and personalize your favorite"
                                }
                            ]
                        }
                    }
                }
            },
            4: {
                "step_name": "Local Attractions",
                "content": {
                    "title": "Share Your Local Knowledge",
                    "description": "Help guests discover the best of your area with AI-suggested attractions and your personal insights.",
                    "categories": ["Hidden Gems", "Local Favorites", "Cultural Sites", "Natural Beauty", "Food & Drink"]
                },
                "ui_components": {
                    "attraction_builder": {
                        "component": "AttractionBuilder",
                        "props": {
                            "title": "Build Your Local Guide",
                            "description": "AI will suggest attractions, you add your personal touch",
                            "features": [
                                {
                                    "icon": "🔍",
                                    "title": "AI Discovery",
                                    "description": "Find hidden gems and local favorites"
                                },
                                {
                                    "icon": "📝",
                                    "title": "Personal Stories",
                                    "description": "Add your insider knowledge and tips"
                                },
                                {
                                    "icon": "📸",
                                    "title": "Visual Appeal",
                                    "description": "Upload photos and create visual guides"
                                }
                            ]
                        }
                    }
                }
            },
            5: {
                "step_name": "Review & Launch",
                "content": {
                    "title": "You're Ready to Host!",
                    "description": "Review your profile and start welcoming guests to authentic Croatian experiences.",
                    "next_steps": [
                        "Review your complete profile",
                        "Set up your first guest group",
                        "Start creating memorable experiences"
                    ]
                },
                "ui_components": {
                    "launch_ready": {
                        "component": "LaunchSection",
                        "props": {
                            "title": "🎉 Your Croatian Host Profile is Ready!",
                            "subtitle": "Join the community of authentic Croatian hosts",
                            "cta_primary": "Launch My Profile",
                            "cta_secondary": "Make Changes",
                            "celebration_animation": True,
                            "stats": [
                                {"label": "Profile Completeness", "value": "95%"},
                                {"label": "Local Attractions", "value": "12"},
                                {"label": "Ready to Host", "value": "✓"}
                            ]
                        }
                    }
                }
            }
        }

        step_data = steps.get(step)
        if not step_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Step not found"
            )

        return OnboardingStepResponse(
            step=step,
            total_steps=total_steps,
            step_name=step_data["step_name"],
            content=step_data["content"],
            ui_components=step_data["ui_components"],
            next_step_available=step < total_steps
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting onboarding step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get onboarding step"
        )


@router.post("/edit-suggestion")
async def edit_profile_suggestion(
    edit_request: EditSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Edit or improve a profile suggestion with optional AI collaboration.

    Allows hosts to edit AI suggestions and optionally get AI help to improve their edits.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        if edit_request.is_collaborative and edit_request.collaboration_prompt:
            # Use AI to help improve the user's edit
            collaboration_context = {
                "original_suggestion": edit_request.original_text,
                "user_edit": edit_request.user_edit,
                "category": edit_request.category,
                "collaboration_request": edit_request.collaboration_prompt
            }

            messages = [
                {
                    "role": "system",
                    "content": "You are helping a Croatian host improve their profile content. The user has edited an AI suggestion and wants your help to make it even better while preserving their personal voice and intent."
                },
                {
                    "role": "user",
                    "content": f"""
Original AI suggestion: "{edit_request.original_text}"

User's edit: "{edit_request.user_edit}"

User's request: "{edit_request.collaboration_prompt}"

Please help improve the user's edit while:
1. Preserving their personal voice and intent
2. Maintaining authentic Croatian hospitality tone
3. Keeping it natural and genuine
4. Making it more compelling for guests

Return only the improved version, no additional text.
"""
                }
            ]

            ai_response = await onboarding_service.ai_service.generate_chat_response(
                host_id="onboarding",
                messages=messages,
                context=collaboration_context
            )

            if ai_response.get("success"):
                improved_text = ai_response.get("response", "").strip()
                return {
                    "success": True,
                    "original": edit_request.original_text,
                    "user_edit": edit_request.user_edit,
                    "ai_improved": improved_text,
                    "final_suggestion": improved_text,
                    "collaboration_used": True
                }

        # No collaboration requested, just return the user's edit
        return {
            "success": True,
            "original": edit_request.original_text,
            "user_edit": edit_request.user_edit,
            "final_suggestion": edit_request.user_edit,
            "collaboration_used": False
        }

    except Exception as e:
        logger.error(f"Error editing suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit suggestion"
        )


@router.post("/co-write")
async def co_write_content(
    cowrite_request: CoWriteRequest,
    db: AsyncSession = Depends(get_db),
    current_host: Optional[Host] = Depends(get_current_host_optional)
):
    """
    Co-write content with AI assistance.

    Helps hosts create content from scratch or expand their initial ideas with AI collaboration.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Build context for co-writing
        context = {
            "category": cowrite_request.category,
            "style": cowrite_request.style_preference,
            "user_input": cowrite_request.user_input,
            "additional_context": cowrite_request.context
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are co-writing {cowrite_request.category} content with a Croatian host. Your role is to help them expand and improve their ideas while maintaining their authentic voice.

Style: {cowrite_request.style_preference}
Focus: Croatian hospitality, authenticity, local knowledge

Guidelines:
- Build upon the user's input, don't replace it
- Maintain their personal voice and perspective
- Add Croatian cultural elements naturally
- Keep it genuine and warm
- Make it compelling for guests"""
            },
            {
                "role": "user",
                "content": f"""I want to write {cowrite_request.category} content. Here's what I have so far:

"{cowrite_request.user_input}"

Please help me expand this into a complete, compelling piece that maintains my voice but makes it more engaging for potential guests. Keep the authentic Croatian hospitality feel.

Return only the improved content, no additional text."""
            }
        ]

        ai_response = await onboarding_service.ai_service.generate_chat_response(
            host_id="onboarding",
            messages=messages,
            context=context
        )

        if ai_response.get("success"):
            co_written_content = ai_response.get("response", "").strip()
            return {
                "success": True,
                "user_input": cowrite_request.user_input,
                "co_written_content": co_written_content,
                "category": cowrite_request.category,
                "style_used": cowrite_request.style_preference
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI co-writing failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in co-writing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to co-write content"
        )


@router.get("/google-places/{place_name}", response_model=GooglePlacesResponse)
async def get_google_places_info_endpoint(
    place_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get location details from Google Places API.

    Provides rich location information to enhance host profiles and local recommendations.
    """
    return await get_google_places_info(place_name)


@router.get("/google-places/nearby")
async def get_nearby_google_places_endpoint(
    lat: float,
    lng: float,
    radius: int = 5000,
    place_type: str = "tourist_attraction",
    db: AsyncSession = Depends(get_db)
):
    """
    Get nearby attractions from Google Places API.

    Enhances host onboarding with real Google Places data for authentic local recommendations.
    """
    return await get_nearby_google_places(lat, lng, radius, place_type)


@router.post("/analyze-location", response_model=Dict[str, Any])
async def analyze_location_potential(
    request: EnhancedAttractionSuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze location potential using Croatian tourism hosting best practices.

    Provides comprehensive analysis of a location's tourism potential,
    including market analysis, competitive landscape, and recommendations.
    """
    try:
        onboarding_service = HostOnboardingService(db)

        # Enhanced analysis with multiple data sources
        analysis_results = {
            "location_analysis": {
                "city": request.city,
                "region": request.region.value if request.region else None,
                "coordinates": request.coordinates.model_dump() if request.coordinates else None,
                "local_experience_score": calculate_experience_score(request.local_experience),
                "knowledge_level": request.knowledge_level.value
            },
            "market_potential": {
                "guest_alignment": analyze_guest_alignment(request.preferred_guests),
                "interest_diversity": len(request.interests),
                "location_story_quality": analyze_story_quality(request.location_story),
                "authenticity_indicators": extract_authenticity_indicators(request.location_story)
            },
            "recommendations": {
                "suggested_improvements": generate_improvement_suggestions(request),
                "marketing_angles": identify_marketing_angles(request),
                "competitive_advantages": identify_competitive_advantages(request)
            },
            "metadata": {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "data_sources": ["user_input", "ai_analysis", "tourism_guidelines"],
                "confidence_score": calculate_confidence_score(request)
            }
        }

        return {
            "success": True,
            "analysis": analysis_results,
            "insights": generate_actionable_insights(analysis_results),
            "next_steps": suggest_next_steps(analysis_results)
        }

    except Exception as e:
        logger.error(f"Location analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze location potential"
        )


# Helper functions removed - now imported from host_onboarding_helpers module


@router.post("/complete-onboarding", response_model=Dict[str, Any])
async def complete_host_onboarding(
    onboarding_data: EnhancedAttractionSuggestionsRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete host onboarding and save all data to database.

    SIMPLIFIED VERSION: Uses conservative database operations.
    Only updates the hosts table which we know works.
    """
    try:
        logger.info(f"Completing onboarding for host: {current_host.email}")

        # Generate unique access code for guests
        import secrets
        import string
        access_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

        # Update main host record
        from sqlalchemy import update, select
        from app.models.host import HostProfile

        host_update = update(Host).where(Host.id == current_host.id).values(
            city=onboarding_data.city,
            address=onboarding_data.address or current_host.address,
            latitude=onboarding_data.coordinates.lat if onboarding_data.coordinates else current_host.latitude,
            longitude=onboarding_data.coordinates.lng if onboarding_data.coordinates else current_host.longitude,
            local_specialties=onboarding_data.interests,
            guest_access_code=access_code,
            onboarding_completed=True,
            updated_at=datetime.utcnow()
        )

        await db.execute(host_update)

        # Create or update HostProfile with detailed onboarding data
        profile_query = select(HostProfile).where(HostProfile.host_id == current_host.id)
        result = await db.execute(profile_query)
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            # Update existing profile
            profile_update = update(HostProfile).where(HostProfile.host_id == current_host.id).values(
                city=onboarding_data.city,
                county=onboarding_data.region.value if onboarding_data.region else None,
                address=onboarding_data.address or None,
                latitude=onboarding_data.coordinates.lat if onboarding_data.coordinates else None,
                longitude=onboarding_data.coordinates.lng if onboarding_data.coordinates else None,
                expertise_areas=onboarding_data.interests,
                typical_guest_profile={
                    "preferred_guests": onboarding_data.preferred_guests,
                    "local_experience": onboarding_data.local_experience.value if onboarding_data.local_experience else None,
                    "knowledge_level": onboarding_data.knowledge_level.value
                },
                location_story=onboarding_data.location_story,
                google_verified=bool(onboarding_data.coordinates),
                onboarding_completed=True,
                onboarding_completed_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow()
            )
            await db.execute(profile_update)
        else:
            # Create new profile
            new_profile = HostProfile(
                host_id=current_host.id,
                city=onboarding_data.city,
                county=onboarding_data.region.value if onboarding_data.region else None,
                address=onboarding_data.address or None,
                latitude=onboarding_data.coordinates.lat if onboarding_data.coordinates else None,
                longitude=onboarding_data.coordinates.lng if onboarding_data.coordinates else None,
                expertise_areas=onboarding_data.interests,
                typical_guest_profile={
                    "preferred_guests": onboarding_data.preferred_guests,
                    "local_experience": onboarding_data.local_experience.value if onboarding_data.local_experience else None,
                    "knowledge_level": onboarding_data.knowledge_level.value
                },
                location_story=onboarding_data.location_story,
                google_verified=bool(onboarding_data.coordinates),
                onboarding_completed=True,
                onboarding_completed_at=datetime.utcnow().isoformat(),
                ai_generated_content=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_profile)

        await db.commit()

        logger.info(f"Onboarding completed successfully for host: {current_host.email}")

        return {
            "success": True,
            "message": "Onboarding completed successfully",
            "host_id": str(current_host.id),
            "guest_access_code": access_code,
            "attractions_generated": 0,  # Simplified for now
            "profile_updated": True,
            "guest_access_url": f"/guest/{access_code}",
            "next_steps": [
                "Share your access code with guests",
                "Test guest access with the provided code",
                "Your data is now stored in the database"
            ]
        }

    except Exception as e:
        logger.error(f"Onboarding completion error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.get("/guest-access/{access_code}", response_model=Dict[str, Any])
async def get_host_offerings_for_guest(
    access_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get host offerings and recommendations for guests using access code.

    This is the main endpoint guests use to see what their host recommends.
    """
    try:
        # Find host by access code
        from sqlalchemy import select

        host_query = select(Host).where(Host.guest_access_code == access_code.upper())
        result = await db.execute(host_query)
        host = result.scalar_one_or_none()

        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid access code"
            )

        # Get host profile
        from app.models.host import HostProfile
        profile_query = select(HostProfile).where(HostProfile.host_id == host.id)
        profile_result = await db.execute(profile_query)
        profile = profile_result.scalar_one_or_none()

        from app.services.host_offerings_for_guest import build_host_offerings_payload

        host_offerings = build_host_offerings_payload(host, profile, access_code)

        return {
            "success": True,
            "host_offerings": host_offerings,
            "access_code": access_code,
            "valid_access": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Guest access error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve host offerings"
        )


# AIEnhancementResponse model is imported from host_onboarding_models module

# AI Enhancement endpoint for accommodation descriptions
@router.post("/accommodation/ai-enhance", response_model=AIEnhancementResponse)
async def enhance_accommodation_description(
    request: Dict[str, Any],
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhance accommodation description using AI with existing property data.

    Args:
        request: Dict containing current accommodation details for enhancement
        current_host: Current authenticated host
        db: Database session

    Returns:
        Dict[str, Any]: Enhanced description and suggestions based on existing data
    """
    try:
        logger.info(f"🎯 Enhancing accommodation description with AI for host {current_host.id}")

        # Extract current accommodation data from request
        current_data = request.get("current_data", {})
        enhancement_type = request.get("enhancement_type", "description")  # description, amenities, services, etc.

        if not current_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current accommodation data is required for AI enhancement"
            )

        # Get host profile for additional context
        onboarding_service = HostOnboardingService(db)
        host_profile = await onboarding_service.get_host_profile(current_host.id)

        if not host_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host profile not found"
            )

        # Extract key data for AI enhancement
        property_name = current_data.get("property_name", "")
        property_type = current_data.get("property_type", "")
        current_description = current_data.get("location_story", "")
        max_guests = current_data.get("max_guests", 0)
        number_of_rooms = current_data.get("number_of_rooms", 0)
        current_amenities = current_data.get("amenities", [])
        current_services = current_data.get("services_offered", [])
        current_specialties = current_data.get("expertise_areas", [])
        city = current_data.get("city", "")
        county = current_data.get("county", "")

        # Create context-aware enhancement prompt
        enhancement_prompt = f"""
        You are an AI travel expert specializing in Croatian tourism and accommodation enhancement.
        Your task is to ENHANCE the existing accommodation data, not replace it with generic content.

        CURRENT ACCOMMODATION DATA:
        - Property Name: {property_name}
        - Property Type: {property_type}
        - Current Description: {current_description or 'No description provided yet'}
        - Max Guests: {max_guests}
        - Number of Rooms: {number_of_rooms}
        - Current Amenities: {', '.join(current_amenities) if current_amenities else 'None specified'}
        - Current Services: {', '.join(current_services) if current_services else 'None specified'}
        - Current Specialties: {', '.join(current_specialties) if current_specialties else 'None specified'}
        - Location: {city}, {county}, Croatia

        HOST CONTEXT:
        - Host Location: {host_profile.city or city}, Croatia
        - Local Knowledge: {host_profile.local_knowledge_level or 'intermediate'}
        - Host Interests: {', '.join(host_profile.host_interests or [])}

        ENHANCEMENT REQUIREMENTS:
        1. BUILD UPON existing data - don't replace with generic content
        2. If description exists, enhance it with more detail and local context
        3. If description is missing, create one that matches the property type and location
        4. Suggest additional amenities/services that would complement existing ones
        5. Enhance specialties based on location and property type
        6. Use authentic Croatian/local language and cultural references
        7. Include practical information for guests (transport, local attractions, etc.)
        8. Keep the host's authentic voice and local knowledge

        ENHANCEMENT TYPE: {enhancement_type}

        Please provide enhanced content that builds upon what already exists.
        """

        # Create structured response schema for AI
        from pydantic import BaseModel, Field
        from typing import List

        class AccommodationEnhancementSchema(BaseModel):
            """Schema for structured accommodation enhancement response."""
            enhanced_description: str = Field(..., description="Enhanced property description with local context")
            suggested_amenities: List[str] = Field(..., description="List of suggested amenities to add")
            suggested_services: List[str] = Field(..., description="List of suggested services to offer")
            enhanced_specialties: List[str] = Field(..., description="List of enhanced local specialties")
            welcome_message: str = Field(..., description="Enhanced welcome message in Croatian hospitality style")

        # Use AI service to generate structured enhancement
        ai_response = await onboarding_service.ai_service.generate_structured_response(
            host_id=str(current_host.id),
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI travel expert specializing in Croatian tourism and accommodation enhancement. You must return a structured response with the exact fields specified."
                },
                {
                    "role": "user",
                    "content": enhancement_prompt
                }
            ],
            context={
                "location": f"{city}, {county}, Croatia",
                "property_type": property_type,
                "host_location": f"{host_profile.city or city}, Croatia"
            },
            response_schema=AccommodationEnhancementSchema
        )

        if not ai_response or not ai_response.get("success", False):
            # Fallback to simple enhancement
            enhanced_description = current_description or f"Experience authentic Croatian hospitality in this charming {property_type} in {city}, {county}. Perfect for up to {max_guests} guests seeking an authentic local experience with modern comforts."

            # Suggest additional amenities based on property type
            suggested_amenities = []
            if property_type == "apartment":
                suggested_amenities = ["air_conditioning", "wifi", "kitchen", "balcony", "parking"]
            elif property_type == "villa":
                suggested_amenities = ["air_conditioning", "wifi", "kitchen", "garden", "parking", "bbq", "outdoor_seating"]
            elif property_type == "house":
                suggested_amenities = ["air_conditioning", "wifi", "kitchen", "garden", "parking", "fireplace"]

            # Filter out amenities that already exist
            new_amenities = [amenity for amenity in suggested_amenities if amenity not in current_amenities]

            # Create fallback structured response
            enhanced_data = {
                "enhanced_description": enhanced_description,
                "suggested_amenities": new_amenities,
                "suggested_services": ["guided_tours", "airport_transfer", "cleaning_service"],
                "enhanced_specialties": ["Local Culture", "Gastronomy", "Nature Exploration", "Family Activities"],
                "welcome_message": f"Dobro došli! Welcome to your Croatian home away from home in {city}. We're excited to share the beauty and culture of {county} with you."
            }

        # Parse structured AI response
        try:
            if ai_response.get("success", False) and ai_response.get("structured_data"):
                # Use the structured data directly
                enhanced_data = ai_response["structured_data"]
                logger.info(f"✅ AI structured response successful: {list(enhanced_data.keys())}")
            else:
                # AI service failed or returned unstructured data, use fallback
                logger.warning(f"AI service returned: {ai_response}")
                enhanced_data = {}
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
            enhanced_data = {}

        # Prepare structured response with enhanced content
        response = AIEnhancementResponse(
            success=True,
            enhancement_type=enhancement_type,
            enhanced_content={
                "description": enhanced_data.get("enhanced_description", current_description),
                "amenities": enhanced_data.get("suggested_amenities", []),
                "services": enhanced_data.get("suggested_services", []),
                "specialties": enhanced_data.get("enhanced_specialties", []),
                "welcome_message": enhanced_data.get("welcome_message", "")
            },
            original_data={
                "description": current_description,
                "amenities": current_amenities,
                "services": current_services,
                "specialties": current_specialties
            },
            metadata={
                "host_id": current_host.id,
                "property_name": property_name,
                "property_type": property_type,
                "location": f"{city}, {county}, Croatia",
                "ai_provider": ai_response.get("provider", "unknown") if ai_response else "fallback",
                "enhancement_timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"✅ Successfully enhanced accommodation for host {current_host.id} with structured response")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Accommodation AI enhancement error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enhance accommodation description"
        )


@router.post("/guest-message/{access_code}", response_model=Dict[str, Any])
async def send_message_to_host(
    access_code: str,
    message_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Allow guests to send messages to their host or AI assistant.

    Enables guest-host communication and AI-powered assistance.
    """
    try:
        # Find host by access code
        from sqlalchemy import select

        host_query = select(Host).where(Host.guest_access_code == access_code.upper())
        result = await db.execute(host_query)
        host = result.scalar_one_or_none()

        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid access code"
            )

        message_text = message_data.get("message", "")
        message_type = message_data.get("type", "general")  # general, question, request
        guest_name = message_data.get("guest_name", "Guest")

        # For now, we'll use AI to provide immediate responses
        # Later, this can be enhanced with real host messaging

        if message_type == "question" or "recommend" in message_text.lower():
            # Use AI to provide recommendations
            onboarding_service = HostOnboardingService(db)

            # Get host profile for context
            from app.models.host import HostProfile
            profile_query = select(HostProfile).where(HostProfile.host_id == host.id)
            profile_result = await db.execute(profile_query)
            profile = profile_result.scalar_one_or_none()

            # Generate AI response based on host's knowledge
            ai_context = {
                "host_name": f"{host.first_name} {host.last_name}",
                "location": host.city,
                "specialties": host.local_specialties,
                "attractions": host.local_tips or [],
                "guest_message": message_text,
                "guest_name": guest_name
            }

            # Simple AI response (can be enhanced with actual AI service)
            ai_response = f"Hi {guest_name}! As {host.first_name}'s AI assistant, I'd be happy to help. Based on your question about {host.city}, I recommend checking out our local specialties: {', '.join(host.local_specialties[:3])}. Would you like specific recommendations for activities, restaurants, or hidden gems?"

            response = {
                "success": True,
                "response_type": "ai_assistant",
                "message": ai_response,
                "suggestions": [
                    "Tell me about local restaurants",
                    "What are the best beaches nearby?",
                    "Recommend activities for families",
                    "Show me hidden local gems"
                ],
                "can_contact_host": True,
                "response_time": "Immediate (AI) • Host usually responds within 2 hours"
            }
        else:
            # General message - queue for host
            response = {
                "success": True,
                "response_type": "queued_for_host",
                "message": f"Thanks {guest_name}! Your message has been sent to {host.first_name}. They typically respond within 2 hours. In the meantime, feel free to ask me any questions about {host.city}!",
                "estimated_response_time": "Within 2 hours",
                "ai_available": True
            }

        # Log the interaction (in a real system, save to messages table)
        logger.info(f"Guest message via {access_code}: {message_text[:50]}...")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Guest message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.get("/progress/{host_id}")
async def get_onboarding_progress(
    host_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get onboarding progress for a host.

    Args:
        host_id: Host ID
        db: Database session

    Returns:
        Onboarding progress data
    """
    try:
        analytics_service = OnboardingAnalyticsService(db)
        progress = await analytics_service.get_onboarding_progress(uuid.UUID(host_id))
        return progress

    except Exception as e:
        logger.error(f"Error getting onboarding progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get progress: {str(e)}"
        )


@router.post("/track-step")
async def track_onboarding_step(
    step_data: Dict[str, Any],
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Track an onboarding step completion.

    Args:
        step_data: Step tracking data
        current_host: Current authenticated host
        db: Database session

    Returns:
        Success status
    """
    try:
        analytics_service = OnboardingAnalyticsService(db)

        success = await analytics_service.track_onboarding_step(
            host_id=current_host.id,
            step_name=step_data.get("step_name"),
            step_data=step_data.get("data")
        )

        if success:
            return {"success": True, "message": "Step tracked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track step"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track step: {str(e)}"
        )


@router.get("/analytics")
async def get_onboarding_analytics(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall onboarding analytics.

    Args:
        period_days: Number of days to analyze
        db: Database session

    Returns:
        Analytics data
    """
    try:
        analytics_service = OnboardingAnalyticsService(db)
        analytics = await analytics_service.get_onboarding_analytics(period_days)
        return analytics

    except Exception as e:
        logger.error(f"Error getting onboarding analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.get("/success-metrics/{host_id}")
async def get_success_metrics(
    host_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get success metrics for a host's onboarding.

    Args:
        host_id: Host ID
        db: Database session

    Returns:
        Success metrics
    """
    try:
        analytics_service = OnboardingAnalyticsService(db)
        metrics = await analytics_service.get_success_metrics(uuid.UUID(host_id))
        return metrics

    except Exception as e:
        logger.error(f"Error getting success metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )
