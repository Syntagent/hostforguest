"""Guest-facing weather forecast via Open-Meteo (no API key) with graceful fallback."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx

from app.core.config import settings

from app.services.host_offerings_for_guest import scrub_contact_from_text

logger = logging.getLogger(__name__)

_OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
_OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

_WMO_HR: Dict[int, str] = {
    0: "Vedro",
    1: "Pretežno vedro",
    2: "Djelomično oblačno",
    3: "Oblačno",
    45: "Magla",
    48: "Magla s inje",
    51: "Slaba rosulja",
    53: "Umjerena rosulja",
    55: "Jaka rosulja",
    61: "Slab kiša",
    63: "Umjerena kiša",
    65: "Jaka kiša",
    71: "Slab snijeg",
    73: "Umjeren snijeg",
    75: "Jak snijeg",
    80: "Slabi pljuskovi",
    81: "Umjereni pljuskovi",
    82: "Jaki pljuskovi",
    95: "Grmljavina",
    96: "Grmljavina s gradom",
    99: "Jaka grmljavina s gradom",
}


def _wmo_label(code: Optional[int]) -> str:
    if code is None:
        return "—"
    return _WMO_HR.get(int(code), "Promjenjivo")


def _forecast_api_url(lat: float, lng: float, city: str) -> str:
    custom = (settings.weather_forecast_api_url or os.getenv("WEATHER_FORECAST_API_URL") or "").strip()
    if custom:
        if "{" in custom:
            return custom.format(lat=lat, lng=lng, city=city)
        sep = "&" if "?" in custom else "?"
        return (
            f"{custom}{sep}"
            + urlencode(
                {
                    "latitude": lat,
                    "longitude": lng,
                    "current": "temperature_2m,weather_code,wind_speed_10m",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 3,
                }
            )
        )
    params = urlencode(
        {
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": 3,
        }
    )
    return f"{_OPEN_METEO_FORECAST}?{params}"


async def _geocode_city(city: str) -> Tuple[Optional[float], Optional[float]]:
    city = (city or "").strip()
    if not city:
        return None, None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                _OPEN_METEO_GEOCODE,
                params={"name": city, "count": 1, "language": "hr", "format": "json"},
            )
            resp.raise_for_status()
            results = (resp.json() or {}).get("results") or []
            if results:
                first = results[0]
                return first.get("latitude"), first.get("longitude")
    except Exception as exc:
        logger.debug("Open-Meteo geocode failed for %s: %s", city, exc)
    return None, None


def _format_forecast_payload(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    current = data.get("current") or {}
    temp = current.get("temperature_2m")
    code = current.get("weather_code")
    wind = current.get("wind_speed_10m")
    if temp is not None:
        chunk = f"**Sada:** {round(temp)}°C, {_wmo_label(code)}"
        if wind is not None:
            chunk += f", vjetar {round(wind)} km/h"
        lines.append(chunk)

    daily = data.get("daily") or {}
    times = daily.get("time") or []
    codes = daily.get("weather_code") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    if times:
        lines.append("")
        lines.append("**Sljedećih dana:**")
        for i, day in enumerate(times[:3]):
            try:
                from datetime import datetime

                dt = datetime.strptime(day[:10], "%Y-%m-%d")
                label = dt.strftime("%a %d.%m.")
            except ValueError:
                label = day[:10]
            hi = tmax[i] if i < len(tmax) else None
            lo = tmin[i] if i < len(tmin) else None
            wc = codes[i] if i < len(codes) else None
            if hi is not None and lo is not None:
                lines.append(
                    f"• {label}: {round(lo)}–{round(hi)}°C, {_wmo_label(wc)}"
                )
    return "\n".join(lines).strip()


def weather_fallback_links(city: str) -> str:
    cleaned = scrub_contact_from_text(str(city or "").strip()) or ""
    safe_city = cleaned if cleaned and cleaned != "[contact removed]" else "Lovran"
    city_q = safe_city.replace(" ", "+")
    google = f"https://www.google.com/search?q=vremenska+prognoza+{city_q}"
    return (
        f"Detaljna prognoza trenutno nije dostupna.\n"
        f"Za *{safe_city}* provjerite [DHMZ](https://meteo.hr) ili "
        f"[Google Weather]({google})."
    )


async def fetch_guest_weather_forecast(
    *,
    latitude: Optional[float],
    longitude: Optional[float],
    city: str,
) -> Optional[str]:
    """
    Return formatted Croatian forecast text, or None when lookup fails.
    """
    lat, lng = latitude, longitude
    if lat is None or lng is None:
        lat, lng = await _geocode_city(city)
    if lat is None or lng is None:
        return None

    url = _forecast_api_url(lat, lng, city)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            body = _format_forecast_payload(resp.json())
            return body or None
    except Exception as exc:
        logger.warning("Weather forecast failed for %s (%s,%s): %s", city, lat, lng, exc)
        return None
