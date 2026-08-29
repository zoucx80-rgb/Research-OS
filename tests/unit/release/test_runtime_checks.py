from research_os.release.runtime import CHECKS, run_release_checks


def test_runtime_release_checks_include_machine_safety_regressions():
    required = {
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
    assert required.issubset(CHECKS)
    seen=[]
    def fake_runner(nodeid):
        seen.append(nodeid)
        return "test_distributor_complete_run" not in nodeid
    status=run_release_checks(fake_runner)
    assert status["distributor"] is False
    assert status["pit"] is True
    assert len(seen)==len(CHECKS)


def test_default_path_can_use_single_batch_runner_for_all_release_checks():
    calls=[]
    def batch(nodes):
        calls.append(list(nodes)); return True
    status=run_release_checks(batch_runner=batch)
    assert all(status.values())
    assert len(calls)==1
    assert len(calls[0])==len(CHECKS)
