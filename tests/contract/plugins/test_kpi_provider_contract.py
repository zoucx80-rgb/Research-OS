from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.metrics import MetricDefinition, MetricResult
from research_os.contracts.policies import PolicySnapshot
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.metrics import builtin_metric_registry
from research_os.plugins.builtins import ManufacturingIndustryPlugin
from research_os.plugins.protocols import KpiProvider, MetricDefinitionRegistry
from research_os.domain.evidence import Evidence
from research_os.runtime.context import EvidenceView, FactView


class _Definitions:
    def __init__(self, definitions: tuple[MetricDefinition, ...] = ()):
        self._definitions = {item.metric_id: item for item in definitions}

    def get(self, metric_id: str) -> MetricDefinition | None:
        return self._definitions.get(metric_id)


def _definitions_for(provider: KpiProvider) -> _Definitions:
    builtins = builtin_metric_registry()
    if all(builtins.get(metric_id) is not None for metric_id in provider.metric_ids()):
        return builtins.select(provider.metric_ids())  # type: ignore[return-value]
    return _Definitions(
        tuple(
            MetricDefinition(
                metric_id=metric_id,
                definition_version="1.0.0",
                output_kind="ratio",
                output_unit="provider-defined",
            )
            for metric_id in provider.metric_ids()
        )
    )


def _bound_facts(
    values,
    evidence_by_fact,
    *,
    reporting_period: ReportingPeriod | None = None,
    accounting_scope: AccountingScope | None = None,
) -> FactView:
    timestamp = datetime(2026, 8, 20, tzinfo=timezone.utc)
    reporting_period = reporting_period or ReportingPeriod.from_facts(values)
    accounting_scope = accounting_scope or AccountingScope.from_facts(values)
    metadata_keys = {
        "reporting_period",
        "period_type",
        "period_start",
        "period_end",
        "period_days",
        "is_cumulative",
        "accounting_scope",
        "accounting_standard",
        "consolidation",
        "segment",
        "geography",
        "continuing_operations",
    }
    fact_values = {key: value for key, value in values.items() if key not in metadata_keys}
    evidence_ids = sorted({item for ids in evidence_by_fact.values() for item in ids})
    evidence = [
        Evidence(
            evidence_id=evidence_id,
            revision_no=1,
            company_id="synthetic:company",
            evidence_type="filing_fact",
            publish_ts=timestamp,
            ingested_at=timestamp,
            value=values[next(key for key, ids in evidence_by_fact.items() if evidence_id in ids)],
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for evidence_id in evidence_ids
    ]
    bound = EvidenceView(evidence, company_id="synthetic:company", decision_ts=timestamp)
    refs_by_id = {reference.evidence_id: reference for reference in bound.refs()}
    return FactView(
        company_id="synthetic:company",
        decision_ts=timestamp,
        values=fact_values,
        evidence_refs_by_fact={
            key: tuple(refs_by_id[evidence_id] for evidence_id in evidence_ids)
            for key, evidence_ids in evidence_by_fact.items()
        },
        reporting_period=reporting_period,
        accounting_scope=accounting_scope,
    )


class _ExternalProvider:
    provider_id = "external:synthetic"
    provider_version = "1.0.0"

    def metric_ids(self) -> frozenset[str]:
        return frozenset({"synthetic.margin"})

    def calculate(
        self,
        facts,
        definitions: MetricDefinitionRegistry,
        policy: PolicySnapshot,
    ) -> tuple[MetricResult, ...]:
        return (
            MetricResult(
                metric_id="synthetic.margin",
                value=facts.get("margin"),
                unit="percent",
                status="valid",
                formula_version="synthetic@1",
                reporting_period=ReportingPeriod.from_facts(facts.as_mapping()),
                accounting_scope=AccountingScope.from_facts(facts.as_mapping()),
                evidence_refs=facts.evidence_refs("margin"),
            ),
        )


def _assert_provider_contract(provider: KpiProvider, facts: FactView) -> None:
    assert isinstance(provider, KpiProvider)
    assert provider.provider_id
    assert provider.provider_version
    assert provider.metric_ids()

    results = provider.calculate(facts, _definitions_for(provider), PolicySnapshot())

    assert isinstance(results, tuple)
    assert results
    assert all(isinstance(item, MetricResult) for item in results)
    assert {item.metric_id for item in results} <= provider.metric_ids()


def _builtin_provider() -> KpiProvider:
    provider = ManufacturingIndustryPlugin().services().kpi_provider
    assert provider is not None
    return provider


def test_external_provider_satisfies_the_public_kpi_contract():
    facts = _bound_facts(
        {"margin": 0.25, "period_type": "H1", "period_days": 181},
        {"margin": ["ev:margin"]},
    )

    _assert_provider_contract(_ExternalProvider(), facts)


def test_builtin_provider_satisfies_the_same_public_kpi_contract():
    values = {
            "revenue": 1_000.0,
            "net_profit_parent": 50.0,
            "assets_begin": 800.0,
            "assets_end": 900.0,
            "equity_begin": 400.0,
            "equity_end": 450.0,
            "period_type": "FY",
    }
    evidence_by_fact = {
        key: [f"ev:{key}"]
        for key in values
        if key not in {"period_type", "period_days"}
    }
    facts = _bound_facts(
        values,
        evidence_by_fact,
        reporting_period=ReportingPeriod(period_type="H1", period_days=181),
        accounting_scope=AccountingScope(consolidation="standalone"),
    )
    provider = _builtin_provider()

    _assert_provider_contract(provider, facts)
    assert not hasattr(provider, "_pack")
    result = provider.calculate(facts, _definitions_for(provider), PolicySnapshot())[0]
    assert result.reporting_period.period_type == "H1"
    assert result.accounting_scope.consolidation == "standalone"


def test_builtin_provider_fails_closed_for_unknown_metric_definitions():
    provider = _builtin_provider()
    facts = FactView(
        company_id="synthetic:company",
        decision_ts=datetime(2026, 8, 20, tzinfo=timezone.utc),
        values={},
        evidence_refs_by_fact={},
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )

    with pytest.raises(ValueError, match="undefined metric"):
        provider.calculate(facts, _Definitions(), PolicySnapshot())


def test_builtin_provider_projects_the_core_definition_unit_without_pack_override():
    provider = _builtin_provider()
    registry = _definitions_for(provider)
    results = provider.calculate(
        FactView(
            company_id="synthetic:company",
            decision_ts=datetime(2026, 8, 20, tzinfo=timezone.utc),
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
        registry,
        PolicySnapshot(),
    )

    assert all(item.unit == registry.get(item.metric_id).output_unit for item in results)


def test_provider_fact_view_rejects_values_without_lineage():
    with pytest.raises(ValueError, match="missing evidence references"):
        FactView(
            company_id="synthetic:company",
            decision_ts=datetime(2026, 8, 20, tzinfo=timezone.utc),
            values={"revenue": 1_000.0},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        )


def test_provider_fact_view_rejects_partial_dependency_lineage():
    values = {
        "revenue": 1_000.0,
        "net_profit_parent": 50.0,
        "assets_begin": 800.0,
        "assets_end": 900.0,
        "equity_begin": 400.0,
        "equity_end": 450.0,
        "period_type": "FY",
    }
    evidence_by_fact = {
        key: [f"ev:{key}"]
        for key in values
        if key not in {"period_type", "assets_end"}
    }
    with pytest.raises(ValueError, match="missing evidence references.*assets_end"):
        _bound_facts(values, evidence_by_fact)
