"""HFG agent wrappers — thin adapters over existing backend services."""

from __future__ import annotations

import logging
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest_group import GuestGroupCreate, GuestGroupUpdate
from app.models.host import Host
from app.models.partner import BookingStatus, PartnerBooking
from app.models.recommendation import RecommendationRequestAPI
from app.services.attraction_service import AttractionService
from app.services.booking_service import BookingService
from app.services.event_discovery_service import EventDiscoveryService
from app.services.event_preference_matcher import filter_events_by_preferences
from app.services.events_feed_service import EventsFeedService
from app.services.guest_group_service import GuestGroupService
from app.services.host_service import HostService
from app.services.partner_service import PartnerService
from app.services.recommendation_service import RecommendationService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class BaseHFGAgent(ABC):
    """Base class for all HFG A2A agents."""

    agent_id: str = ""

    def __init__(self, db: Optional[AsyncSession]) -> None:
        self.db = db

    @abstractmethod
    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return {\"response\": markdown_hr, \"data\": optional_dict}."""

    def _error(self, text: str) -> Dict[str, Any]:
        return {"response": f"⚠️ {text}", "data": None}

    def _ok(self, text: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"response": text, "data": data}


class GuestTicketAgent(BaseHFGAgent):
    agent_id = "guest-ticket-hfg"

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.db or not host_id:
            return self._error("Niste povezani s host računom. Kontaktirajte podršku za povezivanje Telegrama.")

        svc = GuestGroupService(self.db)
        text = message.strip().lower()

        create_match = re.search(
            r"(?:create|kreiraj|nova)\s+(?:group|grupa)\s+(.+)",
            text,
            re.IGNORECASE,
        )
        if create_match:
            name = create_match.group(1).strip().title()
            now = datetime.utcnow()
            created = await svc.create_guest_group(
                host_id,
                GuestGroupCreate(
                    group_name=name,
                    group_size=2,
                    check_in_date=now,
                    check_out_date=now + timedelta(days=7),
                    preferred_language="hr",
                ),
            )
            if not created:
                return self._error("Kreiranje grupe nije uspjelo. Pokušajte ponovo.")
            context["last_command"] = "create_group"
            context["last_context"] = {"group_id": str(created.id)}
            cin = created.check_in_date.strftime("%d.%m.%Y") if created.check_in_date else "—"
            return self._ok(
                f"✅ **Grupa kreirana:** *{created.group_name}*\n"
                f"ID: `{created.id}`\n"
                f"Gosti: **{created.group_size}**\n"
                f"Check-in: {cin}",
                {"group_id": str(created.id)},
            )

        ticket_match = re.search(
            r"(?:ticket|ulaznica|qr)\s+(?:za\s+)?([a-f0-9\-]{8,})",
            text,
            re.IGNORECASE,
        )
        if ticket_match:
            try:
                gid = uuid.UUID(ticket_match.group(1))
            except ValueError:
                return self._error("Neispravan ID grupe. Koristite: `ticket za <uuid>`")
            exp = await svc.get_host_guest_experience(host_id, gid)
            if not exp:
                return self._error("Grupa nije pronađena ili nemate pristup.")
            gg = exp.guest_group
            acc = gg.accommodation
            prop = acc.property_name if acc else "Smještaj"
            code = exp.access_code or "—"
            context["last_command"] = "ticket"
            context["last_context"] = {"group_id": str(gid), "access_code": code}
            cin = gg.check_in_date.strftime("%d.%m.%Y") if gg.check_in_date else "—"
            cout = gg.check_out_date.strftime("%d.%m.%Y") if gg.check_out_date else "—"
            return self._ok(
                f"🎫 **Ulaznica za goste**\n\n"
                f"**Objekt:** {prop}\n"
                f"**Grupa:** *{gg.group_name or 'Bez imena'}*\n"
                f"**Gosti:** {gg.group_size}\n"
                f"**Datum:** {cin} – {cout}\n\n"
                f"**Pristupni kod:** `{code}`\n"
                f"**QR:** generirajte QR za URL gost aplikacije: `{exp.guest_app_path}`\n"
                f"_Pošaljite gostima link ili QR kod za brzi pristup._",
                {"access_code": code, "guest_app_path": exp.guest_app_path},
            )

        groups = await svc.get_host_guest_groups(host_id)
        if not groups:
            return self._ok(
                "📋 **Grupe gostiju**\n\nNemate aktivnih grupa.\n"
                "_Napišite:_ `kreiraj grupa Ime grupe`",
                {"groups": []},
            )

        lines = ["📋 **Vaše grupe gostiju**\n"]
        for i, g in enumerate(groups[:15], 1):
            acc = g.accommodation
            prop = acc.property_name if acc else "—"
            cin = g.check_in_date.strftime("%d.%m.%Y") if g.check_in_date else "—"
            cout = g.check_out_date.strftime("%d.%m.%Y") if g.check_out_date else "—"
            lines.append(
                f"{i}. **{g.group_name or 'Grupa'}** — {g.group_size} gostiju\n"
                f"   *{prop}* | {cin} → {cout}\n"
                f"   ID: `{g.id}`"
            )
        context["last_command"] = "list_groups"
        return self._ok("\n\n".join(lines), {"groups": [str(g.id) for g in groups]})


class RecommendationsAgent(BaseHFGAgent):
    agent_id = "recommendations-hfg"

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.db:
            return self._error("Baza podataka nije dostupna.")

        text = message.strip().lower()
        partner_svc = PartnerService(self.db)
        attraction_svc = AttractionService(self.db)

        if "vino" in text or "wine" in text or "degustacij" in text:
            partners = await partner_svc.list_partners(
                partner_type="restaurant",
                limit=10,
            )
            wine = [p for p in partners if p and ("vino" in (p.description or "").lower() or "wine" in (p.name or "").lower())]
            if not wine:
                wine = await partner_svc.list_partners(partner_type="activity", limit=5)
            if not wine:
                return self._ok(
                    "🍷 **Degustacije vina**\n\nTrenutno nema partnera u mreži. "
                    "Dodajte partnere u nadzornoj ploči.",
                )
            lines = ["🍷 **Preporuke za degustaciju vina**\n"]
            for i, p in enumerate(wine[:8], 1):
                lines.append(
                    f"{i}. **{p.name}** — {p.city or 'Kvarner'}\n"
                    f"   _{p.description[:120] if p.description else 'Lokalni partner'}_"
                )
            context["last_command"] = "wine_tasting"
            return self._ok("\n\n".join(lines))

        rest_match = re.search(
            r"(?:restoran|restaurant|restorani)\s+(?:kod|near|blizu|u)?\s*(.+)",
            text,
            re.IGNORECASE,
        )
        city = None
        if rest_match:
            city = rest_match.group(1).strip().title()
        else:
            rec_match = re.search(
                r"(?:preporuk|recommend|što raditi|sto raditi)\s+(?:za|u|in)?\s*(.+)",
                text,
                re.IGNORECASE,
            )
            if rec_match:
                city = rec_match.group(1).strip().title()

        if city:
            restaurants = await partner_svc.list_partners(
                city=city,
                partner_type="restaurant",
                limit=8,
            )
            if restaurants:
                lines = [f"🍽️ **Restorani — {city}**\n"]
                for i, p in enumerate(restaurants, 1):
                    rating = f"⭐ {p.average_rating:.1f}" if p.average_rating else ""
                    lines.append(
                        f"{i}. **{p.name}** {rating}\n"
                        f"   _{p.description[:100] if p.description else 'Preporučeni partner'}_"
                    )
                context["last_command"] = "restaurants_near"
                context["last_context"] = {"city": city}
                return self._ok("\n\n".join(lines), {"city": city})

            attractions = await attraction_svc.get_attractions_by_city(city, limit=8)
            if attractions:
                lines = [f"📍 **Preporuke — {city}**\n"]
                for i, a in enumerate(attractions, 1):
                    lines.append(
                        f"{i}. **{a.name}**\n"
                        f"   _{a.description[:100] if a.description else a.category or 'Atrakcija'}_"
                    )
                context["last_command"] = "recommend_city"
                context["last_context"] = {"city": city}
                return self._ok("\n\n".join(lines), {"city": city})

            return self._ok(f"Nema preporuka za *{city}*. Pokušajte s Lovran, Opatija ili Rijeka.")

        if host_id:
            gg_svc = GuestGroupService(self.db)
            groups = await gg_svc.get_host_guest_groups(host_id)
            if groups:
                rec_svc = RecommendationService(self.db)
                batch = await rec_svc.get_personalized_recommendations(
                    groups[0].id,
                    RecommendationRequestAPI(
                        max_recommendations=5,
                        language="hr",
                        preferred_categories=["dining", "activity"],
                    ),
                )
                if batch.recommendations:
                    lines = ["✨ **Personalizirane preporuke**\n"]
                    for i, r in enumerate(batch.recommendations, 1):
                        lines.append(
                            f"{i}. **{r.title}**\n"
                            f"   _{r.description[:100] if r.description else ''}_"
                        )
                    context["last_command"] = "recommend"
                    return self._ok("\n\n".join(lines))

        popular = await attraction_svc.get_popular_attractions(limit=5)
        if popular:
            lines = ["✨ **Popularne preporuke u regiji**\n"]
            for i, a in enumerate(popular, 1):
                lines.append(f"{i}. **{a.name}** — {a.city or 'Kvarner'}")
            return self._ok("\n\n".join(lines))

        return self._ok(
            "Napišite npr. _preporuka Lovran_, _restorani kod Opatija_ ili _wine tasting_."
        )


class BookingsAgent(BaseHFGAgent):
    agent_id = "bookings-hfg"

    _STATUS_EMOJI = {
        "pending": "🟡",
        "confirmed": "🟢",
        "cancelled": "🔴",
        "completed": "✅",
        "refunded": "💸",
    }

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.db or not host_id:
            return self._error("Niste povezani s host računom.")

        text = message.strip().lower()
        svc = BookingService(self.db)
        gg_svc = GuestGroupService(self.db)

        checkin_match = re.search(r"check\s*in\s+([a-f0-9\-]+)", text)
        checkout_match = re.search(r"check\s*out\s+([a-f0-9\-]+)", text)

        if checkin_match:
            bid = checkin_match.group(1)
            try:
                uid = uuid.UUID(bid)
            except ValueError:
                return self._error("Neispravan ID rezervacije.")
            group = await gg_svc.get_guest_group_by_id(uid)
            if group and str(group.host_id) == str(host_id):
                updated = await gg_svc.update_guest_group(
                    uid,
                    GuestGroupUpdate(actual_arrival=datetime.utcnow()),
                )
                if updated:
                    context["last_command"] = "checkin"
                    return self._ok(f"✅ **Check-in** za grupu *{updated.group_name}* zabilježen.")
            ok = await svc.confirm_booking(uid)
            if ok:
                context["last_command"] = "checkin"
                return self._ok(f"✅ **Check-in** rezervacije `{bid}` potvrđen.")
            return self._error("Check-in nije uspio. Provjerite ID rezervacije.")

        if checkout_match:
            bid = checkout_match.group(1)
            try:
                uid = uuid.UUID(bid)
            except ValueError:
                return self._error("Neispravan ID rezervacije.")
            group = await gg_svc.get_guest_group_by_id(uid)
            if group and str(group.host_id) == str(host_id):
                updated = await gg_svc.update_guest_group(
                    uid,
                    GuestGroupUpdate(actual_departure=datetime.utcnow()),
                )
                if updated:
                    context["last_command"] = "checkout"
                    return self._ok(f"👋 **Check-out** za grupu *{updated.group_name}* zabilježen.")
            try:
                stmt = (
                    update(PartnerBooking)
                    .where(
                        PartnerBooking.id == uid,
                        PartnerBooking.host_id == host_id,
                    )
                    .values(status=BookingStatus.COMPLETED, updated_at=datetime.utcnow())
                )
                result = await self.db.execute(stmt)
                await self.db.commit()
                if result.rowcount:
                    context["last_command"] = "checkout"
                    return self._ok(f"👋 **Check-out** rezervacije `{bid}` završen.")
            except Exception as exc:
                logger.error("Checkout booking failed: %s", exc)
                await self.db.rollback()
            return self._error("Check-out nije uspio. Provjerite ID rezervacije.")

        bookings = await svc.get_bookings_for_host(host_id, limit=20)
        if not bookings:
            return self._ok(
                "📅 **Rezervacije**\n\nNemate nadolazećih rezervacija.\n"
                "_Partner rezervacije pojavljuju se ovdje nakon kreiranja._",
                {"bookings": []},
            )

        lines = ["📅 **Vaše rezervacije** (najnovije)\n"]
        for b in bookings:
            status = b.status.value if hasattr(b.status, "value") else str(b.status)
            emoji = self._STATUS_EMOJI.get(status, "⚪")
            bdate = b.booking_date.strftime("%d.%m.%Y") if b.booking_date else "—"
            lines.append(
                f"{emoji} **{bdate}** — {b.booking_amount:.2f} {b.currency}\n"
                f"   Status: *{status}* | ID: `{b.id}`"
            )
        context["last_command"] = "list_bookings"
        return self._ok("\n\n".join(lines), {"count": len(bookings)})


class EventsAgent(BaseHFGAgent):
    agent_id = "events-hfg"

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.db:
            return self._error("Baza podataka nije dostupna.")

        text = message.strip().lower()
        feed = EventsFeedService(self.db)
        discovery = EventDiscoveryService(self.db)

        weekend = "vikend" in text or "weekend" in text or "ovaj vikend" in text
        city_match = re.search(
            r"(?:događaj|dogadaj|event|events)\s+(?:u|za|in)?\s*(.+)",
            text,
            re.IGNORECASE,
        )
        city = city_match.group(1).strip().title() if city_match else None

        freshness_city = city or "Lovran"
        fresh = await discovery.ensure_fresh_events(
            freshness_city,
            host_id=str(host_id) if host_id else None,
            trigger_if_stale=True,
        )

        if weekend:
            events = await feed.get_local_events(hours=168, limit=15)
            now = datetime.utcnow()
            weekend_end = now + timedelta(days=(5 - now.weekday()) % 7 + 2)
            filtered = []
            for ev in events:
                start = ev.get("start_at") or ev.get("scraped_at")
                if start:
                    try:
                        if isinstance(start, str):
                            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        else:
                            start_dt = start
                        if now <= start_dt.replace(tzinfo=None) <= weekend_end:
                            filtered.append(ev)
                    except (ValueError, TypeError):
                        filtered.append(ev)
                else:
                    filtered.append(ev)
            events = filtered[:10] or events[:10]
            title = "🎉 **Događaji ovaj vikend**\n"
            context["last_command"] = "events_weekend"
        elif city:
            events = await feed.get_local_events(city=city, limit=10)
            title = f"🎉 **Događaji — {city}**\n"
            context["last_command"] = "events_city"
            context["last_context"] = {"city": city}
        else:
            events = await feed.get_local_events(limit=10)
            title = "🎉 **Nadolazeći događaji**\n"
            context["last_command"] = "events"

        events = filter_events_by_preferences(
            events,
            guest_text=text,
            city=freshness_city,
        )

        if not events and fresh.get("discovery_triggered"):
            return self._ok(
                f"🔍 **Tražim događaje za {freshness_city}...**\n\n"
                "Provjeravam turističke izvore i ažuriram kalendar.\n"
                "_Pokušajte ponovo za nekoliko minuta._"
            )

        if not events:
            return self._ok(
                f"{title}\nTrenutno nema događaja u bazi.\n"
                "_Pokušajte:_ `događaji Lovran` ili `events this weekend`"
            )

        lines = [title]
        for i, ev in enumerate(events, 1):
            ev_title = ev.get("title") or "Događaj"
            loc = ev.get("city") or ev.get("region") or "Kvarner"
            start = ev.get("start_at") or ev.get("start_date") or ""
            etype = ev.get("event_type") or ""
            venue = ev.get("venue_name") or ""
            if start and len(str(start)) > 10:
                start = str(start)[:10]
            link = ev.get("url") or ev.get("source_url") or ""
            link_line = f"\n   [Više info]({link})" if link else ""
            meta = f" | 🏷 {etype}" if etype else ""
            venue_line = f"\n   📌 {venue}" if venue else ""
            lines.append(
                f"{i}. **{ev_title}**\n"
                f"   📍 {loc} | 📅 {start or 'uskoro'}{meta}{venue_line}{link_line}"
            )
        if fresh.get("discovery_triggered") and fresh.get("fresh_count", 0) > 0:
            lines.append(f"\n_Evo svježih događaja za {freshness_city}! 🎉_")
        return self._ok("\n\n".join(lines), {"count": len(events), "freshness": fresh})


class HostDashboardAgent(BaseHFGAgent):
    agent_id = "host-dashboard-hfg"

    async def execute(
        self,
        message: str,
        host_id: Optional[uuid.UUID],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.db or not host_id:
            return self._error("Niste povezani s host računom.")

        text = message.strip().lower()
        host_svc = HostService(self.db)
        sub_svc = SubscriptionService(self.db)

        host = await host_svc.get_host_by_id(host_id)
        if not host:
            return self._error("Host profil nije pronađen.")

        if "usage" in text or "korištenje" in text or "limit" in text:
            from sqlalchemy import and_
            from app.models.subscription import UsageLimit

            limits = ["guest_groups", "attractions", "ai_requests"]
            lines = ["📊 **Korištenje resursa**\n"]
            for lt in limits:
                stmt = select(UsageLimit).where(
                    and_(
                        UsageLimit.host_id == host_id,
                        UsageLimit.limit_type == lt,
                        UsageLimit.period_end >= datetime.utcnow(),
                    )
                )
                result = await self.db.execute(stmt)
                usage_limit = result.scalar_one_or_none()
                if usage_limit and usage_limit.limit_value is not None:
                    current = usage_limit.current_usage or 0
                    limit = usage_limit.limit_value
                    pct = min(100, int(100 * current / limit)) if limit else 0
                    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                    lines.append(
                        f"**{lt}:** {current}/{limit}\n"
                        f"`{bar}` {pct}%"
                    )
                else:
                    lines.append(f"**{lt}:** bez limita")
            context["last_command"] = "usage"
            return self._ok("\n".join(lines))

        if "subscription" in text or "pretplata" in text or "plan" in text:
            sub = await sub_svc.get_host_subscription(host_id)
            tier = host.subscription_tier or "basic"
            active = "✅ aktivna" if host.subscription_active else "❌ neaktivna"
            lines = [
                "💳 **Pretplata**\n",
                f"**Plan:** *{tier}*",
                f"**Status:** {active}",
            ]
            if sub:
                status = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
                lines.append(f"**Pretplata:** {status}")
                if sub.current_period_end:
                    lines.append(f"**Vrijedi do:** {sub.current_period_end:%d.%m.%Y}")
            context["last_command"] = "subscription"
            return self._ok("\n".join(lines))

        profile = await host_svc.get_host_profile(host_id)
        prop = profile.property_name if profile else host.business_name or "—"
        lines = [
            "👤 **Vaš račun**\n",
            f"**Ime:** {host.first_name} {host.last_name}",
            f"**Email:** {host.email}",
            f"**Objekt:** *{prop}*",
            f"**Grad:** {host.city}",
            f"**Plan:** {host.subscription_tier or 'basic'}",
            f"**Grupe gostiju:** {host.total_guest_groups or 0}",
            f"**Ocjena:** ⭐ {host.average_rating:.1f}" if host.average_rating else "",
        ]
        context["last_command"] = "account"
        return self._ok("\n".join(l for l in lines if l))


def build_all_agents(db: Optional[AsyncSession]) -> List[BaseHFGAgent]:
    """Instantiate all five HFG agents with a shared DB session."""
    return [
        GuestTicketAgent(db),
        RecommendationsAgent(db),
        BookingsAgent(db),
        EventsAgent(db),
        HostDashboardAgent(db),
    ]
