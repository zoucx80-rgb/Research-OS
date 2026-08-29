import pytest
from research_os.kpi.manufacturing import ManufacturingPack

def test_manufacturing_pack_preserves_core_formula_semantics():
    facts={"revenue":100.0,"net_profit_parent":10.0,"assets_begin":80.0,"assets_end":120.0,
           "equity_begin":40.0,"equity_end":60.0,"ocf":9.0,"ar_begin":15.0,"ar_end":25.0,
           "inventory_begin":20.0,"inventory_end":30.0,"cogs":75.0,"capex_cash":5.0,
           "ppe_begin":20.0,"ppe_end":30.0}
    values={m.metric_id:m.value for m in ManufacturingPack().calculate(facts)}
    assert values["roe"]==pytest.approx(.20)
    assert values["cash_conversion_parent"]==pytest.approx(.9)
    assert values["ar_days"]==pytest.approx(73.0)
    assert values["inventory_days"]==pytest.approx((25/75)*365)
    assert values["simple_fcf"]==pytest.approx(4.0)
    assert values["fixed_asset_turnover"]==pytest.approx(4.0)
