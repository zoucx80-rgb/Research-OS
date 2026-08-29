#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from research_os.release.gate import evaluate_release_gate
from research_os.release.runtime import run_release_checks

def main():
    status=run_release_checks()
    r=evaluate_release_gate(status)
    print("Research OS v1.1 Stable Gate")
    for name,value in status.items(): print(f"{name}: {'PASS' if value else 'FAIL'}")
    if r.failed:
        print("failed:",", ".join(r.failed)); raise SystemExit(1)
    print("READY: v1.1.0 stable")
if __name__=="__main__": main()
