from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess

import pytest
from pydantic import ValidationError

from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.application.bootstrap import (
    RepositoryAttestation,
    RepositoryPreflightError,
)
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    KPI_METRICS,
    STRATEGY_RESOLUTION,
)
from research_os.period.models import ReportingPeriod


DECISION_TS = datetime(2026, 9, 2, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:application"


def _command(values: dict[str, object] | None = None) -> ResearchRunCommand:
    values = dict(values or {})
    period_type = str(values.pop("period_type", "FY"))
    evidence = tuple(
        Evidence(
            evidence_id=f"ev:{fact_id}",
            revision_no=1,
            company_id=COMPANY_ID,
            evidence_type="filing_fact",
            publish_ts=DECISION_TS,
            ingested_at=DECISION_TS,
            value=value,
            source_table=fact_id,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for fact_id, value in values.items()
    )
    evidence_view = EvidenceView(
        evidence,
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
    )
    refs = {
        reference.evidence_id.removeprefix("ev:"): reference
        for reference in evidence_view.refs()
    }
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="run:application",
            company=CompanyRef(company_id=COMPANY_ID),
            decision_ts=DECISION_TS,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=subprocess.check_output(
                    ("git", "rev-parse", "HEAD"), text=True
                ).strip(),
                research_os_version="1.6.0",
                core_api_version="2.0",
            ),
            evidence=evidence_view,
            facts=FactView(
                company_id=COMPANY_ID,
                decision_ts=DECISION_TS,
                values=values,
                evidence_refs_by_fact={key: (reference,) for key, reference in refs.items()},
                reporting_period=ReportingPeriod(period_type=period_type),
                accounting_scope=AccountingScope(),
            ),
        )
    )


class _RepositoryAttestor:
    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=subprocess.check_output(
                ("git", "rev-parse", "HEAD"), text=True
            ).strip(),
        )


def _application() -> ResearchApplication:
    return ResearchApplication.build(repository_attestor=_RepositoryAttestor())


def test_application_returns_auditable_incomplete_result_without_evidence_or_plugin():
    result = _application().run(_command())

    assert result.run_id == "run:application"
    assert result.execution_completion.final_status == "INCOMPLETE"
    assert result.research_readiness.final_status == "NOT_READY"
    assert result.snapshot is None
    assert result.artifacts.require(STRATEGY_RESOLUTION).coverage_gaps
    assert result.artifacts.require(KPI_METRICS).metrics == ()
    assert "core:kpi-provider" in result.execution_completion.blocking_capabilities


def test_application_build_keeps_plugin_registries_run_scoped():
    application = _application()

    first = application.run(_command({"business_description": "precision manufacturing"}))
    second = application.run(_command({"business_description": "precision manufacturing"}))

    assert first.strategy_resolution == second.strategy_resolution


def test_application_discovers_installed_entry_point_plugins(monkeypatch):
    calls = []

    def discover(registry):
        calls.append(registry)
        return ()

    monkeypatch.setattr("research_os.application.service.discover_plugins", discover)

    _application().run(_command())

    assert len(calls) == 1


def test_repository_preflight_failure_aborts_without_a_research_result():
    command = _command().model_copy(
        update={
            "context": _command().context.model_copy(
                update={
                    "baseline": _command().context.baseline.model_copy(
                        update={"repository_id": 1}
                    )
                }
            )
        }
    )

    with pytest.raises(RepositoryPreflightError, match="repository id"):
        _application().run(command)


def test_repository_preflight_rejects_a_well_formed_but_non_current_sha():
    command = _command().model_copy(
        update={
            "context": _command().context.model_copy(
                update={
                    "baseline": _command().context.baseline.model_copy(
                        update={"commit_sha": "0" * 40}
                    )
                }
            )
        }
    )

    with pytest.raises(RepositoryPreflightError, match="repository HEAD"):
        _application().run(command)


def test_application_executes_selected_builtin_kpi_provider_through_engine():
    result = _application().run(
        _command(
            {
                "business_description": "precision manufacturing",
                "revenue": 1_000.0,
                "net_profit_parent": 50.0,
                "assets_begin": 800.0,
                "assets_end": 900.0,
                "equity_begin": 400.0,
                "equity_end": 450.0,
                "period_type": "FY",
            }
        )
    )

    metrics = result.artifacts.require(KPI_METRICS).metrics
    assert [item.plugin_id for item in result.strategy_resolution.industry_plugins] == [
        "industry:manufacturing"
    ]
    assert metrics
    assert all(item.evidence_refs for item in metrics if item.status == "valid")
    assert result.execution_completion.final_status == "COMPLETE"
    assert result.research_readiness.final_status == "NOT_READY"
    assert {item.component_id for item in result.versions.metrics} == {
        item.metric_id for item in metrics
    }
    assert all(item.version for item in result.versions.metrics)
    assert [item.component_id for item in result.component_fingerprints] == sorted(
        item.component_id for item in result.component_fingerprints
    )
    business_model = result.artifacts.require(BUSINESS_MODEL_PROFILE)
    assert tuple(
        reference.evidence_id for reference in business_model.evidence_refs
    ) == ("ev:business_description",)
    business_model_envelope = result.artifacts.envelope(BUSINESS_MODEL_PROFILE)
    strategy_envelope = result.artifacts.envelope(STRATEGY_RESOLUTION)
    assert business_model_envelope is not None
    assert strategy_envelope is not None
    assert business_model_envelope.evidence_refs == business_model.evidence_refs
    assert strategy_envelope.evidence_refs == business_model.evidence_refs
    identity_only = {
        item.component_id: hashlib.sha256(
            json.dumps(
                (
                    item.component_type,
                    item.component_id,
                    item.component_version,
                    item.api_version,
                ),
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("ascii")
        ).hexdigest()
        for item in result.component_fingerprints
    }
    assert all(
        item.fingerprint != identity_only[item.component_id]
        for item in result.component_fingerprints
    )


def test_application_result_and_artifact_snapshot_are_immutable():
    result = _application().run(_command())

    with pytest.raises(ValidationError, match="frozen"):
        result.run_id = "changed"  # type: ignore[misc]
    strategy = result.artifacts.require(STRATEGY_RESOLUTION)
    changed = strategy.model_copy(update={"rationale": ("changed",)})

    assert changed != result.artifacts.require(STRATEGY_RESOLUTION)


def test_application_result_does_not_expose_mutable_module_write_values():
    result = _application().run(_command({"unmodeled_payload": {"nested": [1]}}))
    pit_result = next(
        item
        for item in result.module_results
        if item.module_id == "core:pit-lineage"
    )
    payload = pit_result.writes[0].value.items[0].value

    payload["nested"].append(2)

    unchanged = next(
        item
        for item in result.module_results
        if item.module_id == "core:pit-lineage"
    )
    assert unchanged.writes[0].value.items[0].value == {"nested": [1]}
