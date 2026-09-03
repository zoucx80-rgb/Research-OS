from research_os.release.gate import REQUIRED, evaluate_release_gate
from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.verification import resolve_release_checks


def test_release_gate_tracks_current_manifest_checks_exactly():
    assert REQUIRED == tuple(resolve_release_checks(CURRENT_RELEASE))


def test_release_gate_fails_closed_for_any_declared_condition():
    assert REQUIRED
    failed_key = REQUIRED[0]
    status = {key: True for key in REQUIRED}
    status[failed_key] = False
    result = evaluate_release_gate(status)
    assert result.ready is False
    assert result.failed == [failed_key]


def test_release_gate_accepts_every_declared_condition():
    result = evaluate_release_gate({key: True for key in REQUIRED})
    assert result.ready is True
    assert result.failed == []
