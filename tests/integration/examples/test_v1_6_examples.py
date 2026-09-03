from __future__ import annotations

import subprocess
import sys
from pathlib import Path


EXAMPLES = (
    Path("examples/core_api_v2_run.py"),
    Path("examples/plugin_api_v2.py"),
    Path("examples/http_api_v1.py"),
)


def test_v1_6_examples_exist_with_stable_names() -> None:
    assert all(path.is_file() for path in EXAMPLES)


def test_v1_6_examples_execute_offline() -> None:
    for path in EXAMPLES:
        completed = subprocess.run(
            [sys.executable, str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, (
            f"{path} failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def test_v1_6_docs_point_to_current_examples_and_historical_replay() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    prompt = Path("docs/prompts/stock_research.md").read_text(encoding="utf-8")

    for path in EXAMPLES:
        assert path.as_posix() in readme
    assert "Core API 2.0" in readme
    assert "Plugin API 2.0" in readme
    assert "Snapshot Schema 2.0" in readme
    assert "historical replay" in readme.lower()
    assert "ResearchRunResult" in prompt
    assert "HumanReadableResearchView" in prompt
    assert "ResearchReportDocument" in prompt
    assert "historical replay" in prompt.lower()
