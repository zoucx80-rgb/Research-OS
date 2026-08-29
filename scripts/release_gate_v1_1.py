#!/usr/bin/env python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_os import __version__
from research_os.release.gate import evaluate_release_gate
from research_os.release.runtime import run_release_checks


def main():
    status = run_release_checks()
    result = evaluate_release_gate(status)
    print(f"Research OS v{__version__} Architecture & Correctness Stable Gate")
    for name, value in status.items():
        print(f"{name}: {'PASS' if value else 'FAIL'}")
    if result.failed:
        print("failed:", ", ".join(result.failed))
        raise SystemExit(1)
    print(f"READY: v{__version__} stable")


if __name__ == "__main__":
    main()
