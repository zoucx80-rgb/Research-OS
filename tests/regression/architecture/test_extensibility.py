from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.kpi.base import MetricResult
from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchInputs,
    ResearchOptions,
)
from research_os.runtime.factory import ResearchRuntimeFactory
from research_os.runtime.modules import ModuleResult, ModuleSpec


class _SyntheticSoftwareKpiModule:
    spec = ModuleSpec(
        module_id="industry:synthetic-software:kpi",
        module_version="1.0.0",
        requires={"business_model.profile"},
        provides={"kpi.metrics"},
    )

    def run(self, context, state):
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            artifacts={
                "kpi.metrics": [
                    MetricResult(
                        metric_id="synthetic_retention_signal",
                        value=0.91,
                        status="valid",
                        formula_version="synthetic-software@1.0.0",
                        evidence_ids=context.facts.evidence_ids("retention_signal"),
                    )
                ]
            },
            evidence_ids=context.facts.evidence_ids("retention_signal"),
        )


class _SyntheticSoftwarePlugin:
    manifest = PluginManifest(
        plugin_id="industry:synthetic-software",
        plugin_type="industry",
        plugin_version="1.0.0",
        api_version="1.0",
        min_research_os_version="1.4.0",
        provides={"kpi.metrics"},
        requires={"business_model.profile"},
        supported_business_models={"software"},
        priority=10,
        maturity="stable",
    )

    def applicability(self, context):
        return ApplicabilityResult(
            applicable=True,
            score=1.0,
            rationale=["synthetic software contract proof"],
        )

    def modules(self):
        return [_SyntheticSoftwareKpiModule()]

    def report_contributions(self):
        return []


class _SyntheticProvider:
    def plugins(self):
        return [_SyntheticSoftwarePlugin()]


def _context():
    publish_ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    facts = {
        "business_description": "subscription software cloud platform",
        "retention_signal": 0.91,
        "period_type": "FY",
    }
    evidence = [
        Evidence(
            evidence_id=f"ev:{key}",
            company_id="synthetic:software",
            evidence_type=EvidenceType.FILING_FACT,
            publish_ts=publish_ts,
            ingested_at=publish_ts,
            value=value,
            source_table=key,
            confidence_grade=ConfidenceGrade.A,
            verification_status=VerificationStatus.PRIMARY_VERIFIED,
        )
        for key, value in facts.items()
    ]
    return ResearchContext(
        run_id="run:synthetic:software",
        company=CompanyRef(company_id="synthetic:software"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.4.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(
            values=facts,
            evidence_by_fact={key: [f"ev:{key}"] for key in facts},
        ),
        options=ResearchOptions(),
    )


def test_new_industry_plugin_resolves_and_executes_without_engine_changes():
    runtime = ResearchRuntimeFactory.with_providers(_SyntheticProvider())
    result = runtime.run_context(
        _context(),
        ResearchInputs(
            versions={
                "research_os_version": "1.4.0",
                "dataset_version": "synthetic@1",
                "parser_version": "synthetic@1",
                "formula_version": "synthetic@1",
                "router_version": "router@1.0.0",
                "kpi_pack_version": "auto",
                "driver_model_version": "driver@1",
                "forecast_version": "none",
                "valuation_version": "none",
                "report_version": "runtime@1",
                "core_api_version": "1.0",
            }
        ),
    )

    assert result.business_model.primary_model == "software"
    assert result.strategy_resolution.industry_plugins[0].plugin_id == "industry:synthetic-software"
    assert result.module_results["core:industry-kpi"].status == "PASS"
    assert any(
        metric.metric_id == "synthetic_retention_signal"
        for metric in result.artifacts["kpi.metrics"]
    )
