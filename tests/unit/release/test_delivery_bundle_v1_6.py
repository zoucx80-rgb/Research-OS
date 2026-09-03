from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from scripts.build_release_delivery import (
    assert_clean_source_archive,
    sha256_file,
    write_sha256sums,
)


def test_source_archive_rejects_git_cache_build_and_secret_payloads(tmp_path: Path) -> None:
    for offender in (
        ".git/config",
        "src/research_os/__pycache__/x.pyc",
        "build/report.pdf",
        "private.pem",
    ):
        archive = tmp_path / f"bad-{len(offender)}.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("README.md", "ok")
            zipped.writestr(offender, "bad")
        with pytest.raises(ValueError, match="forbidden source archive entry"):
            assert_clean_source_archive(archive)


def test_source_archive_accepts_tracked_source_shape(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("README.md", "ok")
        zipped.writestr("src/research_os/version.py", 'RESEARCH_OS_VERSION = "1.6.0"')
    assert_clean_source_archive(archive)


def test_sha256sums_is_deterministic_and_excludes_itself(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("alpha\n", encoding="utf-8")
    second.write_text("beta\n", encoding="utf-8")

    sums = tmp_path / "SHA256SUMS"
    write_sha256sums(tmp_path, sums)
    lines = sums.read_text(encoding="utf-8").splitlines()

    assert lines == [
        f"{sha256_file(first)}  a.txt",
        f"{sha256_file(second)}  b.txt",
    ]
