#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_os.release.manifest import CURRENT_RELEASE


TARGET = ROOT / "research_os_version.json"


def rendered_metadata() -> str:
    return (
        json.dumps(
            CURRENT_RELEASE.to_public_metadata(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = rendered_metadata()
    if args.check:
        actual = TARGET.read_text(encoding="utf-8")
        if actual != expected:
            print(
                "research_os_version.json is stale; run scripts/generate_release_metadata.py",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print("release metadata: PASS")
        return

    TARGET.write_text(expected, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
