import subprocess, sys

def test_release_gate_script_runs_from_clean_repo_checkout():
    p=subprocess.run([sys.executable,"scripts/release_gate_v1_1.py"],capture_output=True,text=True)
    assert p.returncode==0, p.stderr
    assert "READY: v1.1.0 stable" in p.stdout
