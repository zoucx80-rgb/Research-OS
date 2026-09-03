from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path("src/research_os")
DOMAIN_ROOTS = (
    "contracts",
    "domain",
    "runtime",
    "plugins",
    "metrics",
    "policies",
    "router",
    "thesis",
    "decision",
    "valuation",
    "forecasting",
    "peers",
    "monitoring",
)
FORBIDDEN_DOMAIN_PREFIXES = (
    "research_os.api",
    "research_os.adapters.persistence",
    "research_os.reporting",
    "research_os.presentation",
    "research_os.release",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_domain_and_runtime_semantics_do_not_depend_on_outer_adapters() -> None:
    offenders: list[tuple[str, str]] = []
    for root in DOMAIN_ROOTS:
        package = ROOT / root
        if not package.exists():
            continue
        for path in package.rglob("*.py"):
            for imported in _imports(path):
                if imported.startswith(FORBIDDEN_DOMAIN_PREFIXES):
                    offenders.append((str(path), imported))
    assert offenders == []


def test_reporting_does_not_import_runtime_engine_or_professional_modules() -> None:
    offenders: list[tuple[str, str]] = []
    for path in (ROOT / "reporting").rglob("*.py"):
        for imported in _imports(path):
            if imported.startswith("research_os.runtime.engine") or imported.startswith(
                "research_os.runtime.professional_modules"
            ):
                offenders.append((str(path), imported))
    assert offenders == []


def test_import_linter_configuration_declares_the_same_boundaries() -> None:
    config = Path(".importlinter").read_text(encoding="utf-8")
    assert "root_package = research_os" in config
    assert "type = forbidden" in config
    for prefix in (
        "research_os.api",
        "research_os.adapters.persistence",
        "research_os.reporting",
        "research_os.presentation",
        "research_os.release",
    ):
        assert prefix in config
