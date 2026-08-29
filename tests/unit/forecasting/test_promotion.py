from research_os.forecasting.promotion import decide_promotion

def test_model_cannot_promote_if_not_better_than_naive():
    d=decide_promotion(current_stage="candidate",model_mae=12,benchmark_mae=10,pit_compliant=True,stable=True,hypothesis_registered=True)
    assert d.next_stage=="candidate" and "benchmark" in d.reason

def test_validated_model_can_promote_to_production_only_with_all_gates():
    d=decide_promotion(current_stage="validated",model_mae=8,benchmark_mae=10,pit_compliant=True,stable=True,hypothesis_registered=True)
    assert d.next_stage=="production"
