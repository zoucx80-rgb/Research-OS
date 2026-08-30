from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[3]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_research_runtime_and_reporting_do_not_depend_on_pdf_presentation_backend():
    guarded_roots = (
        ROOT / "src/research_os/runtime",
        ROOT / "src/research_os/reporting",
        ROOT / "src/research_os/plugins",
        ROOT / "src/research_os/valuation",
        ROOT / "src/research_os/decision",
        ROOT / "src/research_os/completion",
    )
    forbidden: list[tuple[Path, str]] = []

    for guarded_root in guarded_roots:
        for path in guarded_root.rglob("*.py"):
            for imported in _imports(path):
                if imported == "playwright" or imported.startswith("playwright."):
                    forbidden.append((path, imported))
                if imported.startswith("research_os.presentation"):
                    forbidden.append((path, imported))

    assert forbidden == []


def test_playwright_import_is_delayed_inside_the_pdf_adapter_method():
    path = ROOT / "src/research_os/presentation/pdf_adapter.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    top_level_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and any(
            name.startswith("playwright")
            for name in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
        )
    ]

    assert top_level_imports == []
