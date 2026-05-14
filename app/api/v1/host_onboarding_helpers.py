"""
Helper functions for host onboarding analysis and validation.

Contains utility functions for profile analysis, scoring, and suggestions.
"""

from typing import List, Optional, Dict, Any
from app.api.v1.host_onboarding_models import (
    LocalExperience,
    EnhancedAttractionSuggestionsRequest
)


def calculate_experience_score(experience: Optional[LocalExperience]) -> float:
    """
    Calculate experience score based on local experience level.
    
    Args:
        experience: Local experience enum value
        
    Returns:
        Experience score (0.0 to 1.0)
    """
    if not experience:
        return 0.3
    
    experience_scores = {
        LocalExperience.BORN_HERE: 1.0,
        LocalExperience.FIFTEEN_PLUS_YEARS: 0.9,
        LocalExperience.FIVE_TO_15_YEARS: 0.7,
        LocalExperience.ONE_TO_5_YEARS: 0.5,
        LocalExperience.LESS_THAN_1_YEAR: 0.3
    }
    
    return experience_scores.get(experience, 0.3)


def analyze_guest_alignment(preferred_guests: List[str]) -> Dict[str, Any]:
    """
    Analyze alignment between host preferences and guest types.
    
    Args:
        preferred_guests: List of preferred guest types
        
    Returns:
        Analysis dictionary with alignment metrics
    """
    if not preferred_guests:
        return {
            "score": 0.5,
            "coverage": "limited",
            "recommendations": ["Define target guest segments for better personalization"]
        }
    
    score = min(len(preferred_guests) / 3.0, 1.0)
    
    return {
        "score": score,
        "coverage": "broad" if len(preferred_guests) >= 3 else "focused",
        "recommendations": []
    }


def analyze_story_quality(story: Optional[str]) -> Dict[str, Any]:
    """
    Analyze quality and authenticity of location story.
    
    Args:
        story: Host's location story text
        
    Returns:
        Analysis dictionary with quality metrics
    """
    if not story:
        return {
            "score": 0.0,
            "word_count": 0,
            "authenticity_keywords": 0,
            "quality": "missing",
            "suggestions": ["Add a personal story about your connection to the area"]
        }
    
    word_count = len(story.split())
    
    authenticity_keywords = [
        "family", "generation", "local", "native", "secret", "hidden",
        "tradition", "cultural", "heritage", "childhood", "memories"
    ]
    keyword_matches = sum(1 for keyword in authenticity_keywords if keyword.lower() in story.lower())
    
    score = min((word_count / 100.0) + (keyword_matches / len(authenticity_keywords)), 1.0)
    
    return {
        "score": score,
        "word_count": word_count,
        "authenticity_keywords": keyword_matches,
        "quality": "excellent" if score >= 0.8 else "good" if score >= 0.6 else "needs_improvement",
        "suggestions": generate_story_suggestions(score, word_count, keyword_matches)
    }


def extract_authenticity_indicators(story: Optional[str]) -> List[str]:
    """
    Extract authenticity indicators from the story.
    
    Args:
        story: Host's location story
        
    Returns:
        List of authenticity indicator strings
    """
    if not story:
        return []
    
    indicators = []
    story_lower = story.lower()
    
    if "family" in story_lower or "generation" in story_lower:
        indicators.append("family_heritage")
    if "local" in story_lower or "native" in story_lower:
        indicators.append("local_knowledge")
    if "secret" in story_lower or "hidden" in story_lower:
        indicators.append("insider_access")
    if "tradition" in story_lower or "cultural" in story_lower:
        indicators.append("cultural_connection")
    
    return indicators


def generate_improvement_suggestions(request: EnhancedAttractionSuggestionsRequest) -> List[str]:
    """
    Generate improvement suggestions based on request data.
    
    Args:
        request: Enhanced attraction suggestions request
        
    Returns:
        List of improvement suggestion strings
    """
    suggestions = []
    
    if not request.location_story:
        suggestions.append("Add a personal story about your connection to the area")
    
    if len(request.interests) < 3:
        suggestions.append("Expand your interests/specialties to show diverse knowledge")
    
    if len(request.preferred_guests) < 2:
        suggestions.append("Define multiple target guest segments for broader appeal")
    
    if not request.coordinates:
        suggestions.append("Verify your location with Google Places for better accuracy")
    
    return suggestions


