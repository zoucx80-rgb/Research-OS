from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[3]
_FORBIDDEN_PATTERNS = (
    "scripts/release_gate_v1_*.py",
    "scripts/render_field_acceptance_v1_5_*.py",
    "src/research_os/**/*_v1_5_*.py",
)


def test_current_tree_does_not_ship_legacy_runtime_entrypoints() -> None:
    found = sorted(
        str(path.relative_to(_ROOT))
        for pattern in _FORBIDDEN_PATTERNS
        for path in _ROOT.glob(pattern)
    )

    assert found == []
