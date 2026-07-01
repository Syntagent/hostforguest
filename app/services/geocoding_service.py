"""Address geocoding helpers for host accommodation and attractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.services.attraction_service import AttractionService


@dataclass
class GeocodeResult:
    latitude: float
    longitude: float
    matched_query: str
    precision: str  # address | city | approximate


class GeocodingService:
    """Resolve WGS84 coordinates from Croatian address parts."""

    @staticmethod
    def _query_candidates(
        address: Optional[str],
        city: Optional[str],
        county: Optional[str],
    ) -> List[Tuple[str, str]]:
        addr = (address or "").strip()
        cty = (city or "").strip()
        cnt = (county or "").strip()
        candidates: List[Tuple[str, str]] = []

        if addr and cty and cnt:
            candidates.append((f"{addr}, {cty}, {cnt}, Croatia", "address"))
        if addr and cty:
            candidates.append((f"{addr}, {cty}, Croatia", "address"))
        if addr and cnt:
            candidates.append((f"{addr}, {cnt}, Croatia", "approximate"))
        if cty and cnt:
            candidates.append((f"{cty}, {cnt}, Croatia", "city"))
        if cty:
            candidates.append((f"{cty}, Croatia", "city"))
        if addr:
            candidates.append((f"{addr}, Croatia", "approximate"))

        seen: set[str] = set()
        unique: List[Tuple[str, str]] = []
        for query, precision in candidates:
            key = query.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append((query, precision))
        return unique

    @classmethod
    def geocode(
        cls,
        address: Optional[str] = None,
        city: Optional[str] = None,
        county: Optional[str] = None,
    ) -> Optional[GeocodeResult]:
        svc = AttractionService(db=None)
        for query, precision in cls._query_candidates(address, city, county):
            resolved = svc._resolve_with_query_variants(query)
            if resolved:
                return GeocodeResult(
                    latitude=resolved[0],
                    longitude=resolved[1],
                    matched_query=query,
                    precision=precision,
                )
        return None