def identify_marketing_angles(request: EnhancedAttractionSuggestionsRequest) -> List[str]:
    """
    Identify potential marketing angles.
    
    Args:
        request: Enhanced attraction suggestions request
        
    Returns:
        List of marketing angle strings
    """
    angles = []
    
    if request.local_experience in [LocalExperience.BORN_HERE, LocalExperience.FIFTEEN_PLUS_YEARS]:
        angles.append("Deep local expertise and insider knowledge")
    
    if "food" in [i.lower() for i in request.interests]:
        angles.append("Authentic Croatian culinary experiences")
    
    if "nature" in [i.lower() for i in request.interests]:
        angles.append("Hidden natural gems and outdoor adventures")
    
    if request.location_story and len(request.location_story) > 100:
        angles.append("Rich personal connection and storytelling")
    
    return angles


def identify_competitive_advantages(request: EnhancedAttractionSuggestionsRequest) -> List[str]:
    """
    Identify competitive advantages.
    
    Args:
        request: Enhanced attraction suggestions request
        
    Returns:
        List of competitive advantage strings
    """
    advantages = []
    
    if request.local_experience == LocalExperience.BORN_HERE:
        advantages.append("Born and raised local - unmatched area knowledge")
    
    if len(request.interests) >= 5:
        advantages.append("Diverse expertise across multiple areas")
    
    if request.location_story and "generation" in request.location_story.lower():
        advantages.append("Multi-generational family connection to the area")
    
    return advantages


def calculate_confidence_score(request: EnhancedAttractionSuggestionsRequest) -> float:
    """
    Calculate overall confidence score for the analysis.
    
    Args:
        request: Enhanced attraction suggestions request
        
    Returns:
        Confidence score (0.0 to 1.0)
    """
    score = 0.0
    
    # Location data completeness
    if request.coordinates:
        score += 0.2
    if request.address:
        score += 0.1
    
    # Experience and knowledge
    experience_scores = {
        LocalExperience.BORN_HERE: 0.3,
        LocalExperience.FIFTEEN_PLUS_YEARS: 0.25,
        LocalExperience.FIVE_TO_15_YEARS: 0.2,
        LocalExperience.ONE_TO_5_YEARS: 0.15,
        LocalExperience.LESS_THAN_1_YEAR: 0.1
    }
    
    if request.local_experience:
        score += experience_scores.get(request.local_experience, 0.1)
    
    # Interests and specialties
    if len(request.interests) >= 5:
        score += 0.2
    elif len(request.interests) >= 3:
        score += 0.1
    
    # Story quality
    if request.location_story:
        story_analysis = analyze_story_quality(request.location_story)
        score += story_analysis["score"] * 0.2
    
    return min(1.0, score)


def generate_guest_recommendations(preferred_guests: List[str]) -> List[str]:
    """
    Generate guest type recommendations.
    
    Args:
        preferred_guests: List of preferred guest types
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    if "families" not in preferred_guests:
        recommendations.append("Consider adding families - great for longer stays")
    
    if "couples" not in preferred_guests:
        recommendations.append("Couples often seek romantic experiences")
    
    if "solo_travelers" not in preferred_guests:
        recommendations.append("Solo travelers appreciate local insights")
    
    return recommendations


def generate_story_suggestions(score: float, word_count: int, keyword_matches: int) -> List[str]:
    """
    Generate story improvement suggestions.
    
    Args:
        score: Story quality score
        word_count: Number of words in story
        keyword_matches: Number of authenticity keywords found
        
    Returns:
        List of suggestion strings
    """
    suggestions = []
    
    if word_count < 50:
        suggestions.append("Expand your story to at least 100 words for better engagement")
    
    if keyword_matches < 3:
        suggestions.append("Include more personal details about your connection to the area")
    
    if score < 0.6:
        suggestions.append("Add specific memories or experiences that make your location special")
    
    return suggestions


def generate_actionable_insights(analysis: Dict[str, Any]) -> List[str]:
    """
    Generate actionable insights from analysis.
    
    Args:
        analysis: Analysis dictionary
        
    Returns:
        List of actionable insight strings
    """
    insights = []
    
    if analysis.get("confidence_score", 0) < 0.7:
        insights.append("Complete your profile to increase recommendation accuracy")
    
    if analysis.get("story_quality", {}).get("score", 0) < 0.6:
        insights.append("Enhance your location story to better connect with guests")
    
    if len(analysis.get("marketing_angles", [])) < 2:
        insights.append("Define your unique selling points for better marketing")
    
    return insights


def suggest_next_steps(analysis: Dict[str, Any]) -> List[str]:
    """
    Suggest next steps based on analysis.
    
    Args:
        analysis: Analysis dictionary
        
    Returns:
        List of next step strings
    """
    steps = []
    
    if analysis.get("completeness_score", 0) < 80:
        steps.append("Complete missing profile sections")
    
    if not analysis.get("google_verified", False):
        steps.append("Verify location with Google Places")
    
    if len(analysis.get("improvement_suggestions", [])) > 0:
        steps.append("Review and implement improvement suggestions")
    
    steps.append("Generate attraction suggestions based on your profile")
    
    return steps

