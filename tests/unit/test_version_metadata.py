import json
import tomllib
from pathlib import Path

import research_os


def test_all_public_version_metadata_is_1_2_0():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())
    assert project["project"]["version"] == "1.2.0"
    assert metadata["research_os_version"] == "1.2.0"
    assert research_os.__version__ == "1.2.0"


def test_v1_2_release_docs_exist_and_changelog_records_release():
    assert Path("docs/migrations/v1.1-to-v1.2.md").exists()
    assert Path("docs/specs/Research_OS_v1.2_安全门禁增量规范.md").exists()
    changelog = Path("CHANGELOG.md").read_text()
    assert "## 1.2.0 — 2026-08-29" in changelog
