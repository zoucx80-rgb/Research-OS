from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from research_os.application.command import (
    ExpectationResearchInput,
    ExternalVersionInputs,
    FinancialResearchInput,
    ForecastResearchInput,
    MonitoringResearchInput,
    PeerResearchInput,
    ResearchReadinessInput,
    ResearchRunCommand,
    ResearchRunOptions,
    ThesisResearchInput,
    ValuationResearchInput,
)
from research_os.contracts.artifact_values import AssumptionRef, FinancialObservation
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)


def _evidence_ref() -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev:revenue",
        revision=1,
        content_fingerprint="a" * 64,
    )


def _context() -> ResearchContext:
    decision_ts = datetime(2026, 9, 2, tzinfo=timezone.utc)
    company_id = "synthetic:command"
    return ResearchContext(
        run_id="run:command",
        company=CompanyRef(company_id=company_id),
        decision_ts=decision_ts,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.0",
            core_api_version="2.0",
        ),
        evidence=EvidenceView([], company_id=company_id, decision_ts=decision_ts),
        facts=FactView(
            company_id=company_id,
            decision_ts=decision_ts,
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
    )


def test_command_has_frozen_independent_domain_defaults():
    first = ResearchRunCommand(context=_context())
    second = ResearchRunCommand(context=_context())

    assert first.financial == FinancialResearchInput()
    assert first.thesis == ThesisResearchInput()
    assert first.expectations == ExpectationResearchInput()
    assert first.valuation == ValuationResearchInput()
    assert first.monitoring == MonitoringResearchInput()
    assert first.forecasting == ForecastResearchInput()
    assert first.peers == PeerResearchInput()
    assert first.readiness == ResearchReadinessInput()
    assert first.options == ResearchRunOptions()
    assert first.financial is not second.financial

    with pytest.raises(ValidationError, match="frozen"):
        first.options.persist_snapshot = False  # type: ignore[misc]


def test_command_copies_mutable_domain_inputs_at_its_boundary():
    payload = {
        "observations": [
            {
                "metric_id": "revenue",
                "period": "FY2025",
                "value": 100.0,
                "unit": "CNY",
                "evidence_refs": [_evidence_ref()],
            }
        ]
    }
    financial = FinancialResearchInput.model_validate(payload)
    command = ResearchRunCommand(context=_context(), financial=financial)

    payload["observations"][0]["value"] = 999.0

    frozen = command.financial.observations[0]
    assert frozen.value == 100.0
    assert frozen.evidence_refs == (_evidence_ref(),)


def test_command_nested_fields_are_observably_immutable():
    command = ResearchRunCommand(
        context=_context(),
        financial=FinancialResearchInput(
            observations=(
                FinancialObservation(
                    metric_id="revenue",
                    period="FY2025",
                    value=100.0,
                    unit="CNY",
                    evidence_refs=(_evidence_ref(),),
                ),
            )
        ),
    )

    with pytest.raises(ValidationError, match="frozen"):
        command.financial.observations[0].value = 999.0

    unchanged = command.financial.observations[0]
    assert unchanged.value == 100.0
    assert unchanged.evidence_refs == (_evidence_ref(),)


@pytest.mark.parametrize(
    "model, payload",
    [
        (ResearchRunCommand, {"context": _context(), "unexpected": True}),
        (FinancialResearchInput, {"fundamental_state": "IMPROVING"}),
        (ValuationResearchInput, {"valuation_state": "FAIR"}),
        (ExpectationResearchInput, {"expectation_state": "MIXED"}),
        (
            ResearchReadinessInput,
            {"not_applicable_dimensions": ["time_series"]},
        ),
    ],
)
def test_command_models_reject_unknown_and_removed_fallback_fields(model, payload):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate(payload)


@pytest.mark.parametrize(
    "owned_version",
    [
        "research_os_version",
        "core_api_version",
        "plugin_api_version",
        "snapshot_schema_version",
        "http_api_version",
        "formula_version",
        "router_version",
    ],
)
def test_external_versions_reject_research_os_owned_component_overrides(owned_version):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExternalVersionInputs.model_validate({owned_version: "caller-controlled"})


def test_domain_inputs_own_only_their_declared_fields():
    assert "sensitivities" in ResearchReadinessInput.model_fields
    assert "not_applicable_dimensions" not in ResearchReadinessInput.model_fields
    assert "sensitivities" not in ValuationResearchInput.model_fields
    assert "peer_comparables" in PeerResearchInput.model_fields
    assert "peer_comparables" not in FinancialResearchInput.model_fields
    assert "monitoring_rules" in MonitoringResearchInput.model_fields
    assert "consensus_observations" in ExpectationResearchInput.model_fields


def test_command_module_has_no_legacy_input_dependency_or_migration_surface():
    import research_os.application.command as command_module

    source = inspect.getsource(command_module)
    assert "ResearchInputs" not in source
    assert "migrate_" not in source
    assert "compat" not in source


def _model_field_paths(
    model: type[BaseModel], seen: set[type[BaseModel]] | None = None
) -> set[str]:
    seen = set() if seen is None else seen
    if model in seen:
        return set()
    seen.add(model)
    paths = set()
    for field_name, field in model.model_fields.items():
        paths.add(field_name)
        candidates = (field.annotation, *get_args(field.annotation))
        for candidate in candidates:
            origin = get_origin(candidate)
            nested_candidates = get_args(candidate) if origin is not None else (candidate,)
            for nested in nested_candidates:
                if isinstance(nested, type) and issubclass(nested, BaseModel):
                    if nested in {EvidenceRef, AssumptionRef}:
                        continue
                    paths.update(
                        f"{field_name}.{path}" for path in _model_field_paths(nested, seen.copy())
                    )
    return paths


def test_v2_command_field_graph_has_no_id_only_lineage():
    field_paths = _model_field_paths(ResearchRunCommand)

    assert not any(
        path.rsplit(".", 1)[-1]
        in {"evidence_id", "evidence_ids", "assumption_id", "assumption_ids"}
        for path in field_paths
    )
