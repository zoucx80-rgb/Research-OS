#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

from research_os.release.manifest import CURRENT_RELEASE

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ARCHIVE_PARTS = (
    ".git/",
    "/__pycache__/",
    ".pyc",
    ".pyo",
    "/build/",
    "/dist/",
    ".pem",
    ".key",
)


def _git(*args: str) -> str:
    return subprocess.check_output(("git", "-C", str(ROOT), *args), text=True).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_clean_source_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if not names:
        raise ValueError("source archive is empty")
    for name in names:
        normalized = f"/{name}"
        if any(part in normalized for part in FORBIDDEN_ARCHIVE_PARTS):
            raise ValueError(f"forbidden source archive entry: {name}")


def write_sha256sums(directory: Path, output: Path) -> None:
    files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.resolve() != output.resolve()
    )
    output.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in files),
        encoding="utf-8",
    )


def _verify_single_commit_delivery(parent_sha: str, head_sha: str) -> None:
    actual_parent = _git("rev-parse", f"{head_sha}^")
    if actual_parent != parent_sha:
        raise SystemExit(
            f"delivery parent mismatch: expected {parent_sha}, got {actual_parent}"
        )
    count = _git("rev-list", "--count", f"{parent_sha}..{head_sha}")
    if count != "1":
        raise SystemExit(f"delivery commit count must be 1, got {count}")
    if _git("merge-base", parent_sha, head_sha) != parent_sha:
        raise SystemExit("delivery parent is not the direct ancestry baseline")


def _write_text_files(output_dir: Path, *, parent_sha: str, head_sha: str) -> None:
    baseline = {
        "repository": "zoucx80-rgb/Research-OS",
        "delivery_parent_sha": parent_sha,
        "head_sha": head_sha,
        "research_os_version": CURRENT_RELEASE.version,
        "core_api_version": CURRENT_RELEASE.core_api_version,
        "plugin_api_version": CURRENT_RELEASE.plugin_api_version,
        "snapshot_schema_version": CURRENT_RELEASE.snapshot_schema_version,
        "http_api_version": CURRENT_RELEASE.http_api_version,
        "release_status": CURRENT_RELEASE.status,
    }
    (output_dir / "BASELINE.json").write_text(
        json.dumps(baseline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "VERIFICATION.md").write_text(
        "# Research OS v1.6.0 Delivery Verification\n\n"
        f"- Delivery parent: `{parent_sha}`\n"
        f"- Final HEAD: `{head_sha}`\n"
        "- Commit count from delivery parent: `1`\n"
        "- Release status: `stable`\n"
        "- This bundle is generated only by the final `main` release-gate job after "
        "quality, unit, integration, acceptance, security/package, full pytest, and "
        "Manifest-selected release checks have succeeded.\n",
        encoding="utf-8",
    )
    (output_dir / "PUSH-INSTRUCTIONS.md").write_text(
        "# Push Instructions\n\n"
        "This delivery is fast-forward only. Do not force-push or rewrite M1–M4 history.\n\n"
        "Before applying, fetch `origin/main` and verify it still points to the delivery "
        f"parent `{parent_sha}`. If it has moved, stop and review the new commits.\n\n"
        "The supplied patch/bundle represents exactly one M5 commit on top of that parent.\n",
        encoding="utf-8",
    )


def build_delivery(output_dir: Path, *, parent_sha: str) -> None:
    head_sha = _git("rev-parse", "HEAD")
    _verify_single_commit_delivery(parent_sha, head_sha)

    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    source_zip = output_dir / "Research-OS-v1.6.0-source.zip"
    patch = output_dir / "Research-OS-v1.6.0.patch"
    bundle = output_dir / "Research-OS-v1.6.0.bundle"

    subprocess.run(
        (
            "git",
            "-C",
            str(ROOT),
            "archive",
            "--format=zip",
            f"--output={source_zip}",
            head_sha,
        ),
        check=True,
    )
    assert_clean_source_archive(source_zip)

    patch.write_bytes(
        subprocess.check_output(
            (
                "git",
                "-C",
                str(ROOT),
                "format-patch",
                "-1",
                head_sha,
                "--stdout",
                "--binary",
            )
        )
    )
    subprocess.run(
        (
            "git",
            "-C",
            str(ROOT),
            "bundle",
            "create",
            str(bundle),
            head_sha,
            parent_sha,
        ),
        check=True,
    )
    subprocess.run(("git", "bundle", "verify", str(bundle)), cwd=ROOT, check=True)

    _write_text_files(output_dir, parent_sha=parent_sha, head_sha=head_sha)
    sums = output_dir / "SHA256SUMS"
    write_sha256sums(output_dir, sums)

    expected = {
        line.split("  ", 1)[1]: line.split("  ", 1)[0]
        for line in sums.read_text(encoding="utf-8").splitlines()
    }
    for filename, digest in expected.items():
        if sha256_file(output_dir / filename) != digest:
            raise SystemExit(f"delivery checksum mismatch: {filename}")

    print(f"DELIVERY VERIFIED: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the one-commit Research OS M5 delivery")
    parser.add_argument("--delivery-parent-sha", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    build_delivery(args.output_dir.resolve(), parent_sha=args.delivery_parent_sha)


if __name__ == "__main__":
    main()
