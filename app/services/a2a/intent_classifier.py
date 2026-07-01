"""Model-driven A2A intent classification with optional embedding routing."""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.services.a2a.agent_card import GUEST_AGENT_CARDS, HFG_AGENT_CARDS
from app.services.ai_service_fallback import AIServiceWithFallback
from app.services.embedding_stub import deterministic_stub_embedding

logger = logging.getLogger(__name__)

SYSTEM_HOST_ID = "system"

_HOST_DEFAULT = "guest-ticket-hfg"
_GUEST_DEFAULT = "guest-concierge-hfg"
_LATENT_MIN_SCORE = float(os.getenv("A2A_LATENT_MIN_SCORE", "0.25"))

_INTENT_PROTOTYPES: Dict[str, str] = {}
for _card in {**HFG_AGENT_CARDS, **GUEST_AGENT_CARDS}.values():
    if _card.id == "guest-welcome-hfg":
        continue
    caps = ", ".join(_card.capabilities[:6])
    _INTENT_PROTOTYPES[_card.id] = f"{_card.name}: {_card.description} Capabilities: {caps}"


class A2AIntentResult(BaseModel):
    agent_id: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning: str = ""


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class A2AIntentClassifier:
    """Routes Telegram / A2A messages to specialized agents via AI, then latent, then default."""

    def __init__(self, ai_service: Optional[AIServiceWithFallback] = None) -> None:
        self.ai_service = ai_service or AIServiceWithFallback(settings_service=None)
        self.last_routing_method: Optional[str] = None
        self._prototype_embeddings: Dict[str, List[float]] = {}

    def _latent_mode_enabled(self) -> bool:
        return os.getenv("LATENT_MODE", "").strip().lower() == "auto"

    async def classify_intent(self, message: str, context: Dict[str, Any]) -> str:
        if context.get("role") == "guest" or context.get("guest_group_id"):
            if not context.get("prefs_captured"):
                self.last_routing_method = "structural"
                return "guest-welcome-hfg"
            return await self.classify_guest_intent(message, context)
        return await self.classify_host_intent(message, context)

    async def classify_host_intent(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        allowed = set(HFG_AGENT_CARDS.keys())
        agent_id = await self._route(message, allowed, role="host", context=context or {})
        return agent_id if agent_id in allowed else _HOST_DEFAULT

    async def classify_guest_intent(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        allowed = {k for k in GUEST_AGENT_CARDS.keys() if k != "guest-welcome-hfg"}
        agent_id = await self._route(message, allowed, role="guest", context=context or {})
        return agent_id if agent_id in allowed else _GUEST_DEFAULT

    async def _route(
        self,
        message: str,
        allowed: set[str],
        *,
        role: str,
        context: Dict[str, Any],
    ) -> str:
        text = (message or "").strip()
        if not text:
            self.last_routing_method = "default"
            return _GUEST_DEFAULT if role == "guest" else _HOST_DEFAULT

        ai_result = await self._classify_with_ai(text, allowed, role=role, context=context)
        if ai_result:
            self.last_routing_method = "ai"
            return ai_result

        if self._latent_mode_enabled():
            latent_result = await self._classify_with_embeddings(text, allowed)
            if latent_result:
                self.last_routing_method = "latent"
                return latent_result

        self.last_routing_method = "default"
        return _GUEST_DEFAULT if role == "guest" else _HOST_DEFAULT

    async def _classify_with_ai(
        self,
        message: str,
        allowed: set[str],
        *,
        role: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        agents_block = "\n".join(
            f"- {aid}: {_INTENT_PROTOTYPES.get(aid, aid)}"
            for aid in sorted(allowed)
        )
        system = (
            "You classify user messages for a Croatian vacation rental Telegram assistant. "
            "Return JSON with agent_id (must be one of the listed ids), confidence 0-1, and brief reasoning. "
            "Interpret natural language; do not rely on single keywords."
        )
        user = (
            f"Role: {role}\n"
            f"Available agents:\n{agents_block}\n\n"
            f"User message: {message}"
        )
        host_id = str(context.get("host_id") or SYSTEM_HOST_ID)
        try:
            result = await self.ai_service.generate_structured_response(
                host_id,
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_schema=A2AIntentResult,
            )
        except Exception as exc:
            logger.warning("A2A AI intent classification failed: %s", exc)
            return None

        if not result.get("success"):
            return None

        structured = result.get("structured_data")
        if not structured:
            return None

        try:
            parsed = A2AIntentResult.model_validate(structured)
        except Exception:
            return None

        if parsed.agent_id in allowed:
            return parsed.agent_id
        return None

    async def _embed_texts(self, texts: List[str]) -> Optional[List[List[float]]]:
        try:
            ai_config = await self.ai_service.get_ai_config_for_host_with_fallback(SYSTEM_HOST_ID)
            if os.environ.get("PYTEST_CURRENT_TEST") or os.getenv("SKIP_SENTENCE_TRANSFORMERS", "").lower() in (
                "1",
                "true",
                "yes",
            ):
                dim = int(ai_config.get("embedding_dimensions", 384))
                return [deterministic_stub_embedding(t or "", dim) for t in texts]

            provider = ai_config.get("embedding_provider", "sentence_transformers")
            if provider == "openai":
                out = await self.ai_service._generate_openai_embeddings(SYSTEM_HOST_ID, texts, ai_config)
            else:
                out = await self.ai_service._generate_sentence_transformer_embeddings(texts, ai_config)
            if out.get("success") and out.get("embeddings"):
                return out["embeddings"]
        except Exception as exc:
            logger.warning("A2A latent embedding generation failed: %s", exc)
        return None

    async def _ensure_prototype_embeddings(self, allowed: set[str]) -> Dict[str, List[float]]:
        missing = [aid for aid in allowed if aid not in self._prototype_embeddings]
        if not missing:
            return {aid: self._prototype_embeddings[aid] for aid in allowed if aid in self._prototype_embeddings}

        texts = [_INTENT_PROTOTYPES.get(aid, aid) for aid in missing]
        vectors = await self._embed_texts(texts)
        if not vectors or len(vectors) != len(missing):
            return {aid: self._prototype_embeddings[aid] for aid in allowed if aid in self._prototype_embeddings}

        for aid, vec in zip(missing, vectors):
            self._prototype_embeddings[aid] = vec
        return {aid: self._prototype_embeddings[aid] for aid in allowed if aid in self._prototype_embeddings}

    async def _classify_with_embeddings(self, message: str, allowed: set[str]) -> Optional[str]:
        prototypes = await self._ensure_prototype_embeddings(allowed)
        if not prototypes:
            return None

        msg_vectors = await self._embed_texts([message])
        if not msg_vectors:
            return None
        msg_vec = msg_vectors[0]

        best_id: Optional[str] = None
        best_score = -1.0
        for aid, proto_vec in prototypes.items():
            score = _cosine_similarity(msg_vec, proto_vec)
            if score > best_score:
                best_score = score
                best_id = aid

        if best_id and best_score >= _LATENT_MIN_SCORE:
            return best_id
        return None
