"""Ensure reverse-proxy examples stay aligned with documented VPS/Docker ports."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY = REPO_ROOT / "deploy"


def _read(rel: str) -> str:
    return (DEPLOY / rel).read_text(encoding="utf-8")


def test_deploy_readme_points_at_full_guide_and_examples():
    text = _read("README.md")
    assert "docs/REVERSE_PROXY.md" in text
    assert "nginx/hostforguest.conf.example" in text
    assert "8006" in text
    assert "3007" in text


def test_nginx_example_routes_api_before_ui():
    text = _read("nginx/hostforguest.conf.example")
    api_idx = text.index("location /api/")
    ui_idx = text.index("location / {")
    assert api_idx < ui_idx
    assert "hostforguest_api" in text
    assert "127.0.0.1:8006" in text
    assert "127.0.0.1:3007" in text


def test_caddy_example_routes_api_before_ui():
    text = _read("caddy/Caddyfile.example")
    assert "handle /api/*" in text
    assert "127.0.0.1:8006" in text
    assert "127.0.0.1:3007" in text
