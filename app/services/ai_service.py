"""
AI Service for handling OpenAI and Google Gemini interactions.

This service provides a unified interface for AI operations across different providers,
supporting both OpenAI GPT models and Google Gemini models.
"""

import logging
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import json
import asyncio

from app.services.embedding_stub import deterministic_stub_embedding

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.settings_service import SettingsService

_google_genai_cache: Optional[Tuple[Any, Any]] = None
_openai_cache: Optional[Any] = None


def _import_openai() -> Any:
    """
    Import OpenAI only when it is used.

    The SDK imports a large generated type tree. Deferring it keeps app startup
    and pytest collection responsive when OpenAI is not the selected provider.
    """
    global _openai_cache
    if _openai_cache is None:
        import openai

        _openai_cache = openai
    return _openai_cache


def _import_google_genai() -> Tuple[Any, Any]:
    """
    Import google.genai only when Gemini is used.

    Keeps `import app.services.ai_service` (and pytest collection) lighter; avoids
    MemoryError / long startup on constrained CI when tests never call Gemini.
    """
    global _google_genai_cache
    if _google_genai_cache is not None:
        return _google_genai_cache
    from google import genai as genai_mod
    from google.genai import types as genai_types

    _google_genai_cache = (genai_mod, genai_types)
    return _google_genai_cache

