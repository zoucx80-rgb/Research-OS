from __future__ import annotations

import ast
from pathlib import Path


INNER_RUNTIME_ROOTS = (
    "src/research_os/contracts",
    "src/research_os/domain",
    "src/research_os/runtime",
    "src/research_os/metrics",
    "src/research_os/policies",
    "src/research_os/router",
    "src/research_os/thesis",
    "src/research_os/decision",
    "src/research_os/valuation",
    "src/research_os/forecasting",
    "src/research_os/peers",
    "src/research_os/monitoring",
)
FORBIDDEN_OUTER_PREFIXES = (
    "research_os.api",
    "research_os.adapters.persistence",
    "research_os.reporting",
    "research_os.presentation",
    "research_os.release",
)
PLUGIN_ROOT = Path("src/research_os/plugins")
PLUGIN_FORBIDDEN_OUTER_PREFIXES = (
    "research_os.api",
    "research_os.adapters.persistence",
    "research_os.presentation",
    "research_os.release",
)
PLUGIN_REPORTING_PREFIX = "research_os.reporting"
PLUGIN_ALLOWED_REPORTING_PREFIX = "research_os.reporting.contributions"
REPORTING_ROOT = Path("src/research_os/reporting")
REPORTING_FORBIDDEN_PREFIXES = (
    "research_os.runtime.engine",
    "research_os.runtime.professional_modules",
)


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if path.is_file()))


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return tuple(imports)


def _matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def test_inner_runtime_packages_do_not_depend_on_outer_adapters() -> None:
    violations: list[str] = []
    for root_name in INNER_RUNTIME_ROOTS:
        root = Path(root_name)
        for path in _python_files(root):
            for imported in _imports(path):
                if any(
                    _matches_prefix(imported, forbidden) for forbidden in FORBIDDEN_OUTER_PREFIXES
                ):
                    violations.append(f"{path}: {imported}")

    assert not violations, "inner runtime dependency violations:\n" + "\n".join(violations)


def test_plugins_only_depend_on_typed_reporting_contributions() -> None:
    violations: list[str] = []
    for path in _python_files(PLUGIN_ROOT):
        for imported in _imports(path):
            if any(
                _matches_prefix(imported, forbidden)
                for forbidden in PLUGIN_FORBIDDEN_OUTER_PREFIXES
            ):
                violations.append(f"{path}: {imported}")
                continue
            if _matches_prefix(imported, PLUGIN_REPORTING_PREFIX) and not _matches_prefix(
                imported, PLUGIN_ALLOWED_REPORTING_PREFIX
            ):
                violations.append(f"{path}: {imported}")

    assert not violations, "plugin dependency violations:\n" + "\n".join(violations)


def test_reporting_does_not_depend_on_research_runtime_engine() -> None:
    violations: list[str] = []
    for path in _python_files(REPORTING_ROOT):
        for imported in _imports(path):
            if any(
                _matches_prefix(imported, forbidden) for forbidden in REPORTING_FORBIDDEN_PREFIXES
            ):
                violations.append(f"{path}: {imported}")

    assert not violations, "reporting dependency violations:\n" + "\n".join(violations)


def test_import_linter_configuration_declares_same_boundaries() -> None:
    config = Path(".importlinter").read_text(encoding="utf-8")

    for module in (
        "research_os.api",
        "research_os.adapters.persistence",
        "research_os.presentation",
        "research_os.release",
        "research_os.runtime.engine",
        "research_os.runtime.professional_modules",
    ):
        assert module in config
    assert "research_os.plugins" in config
    assert "research_os.reporting" in config
