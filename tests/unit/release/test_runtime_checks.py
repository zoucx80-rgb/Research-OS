from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.runtime import CHECKS, run_release_checks
from research_os.release.verification import resolve_release_checks


def test_runtime_release_checks_match_current_manifest():
    assert CHECKS == resolve_release_checks(CURRENT_RELEASE)


def test_runtime_release_checks_preserve_per_check_failure():
    failed_key = next(iter(CHECKS))
    failed_nodeid = CHECKS[failed_key]
    seen: list[str] = []

    def fake_runner(nodeid: str) -> bool:
        seen.append(nodeid)
        return nodeid != failed_nodeid

    status = run_release_checks(fake_runner)
    assert status[failed_key] is False
    assert all(status[key] is True for key in CHECKS if key != failed_key)
    assert len(seen) == len(CHECKS)


def test_default_path_can_use_single_batch_runner_for_current_checks():
    calls: list[list[str]] = []

    def batch(nodes):
        calls.append(list(nodes))
        return True

    status = run_release_checks(batch_runner=batch)
    assert all(status.values())
    assert calls == [list(CHECKS.values())]
