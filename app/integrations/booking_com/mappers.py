"""
Normalize Booking.com–style payloads to internal channel DTOs.

Supports mock JSON (tests/dev) and minimal XML parsing (Connectivity-style responses).
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def normalized_reservation_from_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a flat dict (mock or pre-parsed) to internal shape."""
    return {
        "external_reservation_id": str(row.get("id") or row.get("reservation_id") or ""),
        "external_room_id": str(row.get("room_id") or row.get("room") or "") or None,
        "external_hotel_id": str(row.get("hotel_id") or row.get("property_id") or "") or None,
        "status": str(row.get("status") or "confirmed").lower(),
        "check_in": row.get("check_in") or row.get("arrival"),
        "check_out": row.get("check_out") or row.get("departure"),
        "currency": row.get("currency") or "EUR",
        "total_price": float(row.get("total_price") or row.get("amount") or 0),
        "guest_name": row.get("guest_name") or row.get("customer_name"),
        "external_updated_at": _parse_dt(row.get("modified_at") or row.get("last_change")),
        "raw": row,
    }


def reservations_from_mock_json(body: str) -> List[Dict[str, Any]]:
    data = json.loads(body)
    rows = data if isinstance(data, list) else data.get("reservations", [])
    return [normalized_reservation_from_dict(r) for r in rows]


def reservations_from_xml(xml_text: str) -> List[Dict[str, Any]]:
    """Best-effort parse; Booking.com XML varies by endpoint."""
    out: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("Could not parse Booking.com XML: %s", e)
        return out

    # Try common reservation node names
    for res in root.iter():
        tag = res.tag.split("}")[-1].lower()
        if tag not in ("reservation", "booking", "res"):
            continue
        row: Dict[str, Any] = {}
        for child in res:
            name = child.tag.split("}")[-1].lower()
            if child.text:
                row[name] = child.text.strip()
        if row.get("id") or row.get("reservation_id"):
            out.append(normalized_reservation_from_dict(row))
    return out


def build_availability_update_payload(
    hotel_id: str,
    room_id: str,
    date_from: str,
    date_to: str,
    available: int,
) -> Dict[str, Any]:
    """JSON-friendly payload for push (client may serialize to XML)."""
    return {
        "hotel_id": hotel_id,
        "room_id": room_id,
        "date_from": date_from,
        "date_to": date_to,
        "available": available,
    }


def build_rate_update_payload(
    hotel_id: str,
    room_id: str,
    rate_id: Optional[str],
    date_from: str,
    date_to: str,
    price: float,
    currency: str,
) -> Dict[str, Any]:
    return {
        "hotel_id": hotel_id,
        "room_id": room_id,
        "rate_id": rate_id,
        "date_from": date_from,
        "date_to": date_to,
        "price": price,
        "currency": currency,
    }
