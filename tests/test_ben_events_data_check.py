"""Pytest wrapper for Ben events data check."""

import subprocess
import sys
from pathlib import Path


def test_ben_events_data_check() -> None:
    script = Path(__file__).resolve().parent / "ben_events_data_check.py"
    result = subprocess.run([sys.executable, str(script)], check=False)
    assert result.returncode == 0, "ben_events_data_check.py failed"
