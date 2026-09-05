from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCANNED_ROOTS = (
    ROOT / "src" / "research_os" / "application",
    ROOT / "src" / "research_os" / "plugins",
    ROOT / "src" / "research_os" / "runtime",
)
ENGINE = ROOT / "src" / "research_os" / "runtime" / "engine.py"


def test_only_research_engine_invokes_module_run() -> None:
    violations: list[str] = []
    for root in SCANNED_ROOTS:
        for path in root.rglob("*.py"):
            if path == ENGINE:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "run"
                    and not (
                        isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "_backtester"
                    )
                ):
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}")

    assert violations == []


def test_retired_parallel_runtime_surfaces_are_absent() -> None:
    runtime = ROOT / "src" / "research_os" / "runtime"
    retired = {
        "builtin_modules.py",
        "factory.py",
        "inputs.py",
        "professional_modules.py",
        "provenance.py",
        "research_completeness.py",
        "result.py",
        "semantic_claims.py",
        "semantic_preservation.py",
        "source_pins.py",
    }

    assert {path.name for path in runtime.iterdir()} & retired == set()
