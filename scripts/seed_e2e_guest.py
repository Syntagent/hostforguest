#!/usr/bin/env python3
"""
Ensure a dev host guest group exists for Playwright CI (Events tab smoke).

Prints E2E_GUEST_ACCESS_CODE=<code> on success (stdout). Idempotent by group name.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

API_BASE = os.getenv("E2E_API_URL", "http://127.0.0.1:8000").rstrip("/")
GROUP_NAME = os.getenv("E2E_GUEST_GROUP_NAME", "E2E CI Guest Group")
DEV_EMAIL = os.getenv("DEV_LOGIN_SEED_EMAIL", "dev@touristguide.local").strip().lower()
DEV_PASSWORD = os.getenv("DEV_LOGIN_SEED_PASSWORD", "devlogin123")
HEALTH_TIMEOUT_SEC = int(os.getenv("E2E_HEALTH_TIMEOUT_SEC", "120"))


def _wait_for_api(client: httpx.Client) -> None:
    deadline = time.monotonic() + HEALTH_TIMEOUT_SEC
    last_error = "API not reachable"
    while time.monotonic() < deadline:
        try:
            r = client.get("/health", timeout=5.0)
            if r.status_code == 200:
                return
            last_error = f"/health returned {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"API at {API_BASE} not ready: {last_error}")


def _login(client: httpx.Client) -> str:
    r = client.post(
        "/api/v1/hosts/login",
        json={"email": DEV_EMAIL, "password": DEV_PASSWORD},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Dev login failed ({r.status_code}): {r.text}")
    token = (r.json() or {}).get("session_token")
    if not token:
        raise RuntimeError("Dev login response missing session_token")
    return token


def _group_payload() -> dict:
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(days=5)
    return {
        "group_name": GROUP_NAME,
        "group_size": 2,
        "check_in_date": start.isoformat(),
        "check_out_date": end.isoformat(),
        "lead_guest_name": "E2E Guest",
        "lead_guest_email": "e2e-guest@example.com",
        "preferred_language": "en",
        "interests": ["culture", "food", "events"],
        "budget_level": "moderate",
    }


def _ensure_guest_preferences(client: httpx.Client, access_code: str) -> None:
    prefs = client.get(f"/api/v1/guest-groups/access/{access_code}/preferences")
    if prefs.status_code != 200:
        raise RuntimeError(f"Get preferences failed ({prefs.status_code}): {prefs.text}")
    if prefs.json():
        return

    created = client.post(
        f"/api/v1/guest-groups/access/{access_code}/preferences",
        json={
            "guest_name": "E2E Guest",
            "personal_interests": ["culture", "food", "events"],
            "language_preference": "en",
            "food_interests": ["local_cuisine"],
            "cultural_interests": ["history"],
        },
    )
    if created.status_code != 201:
        raise RuntimeError(f"Create preferences failed ({created.status_code}): {created.text}")


def ensure_e2e_guest_group() -> str:
    with httpx.Client(base_url=API_BASE, timeout=60.0, follow_redirects=True) as client:
        _wait_for_api(client)
        token = _login(client)
        headers = {"X-Session-Token": token}

        groups = client.get("/api/v1/guest-groups/host", headers=headers)
        if groups.status_code != 200:
            raise RuntimeError(f"List guest groups failed ({groups.status_code}): {groups.text}")

        access_code: str | None = None
        for row in groups.json() or []:
            if row.get("group_name") == GROUP_NAME and row.get("access_code"):
                access_code = str(row["access_code"])
                break

        if not access_code:
            created = client.post(
                "/api/v1/guest-groups/",
                json=_group_payload(),
                headers=headers,
            )
            if created.status_code != 201:
                raise RuntimeError(f"Create guest group failed ({created.status_code}): {created.text}")
            access_code = (created.json() or {}).get("access_code")
            if not access_code:
                raise RuntimeError("Create guest group response missing access_code")
            access_code = str(access_code)

        _ensure_guest_preferences(client, access_code)
        return access_code


def main() -> int:
    try:
        access_code = ensure_e2e_guest_group()
    except Exception as exc:  # noqa: BLE001
        print(f"seed_e2e_guest failed: {exc}", file=sys.stderr)
        return 1

    print(f"E2E_GUEST_ACCESS_CODE={access_code}")
    print(f"E2E_GUEST_GROUP_NAME={GROUP_NAME!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
