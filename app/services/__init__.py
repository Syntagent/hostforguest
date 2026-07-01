"""
Services package for HostForGuest.

Contains business logic and service layer classes.
"""

from typing import Any

__all__ = [
    "AIService",
    "SettingsService",
    "HostService",
    "GuestGroupService",
    "AttractionService",
    "ContentScraperService",
]

_SERVICE_EXPORTS = {
    "AIService": ("app.services.ai_service", "AIService"),
    "SettingsService": ("app.services.settings_service", "SettingsService"),
    "HostService": ("app.services.host_service", "HostService"),
    "GuestGroupService": ("app.services.guest_group_service", "GuestGroupService"),
    "AttractionService": ("app.services.attraction_service", "AttractionService"),
    "ContentScraperService": (
        "app.services.content_scraper_service",
        "ContentScraperService",
    ),
}


def __getattr__(name: str) -> Any:
    if name not in _SERVICE_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _SERVICE_EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
