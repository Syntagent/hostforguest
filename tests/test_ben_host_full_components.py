#!/usr/bin/env python3
"""Pytest wrapper for Ben host full-component API scenario."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.integration
def test_ben_host_full_components_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tests", "ben_host_full_components.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
