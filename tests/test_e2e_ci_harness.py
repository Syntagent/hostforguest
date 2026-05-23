"""Contract checks for CI Playwright guest-events harness."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SCRIPT = REPO_ROOT / "scripts" / "run-e2e-ci.sh"
SEED_SCRIPT = REPO_ROOT / "scripts" / "seed_e2e_guest.py"
PW_CONFIG = REPO_ROOT / "tests" / "e2e" / "playwright.ci.config.ts"
PW_SPEC = REPO_ROOT / "tests" / "e2e" / "ci-guest-events.spec.ts"


def test_e2e_ci_harness_files_exist() -> None:
    assert RUN_SCRIPT.is_file()
    assert os.access(RUN_SCRIPT, os.X_OK)
    assert SEED_SCRIPT.is_file()
    assert PW_CONFIG.is_file()
    assert PW_SPEC.is_file()


def test_seed_e2e_guest_script_compiles() -> None:
    proc = subprocess.run(
        ["python3", "-m", "py_compile", str(SEED_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.returncode == 0


def test_run_e2e_ci_script_documents_stack_ports() -> None:
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert "uvicorn app.main:app" in text
    assert "playwright.ci.config.ts" in text
    assert "seed_e2e_guest.py" in text
    assert "3055" in text
    assert "8000" in text
