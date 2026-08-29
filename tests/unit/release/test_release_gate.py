from research_os.release.gate import REQUIRED, evaluate_release_gate


SAFETY_CHECKS = {
    "repository_preflight",
    "evidence_lineage",
    "financial_sanity",
    "expectation_evidence",
    "valuation_execution",
    "decision_validation",
    "completion_gate",
    "temporal_consistency",
    "distributor_kpi_safety",
}


def test_release_gate_requires_all_research_safety_checks():
    assert SAFETY_CHECKS.issubset(set(REQUIRED))
    status = {k: True for k in REQUIRED}
    status["financial_sanity"] = False
    r = evaluate_release_gate(status)
    assert r.ready is False
    assert "financial_sanity" in r.failed


def test_release_gate_accepts_every_declared_condition():
    r = evaluate_release_gate({k: True for k in REQUIRED})
    assert r.ready is True and r.failed == []
