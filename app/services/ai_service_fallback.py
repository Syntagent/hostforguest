"""
AI Service with environment variable fallback for development.

This extends the main AI service to use environment variables when database
keys are not available, making development easier.
"""

import os
import logging
from typing import Dict, List, Optional, Any
import openai
import google.generativeai as genai
from app.services.ai_service import AIService
from app.services.settings_service import SettingsService

# Ensure environment variables are loaded
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class AIServiceWithFallback(AIService):
    """
    AI Service that falls back to environment variables for development.
    
    This makes it easier to test AI features without setting up database keys.
    """
    
    async def _get_openai_client(self, host_id: str) -> Optional[openai.AsyncOpenAI]:
        """Get configured OpenAI client with environment variable fallback."""
        try:
            # For onboarding flow, use environment variable directly
            if host_id == "onboarding":
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    logger.info(f"Using OpenAI API key from environment for onboarding flow")
                    return openai.AsyncOpenAI(api_key=api_key)
                else:
                    logger.warning(f"No OpenAI API key found for onboarding flow")
                    return None
            
            # Try to get API key from database first
            api_key = await self.settings_service.get_host_api_key(host_id, "openai")
            
            # Fallback to environment variable
            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    logger.info(f"Using OpenAI API key from environment for host {host_id}")
                else:
                    logger.warning(f"No OpenAI API key found for host {host_id}")
                    return None
                
            return openai.AsyncOpenAI(api_key=api_key)
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            return None
    
    async def _get_gemini_model(self, host_id: str, model_name: str) -> Optional[Any]:
        """Get configured Gemini model with environment variable fallback."""
        try:
            # For onboarding flow, use environment variable directly
            if host_id == "onboarding":
                api_key = os.getenv('GOOGLE_AI_API_KEY')
                if not api_key:
                    logger.warning(f"No Google AI API key found for onboarding flow")
                    return None
                logger.info(f"Using Google AI API key from environment for onboarding flow")
            else:
                # Try to get API key from database first
                api_key = await self.settings_service.get_host_api_key(host_id, "google_ai")
                
                # Fallback to environment variable
                if not api_key:
                    api_key = os.getenv('GOOGLE_AI_API_KEY')
                    if api_key:
                        logger.info(f"Using Google AI API key from environment for host {host_id}")
                    else:
                        logger.warning(f"No Google AI API key found for host {host_id}")
                        return None
            
            # Configure Gemini with the API key
            genai.configure(api_key=api_key)
            
            # Configure safety settings for tourism content - DISABLE ALL FILTERS
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            model = genai.GenerativeModel(
                model_name=model_name,
                safety_settings=safety_settings
            )
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model {model_name}: {e}")
            return None

    async def get_ai_config_for_host_with_fallback(self, host_id: str) -> Dict[str, Any]:
        """Get AI configuration with environment variable defaults."""
        try:
            # For onboarding flow, use environment defaults directly
            if host_id == "onboarding":
                return {
                    "preferred_ai_provider": os.getenv('PREFERRED_AI_PROVIDER', 'google'),
                    "openai_model": os.getenv('OPENAI_MODEL', 'gpt-4o'),
                    "gemini_model": os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
                    "gemini_pro_model": os.getenv('GEMINI_PRO_MODEL', 'gemini-2.5-pro'),
                    "gemini_temperature": float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
                    "embedding_provider": os.getenv('EMBEDDING_PROVIDER', 'openai'),
                    "embedding_model": os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small'),
                    "default_language": os.getenv('DEFAULT_LANGUAGE', 'en')
                }
            
            # Try to get from database first
            ai_config = await self.settings_service.get_ai_config_for_host(host_id)
            
            # Apply environment variable defaults if not set
            defaults = {
                "preferred_ai_provider": os.getenv('PREFERRED_AI_PROVIDER', 'google'),
                "openai_model": os.getenv('OPENAI_MODEL', 'gpt-4o'),
                "gemini_model": os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
                "gemini_pro_model": os.getenv('GEMINI_PRO_MODEL', 'gemini-2.5-pro'),
                "gemini_temperature": os.getenv('GEMINI_TEMPERATURE', '0.7'),
                "embedding_provider": os.getenv('EMBEDDING_PROVIDER', 'openai'),
                "embedding_model": os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small'),
                "default_language": os.getenv('DEFAULT_LANGUAGE', 'en')
            }
            
            # Merge with defaults
            for key, default_value in defaults.items():
                if key not in ai_config or not ai_config[key]:
                    ai_config[key] = default_value
            
            return ai_config
            
        except Exception as e:
            logger.error(f"Failed to get AI config for host {host_id}: {e}")
            # Return environment defaults
            return {
                "preferred_ai_provider": os.getenv('PREFERRED_AI_PROVIDER', 'google'),
                "openai_model": os.getenv('OPENAI_MODEL', 'gpt-4o'),
                "gemini_model": os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
                "gemini_pro_model": os.getenv('GEMINI_PRO_MODEL', 'gemini-2.5-pro'),
                "gemini_temperature": os.getenv('GEMINI_TEMPERATURE', '0.7'),
                "embedding_provider": os.getenv('EMBEDDING_PROVIDER', 'openai'),
                "embedding_model": os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small'),
                "default_language": os.getenv('DEFAULT_LANGUAGE', 'en')
            }

    async def generate_chat_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate chat response with fallback configuration."""
        try:
            # Get AI configuration with fallback
            ai_config = await self.get_ai_config_for_host_with_fallback(host_id)
            preferred_provider = ai_config.get("preferred_ai_provider", "google")
            
            # Add Croatian tourism context if provided
            if context:
                system_context = self._build_system_context(context, ai_config)
                messages = [{"role": "system", "content": system_context}] + messages
            
            # Try preferred provider first
            if preferred_provider == "openai" or preferred_provider == "both":
                response = await self._generate_openai_response(
                    host_id, messages, ai_config, use_reasoning
                )
                if response["success"]:
                    return response
            
            if preferred_provider == "google" or preferred_provider == "both":
                response = await self._generate_gemini_response(
                    host_id, messages, ai_config, use_reasoning
                )
                if response["success"]:
                    return response
            
            # Provide helpful error message for missing keys
            missing_keys = []
            if not os.getenv('OPENAI_API_KEY'):
                missing_keys.append("OPENAI_API_KEY")
            if not os.getenv('GOOGLE_AI_API_KEY'):
                missing_keys.append("GOOGLE_AI_API_KEY")
            
            error_msg = "AI service not configured. "
            if missing_keys:
                error_msg += f"Missing environment variables: {', '.join(missing_keys)}. "
                error_msg += "Please set these in your .env file or run 'python setup_ai_keys.py'."
            
            return {
                "success": False,
                "response": error_msg,
                "model": "none",
                "provider": "none",
                "error": "No available AI providers configured"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate chat response: {e}")
            return {
                "success": False,
                "response": "An error occurred while processing your request.",
                "error": str(e)
            }
    
    async def generate_structured_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        response_schema: Optional[Any] = None,
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a structured response using Pydantic schema enforcement.
        
        Args:
            host_id: Host UUID
            messages: List of chat messages
            context: Additional context
            response_schema: Pydantic model class for structured output
            use_reasoning: Whether to use reasoning models
            
        Returns:
            Dict with structured response
        """
        try:
            # Get AI configuration for host
            ai_config = await self.get_ai_config_for_host_with_fallback(host_id)
            preferred_provider = ai_config.get("preferred_ai_provider", "google")
            
            # Add Croatian tourism context if provided
            if context:
                system_context = self._build_system_context(context, ai_config)
                messages = [{"role": "system", "content": system_context}] + messages
            
            # Use Google Gemini with structured output (preferred for Pydantic)
            if preferred_provider == "google" or preferred_provider == "both":
                response = await self._generate_gemini_structured_response(
                    host_id, messages, ai_config, response_schema, use_reasoning
                )
                if response["success"]:
                    return response
            
            # Fallback to regular chat response if structured output fails
            return await self.generate_chat_response(host_id, messages, context, use_reasoning)
            
        except Exception as e:
            logger.error(f"Failed to generate structured response: {e}")
            return {
                "success": False,
                "response": "An error occurred while processing your request.",
                "error": str(e)
            }
    
    async def _generate_gemini_structured_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        response_schema: Any,
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """
        Generate structured response using Google Gemini with enhanced fallback handling.
        
        This method implements a robust approach to handle Gemini's inconsistent
        native Pydantic support by combining structured output attempts with
        intelligent fallback parsing.
        """
        try:
            # Select model based on reasoning requirement
            if use_reasoning:
                model_name = ai_config.get("gemini_pro_model", "gemini-2.5-pro")
            else:
                model_name = ai_config.get("gemini_model", "gemini-2.5-flash")
            
            # Use our overridden _get_gemini_model method
            model = await self._get_gemini_model(host_id, model_name)
            if not model:
                return {"success": False, "error": "Gemini model not available"}
            
            # Convert messages to Gemini format
            gemini_messages = self._convert_to_gemini_format(messages)
            
            # Generate response with structured output
            import google.generativeai as genai
            import json
            
            # ATTEMPT 1: Try native Pydantic structured output
            logger.info(f"Attempting native Gemini structured output with schema: {response_schema.__name__ if response_schema else 'None'}")
            
            try:
                generation_config = genai.types.GenerationConfig(
                    temperature=float(ai_config.get("gemini_temperature", "0.7")),
                    max_output_tokens=2000,
                    response_mime_type="application/json"
                )
                
                # Add response schema if provided
                if response_schema:
                    generation_config.response_schema = response_schema
                
                response = await model.generate_content_async(
                    gemini_messages,
                    generation_config=generation_config
                )
                
                if response and response.text:
                    structured_data = json.loads(response.text)
                    
                    # Validate with Pydantic if schema provided
                    if response_schema:
                        # Try to validate - this is where the original error occurred
                        try:
                            validated_data = response_schema(**structured_data)
                            logger.info("✅ Native Gemini structured output successful")
                            return {
                                "success": True,
                                "response": response.text,
                                "structured_data": validated_data.model_dump(),
                                "model": model_name,
                                "provider": "google_gemini_native",
                                "usage": getattr(response, 'usage_metadata', {})
                            }
                        except Exception as validation_error:
                            logger.warning(f"Native structured output validation failed: {validation_error}")
                            logger.info(f"Received data keys: {list(structured_data.keys())}")
                            # Continue to ATTEMPT 2
                    else:
                        return {
                            "success": True,
                            "response": response.text,
                            "structured_data": structured_data,
                            "model": model_name,
                            "provider": "google_gemini_native",
                            "usage": getattr(response, 'usage_metadata', {})
                        }
                        
            except Exception as native_error:
                logger.warning(f"Native structured output failed: {native_error}")
                # Continue to ATTEMPT 2
            
            # ATTEMPT 2: Enhanced JSON-guided generation with explicit field requirements
            logger.info("Attempting enhanced JSON-guided generation with explicit schema")
            
            # Modify the prompt to explicitly request all required fields
            if response_schema and messages:
                # Get the schema field information
                schema_fields = {}
                if hasattr(response_schema, 'model_fields'):
                    schema_fields = response_schema.model_fields
                elif hasattr(response_schema, '__annotations__'):
                    schema_fields = response_schema.__annotations__
                
                # Create explicit field requirements
                field_requirements = []
                for field_name, field_info in schema_fields.items():
                    if hasattr(field_info, 'description'):
                        field_requirements.append(f'"{field_name}": {field_info.description}')
                    else:
                        field_requirements.append(f'"{field_name}": Array of strings for {field_name.replace("_", " ")}')
                
                # Enhance the last user message with explicit JSON requirements
                enhanced_messages = messages.copy()
                if enhanced_messages:
                    last_message = enhanced_messages[-1]
                    _req_sep = ",\n  "
                    enhanced_content = f"""{last_message['content']}

CRITICAL: You MUST return valid JSON with ALL of these exact fields:
{{
  {_req_sep.join(field_requirements)}
}}

Each field must be an array of strings. Do not omit any fields. Return ONLY the JSON object, no additional text."""
                    
                    enhanced_messages[-1] = {
                        "role": last_message["role"],
                        "content": enhanced_content
                    }
                    
                    gemini_messages_enhanced = self._convert_to_gemini_format(enhanced_messages)
                    
                    # Generate with basic JSON mode (no schema constraint)
                    generation_config_basic = genai.types.GenerationConfig(
                        temperature=float(ai_config.get("gemini_temperature", "0.7")),
                        max_output_tokens=2000,
                        response_mime_type="application/json"
                    )
                    
                    response = await model.generate_content_async(
                        gemini_messages_enhanced,
                        generation_config=generation_config_basic
                    )
                    
                    if response and response.text:
                        try:
                            structured_data = json.loads(response.text)
                            
                            # Validate with Pydantic
                            validated_data = response_schema(**structured_data)
                            logger.info("✅ Enhanced JSON-guided generation successful")
                            return {
                                "success": True,
                                "response": response.text,
                                "structured_data": validated_data.model_dump(),
                                "model": model_name,
                                "provider": "google_gemini_enhanced",
                                "usage": getattr(response, 'usage_metadata', {})
                            }
                        except Exception as enhanced_error:
                            logger.warning(f"Enhanced generation validation failed: {enhanced_error}")
                            logger.info(f"Raw response: {response.text[:500]}")
                            # Continue to ATTEMPT 3
            
            # ATTEMPT 3: Fallback to regular generation with intelligent parsing
            logger.info("Attempting fallback generation with intelligent parsing")
            
            # Generate regular response and use existing parsing logic
            generation_config_fallback = genai.types.GenerationConfig(
                temperature=float(ai_config.get("gemini_temperature", "0.7")),
                max_output_tokens=2000
            )
            
            response = await model.generate_content_async(
                gemini_messages,
                generation_config=generation_config_fallback
            )
            
            if response and response.text:
                # Use the existing parsing logic from host_onboarding_service
                if response_schema:
                    # Import the parsing function
                    from app.services.host_onboarding_service import HostOnboardingService
                    
                    # Create a temporary instance to use the parsing method
                    temp_service = HostOnboardingService.__new__(HostOnboardingService)
                    parsed_data = temp_service._parse_profile_suggestions_DEPRECATED(
                        response.text, 
                        context={"host": {}, "location": {}, "property": {}}  # Basic context
                    )
                    
                    logger.info("✅ Fallback parsing successful")
                    return {
                        "success": True,
                        "response": response.text,
                        "structured_data": parsed_data,
                        "model": model_name,
                        "provider": "google_gemini_fallback",
                        "usage": getattr(response, 'usage_metadata', {})
                    }
                else:
                    return {
                        "success": True,
                        "response": response.text,
                        "structured_data": {"raw_response": response.text},
                        "model": model_name,
                        "provider": "google_gemini_fallback",
                        "usage": getattr(response, 'usage_metadata', {})
                    }
            else:
                return {"success": False, "error": "Empty response from Gemini"}
                
        except Exception as e:
            logger.error(f"All Gemini structured response attempts failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_gemini_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate response using Google Gemini models with environment fallback."""
        try:
            # Select model based on reasoning requirement
            if use_reasoning:
                model_name = ai_config.get("gemini_pro_model", "gemini-2.5-pro")
            else:
                model_name = ai_config.get("gemini_model", "gemini-2.5-flash")
            
            # Use our overridden _get_gemini_model method
            model = await self._get_gemini_model(host_id, model_name)
            if not model:
                return {"success": False, "error": "Gemini model not available"}
            
            # Convert messages to Gemini format
            gemini_messages = self._convert_to_gemini_format(messages)
            
            # Generate response
            import google.generativeai as genai
            response = await model.generate_content_async(
                gemini_messages,
                generation_config=genai.types.GenerationConfig(
                    temperature=float(ai_config.get("gemini_temperature", "0.7")),
                    max_output_tokens=2000,
                )
            )
            
            return {
                "success": True,
                "response": response.text,
                "model": model_name,
                "provider": "google",
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                    "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_openai_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate response using OpenAI models with environment fallback."""
        try:
            # Use our overridden _get_openai_client method
            client = await self._get_openai_client(host_id)
            if not client:
                return {"success": False, "error": "OpenAI client not available"}
            
            # Select model based on reasoning requirement
            if use_reasoning:
                model_name = ai_config.get("openai_reasoning_model", "gpt-4o")
            else:
                model_name = ai_config.get("openai_model", "gpt-4o")
            
            # Generate response
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=float(ai_config.get("openai_temperature", "0.7")),
                max_tokens=2000
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "model": model_name,
                "provider": "openai",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return {"success": False, "error": str(e)}
