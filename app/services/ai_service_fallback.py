"""
AI Service with environment variable fallback for development.

This extends the main AI service to use environment variables when database
keys are not available, making development easier.
"""

import os
import logging
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Union
from app.services.ai_service import AIService, _import_google_genai, _import_openai

# Ensure environment variables are loaded
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class _GeminiModelAdapter:
    """Adapter for old generate_content_async call sites using google.genai."""

    def __init__(self, *, client: Any, model_name: str, genai_types: Any) -> None:
        self.client = client
        self.model_name = model_name
        self.genai_types = genai_types

    def _config(self, generation_config: Any = None) -> Any:
        if generation_config is None:
            return None
        kwargs: dict[str, Any] = {}
        for key in ("temperature", "max_output_tokens", "response_mime_type", "response_schema"):
            value = getattr(generation_config, key, None)
            if value is not None:
                kwargs[key] = value
        return self.genai_types.GenerateContentConfig(**kwargs)

    async def generate_content_async(self, contents: Any, generation_config: Any = None) -> Any:
        return await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=self._config(generation_config),
        )


def _generation_config_factory(**kwargs: Any) -> Any:
    return SimpleNamespace(**kwargs)


class _GenerationTypesCompat:
    GenerationConfig = staticmethod(_generation_config_factory)

