from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from research_os.application.command import (
    ResearchRunCommand,
    ValuationModelInput,
    ValuationResearchInput,
)
from research_os.application.professional_modules import ValuationResearchModule
from research_os.contracts.artifact_values import (
    FundingLoop,
    ModelFitnessInputs,
    NormalizedPeerSet,
    ValuationRange,
)
from research_os.contracts.artifacts import ArtifactStore, ArtifactWrite
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.router.models import BusinessModelProfile
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
    BUSINESS_MODEL_PROFILE,
    CAPITAL_FUNDING_LOOP,
    PEERS_NORMALIZED,
    VALUATION_EXECUTION,
    VALUATION_MARKET_ANCHOR,
    VALUATION_MARKET_GAP,
    build_core_artifact_catalog,
)
from research_os.valuation.execution import ValuationExecutionRequest
from research_os.valuation.market import PitMarketAnchor
from research_os.valuation.methods import ValuationMethodInput


DECISION_TS = datetime(2026, 8, 30, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:valuation-market-gap"


def _reference(identity: str, fingerprint: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=identity,
        revision=1,
        content_fingerprint=fingerprint * 64,
    )


def _command() -> ResearchRunCommand:
    valuation_ref = _reference("ev:valuation:inputs", "a")
    market_ref = _reference("ev:market:close", "b")
    context = ResearchContext(
        run_id="run:valuation-market-gap",
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
    ranges = tuple(
        ValuationRange(
            range_key=f"range:{index}",
            low=low,
            high=high,
            basis="per_share",
            currency="CNY",
            unit="CNY/share",
            share_class="A",
            corporate_action_basis="unadjusted_close",
            role="model_implied",
            evidence_refs=(valuation_ref,),
        )
        for index, low, high in ((1, Decimal("16"), Decimal("24")), (2, Decimal("18"), Decimal("22")))
    )
    return ResearchRunCommand(
        context=context,
        valuation=ValuationResearchInput(
            models=(
                ValuationModelInput(
                    model_id="pe",
                    fitness=ModelFitnessInputs(
                        data_quality=0.9,
                        earnings_stability=0.9,
                        cash_flow_visibility=0.9,
                        capital_structure_fit=0.9,
                        business_model_fit=0.9,
                        forecast_stability=0.9,
                    ),
                ),
            ),
            execution_requests=(
                ValuationExecutionRequest(
                    model_key="pe",
                    method_input=ValuationMethodInput(
                        currency="CNY",
                        basis="per_share",
                        valuation_date=date(2026, 8, 28),
                        values={"eps": Decimal("2"), "multiple": Decimal("10")},
                        evidence_refs=(valuation_ref,),
                    ),
                    scenario_logic="Evidence-bound EPS multiplied by an explicit PE multiple.",
                ),
            ),
            ranges=ranges,
            market_anchor=PitMarketAnchor(
                company_id=COMPANY_ID,
                security_id="300034.SZ",
                share_class="A",
                source_id="exchange:daily-close",
                observed_ts=datetime(2026, 8, 28, 7, 0, tzinfo=timezone.utc),
                available_ts=datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc),
                price=Decimal("12"),
                currency="CNY",
                unit="CNY/share",
                valuation_basis="per_share",
                corporate_action_basis="unadjusted_close",
                evidence_refs=(market_ref,),
            ),
        ),
    )


def test_valuation_module_executes_and_publishes_market_gap() -> None:
    command = _command()
    catalog = build_core_artifact_catalog()
    initial = ArtifactStore(catalog)
    for key, value in (
        (
            BUSINESS_MODEL_PROFILE,
            BusinessModelProfile(
                company_id=COMPANY_ID,
                primary_model="manufacturing",
                classification_status="CLASSIFIED",
            ),
        ),
        (
            CAPITAL_FUNDING_LOOP,
            FundingLoop(domain_status="SUPPORTED", funding_state="self_funded"),
        ),
        (PEERS_NORMALIZED, NormalizedPeerSet()),
    ):
        initial.write(ArtifactWrite(key=key, value=value, producer_id="test:initial"))
    plan = ModulePlanCompiler(catalog).compile(
        (ValuationResearchModule(command),),
        initial_snapshot=initial.freeze(),
    )

    execution = ResearchEngine().execute(
        plan,
        command.context,
        catalog,
        initial_snapshot=initial.freeze(),
    )

    valuation = execution.snapshot.require(VALUATION_EXECUTION)
    anchor = execution.snapshot.require(VALUATION_MARKET_ANCHOR)
    gap = execution.snapshot.require(VALUATION_MARKET_GAP)
    assert valuation.results[0].status == "SUPPORTED"
    assert valuation.execution_source == "CONTROLLED"
    assert valuation.validation_status == "PASS"
    assert anchor.price == Decimal("12")
    assert gap.comparison_status == "PASS"
    assert gap.state == "UNDERVALUED"
