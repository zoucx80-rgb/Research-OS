from __future__ import annotations

import ast
from pathlib import Path


def test_version_identity_leaf_has_no_imports():
    path = Path("src/research_os/version.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))


def test_all_v1_6_version_constants_live_in_the_identity_leaf():
    source = Path("src/research_os/version.py").read_text(encoding="utf-8")

    for name in (
        "RESEARCH_OS_VERSION",
        "CORE_API_VERSION",
        "PLUGIN_API_VERSION",
        "SNAPSHOT_SCHEMA_VERSION",
        "HTTP_API_VERSION",
    ):
        assert source.count(name) == 1
