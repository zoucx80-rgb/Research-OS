from datetime import datetime, timezone

from research_os.capital.engine import FundingLoopResult
from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.expectations.models import ConsensusVintage
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.factory import ResearchRuntimeFactory
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.professional_modules import ProfessionalDecisionModule
from research_os.runtime.provenance import StateInput


def _evidence(key: str, value) -> Evidence:
    ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    return Evidence(
        evidence_id=f"ev:{key}",
        company_id="synthetic:v1.5.03:runtime",
        evidence_type=EvidenceType.FILING_FACT,
        publish_ts=ts,
        ingested_at=ts,
        value=value,
        source_table=key,
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
    )


def _context(evidence: list[Evidence]) -> ResearchContext:
    facts = {item.source_table: item.value for item in evidence if item.source_table}
    by_fact = {
        key: [item.evidence_id for item in evidence if item.source_table == key]
        for key in facts
    }
    return ResearchContext(
        run_id="run:v1.5.03:runtime",
        company=CompanyRef(company_id="synthetic:v1.5.03:runtime"),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="2" * 40,
            research_os_version="1.5.2",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=facts, evidence_by_fact=by_fact),
        options=ResearchOptions(),
    )


def test_canonical_decision_module_result_contains_explicit_state_provenance():
    evidence = [
        _evidence("business_description", "manufacturing production"),
        _evidence("revenue_growth", 0.15),
        _evidence("margin_change", 0.02),
        _evidence("ocf", 10.0),
    ]
    inputs = ResearchInputs(
        fundamental_state_input=StateInput(
            value="IMPROVING",
            source="derived",
            evidence_ids=["ev:revenue_growth", "ev:margin_change"],
            method="directional operating signal model",
        ),
        valuation_state="UNRELIABLE",
        expectation_state="MIXED",
    )
    result = ResearchRuntimeFactory.default().run_context(_context(evidence), inputs)
    module = result.module_results["core:decision"]
    provenance = module.artifacts["decision.state_provenance"]
    assert provenance["fundamental"].source == "derived"
    assert provenance["fundamental"].evidence_ids == ["ev:revenue_growth", "ev:margin_change"]
    assert result.artifacts["decision.state_provenance"]["fundamental"].source == "derived"


def test_factoring_exposure_enhances_existing_stress_but_is_not_debt_by_itself():
    factoring_only = FundingLoopResult(
        funding_state="mixed",
        reason_codes=["MATERIAL_FACTORING_EXPOSURE"],
    )
    factoring_and_negative_cash = FundingLoopResult(
        funding_state="mixed",
        reason_codes=["MATERIAL_FACTORING_EXPOSURE", "NEGATIVE_OCF"],
    )
    assert ProfessionalDecisionModule._funding_material_risk(factoring_only) is False
    assert ProfessionalDecisionModule._funding_material_risk(factoring_and_negative_cash) is True


def test_expectation_quality_inside_canonical_module_is_material_event_relative():
    evidence = [_evidence("business_description", "hotel hospitality lodging operations")]
    inputs = ResearchInputs(
        expectation_vintage=ConsensusVintage(
            company_id="synthetic:v1.5.03:runtime",
            as_of=datetime(2026, 7, 27, tzinfo=timezone.utc),
            forecast_period="2026",
            net_profit=100.0,
            source_count=4,
            source_quality=0.8,
        ),
        latest_material_event_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        latest_material_event_label="2026年半年报",
    )
    result = ResearchRuntimeFactory.default().run_context(_context(evidence), inputs)
    module_quality = result.module_results["core:expectation"].artifacts["expectation.quality"]
    assert module_quality.status == "LOW"
    assert module_quality.post_event_consensus is False
    assert "CONSENSUS_PREDATES_MATERIAL_EVENT" in module_quality.reason_codes


def test_driver_thesis_component_fingerprint_advances_to_v1_2_0():
    evidence = [
        _evidence("business_description", "manufacturing production"),
        _evidence("revenue_growth", 0.15),
        _evidence("margin_change", 0.02),
        _evidence("ocf", 10.0),
    ]
    result = ResearchRuntimeFactory.default().run_context(_context(evidence), ResearchInputs())
    fp = next(
        item for item in result.component_fingerprints
        if item.component_id == "core:driver-thesis"
    )
    assert fp.component_version == "1.2.0"
