"""
AI-powered content generation service.

Provides automated content generation for:
- Attraction descriptions
- Local tips
- Multi-language content
- SEO-optimized descriptions
- Social media posts
- Email templates
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.ai_service import AIService
from app.services.settings_service import SettingsService
from app.models.attraction import Attraction
from app.models.host import Host

logger = logging.getLogger(__name__)


class ContentGenerationService:
    """
    Service for AI-powered content generation.
    
    Generates high-quality, personalized content for hosts
    to save time and improve content quality.
    """

    @staticmethod
    def _host_region(host: Host) -> str:
        return (host.county or host.country or "Croatia") if host else "Croatia"

    @staticmethod
    def _host_display_name(host: Host) -> str:
        if not host:
            return "Your host"
        return f"{host.first_name} {host.last_name}".strip() or "Your host"
    
    def __init__(self, ai_service: Optional[AIService] = None, settings_service: Optional[SettingsService] = None):
        """
        Initialize the content generation service.
        
        Args:
            ai_service: AI service for content generation
            settings_service: Settings service for AI configuration
        """
        # AIService requires SettingsService, so we need to handle initialization properly
        # For now, we'll accept an optional ai_service and create one if needed
        self.ai_service = ai_service
        self.settings_service = settings_service
    
    async def generate_attraction_description(
        self,
        attraction: Attraction,
        host: Host,
        language: str = "en"
    ) -> Optional[str]:
        """
        Generate compelling attraction description using AI.
        
        Args:
            attraction: Attraction model instance
            host: Host who owns the attraction
            language: Target language (en, hr, de, it)
            
        Returns:
            Generated description or None
        """
        try:
            # Build context for AI
            context = {
                "name": attraction.name,
                "type": attraction.attraction_type,
                "city": attraction.city,
                "region": attraction.region,
                "host_location": f"{host.city}, {self._host_region(host)}",
                "category_tags": attraction.category_tags or [],
                "existing_description": attraction.description or ""
            }
            
            prompt = f"""
            Generate a compelling, SEO-friendly description for a Croatian tourism attraction.
            
            Attraction Name: {context['name']}
            Type: {context['type']}
            Location: {context['city']}, {context['region']}
            Host Location: {context['host_location']}
            Categories: {', '.join(context['category_tags'])}
            
            Requirements:
            1. Write in {language} language
            2. Make it engaging and persuasive (150-300 words)
            3. Include what makes it special
            4. Mention how it relates to Croatian culture/tourism
            5. Include specific details (rating, types, price level if available)
            6. Connect it meaningfully to the host's location
            7. Mention nearby attractions for day trip planning
            8. Give persuasive reasons why guests should visit
            
            Generate the description now:
            """
            
            # Use AI service to generate content
            description = await self._generate_with_ai(prompt, language, str(host.id))
            
            if description:
                logger.info(f"Generated description for attraction {attraction.id} in {language}")
                return description

            base = attraction.description or attraction.short_description or ""
            if base:
                return base
            return (
                f"{attraction.name} is a {attraction.attraction_type} in {attraction.city}, "
                f"{self._host_region(host)} — recommended by your local host."
            )
            
        except Exception as e:
            logger.error(f"Error generating attraction description: {e}")
            return None
    
    async def generate_local_tips(
        self,
        host: Host,
        attraction: Optional[Attraction] = None,
        language: str = "en"
    ) -> List[str]:
        """
        Generate local tips based on host location and attraction.
        
        Args:
            host: Host instance
            attraction: Optional attraction for context
            language: Target language
            
        Returns:
            List of local tips
        """
        try:
            context = {
                "host_city": host.city,
                "host_region": self._host_region(host),
                "attraction_name": attraction.name if attraction else None,
                "attraction_type": attraction.attraction_type if attraction else None
            }
            
            prompt = f"""
            Generate 5-7 practical local tips for tourists visiting {context['host_city']}, {context['host_region'] or 'Croatia'}.
            
            {f"Context: The tip is related to {context['attraction_name']} ({context['attraction_type']})" if context['attraction_name'] else ""}
            
            Requirements:
            1. Write in {language} language
            2. Make tips practical and actionable
            3. Include insider knowledge that tourists wouldn't know
            4. Cover: best times to visit, hidden spots, local customs, transportation, food recommendations
            5. Be specific to the location
            
            Generate tips as a numbered list:
            """
            
            tips_text = await self._generate_with_ai(prompt, language, str(host.id))
            
            if tips_text:
                # Parse tips from numbered list
                tips = [tip.strip() for tip in tips_text.split('\n') if tip.strip() and (tip.strip()[0].isdigit() or tip.strip().startswith('-'))]
                return tips[:7]  # Limit to 7 tips
            
            return [
                f"Explore the waterfront and old town in {host.city}",
                f"Ask your host for seasonal events in {self._host_region(host)}",
                "Carry comfortable shoes for cobblestone streets and coastal paths",
            ]

        except Exception as e:
            logger.error(f"Error generating local tips: {e}")
            return [
                f"Visit {host.city} early morning for fewer crowds",
                "Try local seafood and Istrian olive oil",
            ]
    
    async def generate_multi_language_content(
        self,
        source_text: str,
        source_language: str,
        target_languages: List[str]
    ) -> Dict[str, str]:
        """
        Generate translations for content in multiple languages.
        
        Args:
            source_text: Source text to translate
            source_language: Source language code
            target_languages: List of target language codes
            
        Returns:
            Dictionary mapping language codes to translated text
        """
        translations = {}
        
        for target_lang in target_languages:
            if target_lang == source_language:
                translations[target_lang] = source_text
                continue
            
            try:
                prompt = f"""
                Translate the following text from {source_language} to {target_lang}.
                Maintain the tone, style, and meaning. Keep tourism terminology accurate.
                
                Text to translate:
                {source_text}
                
                Translation:
                """
                
                translation = await self._generate_with_ai(prompt, target_lang, None)
                if translation:
                    translations[target_lang] = translation
                    
            except Exception as e:
                logger.warning(f"Error translating to {target_lang}: {e}")
                continue
        
        return translations
    
    async def generate_seo_description(
        self,
        attraction: Attraction,
        keywords: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate SEO-optimized description for an attraction.
        
        Args:
            attraction: Attraction instance
            keywords: Optional list of SEO keywords
            
        Returns:
            SEO-optimized description
        """
        try:
            # Auto-generate keywords if not provided
            if not keywords:
                keywords = self._extract_keywords(attraction)
            
            prompt = f"""
            Generate an SEO-optimized description for a Croatian tourism attraction.
            
            Attraction: {attraction.name}
            Type: {attraction.attraction_type}
            Location: {attraction.city}, {attraction.region}
            Keywords to include: {', '.join(keywords)}
            
            Requirements:
            1. 150-250 words
            2. Naturally incorporate all keywords
            3. Include location-specific terms (e.g., "Lovran", "Istria", "Kvarner")
            4. Use semantic variations of keywords
            5. Make it readable and engaging (not keyword-stuffed)
            6. Include call-to-action
            
            SEO Description:
            """
            
            description = await self._generate_with_ai(prompt, "en", None)
            return description
            
        except Exception as e:
            logger.error(f"Error generating SEO description: {e}")
            return None
    
    async def generate_social_media_post(
        self,
        attraction: Attraction,
        post_type: str = "instagram",
        language: str = "en"
    ) -> Optional[str]:
        """
        Generate social media post for an attraction.
        
        Args:
            attraction: Attraction instance
            post_type: Type of post (instagram, facebook, twitter)
            language: Target language
            
        Returns:
            Social media post text
        """
        try:
            char_limit = {
                "instagram": 2200,
                "facebook": 5000,
                "twitter": 280
            }.get(post_type, 500)
            
            prompt = f"""
            Generate a {post_type} social media post about a Croatian tourism attraction.
            
            Attraction: {attraction.name}
            Location: {attraction.city}
            Type: {attraction.attraction_type}
            
            Requirements:
            1. Write in {language} language
            2. Maximum {char_limit} characters
            3. Engaging and shareable
            4. Include relevant hashtags
            5. Add a call-to-action
            6. Use emojis appropriately
            
            Social Media Post:
            """
            
            post = await self._generate_with_ai(prompt, language, None)
            if post:
                return post
            return (
                f"Discover {attraction.name} in {attraction.city}! "
                f"#{attraction.city.replace(' ', '')} #Croatia #VisitCroatia"
            )

        except Exception as e:
            logger.error(f"Error generating social media post: {e}")
            return (
                f"Explore {attraction.name} in {attraction.city} — "
                "a highlight of the Kvarner coast."
            )
    
    async def generate_email_template(
        self,
        template_type: str,
        host: Host,
        guest_group: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Optional[str]:
        """
        Generate email template for guest communications.
        
        Args:
            template_type: Type of email (welcome, pre_arrival, follow_up, etc.)
            host: Host instance
            guest_group: Optional guest group data
            language: Target language
            
        Returns:
            Email template text
        """
        try:
            templates = {
                "welcome": self._get_welcome_email_prompt,
                "pre_arrival": self._get_pre_arrival_email_prompt,
                "follow_up": self._get_follow_up_email_prompt
            }
            
            prompt_func = templates.get(template_type)
            if not prompt_func:
                logger.warning(f"Unknown email template type: {template_type}")
                return None
            
            prompt = prompt_func(host, guest_group, language)
            email_content = await self._generate_with_ai(prompt, language, str(host.id))

            if email_content:
                return email_content

            group_name = ""
            if guest_group and guest_group.get("group"):
                group_name = getattr(guest_group["group"], "group_name", None) or ""
            return (
                f"Dear {group_name or 'guest'},\n\n"
                f"Welcome from {self._host_display_name(host)} in {host.city}, {self._host_region(host)}.\n"
                f"We look forward to your stay.\n\nBest regards,\n{self._host_display_name(host)}"
            )
            
        except Exception as e:
            logger.error(f"Error generating email template: {e}")
            return None
    
    async def _generate_with_ai(
        self,
        prompt: str,
        language: str = "en",
        host_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate content using AI service.
        
        Args:
            prompt: Generation prompt
            language: Target language
            host_id: Optional host ID for AI configuration
            
        Returns:
            Generated content or None
        """
        try:
            if not self.ai_service:
                # Create AI service if not provided
                if not self.settings_service:
                    from sqlalchemy.ext.asyncio import AsyncSession
                    # We need a db session, but we can't create one here
                    # For now, log and return None
                    logger.warning("AI service and settings service not available")
                    return None
                self.ai_service = AIService(self.settings_service)
            
            if not host_id:
                # Use a default host ID or get from context
                host_id = "default"
            
            # Use AI service to generate content
            # Build messages for chat API
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # Generate response using AI service
            response = await self.ai_service.generate_chat_response(
                host_id=host_id,
                messages=messages,
                context={"language": language}
            )
            
            if response.get("success") and response.get("response"):
                return response["response"]
            
            logger.warning("AI generation returned no content")
            return None
            
        except Exception as e:
            logger.error(f"Error in AI generation: {e}")
            return None
    
    def _extract_keywords(self, attraction: Attraction) -> List[str]:
        """Extract SEO keywords from attraction."""
        keywords = [
            attraction.name,
            attraction.city,
            attraction.attraction_type,
            "Croatia",
            "tourism",
            "travel"
        ]
        
        if attraction.region:
            keywords.append(attraction.region)
        
        if attraction.category_tags:
            keywords.extend(attraction.category_tags[:5])
        
        return keywords
    
    def _get_welcome_email_prompt(
        self,
        host: Host,
        guest_group: Optional[Dict[str, Any]],
        language: str
    ) -> str:
        """Get prompt for welcome email."""
        return f"""
        Generate a warm, welcoming email for guests arriving at {host.city}, Croatia.
        
        Host: {self._host_display_name(host)}
        Location: {host.city}, {self._host_region(host)}
        {f"Guest Group: {guest_group.get('group_name', 'guests')}" if guest_group else ""}
        
        Requirements:
        1. Write in {language} language
        2. Warm and welcoming tone
        3. Include practical arrival information
        4. Mention local recommendations
        5. Offer assistance
        6. Professional but friendly
        
        Email Content:
        """
    
    def _get_pre_arrival_email_prompt(
        self,
        host: Host,
        guest_group: Optional[Dict[str, Any]],
        language: str
    ) -> str:
        """Get prompt for pre-arrival email."""
        return f"""
        Generate a pre-arrival email for guests coming to {host.city}, Croatia.
        
        Include:
        1. What to expect
        2. Weather information
        3. Local tips
        4. Recommended attractions
        5. Contact information
        
        Write in {language} language.
        """
    
    def _get_follow_up_email_prompt(
        self,
        host: Host,
        guest_group: Optional[Dict[str, Any]],
        language: str
    ) -> str:
        """Get prompt for follow-up email."""
        return f"""
        Generate a follow-up email after guests' stay in {host.city}, Croatia.
        
        Include:
        1. Thank you message
        2. Request for feedback/review
        3. Invitation to return
        4. Special offers if applicable
        
        Write in {language} language.
        """

