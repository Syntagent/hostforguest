"""Agent Card definitions for HostForGuest A2A protocol."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    """Describes a specialized HFG agent for orchestrator routing."""

    id: str
    name: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    version: str = "1.0.0"
    language: str = "hr"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


HFG_AGENT_CARDS: Dict[str, AgentCard] = {
    "guest-ticket-hfg": AgentCard(
        id="guest-ticket-hfg",
        name="Gostinski ulaznice",
        description="Upravljanje grupama gostiju, QR ulaznicama i check-in kodovima.",
        capabilities=[
            "list_groups",
            "guest_ticket",
            "create_group",
        ],
        keywords=["ticket", "guest", "qr", "checkin", "gost", "ulaznica", "grupa"],
    ),
    "recommendations-hfg": AgentCard(
        id="recommendations-hfg",
        name="Preporuke",
        description="Personalizirane preporuke za restorane, aktivnosti i lokalne znamenitosti.",
        capabilities=[
            "recommend_city",
            "restaurants_near",
            "wine_tasting",
        ],
        keywords=["preporuka", "recommend", "restoran", "što raditi", "vino", "aktivnost"],
    ),
    "bookings-hfg": AgentCard(
        id="bookings-hfg",
        name="Rezervacije",
        description="Pregled rezervacija, check-in i check-out gostiju.",
        capabilities=[
            "list_bookings",
            "checkin",
            "checkout",
        ],
        keywords=["booking", "rezervacija", "dolazak", "odlazak", "checkin", "checkout"],
    ),
    "events-hfg": AgentCard(
        id="events-hfg",
        name="Događaji",
        description="Lokalni događaji, koncerti i vikend aktivnosti u regiji.",
        capabilities=[
            "events_city",
            "events_weekend",
        ],
        keywords=["događaj", "event", "vikend", "koncert", "festival"],
    ),
    "host-dashboard-hfg": AgentCard(
        id="host-dashboard-hfg",
        name="Host nadzorna ploča",
        description="Profil domaćina, pretplata i korištenje resursa.",
        capabilities=[
            "account",
            "subscription",
            "usage",
        ],
        keywords=["račun", "account", "subscription", "plan", "limit", "pretplata"],
    ),
}
