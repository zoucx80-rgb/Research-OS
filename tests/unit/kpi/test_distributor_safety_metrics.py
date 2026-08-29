from research_os.kpi.distributor import DistributorPack


def _metrics(facts):
    return {item.metric_id: item.value for item in DistributorPack().calculate(facts)}


def test_distributor_pack_covers_required_growth_quality_metrics():
    facts = {
        "revenue": 100.0,
        "cogs": 95.0,
        "avg_ar": 20.0,
        "avg_inventory": 10.0,
        "avg_ap": 8.0,
        "ar": 21.0,
        "inventory": 11.0,
        "ap": 9.0,
        "gross_profit": 5.0,
        "interest_expense": 1.0,
        "credit_impairment": 0.2,
        "inventory_impairment": 0.1,
        "revenue_growth": 0.20,
        "working_capital_growth": 0.35,
        "nopat": 3.0,
        "avg_invested_capital": 30.0,
        "delta_nopat": 0.6,
        "delta_invested_capital": 10.0,
    }
    metrics = _metrics(facts)
    required = {
        "inventory_turns",
        "gross_profit_to_working_capital",
        "credit_impairment_to_gross_profit",
        "inventory_impairment_to_gross_profit",
        "revenue_growth_vs_working_capital_growth",
        "incremental_roic",
    }
    assert required.issubset(metrics)
    assert abs(metrics["inventory_turns"] - 9.5) < 1e-9
    assert abs(metrics["incremental_roic"] - 0.06) < 1e-9
