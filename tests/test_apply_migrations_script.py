"""Smoke checks for scripts/apply-migrations.sh (dry-run, no DB writes)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "apply-migrations.sh"
ORDER_FILE = REPO_ROOT / "migrations" / "MIGRATION_ORDER.txt"


def test_apply_migrations_script_exists_and_is_executable() -> None:
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK)


def test_apply_migrations_dry_run_lists_all_ordered_files() -> None:
    expected = [
        line.strip()
        for line in ORDER_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert expected, "MIGRATION_ORDER.txt should list at least one migration"

    proc = subprocess.run(
        [str(SCRIPT), "--dry-run"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout
    for name in expected:
        assert name in out, f"dry-run output should mention {name}"
    assert f"Applying {len(expected)} migration(s)" in out
