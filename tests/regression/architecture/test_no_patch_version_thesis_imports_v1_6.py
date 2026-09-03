from __future__ import annotations

import ast
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[3]


def test_current_tests_do_not_import_patch_version_thesis_runtime() -> None:
    offenders: list[tuple[str, str]] = []
    for path in (_ROOT / "tests").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom):
                module = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name.startswith("research_os.thesis.")
                        and "_v1_5_" in alias.name
                    ):
                        offenders.append((str(path.relative_to(_ROOT)), alias.name))
            if (
                module is not None
                and module.startswith("research_os.thesis.")
                and "_v1_5_" in module
            ):
                offenders.append((str(path.relative_to(_ROOT)), module))

    assert offenders == []
