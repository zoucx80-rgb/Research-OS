from research_os.release.runtime import run_release_checks

def test_runtime_release_checks_map_actual_runner_results_to_all_ten_conditions():
    seen=[]
    def fake_runner(nodeid):
        seen.append(nodeid)
        return "test_distributor_complete_run" not in nodeid
    status=run_release_checks(fake_runner)
    assert len(status)==10
    assert status["distributor"] is False
    assert status["pit"] is True
    assert len(seen)==10

def test_default_path_can_use_single_batch_runner_for_all_release_checks():
    calls=[]
    def batch(nodes):
        calls.append(list(nodes)); return True
    status=run_release_checks(batch_runner=batch)
    assert all(status.values())
    assert len(calls)==1
    assert len(calls[0])==10
