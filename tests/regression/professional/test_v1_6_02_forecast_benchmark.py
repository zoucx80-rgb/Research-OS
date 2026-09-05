from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

import pytest

from research_os.application.command import ForecastResearchInput, ResearchRunCommand
from research_os.application.professional_modules import ForecastResearchModule
from research_os.contracts.artifact_values import ForecastHypothesis
from research_os.contracts.evidence import EvidenceRef, evidence_content_fingerprint
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
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
COMPANY_ID = "synthetic:forecast-regression"
REAL_COMPANY_IDS = ("300034.SZ",)
FIELD_FIXTURES = Path("tests/fixtures/field_acceptance/v1_6_02")


def _reference(index: int) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=f"ev:forecast-regression:{index}",
        revision=1,
        content_fingerprint=f"{index:064x}",
    )


def _context() -> ResearchContext:
    return ResearchContext(
        run_id="run:forecast-regression",
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


def _execute(command: ResearchRunCommand):
    catalog = build_core_artifact_catalog()
    plan = ModulePlanCompiler(catalog).compile((ForecastResearchModule(command),))
    return ResearchEngine().execute(plan, command.context, catalog)


def test_missing_experiment_publishes_typed_reason_on_both_artifacts() -> None:
    command = ResearchRunCommand(context=_context())

    result = _execute(command)

    evaluation = result.snapshot.require(FORECAST_EVALUATION)
    evidence = result.snapshot.require(FORECAST_BENCHMARK_EVIDENCE)
    assert evaluation.domain_status == "INSUFFICIENT_EVIDENCE"
    assert evidence.domain_status == "INSUFFICIENT_EVIDENCE"
    assert evaluation.reason_codes == ("EXPERIMENT_NOT_PROVIDED",)
    assert evidence.reason_codes == ("EXPERIMENT_NOT_PROVIDED",)


def test_invalid_experiment_does_not_call_backtester(monkeypatch: pytest.MonkeyPatch) -> None:
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    observations = tuple(
        ForecastObservation(
            observation_id=f"obs:{index}",
            observed_ts=timestamp,
            feature_available_ts={"orders": timestamp},
            label_mature_ts=timestamp,
            features={"orders": float(index)},
            realized_outcome=float(index),
            evidence_refs=(_reference(index),),
        )
        for index in range(1, 4)
    )
    command = ResearchRunCommand(
        context=_context(),
        forecasting=ForecastResearchInput(
            hypotheses=(
                ForecastHypothesis(
                    hypothesis_key="hyp:registered",
                    statement="A preregistered hypothesis.",
                    target_metric="revenue",
                    horizon="FY+1",
                    evidence_refs=(_reference(1),),
                ),
            ),
            experiment=ForecastExperimentInput(
                hypothesis_key="hyp:unregistered",
                model_key="ols:revenue",
                target_metric="revenue",
                horizon="FY+1",
                feature_names=("orders",),
                observations=observations,
                benchmark_id="missing:benchmark",
                evaluation_ts=DECISION_TS,
                n_splits=3,
                applicability="annual periods",
                model_boundary="linear explanatory forecast",
            ),
        ),
    )
    module = ForecastResearchModule(command)

    def fail_if_called(**_: object) -> None:
        raise AssertionError("backtester must not run for an insufficient experiment")

    monkeypatch.setattr(module._backtester, "run", fail_if_called)
    catalog = build_core_artifact_catalog()
    plan = ModulePlanCompiler(catalog).compile((module,))

    result = ResearchEngine().execute(plan, command.context, catalog)

    expected = (
        "HYPOTHESIS_NOT_PREREGISTERED",
        "INSUFFICIENT_OBSERVATIONS",
        "UNREGISTERED_BENCHMARK",
    )
    assert result.snapshot.require(FORECAST_EVALUATION).reason_codes == expected
    assert result.snapshot.require(FORECAST_BENCHMARK_EVIDENCE).reason_codes == expected


def _real_company_command(company_id: str) -> ResearchRunCommand:
    case = json.loads((FIELD_FIXTURES / f"{company_id}.json").read_text(encoding="utf-8"))
    decision_ts = datetime.fromisoformat(case["decision_ts"].replace("Z", "+00:00"))
    evidence = tuple(
        Evidence(
            evidence_id=item["evidence_id"],
            company_id=company_id,
            evidence_type="filing_fact",
            period_end=date.fromisoformat(item["period_end"]),
            period=item["reporting_period"],
            publish_ts=datetime.fromisoformat(item["publish_ts"].replace("Z", "+00:00")),
            ingested_at=datetime.fromisoformat(item["publish_ts"].replace("Z", "+00:00")),
            value={
                "prior_revenue": item["prior_revenue"],
                "realized_revenue": item["realized_revenue"],
            },
            unit="CNY",
            scope="consolidated",
            version=item["reporting_period"],
            source_document_id=item["source_document_id"],
            source_table="primary_financial_metrics",
            source_url=item["source_url"],
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
            dataset_version="field-acceptance-v1.6.02@1",
            parser_version="manual-primary-source@1",
            revision_no=1,
        )
        for item in case["observations"]
    )
    for item, source in zip(case["observations"], evidence, strict=True):
        assert source.publish_ts <= decision_ts
        assert evidence_content_fingerprint(source) == item["content_fingerprint"]
    evidence_view = EvidenceView(evidence, company_id=company_id, decision_ts=decision_ts)
    references = {item.evidence_id: item for item in evidence_view.refs()}
    hypothesis = case["hypothesis"]
    experiment = case["experiment"]
    observations = tuple(
        ForecastObservation(
            observation_id=item["observation_id"],
            observed_ts=datetime.fromisoformat(item["publish_ts"].replace("Z", "+00:00")),
            feature_available_ts={
                "prior_revenue": datetime.fromisoformat(
                    item["publish_ts"].replace("Z", "+00:00")
                )
            },
            label_mature_ts=datetime.fromisoformat(
                item["publish_ts"].replace("Z", "+00:00")
            ),
            features={"prior_revenue": item["prior_revenue"]},
            realized_outcome=item["realized_revenue"],
            evidence_refs=(references[item["evidence_id"]],),
        )
        for item in case["observations"]
    )
    context = ResearchContext(
        run_id=f"run:forecast-field:{company_id}",
        company=CompanyRef(company_id=company_id),
        decision_ts=decision_ts,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.02",
            core_api_version="2.0",
        ),
        evidence=evidence_view,
        facts=FactView(
            company_id=company_id,
            decision_ts=decision_ts,
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
                    hypothesis_key=hypothesis["hypothesis_key"],
                    statement=hypothesis["statement"],
                    target_metric=hypothesis["target_metric"],
                    horizon=hypothesis["horizon"],
                    evidence_refs=evidence_view.refs(),
                ),
            ),
            experiment=ForecastExperimentInput(
                hypothesis_key=hypothesis["hypothesis_key"],
                model_key=experiment["model_key"],
                target_metric=hypothesis["target_metric"],
                horizon=hypothesis["horizon"],
                feature_names=tuple(experiment["feature_names"]),
                observations=observations,
                benchmark_id=experiment["benchmark_id"],
                evaluation_ts=decision_ts,
                n_splits=experiment["n_splits"],
                current_model_stage=experiment["current_model_stage"],
                applicability=experiment["applicability"],
                model_boundary=experiment["model_boundary"],
                caveats=tuple(experiment["caveats"]),
            ),
        ),
    )


def _run_v1_6_02_case(company_id: str):
    return _execute(_real_company_command(company_id))


def test_at_least_one_real_company_executes_oos_benchmark() -> None:
    results = [_run_v1_6_02_case(company_id) for company_id in REAL_COMPANY_IDS]
    evidence = [
        item.snapshot.require(FORECAST_BENCHMARK_EVIDENCE) for item in results
    ]

    assert any(item.domain_status == "SUPPORTED" and item.out_of_sample for item in evidence)
    assert all(item.reason_codes or item.metrics for item in evidence)
