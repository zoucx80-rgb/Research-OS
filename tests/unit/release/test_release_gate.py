from research_os.release.gate import evaluate_release_gate

def test_release_gate_rejects_missing_distributor_run():
    r=evaluate_release_gate({"v1_golden":True,"pit":True,"manufacturing":True,"distributor":False,"router_explainable":True,"thesis_falsifiers":True,"ledger":True,"valuation_fitness":True,"decision_no_trade":True,"snapshot_reproducible":True})
    assert r.ready is False

def test_release_gate_accepts_all_ten_conditions():
    keys=["v1_golden","pit","manufacturing","distributor","router_explainable","thesis_falsifiers","ledger","valuation_fitness","decision_no_trade","snapshot_reproducible"]
    r=evaluate_release_gate({k:True for k in keys})
    assert r.ready is True and r.failed==[]
