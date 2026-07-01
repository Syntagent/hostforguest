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

    def to_public_dict(self) -> Dict[str, Any]:
        """Guest/anonymous registry — omit orchestrator routing metadata."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "language": self.language,
        }


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

GUEST_AGENT_CARDS: Dict[str, AgentCard] = {
    "guest-welcome-hfg": AgentCard(
        id="guest-welcome-hfg",
        name="Gost dobrodošlica",
        description="QR ulaznica, dobrodošlica i hvatanje preferencija gosta.",
        capabilities=[
            "parse_ticket",
            "welcome",
            "capture_preferences",
            "initial_recommendations",
        ],
        keywords=["start", "ticket", "dobrodošli", "preferenc", "odmor"],
    ),
    "guest-concierge-hfg": AgentCard(
        id="guest-concierge-hfg",
        name="Gost concierge",
        description="Personalizirane preporuke, praktične informacije (ljekarne, trgovine, prijevoz, servisi), restorani, plaže, atrakcije — sve što gost treba znati.",
        capabilities=[
            "personalized_recommendations",
            "restaurants",
            "beaches",
            "activities",
        ],
        keywords=["posjetiti", "jesti", "restoran", "plaž", "preporuk", "što raditi"],
    ),
    "guest-events-hfg": AgentCard(
        id="guest-events-hfg",
        name="Gost događaji",
        description="Događaji filtrirani po lokaciji, datumu boravka i preferencijama.",
        capabilities=[
            "events_stay",
            "events_weekend",
            "family_events",
        ],
        keywords=["događaj", "dogadaj", "koncert", "festival", "vikend", "što se događa"],
    ),
    "guest-emergency-hfg": AgentCard(
        id="guest-emergency-hfg",
        name="Gost hitna pomoć",
        description="ISKLJUČIVO za hitne situacije: ozljeda, teška bolest, lom, požar, sigurnosna prijetnja. NE za pitanja gdje kupiti lijek.",
        capabilities=[
            "emergency_contacts",
            "host_notify",
            "hospital_info",
        ],
        keywords=["hitno", "ne radi", "problem", "bolest", "doktor", "pomoć", "urgent"],
    ),
    "guest-info-hfg": AgentCard(
        id="guest-info-hfg",
        name="Gost informacije",
        description="WiFi, check-in/out, kućni red, parking, vremenska prognoza, upute do smještaja.",
        capabilities=[
            "wifi",
            "house_rules",
            "directions",
            "weather",
        ],
        keywords=["wifi", "check-in", "check-out", "parking", "pravila", "trgovina", "vrijeme"],
    ),
}

ALL_HFG_AGENT_CARDS: Dict[str, AgentCard] = {**HFG_AGENT_CARDS, **GUEST_AGENT_CARDS}
