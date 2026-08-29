from __future__ import annotations
import subprocess, sys
from pathlib import Path
from collections.abc import Callable, Iterable


CHECKS: dict[str,str]={
    "v1_golden":"tests/golden/test_v1_0_manufacturing_reproducibility.py",
    "pit":"tests/golden/test_no_time_travel.py",
    "manufacturing":"tests/golden/kpi/test_manufacturing_pack.py",
    "distributor":"tests/integration/test_distributor_complete_run.py",
    "router_explainable":"tests/unit/router/test_classifier.py::test_router_classifies_high_inventory_low_fixed_asset_company_as_distributor",
    "thesis_falsifiers":"tests/unit/thesis/test_state_machine.py::test_active_thesis_requires_explicit_anti_thesis",
    "ledger":"tests/unit/ledger/test_ledger.py::test_material_research_conclusion_requires_expiry_and_next_verification",
    "valuation_fitness":"tests/unit/valuation/test_router.py::test_low_fitness_model_cannot_dominate_primary_models",
    "decision_no_trade":"tests/unit/decision/test_models.py::test_decision_state_is_research_only",
    "snapshot_reproducible":"tests/unit/snapshots/test_snapshot_service.py::test_snapshot_freezes_payload_with_verifiable_hash",
    "repository_preflight":"tests/unit/preflight/test_validator.py",
    "evidence_lineage":"tests/unit/domain/test_lineage_contracts.py",
    "financial_sanity":"tests/unit/validation/test_financial_sanity.py",
    "expectation_evidence":"tests/unit/expectations/test_evidence_gate.py",
    "valuation_execution":"tests/unit/valuation/test_execution.py",
    "decision_validation":"tests/unit/decision/test_validation.py",
    "completion_gate":"tests/unit/completion/test_gate.py",
    "temporal_consistency":"tests/unit/events/test_temporal_validation.py",
    "distributor_kpi_safety":"tests/unit/kpi/test_distributor_safety_metrics.py",
    "research_completion_integration":"tests/integration/test_research_safety_context.py",
    "migration_lineage":"tests/integration/storage/test_v1_2_lineage_migration.py",
}

ROOT=Path(__file__).resolve().parents[3]


def _pytest_runner(nodeid:str)->bool:
    result=subprocess.run([sys.executable,"-m","pytest","-q",nodeid],cwd=ROOT,capture_output=True,text=True)
    return result.returncode==0


def _pytest_batch_runner(nodeids:Iterable[str])->bool:
    result=subprocess.run([sys.executable,"-m","pytest","-q",*nodeids],cwd=ROOT,capture_output=True,text=True)
    return result.returncode==0


def run_release_checks(runner:Callable[[str],bool]|None=None,batch_runner:Callable[[Iterable[str]],bool]|None=None)->dict[str,bool]:
    if runner is not None:
        return {name:bool(runner(nodeid)) for name,nodeid in CHECKS.items()}
    batch=batch_runner or _pytest_batch_runner
    passed=bool(batch(CHECKS.values()))
    return {name:passed for name in CHECKS}
