"""Host cleaning: AI-assisted ranking and message drafts (DB candidates only)."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.partner import Partner
from app.services.ai_service import AIService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_AI_HITS: Dict[str, List[float]] = defaultdict(list)
_MAX_AI_PER_HOUR = 40


def _rate_limit_ai(host_id: uuid.UUID) -> bool:
    now = datetime.utcnow().timestamp()
    key = str(host_id)
    bucket = _AI_HITS[key]
    cutoff = now - 3600
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _MAX_AI_PER_HOUR:
        return False
    bucket.append(now)
    return True


def partner_to_candidate_dict(p: Partner) -> Dict[str, Any]:
    return {
        "partner_id": str(p.id),
        "name": p.name,
        "city": p.city,
        "region": p.region or "",
        "price_range": p.price_range or "",
        "rate_card": p.rate_card or {},
        "description": (p.description or "")[:400],
    }



