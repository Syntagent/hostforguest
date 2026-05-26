"""Pytest wrapper for Ben guest full API component check."""

import subprocess
import sys
from pathlib import Path


def test_ben_guest_full_components() -> None:
    script = Path(__file__).resolve().parent / "ben_guest_full_components.py"
    result = subprocess.run([sys.executable, str(script)], check=False)
    assert result.returncode == 0, "ben_guest_full_components.py failed"
