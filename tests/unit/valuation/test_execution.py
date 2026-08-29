import importlib
import importlib.util


def _load(name: str):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, f"missing required module {name}"
    return importlib.import_module(name)


def _base_execution(**updates):
    m = _load("research_os.valuation.execution")
    data = dict(
        selected_model="ps",
        model_fitness_score=0.8,
        selection_reason="distributor earnings are distorted by funding costs",
        executed_model="ps",
        business_model="distributor",
        inputs={"revenue": 100.0},
        assumptions=[{"label": "ASSUMPTION", "name": "multiple", "value": 0.5}],
        scenario_logic="revenue times sales multiple",
        lineage={"revenue": ["ev:revenue"]},
        driver_bridge=[
            "Revenue", "Gross Profit", "Working Capital", "Financing Requirement",
            "Financing Cost", "Credit / Inventory Loss", "Net Profit / Cash Economics", "Valuation",
        ],
    )
    data.update(updates)
    return m.ValuationExecution(**data)


def test_selected_ps_executed_pe_fails():
    m = _load("research_os.valuation.execution")
    result = m.ValuationExecutionValidator().validate(_base_execution(executed_model="pe"))
    assert result.status == "VALUATION_GATE_FAIL"


def test_distributor_execution_requires_driver_bridge():
    m = _load("research_os.valuation.execution")
    result = m.ValuationExecutionValidator().validate(_base_execution(driver_bridge=["Revenue", "Valuation"]))
    assert result.status == "VALUATION_GATE_FAIL"


def test_matching_model_with_complete_driver_bridge_passes():
    m = _load("research_os.valuation.execution")
    result = m.ValuationExecutionValidator().validate(_base_execution())
    assert result.status == "PASS"
