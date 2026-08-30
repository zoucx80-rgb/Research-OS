from datetime import date, datetime, timezone

from research_os.capital.engine import FundingLoopResult
from research_os.decision.models import DecisionStateRecord
from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.expectations.models import ConsensusVintage
from research_os.expectations.validation import ExpectationEvidenceValidator
from research_os.plugins.builtins import DistributorIndustryPlugin, ManufacturingIndustryPlugin
from research_os.plugins.models import CoverageGap
from research_os.plugins.resolver import StrategyResolution
from research_os.router.models import BusinessModelProfile
from research_os.runtime.builtin_modules import BusinessModelModule, DecisionModule, DriverThesisModule
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.state import ResearchStateView
from research_os.thesis.models import Falsifier, Thesis


def _evidence(key: str, value, *, company_id: str = "synthetic:v1.5.02") -> Evidence:
    ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    return Evidence(
        evidence_id=f"ev:{key}",
        company_id=company_id,
        evidence_type=EvidenceType.FILING_FACT,
        publish_ts=ts,
        ingested_at=ts,
        value=value,
        source_table=key,
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
    )


def _context(evidence: list[Evidence], values: dict | None = None) -> ResearchContext:
    facts = values or {item.source_table: item.value for item in evidence if item.source_table}
    by_fact = {
        key: [item.evidence_id for item in evidence if item.source_table == key]
        for key in facts
    }
    return ResearchContext(
        run_id="run:v1.5.02:red",
        company=CompanyRef(company_id="synthetic:v1.5.02"),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1" * 40,
            research_os_version="1.5.1",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=facts, evidence_by_fact=by_fact),
        options=ResearchOptions(),
    )


def test_unresolved_business_model_does_not_report_router_pass():
    evidence = [_evidence("business_description", "specialized professional advisory services")]
    context = _context(evidence)

    result = BusinessModelModule().run(
        context,
        ResearchStateView({"evidence.pit": evidence}),
    )

    assert result.artifacts["business_model.profile"].classification_status == "unsupported_taxonomy"
    assert result.status == "INSUFFICIENT_EVIDENCE"


def test_missing_primary_industry_coverage_keeps_generic_drivers_but_blocks_active_thesis():
    evidence = [_evidence("business_description", "hotel hospitality lodging operations")]
    context = _context(evidence)
    profile = BusinessModelProfile(
        company_id="synthetic:v1.5.02",
        primary_model="hospitality",
        confidence=0.9,
        evidence_ids=["ev:business_description"],
        router_version="router@1.1.0",
    )
    resolution = StrategyResolution(
        coverage_gaps=[
            CoverageGap(
                gap_type="industry_strategy",
                business_model="hospitality",
                reason="no compatible industry strategy plugin for primary business model",
                reason_code="NO_COMPATIBLE_INDUSTRY_PLUGIN",
                affected_capabilities=["industry_strategy"],
                fallback_available=True,
            )
        ]
    )

    result = DriverThesisModule().run(
        context,
        ResearchStateView(
            {
                "evidence.pit": evidence,
                "business_model.profile": profile,
                "strategy.resolution": resolution,
                "kpi.pack_ids": [],
            }
        ),
    )

    graph = result.artifacts["drivers.graph"]
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert graph is not None
    assert graph.coverage_scope == "generic"
    assert graph.coverage_limited is True
    assert result.artifacts["thesis.items"] == []
    assert result.artifacts["claims.items"] == []


def test_debt_funded_negative_ocf_is_material_risk_for_decision_state():
    evidence = [_evidence("revenue", 100.0)]
    context = _context(evidence)
    thesis = Thesis(
        thesis_id="synthetic:v1.5.02:thesis",
        company_id="synthetic:v1.5.02",
        title="Cash quality",
        statement="Growth should convert to cash.",
        mechanism="Working-capital efficiency supports cash generation.",
        anti_thesis="Growth remains debt funded.",
        status="active",
        falsifiers=[Falsifier(metric="cfo", operator="<", threshold=0)],
        next_check_date=date(2026, 11, 30),
    )
    funding = FundingLoopResult(
        funding_state="debt_funded",
        incremental_nwc=50.0,
        incremental_debt=45.0,
        operating_cash_flow=-20.0,
        reason_codes=["DEBT_FUNDS_NWC", "NEGATIVE_OCF"],
    )
    module = DecisionModule(
        inputs=ResearchInputs(
            fundamental_state="STABLE",
            valuation_state="FAIR",
            expectation_state="IN_LINE",
        )
    )

    result = module.run(
        context,
        ResearchStateView(
            {
                "thesis.items": [thesis],
                "claims.items": [],
                "evidence.pit": evidence,
                "capital.funding_loop": funding,
            }
        ),
    )

    record: DecisionStateRecord = result.artifacts["decision.record"]
    assert record.state == "RISK_REVIEW"
    assert "FUNDAMENTAL_RISK" in record.reason_codes


def test_expectation_quality_uses_existing_consensus_fields_and_age():
    validator = ExpectationEvidenceValidator()
    decision_ts = datetime(2026, 8, 30, tzinfo=timezone.utc)
    vintage = ConsensusVintage(
        company_id="synthetic:v1.5.02",
        as_of=datetime(2026, 4, 30, tzinfo=timezone.utc),
        forecast_period="2026",
        net_profit=100.0,
        source_count=2,
        source_quality=0.4,
    )

    quality = validator.assess_consensus_quality(vintage=vintage, decision_ts=decision_ts)

    assert quality.status == "LOW"
    assert "THIN_CONSENSUS" in quality.reason_codes
    assert "LOW_SOURCE_QUALITY" in quality.reason_codes
    assert "STALE_CONSENSUS" in quality.reason_codes


def test_builtin_industry_plugins_provide_structured_report_contributions():
    for plugin in (ManufacturingIndustryPlugin(), DistributorIndustryPlugin()):
        contributions = plugin.report_contributions()
        assert contributions
        assert all(item.title for item in contributions)
        assert all(item.description for item in contributions)
        assert all(item.research_questions for item in contributions)
