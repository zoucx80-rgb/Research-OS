import pytest
from research_os.kpi.distributor import DistributorPack

def mmap(result): return {m.metric_id:m.value for m in result}

def test_ccc_equals_dso_plus_dio_minus_dpo():
    v=mmap(DistributorPack().calculate({"avg_ar":100,"revenue":1000,"avg_inventory":200,"cogs":900,"avg_ap":150}))
    assert v["ccc_days"]==pytest.approx(v["dso_days"]+v["dio_days"]-v["dpo_days"])

def test_missing_ap_keeps_dpo_and_ccc_missing():
    v=mmap(DistributorPack().calculate({"avg_ar":100,"revenue":1000,"avg_inventory":200,"cogs":900,"avg_ap":None}))
    assert v["dpo_days"] is None and v["ccc_days"] is None

def test_distributor_pack_calculates_funding_metrics():
    v=mmap(DistributorPack().calculate({"revenue":1000,"cogs":900,"avg_ar":100,"avg_inventory":200,"avg_ap":150,
        "ar":110,"inventory":210,"ap":160,"delta_nwc":30,"delta_revenue":100,"short_debt":120,"equity":200,
        "gross_profit":100,"interest_expense":10,"ocf":20,"net_profit":25,"nopat":20,"avg_invested_capital":250}))
    assert v["nwc_intensity"]==pytest.approx(.16)
    assert v["incremental_nwc_intensity"]==pytest.approx(.30)
    assert v["interest_to_gross_profit"]==pytest.approx(.10)
    assert v["roic"]==pytest.approx(.08)
