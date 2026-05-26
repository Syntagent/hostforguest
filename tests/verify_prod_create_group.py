#!/usr/bin/env python3
"""Verify guest group create on production API (trailing slash → 201)."""

from __future__ import annotations

import json
import os
import sys
import uuid
from urllib import error, request

from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("HOSTFORGUEST_API_URL", "https://hostforguest.ska.syntagent.com").rstrip("/")
if "hostforguestka" in BASE:
    BASE = "https://hostforguest.syntagent.com"

EMAIL = os.getenv("VERIFY_HOST_EMAIL", "ana.mestrovic78@gmail.com")
PASSWORD = os.getenv("VERIFY_HOST_PASSWORD", "")


def http(method: str, path: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    data = None if body is None else json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload


def main() -> int:
    if not PASSWORD:
        print("SKIP: set VERIFY_HOST_PASSWORD in .env for live host verification")
        # Still verify anonymous trailing-slash behavior with register flow
        email = f"verify-{uuid.uuid4().hex[:10]}@example.com"
        password = "VerifyPass123!"
        reg = http(
            "POST",
            "/api/v1/hosts/register",
            {
                "email": email,
                "password": password,
                "first_name": "Verify",
                "last_name": "Bot",
                "address": "1 St",
                "city": "Lovran",
                "country": "Croatia",
            },
        )
        if reg[0] != 201:
            print(f"FAIL register in register: {reg}")
            return 1
        login = http("POST", "/api/v1/hosts/login", {"email": email, "password": password})
        if login[0] != 200:
            print(f"FAIL login: {login}")
            return 1
        token = login[1]["session_token"]
    else:
        login = http("POST", "/api/v1/hosts/login", {"email": EMAIL, "password": PASSWORD})
        if login[0] != 200:
            print(f"FAIL login for {EMAIL}: {login}")
            return 1
        token = login[1]["session_token"]
        print(f"OK login as {EMAIL}")

    headers = {"X-Session-Token": token}
    no_slash = http(
        "POST",
        "/api/v1/guest-groups",
        {"group_name": f"slash-test-{uuid.uuid4().hex[:6]}", "group_size": 2},
        headers,
    )
    with_slash = http(
        "POST",
        "/api/v1/guest-groups/",
        {"group_name": f"create-{uuid.uuid4().hex[:6]}", "group_size": 4},
        headers,
    )

    print(f"POST /guest-groups (no slash): {no_slash[0]}")
    print(f"POST /guest-groups/ (with slash): {with_slash[0]}")

    if with_slash[0] != 201:
        print(f"FAIL create with slash: {with_slash}")
        return 1

    group = with_slash[1]
    if group.get("group_size") != 4:
        print(f"FAIL group_size: {group}")
        return 1

    listed = http("GET", "/api/v1/guest-groups/host", headers=headers)
    if listed[0] != 200:
        print(f"FAIL list groups: {listed}")
        return 1

    ids = {g.get("id") for g in listed[1]}
    if group.get("id") not in ids:
        print(f"FAIL new group not in host list: {group.get('id')}")
        return 1

    print(f"OK created group {group.get('group_name')} id={group.get('id')} access={group.get('access_code')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
