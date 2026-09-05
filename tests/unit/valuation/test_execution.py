import importlib
import importlib.util
from datetime import date

from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.methods import ValuationMethodResult, ValuationSupportAssessment


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
        support_assessment=ValuationSupportAssessment(
            method_id="ps",
            status="CONDITIONALLY_SUPPORTED",
            reason_codes=("FUNDING_COST_DISTORTS_EARNINGS",),
            rationale="Distributor earnings are distorted by funding costs.",
        ),
        executed_model="ps",
        business_model="distributor",
        inputs={"revenue": 100.0},
        scenario_logic="revenue times sales multiple",
        evidence_refs=(
            EvidenceRef(evidence_id="ev:revenue", revision=1, content_fingerprint="a" * 64),
        ),
        driver_bridge=(
            "Revenue",
            "Gross Profit",
            "Working Capital",
            "Financing Requirement",
            "Financing Cost",
            "Credit / Inventory Loss",
            "Net Profit / Cash Economics",
            "Valuation",
        ),
        result=ValuationMethodResult(
            method_id="ps",
            status="SUPPORTED",
            currency="CNY",
            basis="equity_per_share",
            valuation_date=date(2026, 9, 4),
            base_case=10,
        ),
    )
    data.update(updates)
    return m.ValuationExecution(**data)


def test_selected_ps_executed_pe_fails():
    m = _load("research_os.valuation.execution")
    result = m.ValuationExecutionValidator().validate(_base_execution(executed_model="pe"))
    assert result.status == "VALUATION_GATE_FAIL"


def test_distributor_execution_requires_driver_bridge():
    m = _load("research_os.valuation.execution")
    result = m.ValuationExecutionValidator().validate(
        _base_execution(driver_bridge=["Revenue", "Valuation"])
    )
    assert result.status == "VALUATION_GATE_FAIL"


def test_matching_model_with_complete_driver_bridge_passes():
    m = _load("research_os.valuation.execution")
    execution = _base_execution()
    result = m.ValuationExecutionValidator().validate(execution)
    assert result.status == "PASS"
    assert execution.model_dump(mode="json")["inputs"] == {"revenue": 100.0}