class AIServiceWithFallback(AIService):
    """
    AI Service that falls back to environment variables for development.
    
    This makes it easier to test AI features without setting up database keys.
    """
    
    async def _get_openai_client(self, host_id: str) -> Optional[Any]:
        """Get configured OpenAI client with environment variable fallback."""
        try:
            # For onboarding flow, use environment variable directly
            if host_id == "onboarding":
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    logger.info(f"Using OpenAI API key from environment for onboarding flow")
                    openai = _import_openai()
                    return openai.AsyncOpenAI(api_key=api_key)
                else:
                    logger.warning(f"No OpenAI API key found for onboarding flow")
                    return None
            
            # Try to get API key from database first
            api_key = None
            if self.settings_service:
                api_key = await self.settings_service.get_host_api_key(host_id, "openai")
            
            # Fallback to environment variable
            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    logger.info(f"Using OpenAI API key from environment for host {host_id}")
                else:
                    logger.warning(f"No OpenAI API key found for host {host_id}")
                    return None
                
            openai = _import_openai()
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
                api_key = None
                if self.settings_service:
                    api_key = await self.settings_service.get_host_api_key(host_id, "google_ai")
                
                # Fallback to environment variable
                if not api_key:
                    api_key = os.getenv('GOOGLE_AI_API_KEY')
                    if api_key:
                        logger.info(f"Using Google AI API key from environment for host {host_id}")
                    else:
                        logger.warning(f"No Google AI API key found for host {host_id}")
                        return None
            
            genai, genai_types = _import_google_genai()
            return _GeminiModelAdapter(
                client=genai.Client(api_key=api_key),
                model_name=model_name,
                genai_types=genai_types,
            )
            
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
            ai_config = {}
            if self.settings_service:
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
    
    @staticmethod
    def _gemini_structured_content_payload(
        text_blob: str,
        image_parts: Optional[List[Tuple[str, bytes]]],
    ) -> Union[str, List[Any]]:
        """
        Gemini accepts either a string or a list of interleaved text + image dicts
        (``mime_type`` + ``data`` bytes per Google AI SDK).
        """
        if not image_parts:
            return text_blob
        parts: List[Any] = [text_blob]
        for mime, raw in image_parts[:6]:
            if not raw or not mime:
                continue
            parts.append({"mime_type": mime, "data": raw})
        return parts if len(parts) > 1 else text_blob

    async def generate_structured_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        response_schema: Optional[Any] = None,
        use_reasoning: bool = False,
        image_parts: Optional[List[Tuple[str, bytes]]] = None,
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
                    host_id,
                    messages,
                    ai_config,
                    response_schema,
                    use_reasoning,
                    image_parts=image_parts,
                )
                if response["success"]:
                    return response

            if (
                preferred_provider in ("openai", "both")
                and response_schema is not None
            ):
                oresp = await self._generate_openai_structured_response(
                    host_id,
                    messages,
                    ai_config,
                    response_schema,
                    image_parts=image_parts,
                )
                if oresp.get("success"):
                    return oresp

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
        use_reasoning: bool = False,
        image_parts: Optional[List[Tuple[str, bytes]]] = None,
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
            multimodal = bool(image_parts)
            content_payload = self._gemini_structured_content_payload(gemini_messages, image_parts)

            # Generate response with structured output
            genai = SimpleNamespace(types=_GenerationTypesCompat)
            import json

            # ATTEMPT 1: Try native Pydantic structured output
            logger.info(
                "Attempting native Gemini structured output with schema: %s (multimodal=%s)",
                response_schema.__name__ if response_schema else "None",
                multimodal,
            )

            try:
                max_tokens = 4096 if multimodal else 2000
                generation_config = genai.types.GenerationConfig(
                    temperature=float(ai_config.get("gemini_temperature", "0.7")),
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                )

                # Add response schema if provided
                if response_schema:
                    generation_config.response_schema = response_schema

                try:
                    response = await model.generate_content_async(
                        content_payload,
                        generation_config=generation_config,
                    )
                except Exception as vision_err:
                    if multimodal:
                        logger.warning(
                            "Gemini native structured multimodal failed (%s); retrying text-only",
                            vision_err,
                        )
                        response = await model.generate_content_async(
                            gemini_messages,
                            generation_config=generation_config,
                        )
                    else:
                        raise

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
            
            # ATTEMPT 2: JSON mode with a real schema summary (nested objects/arrays, not "all strings")
            logger.info("Attempting enhanced JSON-guided generation with explicit schema")

            if response_schema and messages:
                schema_hint = ""
                if hasattr(response_schema, "model_json_schema"):
                    try:
                        full = response_schema.model_json_schema()
                        props = full.get("properties") or {}
                        slim_props: Dict[str, Any] = {}
                        for k, v in props.items():
                            if not isinstance(v, dict):
                                continue
                            entry: Dict[str, Any] = {}
                            if "type" in v:
                                entry["type"] = v.get("type")
                            if v.get("description"):
                                entry["description"] = str(v.get("description"))[:240]
                            if "items" in v:
                                entry["items"] = v.get("items")
                            if "properties" in v:
                                entry["properties"] = list((v.get("properties") or {}).keys())[:24]
                            slim_props[k] = entry
                        slim = {
                            "title": full.get("title"),
                            "required": full.get("required", []),
                            "properties": slim_props,
                        }
                        schema_hint = json.dumps(slim, ensure_ascii=False)[:12000]
                    except Exception as schema_err:
                        logger.debug("model_json_schema slim failed: %s", schema_err)

                if not schema_hint and hasattr(response_schema, "model_fields"):
                    names = list(response_schema.model_fields.keys())
                    schema_hint = json.dumps({"required_top_level_keys": names}, ensure_ascii=False)

                enhanced_messages = messages.copy()
                if enhanced_messages:
                    last_message = enhanced_messages[-1]
                    enhanced_content = f"""{last_message['content']}

CRITICAL: Return ONLY one JSON object (no markdown fences, no commentary) that matches this structure.
Respect nested types (objects, arrays of objects, arrays of strings) exactly as in the schema summary:
{schema_hint or "{}"}

Include every top-level key listed under "required" when present; use sensible defaults only where the schema allows optional fields."""
                    
                    enhanced_messages[-1] = {
                        "role": last_message["role"],
                        "content": enhanced_content
                    }
                    
                    gemini_messages_enhanced = self._convert_to_gemini_format(enhanced_messages)
                    enhanced_payload = self._gemini_structured_content_payload(
                        gemini_messages_enhanced, image_parts
                    )
                    
                    # Generate with basic JSON mode (no schema constraint)
                    generation_config_basic = genai.types.GenerationConfig(
                        temperature=float(ai_config.get("gemini_temperature", "0.7")),
                        max_output_tokens=4096 if multimodal else 2000,
                        response_mime_type="application/json"
                    )
                    
                    try:
                        response = await model.generate_content_async(
                            enhanced_payload,
                            generation_config=generation_config_basic
                        )
                    except Exception as vision_err2:
                        if multimodal:
                            logger.warning(
                                "Gemini enhanced JSON multimodal failed (%s); retrying text-only",
                                vision_err2,
                            )
                            response = await model.generate_content_async(
                                gemini_messages_enhanced,
                                generation_config=generation_config_basic,
                            )
                        else:
                            raise
                    
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
                max_output_tokens=4096 if multimodal else 2000
            )
            
            try:
                response = await model.generate_content_async(
                    content_payload,
                    generation_config=generation_config_fallback
                )
            except Exception as vision_err3:
                if multimodal:
                    logger.warning(
                        "Gemini fallback multimodal failed (%s); retrying text-only",
                        vision_err3,
                    )
                    response = await model.generate_content_async(
                        gemini_messages,
                        generation_config=generation_config_fallback,
                    )
                else:
                    raise
            
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

    async def _generate_openai_structured_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        response_schema: Any,
        image_parts: Optional[List[Tuple[str, bytes]]] = None,
    ) -> Dict[str, Any]:
        """
        Structured JSON via OpenAI Chat Completions (``response_format: json_object``),
        with optional vision on the last user turn (base64 data URLs).
        """
        import base64
        import json

        client = await self._get_openai_client(host_id)
        if not client:
            return {"success": False, "error": "OpenAI client not available"}

        model_name = ai_config.get("openai_model", "gpt-4o")
        last_user_i: Optional[int] = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                last_user_i = i
                break

        oai_messages: List[Dict[str, Any]] = []
        for i, m in enumerate(messages):
            role = m.get("role") or "user"
            content = m.get("content") or ""
            if role == "user" and i == last_user_i and image_parts:
                user_parts: List[Dict[str, Any]] = [{"type": "text", "text": content}]
                for mime, raw in image_parts[:6]:
                    if not raw:
                        continue
                    b64 = base64.standard_b64encode(raw).decode("ascii")
                    mt = mime if mime in ("image/jpeg", "image/png", "image/gif", "image/webp") else "image/jpeg"
                    user_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mt};base64,{b64}", "detail": "auto"},
                        }
                    )
                oai_messages.append({"role": "user", "content": user_parts})
            else:
                oai_messages.append({"role": role, "content": content})

        max_tok = 4096 if image_parts else 2000
        try:
            completion = await client.chat.completions.create(
                model=model_name,
                messages=oai_messages,
                temperature=float(ai_config.get("openai_temperature", "0.7")),
                max_tokens=max_tok,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.warning("OpenAI structured completion failed: %s", e)
            return {"success": False, "error": str(e)}

        text = (completion.choices[0].message.content or "").strip()
        if not text:
            return {"success": False, "error": "Empty OpenAI response"}

        try:
            structured_data = json.loads(text)
        except json.JSONDecodeError as je:
            return {"success": False, "error": f"OpenAI JSON parse error: {je}", "response": text[:2000]}

        if response_schema:
            try:
                validated = response_schema(**structured_data)
                structured_data = validated.model_dump()
            except Exception as ve:
                logger.warning("OpenAI structured Pydantic validation failed: %s", ve)
                return {
                    "success": False,
                    "error": f"Schema validation failed: {ve}",
                    "response": text[:2000],
                }

        u = completion.usage
        return {
            "success": True,
            "response": text,
            "structured_data": structured_data,
            "model": model_name,
            "provider": "openai_structured",
            "usage": {
                "prompt_tokens": getattr(u, "prompt_tokens", 0) if u else 0,
                "completion_tokens": getattr(u, "completion_tokens", 0) if u else 0,
                "total_tokens": getattr(u, "total_tokens", 0) if u else 0,
            },
        }

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
            genai = SimpleNamespace(types=_GenerationTypesCompat)
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
