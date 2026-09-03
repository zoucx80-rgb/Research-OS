#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_WHEEL_PARTS = (
    "/__pycache__/",
    ".pyc",
    ".pyo",
    ".pem",
    ".key",
    "field-acceptance",
    "historical-replay",
    "/tests/",
    "/build/",
)


def wheel_inventory(wheel: Path) -> tuple[str, ...]:
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise ValueError(f"not a wheel: {wheel}")
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(sorted(archive.namelist()))
    if not names:
        raise ValueError("wheel is empty")
    offenders = tuple(
        name for name in names if any(part in f"/{name}" for part in FORBIDDEN_WHEEL_PARTS)
    )
    if offenders:
        raise ValueError(f"wheel contains forbidden files: {offenders}")
    if not any(name.startswith("research_os/") for name in names):
        raise ValueError("wheel does not contain research_os package")
    return names


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def verify_installed_wheel(wheel: Path) -> None:
    wheel = wheel.resolve()
    wheel_inventory(wheel)
    with tempfile.TemporaryDirectory(prefix="research-os-wheel-") as temporary:
        venv = Path(temporary) / "venv"
        _run([sys.executable, "-m", "venv", str(venv)], cwd=ROOT)
        python = _venv_python(venv)
        _run([str(python), "-m", "pip", "install", str(wheel)], cwd=ROOT)

        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONNOUSERSITE"] = "1"
        metadata_probe = """
import json
from importlib.metadata import version
import research_os
from research_os.api.app import create_app
from research_os.version import (
    CORE_API_VERSION,
    HTTP_API_VERSION,
    PLUGIN_API_VERSION,
    RESEARCH_OS_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
)
assert version('research-os') == RESEARCH_OS_VERSION == '1.6.0'
assert research_os.__version__ == '1.6.0'
assert CORE_API_VERSION == '2.0'
assert PLUGIN_API_VERSION == '2.0'
assert SNAPSHOT_SCHEMA_VERSION == '2.0'
assert HTTP_API_VERSION == 'v1'
assert callable(create_app)
print(json.dumps({'distribution': 'PASS', 'version': RESEARCH_OS_VERSION}))
"""
        _run([str(python), "-c", metadata_probe], cwd=Path(temporary), env=environment)
        _run(
            [str(python), str(ROOT / "examples" / "core_api_v2_run.py")],
            cwd=ROOT,
            env=environment,
        )
        _run(
            [str(python), str(ROOT / "examples" / "http_api_v1.py")],
            cwd=ROOT,
            env=environment,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a built Research OS wheel")
    parser.add_argument("wheel", type=Path)
    parser.add_argument(
        "--inventory-json",
        type=Path,
        default=None,
        help="Optional path for the verified wheel inventory",
    )
    args = parser.parse_args()

    names = wheel_inventory(args.wheel)
    verify_installed_wheel(args.wheel)
    if args.inventory_json is not None:
        args.inventory_json.parent.mkdir(parents=True, exist_ok=True)
        args.inventory_json.write_text(
            json.dumps({"wheel": args.wheel.name, "files": names}, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"VERIFIED DISTRIBUTION: {args.wheel}")


if __name__ == "__main__":
    main()
