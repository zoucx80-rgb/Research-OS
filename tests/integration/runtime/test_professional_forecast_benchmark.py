from __future__ import annotations

from datetime import datetime, timedelta, timezone

from research_os.application.command import ForecastResearchInput, ResearchRunCommand
from research_os.application.professional_modules import ForecastResearchModule
from research_os.contracts.artifact_values import ForecastHypothesis
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.forecasting import ForecastExperimentInput, ForecastObservation
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ModulePlanCompiler,
    ResearchContext,
    ResearchEngine,
)
from research_os.runtime.core_artifacts import (
    FORECAST_BENCHMARK_EVIDENCE,
    FORECAST_EVALUATION,
    build_core_artifact_catalog,
)


DECISION_TS = datetime(2026, 9, 4, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:forecast-benchmark"


def _reference(index: int) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=f"ev:forecast:{index}",
        revision=1,
        content_fingerprint=f"{index:064x}",
    )


def _observation(index: int) -> ForecastObservation:
    observed_ts = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=index * 20)
    return ForecastObservation(
        observation_id=f"obs:{index}",
        observed_ts=observed_ts,
        feature_available_ts={"orders": observed_ts},
        label_mature_ts=observed_ts,
        features={"orders": float(index)},
        realized_outcome=float(index * 3 + (index % 2)),
        evidence_refs=(_reference(index),),
    )


def _command() -> ResearchRunCommand:
    context = ResearchContext(
        run_id="run:forecast-benchmark",
        company=CompanyRef(company_id=COMPANY_ID),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.02",
            core_api_version="2.0",
        ),
        evidence=EvidenceView((), company_id=COMPANY_ID, decision_ts=DECISION_TS),
        facts=FactView(
            company_id=COMPANY_ID,
            decision_ts=DECISION_TS,
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
    )
    return ResearchRunCommand(
        context=context,
        forecasting=ForecastResearchInput(
            hypotheses=(
                ForecastHypothesis(
                    hypothesis_key="hyp:revenue",
                    statement="Orders explain next-period revenue.",
                    target_metric="revenue",
                    horizon="FY+1",
                    evidence_refs=(_reference(1),),
                ),
            ),
            experiment=ForecastExperimentInput(
                hypothesis_key="hyp:revenue",
                model_key="ols:revenue",
                target_metric="revenue",
                horizon="FY+1",
                feature_names=("orders",),
                observations=tuple(_observation(index) for index in range(1, 13)),
                benchmark_id="naive:last_value",
                evaluation_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
                n_splits=3,
                current_model_stage="experimental",
                applicability="annual comparable periods",
                model_boundary="linear explanatory forecast",
            ),
        ),
    )


def test_professional_module_executes_registered_oos_benchmark() -> None:
    command = _command()
    catalog = build_core_artifact_catalog()
    plan = ModulePlanCompiler(catalog).compile((ForecastResearchModule(command),))

    execution = ResearchEngine().execute(plan, command.context, catalog)

    evidence = execution.snapshot.require(FORECAST_BENCHMARK_EVIDENCE)
    evaluation = execution.snapshot.require(FORECAST_EVALUATION)
    assert evidence.domain_status == "SUPPORTED"
    assert evidence.out_of_sample is True
    assert evidence.pit_compliant is True
    assert {item.metric_name for item in evidence.metrics} == {
        "MAE",
        "RMSE",
        "DIRECTION_ACCURACY",
        "INTERVAL_COVERAGE",
    }
    assert evidence.benchmark_key == "naive:last_value"
    assert evidence.benchmark_version == "1.0.0"
    assert evidence.sample_count == 12
    assert evidence.fold_count == 3
    assert evaluation.evaluation_status == "PASS"
    assert len(evaluation.folds) == 3
    assert all(item.feature_available_ts <= item.evaluation_ts for item in evaluation.folds)
    assert all(item.label_mature_ts <= item.evaluation_ts for item in evaluation.folds)
    assert execution.module_results[0].status == "PASS"
