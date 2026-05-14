"""
AI Service for handling OpenAI and Google Gemini interactions.

This service provides a unified interface for AI operations across different providers,
supporting both OpenAI GPT models and Google Gemini models.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import asyncio

# AI Libraries
import openai
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Internal imports
from app.core.config import settings
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

class AIService:
    """
    Unified AI service supporting OpenAI and Google Gemini models.

    This service automatically selects the appropriate AI provider based on
    host preferences and handles API key management through the settings service.
    """

    def __init__(self, settings_service: Optional[SettingsService] = None):
        self.settings_service = settings_service
        self._openai_client = None
        self._gemini_models = {}

    async def _get_openai_client(self, host_id: str) -> Optional[openai.AsyncOpenAI]:
        """Get configured OpenAI client for a host."""
        try:
            import os
            api_key = None
            if self.settings_service:
                api_key = await self.settings_service.get_host_api_key(host_id, "openai")
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning(f"No OpenAI API key found for host {host_id}")
                return None

            return openai.AsyncOpenAI(api_key=api_key)

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            return None

    async def _get_gemini_model(self, host_id: str, model_name: str) -> Optional[Any]:
        """Get configured Gemini model for a host."""
        try:
            import os
            api_key = None
            if self.settings_service:
                api_key = await self.settings_service.get_host_api_key(host_id, "google_ai")
            if not api_key:
                api_key = os.environ.get("GOOGLE_AI_API_KEY")
            if not api_key:
                logger.warning(f"No Google AI API key found for host {host_id}")
                return None

            # Configure Gemini with the API key
            genai.configure(api_key=api_key)

            # Configure safety settings for tourism content
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }

            model = genai.GenerativeModel(
                model_name=model_name,
                safety_settings=safety_settings
            )

            return model

        except Exception as e:
            logger.error(f"Failed to initialize Gemini model {model_name}: {e}")
            return None

    async def generate_chat_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        use_reasoning: bool = False,
        use_web_search: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a chat response using the preferred AI provider.

        Args:
            host_id: Host UUID
            messages: List of chat messages [{"role": "user/assistant", "content": "..."}]
            context: Additional context (location, guest preferences, etc.)
            use_reasoning: Whether to use reasoning models (o1, Gemini Pro)

        Returns:
            Dict with response, model used, and metadata
        """
        try:
            # Get AI configuration for host
            ai_config = await self.settings_service.get_ai_config_for_host(host_id)
            preferred_provider = ai_config.get("preferred_ai_provider", "google")

            # Add Croatian tourism context if provided
            if context:
                system_context = self._build_system_context(context, ai_config)
                messages = [{"role": "system", "content": system_context}] + messages

            # Try preferred provider first
            if (preferred_provider == "openai" or preferred_provider == "both") and not use_web_search:
                response = await self._generate_openai_response(
                    host_id, messages, ai_config, use_reasoning
                )
                if response["success"]:
                    return response

            if preferred_provider == "google" or preferred_provider == "both":
                if use_web_search:
                    response = await self._generate_gemini_response_with_search(
                        host_id, messages, ai_config, use_reasoning
                    )
                else:
                    response = await self._generate_gemini_response(
                        host_id, messages, ai_config, use_reasoning
                    )
                if response["success"]:
                    return response

            # Fallback error response
            return {
                "success": False,
                "response": "I apologize, but I'm currently unable to process your request. Please check your AI service configuration.",
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

    async def _generate_gemini_response_with_search(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate response using Gemini with Google Search grounding tools (Context7: Tool.google_search)."""
        try:
            # Prefer pro for better grounding; fallback to flash
            model_name = ai_config.get("gemini_pro_model", "gemini-2.5-pro") if use_reasoning else ai_config.get("gemini_model", "gemini-2.5-flash")

            # Acquire API key via settings service
            api_key = await self.settings_service.get_host_api_key(host_id, "google_ai")
            if not api_key:
                # Fallback to environment variable
                import os
                api_key = os.environ.get("GOOGLE_AI_API_KEY")
            if not api_key:
                logger.warning(f"No Google AI API key found for host {host_id}")
                return {"success": False, "error": "Gemini API key missing"}

            # Use new google.genai client for tools
            try:
                from google import genai as genai_client
                from google.genai import types as genai_types
            except Exception as e:  # pragma: no cover
                logger.error(f"Failed to import google.genai client: {e}")
                return {"success": False, "error": "genai client not available"}

            client = genai_client.Client(api_key=api_key)

            # Compose contents as a single user turn from existing messages
            # Preserve system as instruction header
            system_msgs = "\n\n".join([m["content"] for m in messages if m.get("role") == "system"]) or ""
            user_msgs = "\n\n".join([m["content"] for m in messages if m.get("role") != "system"]) or ""
            combined = (f"System instructions:\n{system_msgs}\n\nUser request:\n{user_msgs}").strip()

            response = await client.aio.models.generate_content(
                model=model_name,
                contents=combined,
                config={
                    "tools": [{"google_search": {}}],
                    "temperature": float(ai_config.get("gemini_temperature", "0.7")),
                    "max_output_tokens": 2000,
                },
            )

            text = getattr(response, "text", None) or ""
            return {
                "success": True,
                "response": text,
                "model": model_name,
                "provider": "google",
            }
        except Exception as e:
            logger.error(f"Gemini with search failed: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_openai_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate response using OpenAI models."""
        try:
            client = await self._get_openai_client(host_id)
            if not client:
                return {"success": False, "error": "OpenAI client not available"}

            # Select model based on reasoning requirement
            if use_reasoning:
                model = "o1-mini"  # Use reasoning model for complex tasks
                # o1 models don't support system messages in the same way
                user_content = "\n\n".join([msg["content"] for msg in messages if msg["role"] != "system"])
                if any(msg["role"] == "system" for msg in messages):
                    system_msg = next(msg["content"] for msg in messages if msg["role"] == "system")
                    user_content = f"System context: {system_msg}\n\nUser request: {user_content}"

                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": user_content}],
                    max_tokens=4000
                )
            else:
                model = ai_config.get("openai_model", "gpt-4o")
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )

            return {
                "success": True,
                "response": response.choices[0].message.content,
                "model": model,
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

    async def _generate_gemini_response(
        self,
        host_id: str,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate response using Google Gemini models."""
        try:
            # Select model based on reasoning requirement
            if use_reasoning:
                model_name = ai_config.get("gemini_pro_model", "gemini-2.5-pro")
            else:
                model_name = ai_config.get("gemini_model", "gemini-2.5-flash")

            model = await self._get_gemini_model(host_id, model_name)
            if not model:
                return {"success": False, "error": "Gemini model not available"}

            # Convert messages to Gemini format
            gemini_messages = self._convert_to_gemini_format(messages)

            # Generate response
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

    def _convert_to_gemini_format(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI format messages to Gemini format."""
        formatted_messages = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            if role == "system":
                formatted_messages.append(f"System: {content}")
            elif role == "user":
                formatted_messages.append(f"Human: {content}")
            elif role == "assistant":
                formatted_messages.append(f"Assistant: {content}")

        return "\n\n".join(formatted_messages)

    def _build_system_context(self, context: Dict[str, Any], ai_config: Dict[str, Any]) -> str:
        """Build system context for Croatian tourism assistance."""
        location = context.get("location", "Lovran, Croatia")
        guest_preferences = context.get("guest_preferences", {})
        local_info = context.get("local_info", {})
        language = ai_config.get("default_language", "en")

        system_prompt = f"""You are a knowledgeable local guide assistant for {location}, Croatia.
You help tourists discover authentic Croatian experiences, local attractions, restaurants, and activities.

Current Context:
- Location: {location}
- Guest Preferences: {json.dumps(guest_preferences, indent=2) if guest_preferences else 'Not specified'}
- Local Information: {json.dumps(local_info, indent=2) if local_info else 'Standard tourist information'}
- Response Language: {language}

Guidelines:
- Provide authentic, local recommendations
- Consider Croatian cultural context and customs
- Suggest seasonal activities when relevant
- Include practical information (opening hours, prices, transportation)
- Be warm and welcoming, representing Croatian hospitality
- If asked about other locations, gently redirect to your local expertise
- Always prioritize guest safety and current local conditions

Remember: You're representing a local Croatian host who wants their guests to have an amazing, authentic experience."""

        return system_prompt

    async def generate_embeddings(
        self,
        host_id: str,
        texts: List[str]
    ) -> Dict[str, Any]:
        """
        Generate embeddings for texts using the configured embedding provider.

        Args:
            host_id: Host UUID
            texts: List of texts to embed

        Returns:
            Dict with embeddings and metadata
        """
        try:
            ai_config = await self.settings_service.get_ai_config_for_host(host_id)
            embedding_provider = ai_config.get("embedding_provider", "openai")

            if embedding_provider == "openai":
                return await self._generate_openai_embeddings(host_id, texts, ai_config)
            elif embedding_provider == "sentence_transformers":
                return await self._generate_sentence_transformer_embeddings(texts, ai_config)
            else:
                return {"success": False, "error": f"Unsupported embedding provider: {embedding_provider}"}

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_openai_embeddings(
        self,
        host_id: str,
        texts: List[str],
        ai_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate embeddings using OpenAI."""
        try:
            client = await self._get_openai_client(host_id)
            if not client:
                return {"success": False, "error": "OpenAI client not available"}

            # Use text-embedding-3-small as the cost-effective default.
            model = ai_config.get("embedding_model", "text-embedding-3-small")
            dimensions = ai_config.get("embedding_dimensions", 1536)

            # Create embeddings with optional dimension reduction for cost optimization
            embedding_params = {
                "model": model,
                "input": texts
            }

            # Add dimensions parameter for text-embedding-3 models (supports dimension reduction)
            if "text-embedding-3" in model and dimensions != 1536:
                embedding_params["dimensions"] = dimensions

            response = await client.embeddings.create(**embedding_params)

            embeddings = [data.embedding for data in response.data]

            return {
                "success": True,
                "embeddings": embeddings,
                "model": model,
                "provider": "openai",
                "dimensions": len(embeddings[0]) if embeddings else 0,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_sentence_transformer_embeddings(
        self,
        texts: List[str],
        ai_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate embeddings using SentenceTransformers (fallback)."""
        try:
            from sentence_transformers import SentenceTransformer

            model_name = ai_config.get("embedding_alternative",
                                     "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

            # Load model (this should be cached after first load)
            model = SentenceTransformer(model_name)

            # Generate embeddings
            embeddings = model.encode(texts).tolist()

            return {
                "success": True,
                "embeddings": embeddings,
                "model": model_name,
                "provider": "sentence_transformers",
                "usage": {
                    "texts_processed": len(texts)
                }
            }

        except Exception as e:
            logger.error(f"SentenceTransformer embedding generation failed: {e}")
            return {"success": False, "error": str(e)}
