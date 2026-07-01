"""Production API must target the prod Postgres container, not shared DNS alias 'postgres'."""

from pathlib import Path


def test_vps_prod_compose_pins_postgres_server():
    compose = Path(__file__).resolve().parents[1] / "docker-compose.vps-prod.yml"
    text = compose.read_text(encoding="utf-8")
    assert "POSTGRES_SERVER: hostforguest_prod_postgres" in text
    assert "POSTGRES_SERVER: postgres" not in text
