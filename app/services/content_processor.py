"""
Content processor service for analyzing and processing scraped content.

Processes content from Crawl4AI scraper with AI analysis, quality scoring,
and structured data extraction for Croatian tourism information.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import AIService
from app.models.content_source import ContentUpdate, ContentType

logger = logging.getLogger(__name__)


class ContentProcessor:
    """
    Service for processing scraped content with AI analysis.
    
    Provides content quality scoring, categorization, and structured
    data extraction from raw scraped content.
    """
    
    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        """
        Initialize the content processor.
        
        Args:
            db: Database session
            ai_service: AI service for content analysis
        """
        self.db = db
        self.ai_service = ai_service or AIService()
    
    async def process_content(
        self,
        raw_content: Dict[str, Any],
        source_url: str,
        extraction_strategy: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process raw scraped content with AI analysis.
        
        Args:
            raw_content: Raw content from scraper
            source_url: URL of the source
            extraction_strategy: Strategy used for extraction
            
        Returns:
            Processed content dictionary or None if processing fails
        """
        try:
            # Extract basic information
            title = raw_content.get('title', raw_content.get('naziv', ''))
            content = raw_content.get('content', raw_content.get('opis', ''))
            
            if not content and not title:
                logger.warning(f"No content found in raw_content: {raw_content}")
                return None
            
            # Analyze content with AI
            analysis = await self._analyze_content_with_ai(title, content)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(raw_content, analysis)
            
            # Detect content type
            content_type = self._detect_content_type(title, content, analysis)
            
            # Extract structured data
            structured_data = await self._extract_structured_data(raw_content, analysis)
            
            # Build processed content
            processed = {
                "title": title or "Untitled",
                "content": content,
                "content_type": content_type,
                "quality_score": quality_score,
                "relevance_score": analysis.get('relevance_score', 0.5),
                "keywords": analysis.get('keywords', []),
                "relevant_cities": structured_data.get('cities', []),
                "relevant_regions": structured_data.get('regions', []),
                "url": raw_content.get('url', raw_content.get('link', source_url)),
                "publication_date": structured_data.get('date'),
                "extraction_strategy": extraction_strategy,
                "metadata": {
                    "source_url": source_url,
                    "language": analysis.get('language', 'hr'),
                    "sentiment": analysis.get('sentiment', 'neutral'),
                    "structured_data": structured_data
                }
            }
            
            logger.info(f"Processed content: {title[:50]}... (quality: {quality_score:.2f})")
            return processed
            
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            return None
    
    async def _analyze_content_with_ai(
        self,
        title: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Analyze content using AI service.
        
        Args:
            title: Content title
            content: Content text
            
        Returns:
            Analysis results dictionary
        """
        try:
            if not self.ai_service:
                return {
                    "relevance_score": 0.5,
                    "keywords": [],
                    "language": "hr",
                    "sentiment": "neutral"
                }
            
            # Use AI to analyze content
            full_text = f"{title}\n{content}"
            
            # Extract keywords and relevance
            analysis_prompt = f"""
            Analyze this Croatian tourism content and extract:
            1. Key topics and keywords
            2. Relevance to Croatian tourism (0-1 score)
            3. Language (hr/en/de/it)
            4. Sentiment (positive/neutral/negative)
            5. Main cities/regions mentioned
            
            Content: {full_text[:500]}
            """
            
            # For now, return basic analysis
            # In production, this would call AI service
            keywords = self._extract_keywords_basic(title, content)
            
            return {
                "relevance_score": 0.7,  # Default relevance
                "keywords": keywords,
                "language": self._detect_language_basic(content),
                "sentiment": "positive",
                "cities": self._extract_cities_basic(content),
                "regions": self._extract_regions_basic(content)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content with AI: {e}")
            return {
                "relevance_score": 0.5,
                "keywords": [],
                "language": "hr",
                "sentiment": "neutral"
            }
    
    def _calculate_quality_score(
        self,
        raw_content: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate quality score for content.
        
        Args:
            raw_content: Raw content dictionary
            analysis: AI analysis results
            
        Returns:
            Quality score between 0 and 1
        """
        score = 0.0
        
        # Title presence (0.2)
        if raw_content.get('title') or raw_content.get('naziv'):
            score += 0.2
        
        # Content length (0.3)
        content = raw_content.get('content', raw_content.get('opis', ''))
        if len(content) > 100:
            score += 0.3
        elif len(content) > 50:
            score += 0.15
        
        # URL presence (0.1)
        if raw_content.get('url') or raw_content.get('link'):
            score += 0.1
        
        # Relevance score from AI (0.3)
        relevance = analysis.get('relevance_score', 0.5)
        score += relevance * 0.3
        
        # Keywords presence (0.1)
        if analysis.get('keywords'):
            score += 0.1
        
        return min(score, 1.0)
    
    def _detect_content_type(
        self,
        title: str,
        content: str,
        analysis: Dict[str, Any]
    ) -> str:
        """
        Detect content type from title and content.
        
        Args:
            title: Content title
            content: Content text
            analysis: AI analysis results
            
        Returns:
            Content type string
        """
        text = f"{title} {content}".lower()
        
        # Croatian and English keywords
        if any(word in text for word in ['događaj', 'event', 'festival', 'manifestacija']):
            return ContentType.EVENTS
        elif any(word in text for word in ['atrakcija', 'attraction', 'muzej', 'museum']):
            return ContentType.ATTRACTIONS
        elif any(word in text for word in ['radno vrijeme', 'opening hours', 'otvoreno']):
            return ContentType.OPENING_HOURS
        elif any(word in text for word in ['cijena', 'price', 'ulaznica', 'ticket']):
            return ContentType.PRICES
        else:
            return ContentType.NEWS
    
    async def _extract_structured_data(
        self,
        raw_content: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured data from content.
        
        Args:
            raw_content: Raw content dictionary
            analysis: AI analysis results
            
        Returns:
            Structured data dictionary
        """
        return {
            "cities": analysis.get('cities', []),
            "regions": analysis.get('regions', []),
            "date": raw_content.get('date', raw_content.get('datum')),
            "location": raw_content.get('location', raw_content.get('lokacija', '')),
            "opening_hours": raw_content.get('opening_hours', raw_content.get('radno_vrijeme', '')),
            "price": raw_content.get('price', raw_content.get('cijena', '')),
            "contact": raw_content.get('contact', raw_content.get('kontakt', ''))
        }
    
    def _extract_keywords_basic(self, title: str, content: str) -> List[str]:
        """Extract keywords using basic text analysis."""
        text = f"{title} {content}".lower()
        keywords = []
        
        # Croatian tourism keywords
        tourism_keywords = [
            'lovran', 'opatija', 'istria', 'kvarner', 'croatia', 'hrvatska',
            'beach', 'plaža', 'restaurant', 'konoba', 'wine', 'vino',
            'hiking', 'šetnja', 'culture', 'kultura', 'festival'
        ]
        
        for keyword in tourism_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        return keywords[:10]  # Limit to 10 keywords
    
    def _detect_language_basic(self, text: str) -> str:
        """Detect language using basic heuristics."""
        croatian_chars = ['č', 'ć', 'đ', 'š', 'ž', 'Č', 'Ć', 'Đ', 'Š', 'Ž']
        if any(char in text for char in croatian_chars):
            return 'hr'
        elif any(word in text.lower() for word in ['the', 'and', 'is', 'are']):
            return 'en'
        elif any(word in text.lower() for word in ['der', 'die', 'das', 'und']):
            return 'de'
        elif any(word in text.lower() for word in ['il', 'la', 'e', 'di']):
            return 'it'
        return 'hr'  # Default to Croatian
    
    def _extract_cities_basic(self, text: str) -> List[str]:
        """Extract city names from text."""
        cities = ['lovran', 'opatija', 'rijeka', 'pula', 'rovinj', 'poreč', 'zadar', 'split', 'dubrovnik']
        found = []
        text_lower = text.lower()
        for city in cities:
            if city in text_lower:
                found.append(city.capitalize())
        return found
    
    def _extract_regions_basic(self, text: str) -> List[str]:
        """Extract region names from text."""
        regions = ['istria', 'istra', 'kvarner', 'dalmatia', 'dalmacija', 'slavonia', 'slavonija']
        found = []
        text_lower = text.lower()
        for region in regions:
            if region in text_lower:
                found.append(region.capitalize())
        return found

