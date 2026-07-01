#!/usr/bin/env python3
"""Browser E2E: host can create a guest group on production."""

from __future__ import annotations

import json
import os
import sys
import uuid

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, expect

load_dotenv()

BASE = os.getenv("HOSTFORGUEST_PUBLIC_URL", "https://hostforguest.syntagent.com").rstrip("/")
API = os.getenv("HOSTFORGUEST_API_URL", BASE).rstrip("/")


def api_register_and_login() -> tuple[str, str]:
    import urllib.request

    email = f"pw-{uuid.uuid4().hex[:10]}@example.com"
    password = "PlaywrightPass123!"
    payload = json.dumps(
        {
            "email": email,
            "password": password,
            "first_name": "PW",
            "last_name": "Test",
            "address": "1 St",
            "city": "Lovran",
            "country": "Croatia",
        }
    ).encode()
    req = urllib.request.Request(
        f"{API}/api/v1/hosts/register",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 201, resp.read()

    login_payload = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API}/api/v1/hosts/login",
        data=login_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    return email, body["session_token"]


def main() -> int:
    email, token = api_register_and_login()
    group_name = f"PW Group {uuid.uuid4().hex[:6]}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Seed session so dashboard loads authenticated
        page.goto(f"{BASE}/login")
        page.evaluate(
            """([sessionToken]) => {
              localStorage.setItem('session_token', sessionToken);
            }""",
            [token],
        )
        page.goto(f"{BASE}/dashboard?tab=groups")
        page.wait_for_load_state("networkidle", timeout=30000)

        create_btn = page.get_by_role("button", name="Create New Guest Group")
        create_btn.wait_for(state="visible", timeout=20000)
        create_btn.click()

        page.get_by_label("Group Name").fill(group_name)
        page.get_by_label("Group Size").fill("3")
        page.get_by_role("button", name="Create Group").click()

        page.wait_for_timeout(2000)
        expect(page.get_by_text(group_name)).to_be_visible(timeout=15000)

        browser.close()

    print(f"OK browser create group: {group_name} ({email})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
