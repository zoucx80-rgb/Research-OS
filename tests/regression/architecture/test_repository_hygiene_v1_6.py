from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]


def _tracked_files() -> tuple[str, ...]:
    output = subprocess.check_output(
        ("git", "-C", str(ROOT), "ls-files"), text=True
    )
    return tuple(line for line in output.splitlines() if line)


def test_tracked_tree_has_no_cache_build_or_distribution_artifacts() -> None:
    forbidden_parts = (
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "/build/",
        "/dist/",
    )
    offenders = [
        path
        for path in _tracked_files()
        if any(part in f"/{path}" for part in forbidden_parts)
        or path.endswith((".pyc", ".pyo"))
    ]
    assert offenders == []


def test_production_source_contains_no_private_key_material() -> None:
    markers = (
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "-----BEGIN EC PRIVATE KEY-----",
    )
    offenders: list[tuple[str, str]] = []
    for path in (ROOT / "src" / "research_os").rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in markers:
            if marker in content:
                offenders.append((str(path.relative_to(ROOT)), marker))
    assert offenders == []


def test_current_source_does_not_restore_v1_compatibility_package() -> None:
    forbidden_paths = (
        ROOT / "src" / "research_os" / "compat",
        ROOT / "src" / "research_os" / "runtime_v1.py",
        ROOT / "src" / "research_os" / "reporting_v1.py",
        ROOT / "src" / "research_os" / "thesis_v1.py",
        ROOT / "src" / "research_os" / "presentation_v1.py",
    )
    assert [str(path.relative_to(ROOT)) for path in forbidden_paths if path.exists()] == []