class AIService:
    """
    Unified AI service supporting OpenAI and Google Gemini models.

    This service automatically selects the appropriate AI provider based on
    host preferences and handles API key management through the settings service.
    """

    def __init__(self, settings_service: Optional["SettingsService"] = None):
        self.settings_service = settings_service
        self._openai_client = None
        self._gemini_models = {}

    async def _get_openai_client(self, host_id: str) -> Optional[Any]:
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

            openai = _import_openai()
            return openai.AsyncOpenAI(api_key=api_key)

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            return None

    async def _get_gemini_api_key(self, host_id: str) -> Optional[str]:
        """Get configured Gemini API key for a host."""
        try:
            api_key = None
            if self.settings_service:
                api_key = await self.settings_service.get_host_api_key(host_id, "google_ai")
            if not api_key:
                api_key = os.environ.get("GOOGLE_AI_API_KEY")
            if not api_key:
                logger.warning(f"No Google AI API key found for host {host_id}")
                return None
            return api_key
        except Exception as e:
            logger.error(f"Failed to load Gemini API key: {e}")
            return None

    async def _get_gemini_client(self, host_id: str) -> Optional[Any]:
        """Get configured google.genai client for a host."""
        try:
            api_key = await self._get_gemini_api_key(host_id)
            if not api_key:
                return None
            genai, _ = _import_google_genai()
            return genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
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

            # Acquire API key via settings service or environment.
            api_key = await self._get_gemini_api_key(host_id)
            if not api_key:
                return {"success": False, "error": "Gemini API key missing"}

            # Use new google.genai client for tools
            try:
                genai_client, genai_types = _import_google_genai()
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
                config=genai_types.GenerateContentConfig(
                    tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                    temperature=float(ai_config.get("gemini_temperature", "0.7")),
                    max_output_tokens=2000,
                ),
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

            client = await self._get_gemini_client(host_id)
            if not client:
                return {"success": False, "error": "Gemini client not available"}
            try:
                _, genai_types = _import_google_genai()
            except Exception as e:  # pragma: no cover
                logger.error(f"Failed to import google.genai types: {e}")
                return {"success": False, "error": "genai client not available"}

            # Generate response
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=self._messages_to_text(messages),
                config=genai_types.GenerateContentConfig(
                    temperature=float(ai_config.get("gemini_temperature", "0.7")),
                    max_output_tokens=2000,
                ),
            )

            return {
                "success": True,
                "response": response.text,
                "model": model_name,
                "provider": "google",
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count if getattr(response, "usage_metadata", None) else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if getattr(response, "usage_metadata", None) else 0,
                    "total_tokens": response.usage_metadata.total_token_count if getattr(response, "usage_metadata", None) else 0
                }
            }

        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def generate_events_extraction(
        self,
        messages: List[Dict[str, str]],
        *,
        host_id: str = "system",
    ) -> Dict[str, Any]:
        """Extract events via Gemma4 (local LLM, zero cost) with Gemini fallback.

        Uses EVENTS_GEMINI_MODEL (default gemini-2.5-flash) as fallback when
        Gemma4 is unavailable or fails.
        """
        # 1. Try Gemma4 first (local LLM via Cloudflare Tunnel, zero cost)
        try:
            import httpx

            gemma4_url = os.getenv("GEMMA4_BASE_URL", "https://gemma4.syntagent.com/v1")
            gemma4_model = os.getenv("GEMMA4_MODEL", "gemma-4-26b-a4b-nvfp4")
            cf_id = os.getenv("GEMMA4_CF_CLIENT_ID", "")
            cf_secret = os.getenv("GEMMA4_CF_CLIENT_SECRET", "")
            temperature = float(os.getenv("EVENTS_GEMINI_TEMPERATURE", "0.2"))
            max_tokens = int(os.getenv("EVENTS_GEMINI_MAX_TOKENS", "4096"))

            if cf_id and cf_secret and gemma4_url:
                payload = {
                    "model": gemma4_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                async with httpx.AsyncClient(timeout=90.0) as client:
                    resp = await client.post(
                        f"{gemma4_url.rstrip('/')}/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "CF-Access-Client-Id": cf_id,
                            "CF-Access-Client-Secret": cf_secret,
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    if content and len(content.strip()) > 10:
                        logger.info("Events extraction via Gemma4 succeeded")
                        return {
                            "success": True,
                            "response": content,
                            "model": gemma4_model,
                            "provider": "gemma4",
                            "task": "events_extraction",
                        }
                    logger.warning("Gemma4 returned empty response, falling back to Gemini")
            else:
                logger.info("Gemma4 not configured, using Gemini directly")
        except Exception as exc:
            logger.warning("Gemma4 extraction failed (%s), falling back to Gemini", exc)

        # 2. Fallback to Gemini API
        try:
            model_name = os.getenv("EVENTS_GEMINI_MODEL", "gemini-2.5-flash").strip()
            temperature = float(os.getenv("EVENTS_GEMINI_TEMPERATURE", "0.2"))
            max_tokens = int(os.getenv("EVENTS_GEMINI_MAX_TOKENS", "4096"))
            max_attempts = int(os.getenv("EVENTS_GEMINI_RETRY_ATTEMPTS", "3"))

            client = await self._get_gemini_client(host_id)
            if not client:
                return {"success": False, "error": "Gemini client not available for events extraction"}
            try:
                _, genai_types = _import_google_genai()
            except Exception as e:  # pragma: no cover
                logger.error("Failed to import google.genai types: %s", e)
                return {"success": False, "error": "genai client not available"}
            prompt = self._messages_to_text(messages)
            last_error: Optional[str] = None

            for attempt in range(max_attempts):
                try:
                    response = await client.aio.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        ),
                    )
                    return {
                        "success": True,
                        "response": response.text,
                        "model": model_name,
                        "provider": "google",
                        "task": "events_extraction",
                    }
                except Exception as exc:
                    last_error = str(exc)
                    if "429" in last_error and attempt < max_attempts - 1:
                        await asyncio.sleep(min(30, 3 * (2 ** attempt)))
                        continue
                    raise

            return {"success": False, "error": last_error or "events extraction failed"}
        except Exception as e:
            logger.error("Events extraction Gemini call failed: %s", e)
            return {"success": False, "error": str(e)}

    def _messages_to_text(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style chat messages to a single Gemini prompt."""
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

    def _convert_to_gemini_format(self, messages: List[Dict[str, str]]) -> str:
        """Backward-compatible alias for older structured AI code paths."""
        return self._messages_to_text(messages)

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
            model_name = ai_config.get("embedding_alternative",
                                     "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            dim = int(ai_config.get("embedding_dimensions", 384))
            if os.environ.get("PYTEST_CURRENT_TEST") or os.getenv(
                "SKIP_SENTENCE_TRANSFORMERS", ""
            ).lower() in ("1", "true", "yes"):
                embeddings = [deterministic_stub_embedding(t or "", dim) for t in texts]
                return {
                    "success": True,
                    "embeddings": embeddings,
                    "model": model_name,
                    "provider": "sentence_transformers_stub",
                    "usage": {"texts_processed": len(texts)},
                }

            from sentence_transformers import SentenceTransformer

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
