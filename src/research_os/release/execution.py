from __future__ import annotations

from collections.abc import Iterable
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


def pytest_node_runner(nodeid: str) -> bool:
    env = os.environ.copy()
    env["RESEARCH_OS_RUN_PDF_INTEGRATION"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", nodeid],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode == 0


def pytest_batch_runner(nodeids: Iterable[str]) -> bool:
    env = os.environ.copy()
    env["RESEARCH_OS_RUN_PDF_INTEGRATION"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *nodeids],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    return result.returncode == 0
