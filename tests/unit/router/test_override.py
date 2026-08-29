from research_os.router.registry import RouterOverrideRegistry

def test_manual_override_preserves_history():
    r=RouterOverrideRegistry()
    r.set_override("X","manufacturer",reason="segment changed",effective_at="2026-08-29")
    h=r.history("X")
    assert h[-1].reason=="segment changed"
    assert h[-1].manual_override is True
