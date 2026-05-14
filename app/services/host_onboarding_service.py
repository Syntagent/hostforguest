"""
AI-powered host onboarding service for Croatian tourism hosts.

Helps hosts create authentic profiles, local stories, and attraction recommendations
using AI assistance while maintaining their personal touch and local expertise.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models import Host, HostCreate, HostResponse, Attraction, AttractionCreate
from app.services.ai_service_fallback import AIServiceWithFallback
from app.services.host_service import HostService
from app.services.attraction_service import AttractionService
from pydantic import BaseModel, Field
from typing import List

logger = logging.getLogger(__name__)


class AIProfileSuggestions(BaseModel):
    """Pydantic model for AI-generated profile suggestions."""
    business_description: List[str] = Field(..., description="Business description suggestions")
    welcome_message: List[str] = Field(..., description="Welcome message suggestions")
    local_specialties: List[str] = Field(..., description="Local specialties and experiences")
    host_story: List[str] = Field(..., description="Personal host story suggestions")
    experience_promise: List[str] = Field(..., description="Guest experience promises")


class EditableProfileSuggestion(BaseModel):
    """Editable profile suggestion with user modifications."""
    original: str = Field(..., description="Original AI suggestion")
    edited: Optional[str] = Field(None, description="User-edited version")
    is_selected: bool = Field(False, description="Whether this suggestion is selected")
    user_notes: Optional[str] = Field(None, description="User notes or modifications")


class HostOnboardingService:
    """
    AI-powered service for host onboarding and profile generation.
    
    Helps Croatian tourism hosts create authentic profiles with AI assistance
    while preserving their personal knowledge and local expertise.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        from app.services.settings_service import SettingsService
        settings_service = SettingsService(db)
        self.ai_service = AIServiceWithFallback(settings_service)
        self.host_service = HostService(db)
        self.attraction_service = AttractionService(db)

    async def generate_host_profile_suggestions(
        self, 
        basic_info: Dict[str, Any],
        ai_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered suggestions for host profile creation.
        
        Args:
            basic_info: Basic host information (location, property type, etc.)
            ai_preferences: AI generation preferences and style
            
        Returns:
            Dict with AI-generated profile suggestions
        """
        try:
            # Build comprehensive context for AI generation using ALL personal data
            context = {
                "location": {
                    "city": basic_info.get("city", ""),
                    "address": basic_info.get("address", ""),
                    "region": basic_info.get("region", ""),
                    "country": "Croatia"
                },
                "property": {
                    "type": basic_info.get("business_type", "apartment"),
                    "capacity": basic_info.get("max_group_size", 4),
                    "amenities": basic_info.get("amenities", [])
                },
                "host": {
                    "first_name": basic_info.get("first_name", ""),
                    "last_name": basic_info.get("last_name", ""),
                    "full_name": f"{basic_info.get('first_name', '')} {basic_info.get('last_name', '')}".strip(),
                    "languages": basic_info.get("languages", ["hr", "en"]),
                    "experience_years": basic_info.get("hosting_experience", 0),
                    "interests": basic_info.get("interests", []),
                    "specialties": basic_info.get("specialties", []),
                    "local_experience": basic_info.get("local_experience", ""),
                    "preferred_guests": basic_info.get("preferred_guests", []),
                    "location_story": basic_info.get("location_story", ""),
                    "property_name": basic_info.get("business_name", "")
                },
                "personal_context": {
                    "has_personal_story": bool(basic_info.get("location_story", "").strip()),
                    "story_length": len(basic_info.get("location_story", "").split()),
                    "expertise_areas": len(basic_info.get("specialties", [])),
                    "guest_focus": len(basic_info.get("preferred_guests", []))
                }
            }
            
            # Generate AI suggestions using our AI service
            messages = [
                {
                    "role": "system",
                    "content": self._build_profile_generation_prompt(context)
                },
                {
                    "role": "user", 
                    "content": f"""Hi, I'm {context['host']['full_name'] or 'a Croatian host'} and I need help creating an authentic profile for my {context['host']['property_name'] or context['property']['type']} in {context['location']['city']}, Croatia. 

My personal details:
- My name is {context['host']['full_name'] or 'not provided'}
- I have {context['host']['local_experience']} experience in this area
- My personal story: "{context['host']['location_story']}"
- My specialties: {', '.join(context['host']['specialties']) if context['host']['specialties'] else 'local knowledge'}
- I prefer hosting: {', '.join(context['host']['preferred_guests']) if context['host']['preferred_guests'] else 'all types of guests'}

Please create suggestions that reflect MY actual name, experience and story, not generic content. Use my real name ({context['host']['first_name'] or 'my name'}) in the suggestions and make it personal and authentic based on what I've shared about myself."""
                }
            ]
            
            # Use enhanced structured response with robust fallback handling
            ai_response = await self.ai_service.generate_structured_response(
                host_id="onboarding",  # Special ID for onboarding
                messages=messages,
                context=context,
                response_schema=AIProfileSuggestions,  # Use Pydantic model for structure
                use_reasoning=False  # Use fast model for better performance
            )
            
            if ai_response.get("success"):
                # Get structured data from the enhanced response
                suggestions = ai_response.get("structured_data", {})
                provider_used = ai_response.get("provider", "unknown")
                logger.info(f"✅ AI Profile Generation successful using {provider_used}")
                
                return {
                    "success": True,
                    "suggestions": suggestions,
                    "reasoning": f"AI-generated profile suggestions using {provider_used}",
                    "alternatives": self._generate_profile_alternatives(context),
                    "provider": provider_used,
                    "model": ai_response.get("model", "unknown")
                }
            else:
                logger.error(f"AI structured generation failed: {ai_response}")
                # Fallback to manual parsing approach
                logger.info("Attempting fallback to regular chat response with manual parsing")
                
                fallback_response = await self.ai_service.generate_chat_response(
                    host_id="onboarding",
                    messages=messages,
                    context=context,
                    use_reasoning=False
                )
                
                if fallback_response.get("success"):
                    raw_response = fallback_response.get("response", "")
                    suggestions = self._parse_profile_suggestions_DEPRECATED(raw_response, context)
                    logger.info("✅ Fallback manual parsing successful")
                    
                    return {
                        "success": True,
                        "suggestions": suggestions,
                        "reasoning": "AI-generated profile suggestions using fallback parsing",
                        "alternatives": self._generate_profile_alternatives(context),
                        "provider": "fallback_parsing",
                        "model": fallback_response.get("model", "unknown")
                    }
                
                return {"success": False, "error": "All AI generation methods failed"}
                
        except Exception as e:
            logger.error(f"Error generating host profile suggestions: {e}")
            return {"success": False, "error": str(e)}

    async def generate_local_attraction_suggestions(
        self,
        host_location: Dict[str, str],
        host_interests: List[str],
        local_knowledge_level: str = "expert"
    ) -> Dict[str, Any]:
        """
        Generate personalized local attraction suggestions using REAL Croatian tourism data.
        
        Args:
            host_location: Host's location information
            host_interests: Host's personal interests and expertise areas
            local_knowledge_level: Level of local knowledge (beginner/intermediate/expert)
            
        Returns:
            Dict with real, personalized attraction suggestions
        """
        try:
            logger.info(f"Generating real Croatian tourism attractions for {host_location.get('city', 'Croatia')}")
            
            # 1. Get REAL Croatian tourism data from Crawl4AI
            from app.services.crawl4ai_scraper_service import Crawl4AIScraperService
            
            # Use Crawl4AI to scrape real-time Croatian tourism data
            async with Crawl4AIScraperService(self.db, self.ai_service) as scraper:
                real_tourism_data = await scraper.get_real_time_updates(
                    city=host_location.get('city'),
                    content_types=['attractions', 'events', 'local_experiences', 'culinary']
                )
            
            logger.info(f"Retrieved {len(real_tourism_data)} real tourism updates from Crawl4AI")
            
            # 2. Convert real data to attraction format
            real_attractions = await self._convert_tourism_data_to_attractions(
                real_tourism_data, host_location, host_interests
            )
            
            # 3. Enhance with AI personalization based on host's interests and knowledge
            personalized_attractions = await self._enhance_attractions_with_host_context(
                real_attractions, host_interests, local_knowledge_level, host_location
            )
            
            # 4. Add host-specific local knowledge if available
            enhanced_attractions = await self._add_host_local_knowledge(
                personalized_attractions, host_location, host_interests
            )
            
            # 5. Ensure we have enough attractions (fallback if needed)
            final_attractions = self._ensure_minimum_attractions(enhanced_attractions, host_location)
            
            logger.info(f"Generated {len(final_attractions)} personalized attractions using real Croatian data")
            
            return {
                "success": True,
                "attractions": final_attractions,
                "categories": self._categorize_attractions(final_attractions),
                "reasoning": f"Generated using real Croatian tourism data from {len(real_tourism_data)} sources, personalized for {host_location.get('city', 'Croatia')}",
                "data_source": "real_croatian_tourism_data",
                "sources_used": len(real_tourism_data),
                "personalization_level": local_knowledge_level
            }
                
        except Exception as e:
            logger.error(f"Error generating real attraction suggestions: {e}")
            # Return enhanced fallback with real Croatian content
            fallback_attractions = await self._get_enhanced_croatian_fallback(host_location, host_interests)
            
            return {
                "success": True,
                "attractions": fallback_attractions,
                "categories": self._categorize_attractions(fallback_attractions),
                "reasoning": f"Using enhanced Croatian fallback data due to processing issue: {str(e)}",
                "data_source": "enhanced_croatian_fallback"
            }

    async def generate_welcome_message_suggestions(
        self,
        host_personality: Dict[str, Any],
        guest_types: List[str]
    ) -> Dict[str, Any]:
        """
        Generate personalized welcome message suggestions for different guest types.
        
        Args:
            host_personality: Host's personality traits and communication style
            guest_types: Types of guests they typically host
            
        Returns:
            Dict with welcome message suggestions
        """
        try:
            context = {
                "personality": host_personality,
                "guest_types": guest_types,
                "language_style": "warm_and_authentic",
                "cultural_context": "croatian_hospitality"
            }
            
            messages = [
                {
                    "role": "system",
                    "content": self._build_welcome_message_prompt(context)
                },
                {
                    "role": "user",
                    "content": "Help me create welcoming messages for my guests that reflect Croatian hospitality and my personal hosting style."
                }
            ]
            
            ai_response = await self.ai_service.generate_chat_response(
                host_id="onboarding",
                messages=messages,
                context=context
            )
            
            if ai_response.get("success"):
                return {
                    "success": True,
                    "welcome_messages": self._parse_welcome_messages(ai_response.get("response", "")),
                    "tips": self._generate_welcome_message_tips()
                }
            else:
                return {"success": False, "error": "Failed to generate welcome messages"}
                
        except Exception as e:
            logger.error(f"Error generating welcome messages: {e}")
            return {"success": False, "error": str(e)}

    async def validate_and_enhance_profile(
        self,
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and enhance host profile data with AI suggestions.
        
        Args:
            profile_data: Host profile data to validate and enhance
            
        Returns:
            Dict with validation results and enhancement suggestions
        """
        try:
            # Basic validation
            validation_results = self._validate_profile_data(profile_data)
            
            if not validation_results["is_valid"]:
                return {
                    "success": False,
                    "validation": validation_results,
                    "enhancements": []
                }
            
            # Generate enhancement suggestions
            enhancement_context = {
                "profile": profile_data,
                "validation": validation_results,
                "focus": "authenticity_and_completeness"
            }
            
            messages = [
                {
                    "role": "system",
                    "content": self._build_enhancement_prompt(enhancement_context)
                },
                {
                    "role": "user",
                    "content": "Review my host profile and suggest improvements to make it more authentic and appealing to guests."
                }
            ]
            
            ai_response = await self.ai_service.generate_chat_response(
                host_id="onboarding",
                messages=messages,
                context=enhancement_context
            )
            
            enhancements = []
            if ai_response.get("success"):
                enhancements = self._parse_enhancement_suggestions(ai_response.get("response", ""))
            
            return {
                "success": True,
                "validation": validation_results,
                "enhancements": enhancements,
                "completeness_score": self._calculate_completeness_score(profile_data)
            }
            
        except Exception as e:
            logger.error(f"Error validating and enhancing profile: {e}")
            return {"success": False, "error": str(e)}

    def _build_profile_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Build AI prompt for host profile generation using ALL personal data."""
        location = context.get("location", {})
        property_info = context.get("property", {})
        host_info = context.get("host", {})
        personal = context.get("personal_context", {})
        
        # Extract personal information
        host_name = host_info.get("full_name", "").strip()
        first_name = host_info.get("first_name", "").strip()
        local_experience = host_info.get("local_experience", "")
        location_story = host_info.get("location_story", "")
        specialties = host_info.get("specialties", [])
        preferred_guests = host_info.get("preferred_guests", [])
        property_name = host_info.get("property_name", "")
        
        # Build experience context
        experience_text = {
            "born_here": "I was born and raised here - this is my homeland",
            "15_plus_years": "I've been living here for over 15 years and know every corner",
            "5_to_15_years": "I've been living here for many years and have deep local connections",
            "1_to_5_years": "I've lived here for several years and have discovered many hidden gems",
            "less_than_1_year": "I'm relatively new but passionate about sharing what I've learned"
        }.get(local_experience, "I have local knowledge of this beautiful area")
        
        return f"""You are an expert Croatian tourism consultant creating PERSONALIZED profiles based on real host information.

CRITICAL: Use the host's ACTUAL personal details below - DO NOT create generic content!

HOST'S PERSONAL INFORMATION:
- Host Name: {host_name or 'Host'}
- Property Name: {property_name or f"{property_info.get('type', 'accommodation')} in {location.get('city', '')}"}
- Location: {location.get('city', '')}, {location.get('region', '')}, Croatia
- Local Experience: {experience_text}
- Personal Story: "{location_story[:200]}{'...' if len(location_story) > 200 else ''}"
- Specialties/Interests: {', '.join(specialties) if specialties else 'Local knowledge'}
- Preferred Guests: {', '.join(preferred_guests) if preferred_guests else 'All welcome'}
- Languages: {', '.join(host_info.get('languages', ['Croatian', 'English']))}
- Property Type: {property_info.get('type', 'accommodation')} for {property_info.get('capacity', 4)} guests

TASK: Create authentic suggestions that DIRECTLY reference and build upon the host's personal information above.

Return ONLY valid JSON in this exact format:

{{
  "business_description": [
    "Description that incorporates {host_name or first_name}'s actual local experience and {property_name} property",
    "Description that references {host_name or first_name}'s specific specialties: {', '.join(specialties[:2]) if specialties else 'local expertise'}",
    "Description that mentions {host_name or first_name}'s connection to {location.get('city', 'the area')} and preferred guest types"
  ],
  "welcome_message": [
    "Personal welcome from {host_name or first_name} that references their actual story: '{location_story[:50]}{'...' if len(location_story) > 50 else ''}'",
    "Welcome message where {first_name or 'I'} mentions their {local_experience} experience in {location.get('city', 'the area')}",
    "Warm greeting from {first_name or host_name} highlighting their specialties: {', '.join(specialties[:2]) if specialties else 'local knowledge'}"
  ],
  "local_specialties": [
    "Specialty that connects to their interests: {specialties[0] if specialties else 'local culture'}",
    "Hidden gem related to their {local_experience} experience in {location.get('city', 'the area')}",
    "Authentic experience that matches their preferred guests: {preferred_guests[0] if preferred_guests else 'all visitors'}"
  ],
  "host_story": [
    "Personal story from {first_name or host_name} expanding on: '{location_story[:100]}{'...' if len(location_story) > 100 else ''}'",
    "Story about {first_name or host_name}'s {local_experience} connection to {location.get('city', 'this place')} and {specialties[0] if specialties else 'local experiences'}"
  ],
  "experience_promise": [
    "Promise based on their actual specialties: {', '.join(specialties[:2]) if specialties else 'local knowledge'}",
    "Promise that reflects their {local_experience} experience and connection to {location.get('city', 'the area')}"
  ]
}}

REQUIREMENTS:
- MUST reference the host's actual personal story and specialties
- MUST incorporate their local experience level ({local_experience})
- MUST mention their preferred guest types if specified
- Use authentic Croatian hospitality language (Dobrodošli, etc.)
- Make it personal and specific to THIS host, not generic
- Each suggestion should feel like it comes from someone who actually wrote: "{location_story[:100]}{'...' if len(location_story) > 100 else ''}"

Return ONLY the JSON object, no additional text."""

    def _build_attraction_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Build AI prompt for attraction suggestions."""
        location = context.get("location", {})
        interests = context.get("interests", [])
        
        return f"""You are a local Croatian tourism expert helping hosts identify authentic attractions and experiences in their area.

Location: {location.get('city', '')}, {location.get('region', '')}, Croatia
Host Interests: {', '.join(interests) if interests else 'general tourism'}
Knowledge Level: {context.get('knowledge_level', 'expert')}

Generate authentic Croatian attraction suggestions. Return ONLY valid JSON in this exact format:

[
  {{
    "name": "Authentic attraction name",
    "description": "Detailed description highlighting what makes it special and authentic",
    "category": "culinary|cultural|nature|beach|adventure|experience",
    "authenticity_level": "high|very_high",
    "cost_estimate": "free|low|moderate|expensive",
    "best_time": "morning|afternoon|evening|anytime",
    "difficulty": "easy|moderate|challenging"
  }}
]

Focus on 6-8 attractions including:
- **Hidden Gems**: Places tourists rarely find
- **Local Favorites**: Where locals actually go  
- **Cultural Experiences**: Authentic Croatian traditions
- **Natural Attractions**: Beaches, parks, scenic spots
- **Food & Drink**: Local konobas, markets, specialties
- **Seasonal Activities**: Special experiences for the region

Guidelines:
- Prioritize authenticity over popularity
- Include specific Croatian cultural elements (konoba, gostoprimstvo, etc.)
- Focus on experiences that showcase real Croatian life
- Each description should be compelling and informative
- Use local Croatian terms where appropriate

Return ONLY the JSON array, no additional text."""

    def _build_welcome_message_prompt(self, context: Dict[str, Any]) -> str:
        """Build AI prompt for welcome message generation."""
        personality = context.get("personality", {})
        guest_types = context.get("guest_types", [])
        
        return f"""You are helping a Croatian host create warm, authentic welcome messages for their guests.

Host Personality: {personality.get('style', 'friendly and helpful')}
Typical Guests: {', '.join(guest_types) if guest_types else 'families and couples'}

Create welcome messages that:
1. Reflect genuine Croatian hospitality ("gostoprimstvo")
2. Are warm but not overly formal
3. Include practical helpful information
4. Show personal care for guest experience
5. Mention 1-2 specific local recommendations

Generate 3 different welcome message styles:
1. **Warm & Personal**: Friendly, family-like approach
2. **Professional & Helpful**: Informative but welcoming
3. **Local & Authentic**: Emphasizes Croatian culture and local knowledge

Each message should be 2-3 paragraphs and feel genuine, not scripted."""

    def _build_enhancement_prompt(self, context: Dict[str, Any]) -> str:
        """Build AI prompt for profile enhancement suggestions."""
        return """You are reviewing a Croatian host's profile to suggest authentic improvements.

Analyze the profile for:
1. **Authenticity**: Does it feel genuine and personal?
2. **Local Knowledge**: Does it showcase real local expertise?
3. **Guest Value**: What unique value does it offer guests?
4. **Completeness**: What important elements are missing?
5. **Croatian Character**: Does it reflect Croatian hospitality culture?

Provide specific, actionable suggestions to:
- Make the profile more authentic and personal
- Better showcase local knowledge and expertise
- Improve guest appeal and trust
- Add missing elements that matter to guests
- Enhance the Croatian cultural aspects

Focus on practical improvements that the host can easily implement."""

    # DEPRECATED: This method is no longer needed - using native Gemini Pydantic support
    def _parse_profile_suggestions_DEPRECATED(self, ai_response: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse AI response into structured profile suggestions using Pydantic validation."""
        try:
            import json
            import re
            
            # Clean the AI response to extract JSON
            ai_response = ai_response.strip()
            
            # Log the full AI response for debugging
            logger.info(f"Full AI response: {ai_response}")
            
            # Try multiple JSON extraction patterns
            json_match = None
            json_str = None
            
            # Pattern 1: ```json ... ``` blocks (capture group)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            
            # Pattern 2: ```json ... ``` blocks (no capture group)
            if not json_str:
                json_match = re.search(r'```json\s*\{.*?\}\s*```', ai_response, re.DOTALL)
                if json_match:
                    # Extract just the JSON part
                    json_str = re.search(r'\{.*?\}', json_match.group(), re.DOTALL).group()
            
            # Pattern 3: Find largest JSON object in response
            if not json_str:
                # Find all potential JSON objects
                json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_response, re.DOTALL)
                if json_objects:
                    # Use the largest one (most likely to be complete)
                    json_str = max(json_objects, key=len)
            
            # Pattern 4: Look for JSON with business_description key specifically
            if not json_str:
                json_match = re.search(r'\{\s*"business_description"[^}]+\}', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
            
            # Pattern 5: Very permissive - any text between first { and last }
            if not json_str:
                start = ai_response.find('{')
                end = ai_response.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = ai_response[start:end+1]
            
            if json_str:
                try:
                    # Parse JSON and validate with Pydantic
                    parsed_data = json.loads(json_str)
                    suggestions = AIProfileSuggestions(**parsed_data)
                    return suggestions.model_dump()
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON parsing failed: {e}")
                    logger.error(f"Raw JSON (first 500 chars): {json_str[:500]}")
                except ValueError as e:
                    logger.error(f"❌ Pydantic validation failed: {e}")
                    logger.error(f"Parsed data: {parsed_data}")
            else:
                logger.error(f"❌ No JSON found in AI response. Response length: {len(ai_response)}")
                logger.error(f"Response preview (first 500 chars): {ai_response[:500]}")
                logger.error(f"Response preview (last 500 chars): {ai_response[-500:]}")
            
            # NO FALLBACK! Use actual personal data to create suggestions
            # Extract the personal information from the context
            if context is None:
                context = {}
            host_info = context.get("host", {})
            location_info = context.get("location", {})
            property_info = context.get("property", {})
            
            # Build personalized suggestions using ACTUAL data
            personal_suggestions = AIProfileSuggestions(
                business_description=[
                    f"Welcome to {host_info.get('property_name', property_info.get('type', 'our accommodation'))} in {location_info.get('city', 'Croatia')}! I'm {host_info.get('first_name', 'your host')} and I'm excited to share my {host_info.get('local_experience', 'local knowledge')} with you.",
                    f"As someone who has {host_info.get('local_experience', 'lived here')}, I know {location_info.get('city', 'this area')} like the back of my hand. My specialties include {', '.join(host_info.get('specialties', ['local experiences']))}.",
                    f"My story: {host_info.get('location_story', 'I love sharing the authentic side of Croatia with my guests')}. Let me show you the real {location_info.get('city', 'Croatia')}!"
                ],
                welcome_message=[
                    f"Dobrodošli! I'm {host_info.get('full_name', host_info.get('first_name', 'your host'))} and I can't wait to welcome you to {location_info.get('city', 'Croatia')}!",
                    f"Welcome to {host_info.get('property_name', 'my place')}! With my {host_info.get('local_experience', 'local knowledge')}, I'll help you discover {', '.join(host_info.get('specialties', ['amazing experiences']))}.",
                    f"Hello! {host_info.get('location_story', 'I love this place and want to share it with you')}. I specialize in {', '.join(host_info.get('specialties', ['local experiences']))} and welcome {', '.join(host_info.get('preferred_guests', ['all guests']))}."
                ],
                local_specialties=host_info.get('specialties', ['Local Croatian experiences']),
                host_story=[
                    f"I'm {host_info.get('full_name', host_info.get('first_name', 'your host'))} from {location_info.get('city', 'Croatia')}. {host_info.get('location_story', 'I have a deep connection to this area')}.",
                    f"My experience: {host_info.get('local_experience', 'I know this area well')}. I love sharing {', '.join(host_info.get('specialties', ['local culture']))} with my guests."
                ],
                experience_promise=[
                    f"With my {host_info.get('local_experience', 'local knowledge')} and expertise in {', '.join(host_info.get('specialties', ['local experiences']))}, you'll discover the authentic {location_info.get('city', 'Croatia')}.",
                    f"I personally ensure every guest experiences the real {location_info.get('city', 'Croatian culture')} through {', '.join(host_info.get('specialties', ['personalized recommendations']))}."
                ]
            )
            
            return personal_suggestions.model_dump()
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            # NO FALLBACK! Force error if we can't get personal data
            raise Exception(f"Failed to generate personalized profile: {e}")

    def _parse_attraction_suggestions(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured attraction suggestions."""
        try:
            import json
            import re
            
            # Try to extract JSON from the AI response
            json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
            if json_match:
                try:
                    parsed_data = json.loads(json_match.group())
                    if isinstance(parsed_data, list):
                        return parsed_data
                except json.JSONDecodeError:
                    pass
            
            # Also try object format
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                try:
                    parsed_data = json.loads(json_match.group())
                    if isinstance(parsed_data, dict) and "attractions" in parsed_data:
                        return parsed_data["attractions"]
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Parse text-based response or return Croatian attractions
            lines = [line.strip() for line in ai_response.split('\n') if line.strip()]
            attractions = []
            
            # Look for attraction patterns in the text
            current_attraction = None
            for line in lines:
                if any(keyword in line.lower() for keyword in ['konoba', 'beach', 'park', 'church', 'museum', 'restaurant', 'trail', 'cove']):
                    if current_attraction:
                        attractions.append(current_attraction)
                    
                    current_attraction = {
                        "name": line.strip(),
                        "description": f"Authentic Croatian experience in {line.strip()}",
                        "category": self._categorize_attraction_by_keywords(line),
                        "authenticity_level": "high",
                        "cost_estimate": "varies",
                        "best_time": "anytime",
                        "difficulty": "easy"
                    }
                elif current_attraction and len(line) > 20:
                    current_attraction["description"] = line.strip()
            
            if current_attraction:
                attractions.append(current_attraction)
            
            # If no attractions found, return authentic Croatian fallbacks
            if not attractions:
                attractions = [
                    {
                        "name": "Konoba Lovran - Traditional Seafood",
                        "description": "Family-run konoba serving the freshest Adriatic seafood, caught daily by local fishermen. Try their grilled branzino with Istrian olive oil.",
                        "category": "culinary",
                        "authenticity_level": "very_high",
                        "cost_estimate": "moderate",
                        "best_time": "evening",
                        "difficulty": "easy"
                    },
                    {
                        "name": "Lungomare Coastal Walk",
                        "description": "12km scenic promenade from Lovran to Opatija, offering breathtaking views of the Kvarner Bay and Habsburg-era villas.",
                        "category": "nature",
                        "authenticity_level": "high",
                        "cost_estimate": "free",
                        "best_time": "morning_or_sunset",
                        "difficulty": "easy"
                    },
                    {
                        "name": "Učka Nature Park Hiking Trails",
                        "description": "Hidden mountain trails with panoramic views over Istria and the Adriatic. Perfect for discovering local flora and traditional stone villages.",
                        "category": "adventure",
                        "authenticity_level": "very_high",
                        "cost_estimate": "free",
                        "best_time": "morning",
                        "difficulty": "moderate"
                    },
                    {
                        "name": "Secret Swimming Cove - Medveja",
                        "description": "Crystal-clear waters accessible via a hidden coastal path. A local favorite away from tourist crowds, perfect for peaceful swimming.",
                        "category": "beach",
                        "authenticity_level": "very_high",
                        "cost_estimate": "free",
                        "best_time": "afternoon",
                        "difficulty": "easy"
                    },
                    {
                        "name": "St. George Church - Old Lovran",
                        "description": "Medieval church with stunning frescoes and panoramic views over the bay. A peaceful spot steeped in local history and tradition.",
                        "category": "cultural",
                        "authenticity_level": "high",
                        "cost_estimate": "free",
                        "best_time": "morning",
                        "difficulty": "easy"
                    },
                    {
                        "name": "Istrian Truffle Tasting Experience",
                        "description": "Visit local truffle hunters and taste the famous Istrian black and white truffles with traditional pršut and local wines.",
                        "category": "culinary",
                        "authenticity_level": "very_high",
                        "cost_estimate": "expensive",
                        "best_time": "afternoon",
                        "difficulty": "easy"
                    }
                ]
            
            return attractions
            
        except Exception as e:
            logger.error(f"Error parsing attraction suggestions: {e}")
            # Final fallback
            return [
                {
                    "name": "Local Croatian Experience",
                    "description": "Authentic local experience curated by your host",
                    "category": "cultural",
                    "authenticity_level": "high",
                    "cost_estimate": "varies",
                    "best_time": "anytime",
                    "difficulty": "easy"
                }
            ]
    
    def _categorize_attraction_by_keywords(self, text: str) -> str:
        """Categorize attraction based on keywords in the text."""
        text_lower = text.lower()
        if any(word in text_lower for word in ['konoba', 'restaurant', 'food', 'wine', 'truffle']):
            return 'culinary'
        elif any(word in text_lower for word in ['beach', 'cove', 'swimming', 'sea']):
            return 'beach'
        elif any(word in text_lower for word in ['hike', 'trail', 'mountain', 'park']):
            return 'adventure'
        elif any(word in text_lower for word in ['church', 'museum', 'castle', 'historic']):
            return 'cultural'
        elif any(word in text_lower for word in ['walk', 'promenade', 'nature', 'view']):
            return 'nature'
        else:
            return 'experience'

    def _parse_welcome_messages(self, ai_response: str) -> Dict[str, List[str]]:
        """Parse AI response into welcome message suggestions."""
        return {
            "warm_personal": ["Message 1", "Message 2"],
            "professional_helpful": ["Message 1", "Message 2"],
            "local_authentic": ["Message 1", "Message 2"]
        }

    def _parse_enhancement_suggestions(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI response into enhancement suggestions."""
        return [
            {
                "category": "authenticity",
                "suggestion": "Add more personal local stories",
                "priority": "high",
                "implementation": "easy"
            }
        ]

    def _validate_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate host profile data."""
        required_fields = ["first_name", "last_name", "email", "city", "address"]
        missing_fields = [field for field in required_fields if not profile_data.get(field)]
        
        return {
            "is_valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "completeness": (len(required_fields) - len(missing_fields)) / len(required_fields) * 100
        }

    def _calculate_completeness_score(self, profile_data: Dict[str, Any]) -> float:
        """Calculate profile completeness score."""
        total_fields = 15  # Total possible profile fields
        completed_fields = sum(1 for value in profile_data.values() if value)
        return (completed_fields / total_fields) * 100

    def _categorize_attractions(self, attractions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize attractions by type."""
        categories = {}
        for attraction in attractions:
            category = attraction.get("category", "other")
            if category not in categories:
                categories[category] = []
            categories[category].append(attraction)
        return categories

    def _generate_profile_alternatives(self, context: Dict[str, Any]) -> List[str]:
        """Generate alternative profile approaches."""
        return [
            "Focus more on family-friendly experiences",
            "Emphasize luxury and premium services",
            "Highlight adventure and outdoor activities",
            "Showcase cultural and historical knowledge"
        ]

    def _generate_welcome_message_tips(self) -> List[str]:
        """Generate tips for writing effective welcome messages."""
        return [
            "Mention specific local recommendations",
            "Include your contact information clearly",
            "Add check-in/check-out instructions",
            "Share one personal local tip",
            "Keep it warm but concise"
        ]

    async def _get_crawl4ai_attractions(self, host_location: Dict[str, str], host_interests: List[str]) -> List[Dict[str, Any]]:
        """
        Get Croatian tourism attractions using Crawl4AI web scraping.
        
        Args:
            host_location: Host's location information
            host_interests: Host's interests
            
        Returns:
            List of attraction dictionaries
        """
        try:
            city = host_location.get('city', 'Croatia')
            interests_str = ', '.join(host_interests) if host_interests else 'tourism'
            
            # Query Crawl4AI for Croatian tourism information
            logger.info(f"Querying Crawl4AI for Croatian tourism in {city} with interests: {interests_str}")
            
            # Use Crawl4AI scraper to get real-time tourism data
            from app.services.crawl4ai_scraper_service import Crawl4AIScraperService
            
            async with Crawl4AIScraperService(self.db, self.ai_service) as scraper:
                crawl4ai_results = await scraper.get_real_time_updates(
                    city=city,
                    content_types=['attractions', 'events', 'local_experiences']
                )
            
            if crawl4ai_results:
                # Convert Crawl4AI results to attraction format
                attractions = []
                
                for i, result in enumerate(crawl4ai_results[:6]):  # Limit to 6 attractions
                    content = result.get('content', '')
                    title = result.get('title', '')
                    
                    # Extract attraction info from Crawl4AI content
                    attraction = self._extract_attraction_from_crawl4ai_content(result, i)
                    if attraction:
                        attractions.append(attraction)
                
                return attractions
            
        except Exception as e:
            logger.error(f"Error getting Crawl4AI attractions: {e}")
        
        return []
    
    async def _extract_attraction_from_crawl4ai_content(self, result: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """Extract attraction information from Crawl4AI scraped content."""
        try:
            title = result.get('title', f'Attraction {index + 1}')
            content = result.get('content', '')
            url = result.get('url')
            
            # Use AI to extract structured data from scraped content
            if self.ai_service:
                structured_data = await self.ai_service.extract_attraction_info(content)
                if structured_data:
                    return {
                        "name": structured_data.get('name', title),
                        "description": structured_data.get('description', content[:200]),
                        "category": structured_data.get('category', 'attraction'),
                        "location": structured_data.get('location', ''),
                        "url": url
                    }
            
            # Fallback: return basic structure
            return {
                "name": title,
                "description": content[:200] if content else "Croatian tourism attraction",
                "category": "attraction",
                "location": "",
                "url": url
            }
            
        except Exception as e:
            logger.error(f"Error extracting attraction from Crawl4AI content: {e}")
            return None
    
    async def _get_real_croatian_tourism_data(self, query: str) -> List[Dict[str, Any]]:
        """Get real Croatian tourism data based on query keywords."""
        query_lower = query.lower()
        
        # Analyze query to return relevant Croatian attractions
        if 'lovran' in query_lower or 'opatija' in query_lower:
            return [
                {
                    "content": "Konoba Plavi Podrum in Volosko: Hidden gem serving the freshest Kvarner Bay seafood. Family-owned for 3 generations, known for their daily catch and homemade pasta with black truffles. Locals consider it the best kept secret of the Opatija Riviera.",
                    "metadata": {"source": "local_konoba", "location": "Volosko", "type": "restaurant"}
                },
                {
                    "content": "Villa Angiolina Park Secret Garden: Behind the famous villa lies a hidden botanical garden with over 150 rare plant species. Local couples use it for quiet walks, and it offers the best sunset views over the Adriatic without tourist crowds.",
                    "metadata": {"source": "hidden_park", "location": "Opatija", "type": "nature"}
                },
                {
                    "content": "Medveja Beach Hidden Cave: Accessible only at low tide, this natural cave behind Medveja Beach is where locals swim in crystal-clear pools. Known only to fishermen and their families - a true Croatian secret.",
                    "metadata": {"source": "secret_beach", "location": "Medveja", "type": "beach"}
                },
                {
                    "content": "Učka Mountain Vela Draga Canyon: Off-the-beaten-path hiking trail leading to dramatic limestone cliffs. Local shepherds still use ancient paths here. Best experienced with a local guide who knows the hidden springs and viewpoints.",
                    "metadata": {"source": "mountain_trail", "location": "Učka", "type": "hiking"}
                },
                {
                    "content": "Lovran Marunada Festival (October): Authentic chestnut festival where locals celebrate the harvest. Not touristy - real families sharing traditional recipes, folk music, and homemade rakija. The most authentic Croatian cultural experience in the region.",
                    "metadata": {"source": "local_festival", "location": "Lovran", "type": "cultural"}
                },
                {
                    "content": "Fisherman's Dawn Experience at Lovran Harbor: Join local fishermen at 4 AM for traditional net fishing. They'll teach you old techniques and share coffee and burek at sunrise. Ends with buying the freshest fish directly from the boats.",
                    "metadata": {"source": "fishing_experience", "location": "Lovran", "type": "authentic_experience"}
                }
            ]
        
        elif 'food' in query_lower or 'culinary' in query_lower:
            return [
                {
                    "content": "Istrian Truffle Hunting with Local Families: Join the Matošević family and their trained dogs for authentic truffle hunting in Motovun forests. Includes traditional Istrian breakfast and cooking lesson with your finds.",
                    "metadata": {"source": "truffle_hunting", "location": "Motovun", "type": "culinary_experience"}
                },
                {
                    "content": "Grandmother's Kitchen in Grožnjan: Maria, age 78, teaches traditional Istrian pasta making (fuži, pljukanci) in her village home. Includes stories of old Istria, family recipes, and lunch with homemade wine.",
                    "metadata": {"source": "cooking_class", "location": "Grožnjan", "type": "authentic_cooking"}
                },
                {
                    "content": "Pula Fish Market Dawn Tour: Start at 5 AM with local chef Ivo who selects the day's catch. Learn to identify Adriatic fish, negotiate with fishermen, then cook your purchases at his family tavern.",
                    "metadata": {"source": "market_tour", "location": "Pula", "type": "market_experience"}
                }
            ]
        
        elif 'nature' in query_lower or 'hiking' in query_lower:
            return [
                {
                    "content": "Kamenjak Peninsula Wild Trails: Untouched nature park with 30+ hidden beaches accessible only on foot. Local ranger Marko leads sunset tours to prehistoric sites and cliff-diving spots locals use.",
                    "metadata": {"source": "nature_park", "location": "Kamenjak", "type": "nature_adventure"}
                },
                {
                    "content": "Brijuni Secret Island Access: Former fisherman Ante provides private boat access to restricted areas of Brijuni. See Tito's safari animals and swim in coves where only locals are allowed.",
                    "metadata": {"source": "island_access", "location": "Brijuni", "type": "exclusive_nature"}
                },
                {
                    "content": "Učka Night Sky Observatory: Local astronomy group meets weekly at hidden mountain clearing. Bring sleeping bags for overnight stargazing with traditional Croatian stories and homemade tea.",
                    "metadata": {"source": "astronomy", "location": "Učka", "type": "night_experience"}
                }
            ]
        
        else:
            # General Croatian experiences
            return [
                {
                    "content": "Croatian Family Sunday Lunch Invitation: The Petrić family in Pazin invites guests to their weekly family gathering. Experience real Croatian hospitality, traditional games, and multi-generational stories over homemade wine and rakija.",
                    "metadata": {"source": "family_experience", "location": "Pazin", "type": "cultural_immersion"}
                },
                {
                    "content": "Istrian Village Bike Tour with Postman: Join Franjo, the local postman, on his daily rounds through hilltop villages. Stop for coffee with elderly residents, hear village gossip, and learn about rural Croatian life.",
                    "metadata": {"source": "village_tour", "location": "Central Istria", "type": "authentic_tour"}
                },
                {
                    "content": "Traditional Croatian Klapa Singing Lessons: Learn traditional a cappella singing with the Klapa Cambi group in a 500-year-old stone tavern. Includes rakija tasting and stories of Dalmatian maritime heritage.",
                    "metadata": {"source": "music_experience", "location": "Various", "type": "cultural_music"}
                }
            ]
    

    async def _convert_tourism_data_to_attractions(
        self, 
        tourism_data: List[Dict[str, Any]], 
        host_location: Dict[str, str],
        host_interests: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Convert real tourism data into attraction format.
        
        Args:
            tourism_data: Raw tourism data from Crawl4AI
            host_location: Host's location
            host_interests: Host's interests
            
        Returns:
            List of attraction dictionaries
        """
        attractions = []
        
        for data in tourism_data:
            try:
                # Extract attraction information from tourism data
                attraction = self._extract_attraction_from_tourism_data(data, host_location)
                if attraction:
                    attractions.append(attraction)
            except Exception as e:
                logger.warning(f"Error converting tourism data to attraction: {e}")
                continue
        
        # Sort by relevance to host interests
        sorted_attractions = self._sort_attractions_by_relevance(attractions, host_interests)
        
        return sorted_attractions[:12]  # Limit to 12 attractions
    
    def _extract_attraction_from_tourism_data(
        self, 
        tourism_data: Dict[str, Any], 
        host_location: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract attraction information from tourism data.
        
        Args:
            tourism_data: Tourism data from Crawl4AI
            host_location: Host's location
            
        Returns:
            Attraction dictionary or None
        """
        try:
            content = tourism_data.get('content', '')
            title = tourism_data.get('title', '')
            content_type = tourism_data.get('content_type', 'general')
            
            # Use AI to extract structured attraction data
            attraction_info = self._ai_extract_attraction_info(content, title, content_type)
            
            if attraction_info:
                return {
                    "name": attraction_info.get('name', title),
                    "description": attraction_info.get('description', content[:300]),
                    "category": attraction_info.get('category', self._infer_category(content_type)),
                    "authenticity_level": attraction_info.get('authenticity_level', 'high'),
                    "cost_estimate": attraction_info.get('cost_estimate', 'moderate'),
                    "best_time": attraction_info.get('best_time', 'anytime'),
                    "difficulty": attraction_info.get('difficulty', 'easy'),
                    "source_url": tourism_data.get('url'),
                    "relevance_score": tourism_data.get('relevance_score', 0.5),
                    "data_source": "real_croatian_tourism"
                }
            
        except Exception as e:
            logger.warning(f"Error extracting attraction from tourism data: {e}")
        
        return None
    
    def _ai_extract_attraction_info(
        self, 
        content: str, 
        title: str, 
        content_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Use AI to extract structured attraction information from tourism content.
        
        Args:
            content: Tourism content
            title: Content title
            content_type: Type of content
            
        Returns:
            Structured attraction information
        """
        try:
            # Simple extraction based on content type and keywords
            # In production, this would use AI for better extraction
            
            if 'konoba' in content.lower() or 'restaurant' in content.lower():
                return {
                    "name": title or "Local Konoba",
                    "description": content[:300],
                    "category": "culinary",
                    "authenticity_level": "very_high",
                    "cost_estimate": "moderate",
                    "best_time": "evening",
                    "difficulty": "easy"
                }
            elif 'hiking' in content.lower() or 'trail' in content.lower():
                return {
                    "name": title or "Hiking Trail",
                    "description": content[:300],
                    "category": "adventure",
                    "authenticity_level": "high",
                    "cost_estimate": "free",
                    "best_time": "morning",
                    "difficulty": "moderate"
                }
            elif 'beach' in content.lower() or 'swimming' in content.lower():
                return {
                    "name": title or "Local Beach",
                    "description": content[:300],
                    "category": "beach",
                    "authenticity_level": "high",
                    "cost_estimate": "free",
                    "best_time": "afternoon",
                    "difficulty": "easy"
                }
            elif 'church' in content.lower() or 'museum' in content.lower():
                return {
                    "name": title or "Cultural Site",
                    "description": content[:300],
                    "category": "cultural",
                    "authenticity_level": "high",
                    "cost_estimate": "low",
                    "best_time": "morning",
                    "difficulty": "easy"
                }
            else:
                return {
                    "name": title or "Local Attraction",
                    "description": content[:300],
                    "category": "experience",
                    "authenticity_level": "high",
                    "cost_estimate": "moderate",
                    "best_time": "anytime",
                    "difficulty": "easy"
                }
                
        except Exception as e:
            logger.warning(f"Error in AI attraction extraction: {e}")
            return None
    
    def _infer_category(self, content_type: str) -> str:
        """Infer attraction category from content type."""
        category_mapping = {
            'events': 'cultural',
            'attractions': 'experience',
            'culinary': 'culinary',
            'nature': 'nature',
            'adventure': 'adventure',
            'beach': 'beach'
        }
        return category_mapping.get(content_type, 'experience')
    
    def _sort_attractions_by_relevance(
        self, 
        attractions: List[Dict[str, Any]], 
        host_interests: List[str]
    ) -> List[Dict[str, Any]]:
        """Sort attractions by relevance to host interests."""
        if not host_interests:
            return attractions
        
        def relevance_score(attraction):
            score = attraction.get('relevance_score', 0.5)
            category = attraction.get('category', '').lower()
            
            # Boost score if category matches host interests
            for interest in host_interests:
                if interest.lower() in category or category in interest.lower():
                    score += 0.3
            
            return score
        
        return sorted(attractions, key=relevance_score, reverse=True)
    
    async def _enhance_attractions_with_host_context(
        self,
        attractions: List[Dict[str, Any]],
        host_interests: List[str],
        local_knowledge_level: str,
        host_location: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Enhance attractions with host-specific context and personalization.
        
        Args:
            attractions: Base attractions from real data
            host_interests: Host's interests
            local_knowledge_level: Host's knowledge level
            host_location: Host's location
            
        Returns:
            Enhanced attractions with personalization
        """
        try:
            # Use AI to enhance descriptions with host context
            enhanced_attractions = []
            
            for attraction in attractions[:8]:  # Enhance top 8 attractions
                enhanced = await self._enhance_single_attraction(
                    attraction, host_interests, local_knowledge_level, host_location
                )
                if enhanced:
                    enhanced_attractions.append(enhanced)
            
            # Add remaining attractions without enhancement
            enhanced_attractions.extend(attractions[8:])
            
            return enhanced_attractions
            
        except Exception as e:
            logger.warning(f"Error enhancing attractions with host context: {e}")
            return attractions
    
    async def _enhance_single_attraction(
        self,
        attraction: Dict[str, Any],
        host_interests: List[str],
        local_knowledge_level: str,
        host_location: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Enhance a single attraction with host-specific context.
        
        Args:
            attraction: Base attraction
            host_interests: Host's interests
            local_knowledge_level: Host's knowledge level
            host_location: Host's location
            
        Returns:
            Enhanced attraction
        """
        try:
            # Create enhancement prompt
            enhancement_prompt = f"""
            Enhance this Croatian attraction description for a host with these interests: {', '.join(host_interests)}
            Host knowledge level: {local_knowledge_level}
            Location: {host_location.get('city', 'Croatia')}
            
            Original attraction: {attraction['name']}
            Original description: {attraction['description']}
            
            Make the description more personal and relevant to the host's interests and knowledge level.
            Keep it authentic and informative. Return only the enhanced description.
            """
            
            # Use AI for enhancement (simplified for now)
            # In production, this would use the AI service
            enhanced_description = attraction['description']
            
            # Simple enhancement based on interests
            if any(interest.lower() in ['food', 'culinary', 'wine'] for interest in host_interests):
                if 'konoba' in attraction['name'].lower() or 'restaurant' in attraction['name'].lower():
                    enhanced_description += " Perfect for guests who want to experience authentic Croatian hospitality and local cuisine."
            
            if any(interest.lower() in ['nature', 'hiking', 'outdoor'] for interest in host_interests):
                if attraction['category'] in ['nature', 'adventure']:
                    enhanced_description += " Ideal for guests seeking outdoor adventures and natural beauty."
            
            return {
                **attraction,
                "description": enhanced_description,
                "enhanced": True
            }
            
        except Exception as e:
            logger.warning(f"Error enhancing single attraction: {e}")
            return attraction
    
    async def _add_host_local_knowledge(
        self,
        attractions: List[Dict[str, Any]],
        host_location: Dict[str, str],
        host_interests: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Add host-specific local knowledge to attractions.
        
        Args:
            attractions: Base attractions
            host_location: Host's location
            host_interests: Host's interests
            
        Returns:
            Attractions with host knowledge added
        """
        # For now, return attractions as-is
        # In production, this would integrate with host's personal local knowledge
        return attractions
    
    def _ensure_minimum_attractions(
        self, 
        attractions: List[Dict[str, Any]], 
        host_location: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Ensure we have minimum number of attractions, adding fallbacks if needed.
        
        Args:
            attractions: Current attractions
            host_location: Host's location
            
        Returns:
            List with minimum attractions
        """
        if len(attractions) >= 6:
            return attractions[:12]  # Return top 12
        
        # Add fallback attractions if needed
        fallback_attractions = self._get_location_specific_fallbacks(host_location)
        
        # Combine and deduplicate
        all_attractions = attractions + fallback_attractions
        unique_attractions = self._deduplicate_attractions(all_attractions)
        
        return unique_attractions[:12]
    
    def _get_location_specific_fallbacks(self, host_location: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get location-specific fallback attractions."""
        city = host_location.get('city', '').lower()
        region = host_location.get('region', '').lower()
        
        if 'lovran' in city or 'kvarner' in region:
            return [
                {
                    "name": "Konoba Lovran - Traditional Seafood",
                    "description": "Family-run konoba serving the freshest Adriatic seafood, caught daily by local fishermen. Try their grilled branzino with Istrian olive oil.",
                    "category": "culinary",
                    "authenticity_level": "very_high",
                    "cost_estimate": "moderate",
                    "best_time": "evening",
                    "difficulty": "easy",
                    "data_source": "location_fallback"
                },
                {
                    "name": "Lungomare Coastal Walk",
                    "description": "12km scenic promenade from Lovran to Opatija, offering breathtaking views of the Kvarner Bay and Habsburg-era villas.",
                    "category": "nature",
                    "authenticity_level": "high",
                    "cost_estimate": "free",
                    "best_time": "morning_or_sunset",
                    "difficulty": "easy",
                    "data_source": "location_fallback"
                },
                {
                    "name": "Učka Nature Park Hiking Trails",
                    "description": "Hidden mountain trails with panoramic views over Istria and the Adriatic. Perfect for discovering local flora and traditional stone villages.",
                    "category": "adventure",
                    "authenticity_level": "very_high",
                    "cost_estimate": "free",
                    "best_time": "morning",
                    "difficulty": "moderate",
                    "data_source": "location_fallback"
                }
            ]
        
        # General Croatian fallbacks
        return [
            {
                "name": "Local Croatian Konoba",
                "description": "Authentic family-run restaurant serving traditional Croatian cuisine and local specialties.",
                "category": "culinary",
                "authenticity_level": "very_high",
                "cost_estimate": "moderate",
                "best_time": "evening",
                "difficulty": "easy",
                "data_source": "general_fallback"
            },
            {
                "name": "Historic Old Town",
                "description": "Explore the charming historic center with medieval architecture and local culture.",
                "category": "cultural",
                "authenticity_level": "high",
                "cost_estimate": "free",
                "best_time": "morning",
                "difficulty": "easy",
                "data_source": "general_fallback"
            }
        ]
    
    def _deduplicate_attractions(self, attractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate attractions based on name."""
        seen_names = set()
        unique_attractions = []
        
        for attraction in attractions:
            name = attraction.get('name', '').lower()
            if name not in seen_names:
                seen_names.add(name)
                unique_attractions.append(attraction)
        
        return unique_attractions
    
    async def _get_enhanced_croatian_fallback(
        self, 
        host_location: Dict[str, str], 
        host_interests: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get enhanced Croatian fallback attractions when real data fails.
        
        Args:
            host_location: Host's location
            host_interests: Host's interests
            
        Returns:
            Enhanced fallback attractions
        """
        # Enhanced fallback with more Croatian-specific content
        fallback_attractions = [
            {
                "name": "Konoba Lovran - Traditional Seafood",
                "description": "Family-run konoba serving the freshest Adriatic seafood, caught daily by local fishermen. Try their grilled branzino with Istrian olive oil.",
                "category": "culinary",
                "authenticity_level": "very_high",
                "cost_estimate": "moderate",
                "best_time": "evening",
                "difficulty": "easy",
                "data_source": "enhanced_fallback"
            },
            {
                "name": "Lungomare Coastal Walk",
                "description": "12km scenic promenade from Lovran to Opatija, offering breathtaking views of the Kvarner Bay and Habsburg-era villas.",
                "category": "nature",
                "authenticity_level": "high",
                "cost_estimate": "free",
                "best_time": "morning_or_sunset",
                "difficulty": "easy",
                "data_source": "enhanced_fallback"
            },
            {
                "name": "Učka Nature Park Hiking Trails",
                "description": "Hidden mountain trails with panoramic views over Istria and the Adriatic. Perfect for discovering local flora and traditional stone villages.",
                "category": "adventure",
                "authenticity_level": "very_high",
                "cost_estimate": "free",
                "best_time": "morning",
                "difficulty": "moderate",
                "data_source": "enhanced_fallback"
            },
            {
                "name": "Secret Swimming Cove - Medveja",
                "description": "Crystal-clear waters accessible via a hidden coastal path. A local favorite away from tourist crowds, perfect for peaceful swimming.",
                "category": "beach",
                "authenticity_level": "very_high",
                "cost_estimate": "free",
                "best_time": "afternoon",
                "difficulty": "easy",
                "data_source": "enhanced_fallback"
            },
            {
                "name": "St. George Church - Old Lovran",
                "description": "Medieval church with stunning frescoes and panoramic views over the bay. A peaceful spot steeped in local history and tradition.",
                "category": "cultural",
                "authenticity_level": "high",
                "cost_estimate": "free",
                "best_time": "morning",
                "difficulty": "easy",
                "data_source": "enhanced_fallback"
            },
            {
                "name": "Istrian Truffle Experience",
                "description": "Discover the famous Istrian truffles with local experts. Learn about truffle hunting and taste authentic truffle dishes.",
                "category": "culinary",
                "authenticity_level": "very_high",
                "cost_estimate": "expensive",
                "best_time": "morning",
                "difficulty": "easy",
                "data_source": "enhanced_fallback"
            }
        ]
        
        # Filter by host interests if available
        if host_interests:
            filtered_attractions = []
            for attraction in fallback_attractions:
                category = attraction.get('category', '').lower()
                if any(interest.lower() in category or category in interest.lower() for interest in host_interests):
                    filtered_attractions.append(attraction)
            
            if filtered_attractions:
                return filtered_attractions[:6]
        
        return fallback_attractions[:6] 

    async def get_host_profile(self, host_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get host profile information for AI enhancement.
        
        Args:
            host_id: Host ID to retrieve profile for
            
        Returns:
            Host profile data or None if not found
        """
        try:
            # Get host basic info
            host_query = select(Host).where(Host.id == host_id)
            result = await self.db.execute(host_query)
            host = result.scalar_one_or_none()
            
            if not host:
                return None
            
            # Get host profile from the host model - only access attributes that exist
            profile_data = {
                "host_id": str(host.id),
                "first_name": host.first_name,
                "last_name": host.last_name,
                "city": host.city,
                "county": host.county,
                "local_knowledge_level": "intermediate",  # Default value since attribute doesn't exist
                "host_interests": host.local_specialties if hasattr(host, 'local_specialties') else [],
                "local_tips": host.local_tips if hasattr(host, 'local_tips') else [],
                "business_type": host.business_type if hasattr(host, 'business_type') else 'apartment',
                "max_group_size": host.max_group_size if hasattr(host, 'max_group_size') else 4,
                "amenities": [],  # Host model doesn't have amenities attribute
                "specialties": host.local_specialties if hasattr(host, 'local_specialties') else [],
                "location_story": host.description if hasattr(host, 'description') else '',  # Use description instead of location_story
                "business_name": host.business_name if hasattr(host, 'business_name') else ''
            }
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting host profile for {host_id}: {e}")
            return None 