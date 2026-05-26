#!/usr/bin/env python3
"""Integration: Ben scenario guest group + multi-guest API interaction."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.integration
def test_ben_guest_interaction_scenario_exits_zero() -> None:
    env = {**os.environ, "BEN_SCENARIO_REUSE": "1"}
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tests", "ben_guest_interaction_scenario.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
