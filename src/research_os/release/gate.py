from pydantic import BaseModel


REQUIRED=(
    "v1_golden",
    "pit",
    "manufacturing",
    "distributor",
    "router_explainable",
    "thesis_falsifiers",
    "ledger",
    "valuation_fitness",
    "decision_no_trade",
    "snapshot_reproducible",
    "repository_preflight",
    "evidence_lineage",
    "financial_sanity",
    "expectation_evidence",
    "valuation_execution",
    "decision_validation",
    "completion_gate",
    "temporal_consistency",
    "distributor_kpi_safety",
    "research_completion_integration",
    "migration_lineage",
    "period_semantics",
    "missing_value_semantics",
    "kpi_applicability",
    "completion_consistency",
    "version_consistency",
)


class ReleaseGateResult(BaseModel):
    ready: bool
    passed: list[str]
    failed: list[str]


def evaluate_release_gate(status:dict[str,bool])->ReleaseGateResult:
    passed=[k for k in REQUIRED if status.get(k) is True]
    failed=[k for k in REQUIRED if status.get(k) is not True]
    return ReleaseGateResult(ready=not failed,passed=passed,failed=failed)
