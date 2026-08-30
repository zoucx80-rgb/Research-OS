import os
import subprocess, sys

import pytest

from research_os.version import RESEARCH_OS_VERSION


@pytest.mark.skipif(
    os.environ.get("RESEARCH_OS_RUN_PDF_INTEGRATION") != "1",
    reason="the stable gate requires the optional Playwright/Chromium backend",
)
def test_release_gate_script_runs_from_clean_repo_checkout():
    p=subprocess.run([sys.executable,"scripts/release_gate_v1_1.py"],capture_output=True,text=True)
    assert p.returncode==0, p.stderr
    assert f"Research OS v{RESEARCH_OS_VERSION} Architecture & Correctness Stable Gate" in p.stdout
    assert f"READY: v{RESEARCH_OS_VERSION} stable" in p.stdout
