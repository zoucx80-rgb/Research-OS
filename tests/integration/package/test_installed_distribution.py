from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from scripts.verify_distribution import wheel_inventory


def _write_wheel(path: Path, names: tuple[str, ...]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, "fixture")
    return path


def test_wheel_inventory_requires_research_os_package(tmp_path: Path) -> None:
    wheel = _write_wheel(tmp_path / "research_os-1.6.0-py3-none-any.whl", ("metadata.txt",))
    with pytest.raises(ValueError, match="does not contain research_os package"):
        wheel_inventory(wheel)


def test_wheel_inventory_rejects_cache_secret_test_and_field_artifacts(tmp_path: Path) -> None:
    for offender in (
        "research_os/__pycache__/x.pyc",
        "research_os/private.key",
        "research_os/tests/test_x.py",
        "research_os/field-acceptance/report.pdf",
    ):
        wheel = _write_wheel(
            tmp_path / f"research_os-1.6.0-{len(offender)}-py3-none-any.whl",
            ("research_os/__init__.py", offender),
        )
        with pytest.raises(ValueError, match="forbidden files"):
            wheel_inventory(wheel)


def test_wheel_inventory_accepts_package_and_dist_info(tmp_path: Path) -> None:
    wheel = _write_wheel(
        tmp_path / "research_os-1.6.0-py3-none-any.whl",
        (
            "research_os/__init__.py",
            "research_os/version.py",
            "research_os-1.6.0.dist-info/METADATA",
        ),
    )
    names = wheel_inventory(wheel)
    assert names == tuple(sorted(names))
    assert "research_os/version.py" in names
