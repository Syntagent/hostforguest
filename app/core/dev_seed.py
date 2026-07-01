"""
Ensure a default host exists in development so "Dev Login" on the frontend works.

Credentials match NEXT_PUBLIC_DEV_LOGIN_* on the frontend (defaults below).

Docker Compose sets DEV_LOGIN_SEED_FORCE=true so the dev user is created or the password
is reset to dev_login_seed_password on each API startup (local only).

passlib + bcrypt: use bcrypt<5 in requirements.txt; bcrypt 5 breaks passlib 1.7.4 hashing.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.db.postgresql.connection import AsyncSessionLocal
from sqlalchemy import select

from app.models.host import Host, HostCreate, HostProfile
from app.services.host_service import HostService
from app.services.rls_service import RLSService

logger = logging.getLogger(__name__)


def _should_seed_dev_user() -> bool:
    if not getattr(settings, "dev_login_seed_enabled", True):
        return False
    if getattr(settings, "dev_login_seed_force", False):
        return True
    if settings.is_development:
        return True
    if getattr(settings, "debug", False):
        return True
    return False


async def seed_dev_login_user_if_needed() -> None:
    """Create dev seed host if missing; with DEV_LOGIN_SEED_FORCE, reset password to match seed."""
    if not _should_seed_dev_user():
        return

    async with AsyncSessionLocal() as session:
        try:
            async with RLSService(session).worker_bypass():
                svc = HostService(session)
                email = (settings.dev_login_seed_email or "").strip().lower()
                if not email:
                    return
                existing = await svc.get_host_by_email(email)
                password = settings.dev_login_seed_password or ""
                if existing:
                    if getattr(settings, "dev_login_seed_force", False) and len(password) >= 8:
                        if await svc.set_password_for_email_normalized(email, password):
                            logger.info(
                                "Dev login seed: synced password for %s (DEV_LOGIN_SEED_FORCE)",
                                email,
                            )
                        else:
                            logger.warning("Dev login seed: could not sync password for %s", email)
                    else:
                        logger.debug("Dev login seed: host already exists (%s)", email)
                    return

                if len(password) < 8:
                    logger.warning("Dev login seed skipped: password must be at least 8 characters")
                    return

                host_data = HostCreate(
                    email=email,
                    password=password,
                    first_name="Dev",
                    last_name="Host",
                    address="1 Dev Road",
                    city="Lovran",
                )
                created = await svc.create_host(host_data)
                if created:
                    logger.info(
                        "Dev login seed: created host %s (matches frontend Dev Login defaults)",
                        email,
                    )
                else:
                    logger.warning("Dev login seed: create_host returned None for %s", email)
        except Exception as e:
            logger.warning("Dev login seed failed (non-fatal): %s", e)
            try:
                await session.rollback()
            except Exception:
                pass


async def seed_dev_host_profile_shell_if_needed() -> None:
    """
    If the dev login host exists but has no host_profiles row, create an empty shell.

    Property / stay location (city, address, coordinates) must be set in the database
    (host dashboard → profile, API, SQL, or migrations) — nothing is hardcoded here.
    """
    if not _should_seed_dev_user():
        return

    email = (settings.dev_login_seed_email or "").strip().lower()
    if not email:
        return

    async with AsyncSessionLocal() as session:
        try:
            async with RLSService(session).worker_bypass():
                hr = await session.execute(select(Host).where(Host.email == email))
                host = hr.scalar_one_or_none()
                if not host:
                    return

                pr = await session.execute(
                    select(HostProfile).where(HostProfile.host_id == host.id)
                )
                if pr.scalar_one_or_none() is not None:
                    return

                # Match migrations/add_location_fields_to_host_profiles.sql NOT NULL columns.
                session.add(
                    HostProfile(
                        host_id=host.id,
                        city="Unknown",
                        county="Unknown",
                        address="Address not specified",
                        latitude=0.0,
                        longitude=0.0,
                    )
                )
                await session.commit()
                logger.info(
                    "Dev seed: created empty HostProfile for %s (edit stay/property in DB or dashboard)",
                    email,
                )
        except Exception as e:
            logger.warning("Dev host profile shell seed failed (non-fatal): %s", e)
            try:
                await session.rollback()
            except Exception:
                pass


async def seed_dev_cleaning_partners_if_needed() -> None:
    """Create sample cleaning Partner rows in dev for the Cleaning dashboard (idempotent by name+city)."""
    if not _should_seed_dev_user():
        return
    from sqlalchemy import select, func
    from app.models.partner import Partner, PartnerStatus, PartnerType
    from app.db.postgresql.connection import AsyncSessionLocal

    samples = [
        {
            "name": "Lovran Turnover Cleaning (Dev)",
            "description": "Sample turnover cleaning for short-term rentals (dev seed).",
            "partner_type": PartnerType.CLEANING.value,
            "category": "cleaning",
            "city": "Lovran",
            "region": "Primorje-Gorski Kotar",
            "email": "dev-cleaners-lov@example.com",
            "phone": "+385991112233",
            "website": "https://example.com",
            "status": PartnerStatus.ACTIVE,
            "price_range": "moderate",
            "rate_card": {"studio": 50, "one_bed": 65, "two_bed": 85, "currency": "EUR"},
            "price_notes": "Indicative only; confirm linen and checkout time with the provider.",
            "languages_spoken": ["hr", "en", "de"],
        },
        {
            "name": "Opatija Riviera Clean Team (Dev)",
            "description": "Sample deep clean and turnover service (dev seed).",
            "partner_type": PartnerType.CLEANING.value,
            "category": "cleaning",
            "city": "Opatija",
            "region": "Primorje-Gorski Kotar",
            "email": "dev-cleaners-op@example.com",
            "phone": "+385992223344",
            "status": PartnerStatus.ACTIVE,
            "price_range": "moderate",
            "rate_card": {"standard_clean": 70, "deep_clean": 120, "currency": "EUR"},
            "price_notes": "Weekend rates may differ. Always confirm before booking.",
            "languages_spoken": ["hr", "en", "it"],
        },
    ]

    async with AsyncSessionLocal() as session:
        try:
            for row in samples:
                stmt = select(Partner).where(
                    func.lower(Partner.name) == row["name"].lower(),
                    func.lower(Partner.city) == row["city"].lower(),
                )
                res = await session.execute(stmt)
                if res.scalar_one_or_none():
                    continue
                p = Partner(**row)
                session.add(p)
            await session.commit()
            logger.info("Dev seed: ensured sample cleaning partners exist")
        except Exception as e:
            logger.warning("Dev cleaning partner seed failed (non-fatal): %s", e)
            try:
                await session.rollback()
            except Exception:
                pass


async def seed_dev_trades_partners_if_needed() -> None:
    """Sample majstori (trades) for Maintenance partner suggestions — idempotent by name+city."""
    if not _should_seed_dev_user():
        return
    from sqlalchemy import select, func
    from app.models.partner import Partner, PartnerStatus, PartnerType
    from app.db.postgresql.connection import AsyncSessionLocal

    samples = [
        {
            "name": "Vodoinstalater Dev (Lovran)",
            "description": "Sample plumber for maintenance tab / AI ranking (dev only).",
            "partner_type": PartnerType.TRADES.value,
            "category": "plumbing",
            "trade_categories": ["plumbing"],
            "emergency_available": True,
            "city": "Lovran",
            "region": "Primorje-Gorski Kotar",
            "phone": "+385993334455",
            "latitude": 45.2919,
            "longitude": 14.2742,
            "status": PartnerStatus.ACTIVE.value,
            "languages_spoken": ["hr", "en"],
        },
        {
            "name": "Električar Dev (Opatija)",
            "description": "Sample electrician for maintenance suggestions (dev only).",
            "partner_type": PartnerType.TRADES.value,
            "category": "electrical",
            "trade_categories": ["electrical"],
            "city": "Opatija",
            "region": "Primorje-Gorski Kotar",
            "phone": "+385994445566",
            "latitude": 45.3376,
            "longitude": 14.3053,
            "status": PartnerStatus.ACTIVE.value,
            "languages_spoken": ["hr", "en", "it"],
        },
    ]

    async with AsyncSessionLocal() as session:
        try:
            for row in samples:
                stmt = select(Partner).where(
                    func.lower(Partner.name) == row["name"].lower(),
                    func.lower(Partner.city) == row["city"].lower(),
                )
                res = await session.execute(stmt)
                if res.scalar_one_or_none():
                    continue
                p = Partner(**row)
                session.add(p)
            await session.commit()
            logger.info("Dev seed: ensured sample trades partners exist")
        except Exception as e:
            logger.warning("Dev trades partner seed failed (non-fatal): %s", e)
            try:
                await session.rollback()
            except Exception:
                pass

