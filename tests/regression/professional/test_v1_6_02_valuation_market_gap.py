from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from research_os.application.command import (
    ResearchRunCommand,
    ValuationModelInput,
    ValuationResearchInput,
)
from research_os.application.professional_modules import ValuationResearchModule
from research_os.contracts.artifact_values import (
    AssumptionRef,
    FundingLoop,
    ModelFitnessInputs,
    NormalizedPeerSet,
    ValuationRange,
)
from research_os.contracts.artifacts import ArtifactStore, ArtifactWrite
from research_os.contracts.evidence import evidence_content_fingerprint
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
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
COMPANY_ID = "synthetic:valuation-regression"
REAL_COMPANY_IDS = ("300034.SZ", "001287.SZ", "301073.SZ")
FIELD_FIXTURES = Path("tests/fixtures/field_acceptance/v1_6_02")


def _command() -> ResearchRunCommand:
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="run:valuation-regression",
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
    )


def test_missing_execution_and_anchor_remain_typed_and_do_not_fabricate_anchor() -> None:
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
        (CAPITAL_FUNDING_LOOP, FundingLoop(funding_state="unknown")),
        (PEERS_NORMALIZED, NormalizedPeerSet()),
    ):
        initial.write(ArtifactWrite(key=key, value=value, producer_id="test:initial"))
    plan = ModulePlanCompiler(catalog).compile(
        (ValuationResearchModule(command),),
        initial_snapshot=initial.freeze(),
    )

    result = ResearchEngine().execute(
        plan,
        command.context,
        catalog,
        initial_snapshot=initial.freeze(),
    )

    execution = result.snapshot.require(VALUATION_EXECUTION)
    gap = result.snapshot.require(VALUATION_MARKET_GAP)
    assert execution.execution_source == "NONE"
    assert execution.validation_status == "INSUFFICIENT_EVIDENCE"
    assert gap.reason_codes == ("MARKET_ANCHOR_MISSING",)
    assert result.snapshot.get(VALUATION_MARKET_ANCHOR) is None


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _market_evidence(company_id: str, item: dict[str, object]) -> Evidence:
    available_ts = _parse_ts(str(item["available_ts"]))
    price = Decimal(str(item["price"]))
    return Evidence(
        evidence_id=str(item["evidence_id"]),
        company_id=company_id,
        evidence_type="market_data",
        period_end=date(2026, 8, 28),
        period="2026-08-28",
        publish_ts=available_ts,
        ingested_at=available_ts,
        value=price,
        raw_value=str(item["price"]),
        normalized_value=price,
        unit=str(item["unit"]),
        scope=str(item["share_class"]),
        version=str(item["corporate_action_basis"]),
        source_document_id=str(item["source_document_id"]),
        source_table="daily_close",
        source_url=str(item["source_url"]),
        confidence_grade="B",
        verification_status="SECONDARY_VERIFIED",
        dataset_version="field-acceptance-v1.6.02@1",
        parser_version="manual-market-observation@1",
        comparison_basis=str(item["valuation_basis"]),
        metric_kind="close_price",
        revision_no=1,
    )


def _valuation_evidence(company_id: str, item: dict[str, object]) -> Evidence:
    publish_ts = _parse_ts(str(item["publish_ts"]))
    value = Decimal(str(item["value"]))
    return Evidence(
        evidence_id=str(item["evidence_id"]),
        company_id=company_id,
        evidence_type="filing_fact",
        period_end=date.fromisoformat(str(item["period_end"])),
        period=str(item["period"]),
        publish_ts=publish_ts,
        ingested_at=publish_ts,
        value=value,
        raw_value=str(item["value"]),
        normalized_value=value,
        unit=str(item["unit"]),
        scope="consolidated",
        version=str(item["period"]),
        source_document_id=str(item["source_document_id"]),
        source_table="net_profit_parent",
        source_url=str(item["source_url"]),
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
        dataset_version="field-acceptance-v1.6.02@1",
        parser_version="manual-primary-source@1",
        comparison_basis="reported",
        metric_kind="financial_statement",
        revision_no=1,
    )


def _assumption_reference(item: dict[str, object]) -> AssumptionRef:
    payload = {key: value for key, value in item.items() if key != "content_fingerprint"}
    fingerprint = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert fingerprint == item["content_fingerprint"]
    return AssumptionRef(
        assumption_key=str(item["assumption_key"]),
        assumption_version=str(item["assumption_version"]),
        content_fingerprint=fingerprint,
    )


def _real_company_command(company_id: str) -> ResearchRunCommand:
    case = json.loads((FIELD_FIXTURES / f"{company_id}.json").read_text(encoding="utf-8"))
    decision_ts = _parse_ts(case["decision_ts"])
    market_item = case["market_anchor"]
    market_evidence = _market_evidence(company_id, market_item)
    assert evidence_content_fingerprint(market_evidence) == market_item["content_fingerprint"]
    evidence = [market_evidence]
    valuation_item = case.get("valuation")
    if valuation_item is not None:
        filing_evidence = _valuation_evidence(company_id, valuation_item["evidence"])
        assert (
            evidence_content_fingerprint(filing_evidence)
            == valuation_item["evidence"]["content_fingerprint"]
        )
        evidence.append(filing_evidence)
    evidence_view = EvidenceView(tuple(evidence), company_id=company_id, decision_ts=decision_ts)
    references = {item.evidence_id: item for item in evidence_view.refs()}
    anchor = PitMarketAnchor(
        company_id=company_id,
        security_id=company_id,
        share_class=market_item["share_class"],
        source_id=market_item["source_id"],
        observed_ts=_parse_ts(market_item["observed_ts"]),
        available_ts=_parse_ts(market_item["available_ts"]),
        price=Decimal(market_item["price"]),
        currency=market_item["currency"],
        unit=market_item["unit"],
        valuation_basis=market_item["valuation_basis"],
        corporate_action_basis=market_item["corporate_action_basis"],
        evidence_refs=(references[market_item["evidence_id"]],),
    )
    context = ResearchContext(
        run_id=f"run:valuation-field:{company_id}",
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
    if valuation_item is None:
        return ResearchRunCommand(
            context=context,
            valuation=ValuationResearchInput(market_anchor=anchor),
        )
    assumptions = tuple(_assumption_reference(item) for item in valuation_item["assumptions"])
    assumption_by_key = {item.assumption_key: item for item in assumptions}
    filing_reference = references[valuation_item["evidence"]["evidence_id"]]
    eps = valuation_item["assumptions"][0]["value"]
    multiples = valuation_item["assumptions"][1]["value"]
    ranges = tuple(
        ValuationRange(
            range_key=item["range_key"],
            low=Decimal(item["low"]),
            high=Decimal(item["high"]),
            basis=market_item["valuation_basis"],
            currency=market_item["currency"],
            unit=market_item["unit"],
            share_class=market_item["share_class"],
            corporate_action_basis=market_item["corporate_action_basis"],
            role=item["role"],
            evidence_refs=(filing_reference,),
            assumption_refs=assumptions,
        )
        for item in valuation_item["ranges"]
    )
    return ResearchRunCommand(
        context=context,
        valuation=ValuationResearchInput(
            models=(
                ValuationModelInput(
                    model_id="pe",
                    fitness=ModelFitnessInputs(**valuation_item["fitness"]),
                ),
            ),
            execution_requests=(
                ValuationExecutionRequest(
                    model_key="pe",
                    method_input=ValuationMethodInput(
                        currency=market_item["currency"],
                        basis=market_item["valuation_basis"],
                        valuation_date=anchor.observed_ts.date(),
                        values={
                            "eps": Decimal(eps),
                            "multiple": Decimal(multiples["base"]),
                            "bear_multiple": Decimal(multiples["bear"]),
                            "bull_multiple": Decimal(multiples["bull"]),
                        },
                        evidence_refs=(filing_reference,),
                        assumption_refs=(
                            assumption_by_key[
                                "assumption:300034.SZ:normalized-forward-eps"
                            ],
                            assumption_by_key["assumption:300034.SZ:pe-band"],
                        ),
                    ),
                    scenario_logic=(
                        "Reported profit evidence is separated from explicit normalized EPS "
                        "and PE-band assumptions."
                    ),
                ),
            ),
            ranges=ranges,
            market_anchor=anchor,
        ),
    )


def _run_v1_6_02_case(company_id: str):
    command = _real_company_command(company_id)
    catalog = build_core_artifact_catalog()
    initial = ArtifactStore(catalog)
    for key, value in (
        (
            BUSINESS_MODEL_PROFILE,
            BusinessModelProfile(
                company_id=company_id,
                primary_model="manufacturing",
                classification_status="CLASSIFIED",
            ),
        ),
        (CAPITAL_FUNDING_LOOP, FundingLoop(funding_state="self_funded")),
        (PEERS_NORMALIZED, NormalizedPeerSet()),
    ):
        initial.write(ArtifactWrite(key=key, value=value, producer_id="test:initial"))
    plan = ModulePlanCompiler(catalog).compile(
        (ValuationResearchModule(command),),
        initial_snapshot=initial.freeze(),
    )
    return ResearchEngine().execute(
        plan,
        command.context,
        catalog,
        initial_snapshot=initial.freeze(),
    )


def test_real_company_anchors_are_revision_bound_and_pit_valid() -> None:
    for company_id in REAL_COMPANY_IDS:
        command = _real_company_command(company_id)
        anchor = command.valuation.market_anchor
        assert anchor is not None
        assert anchor.observed_ts == datetime(2026, 8, 28, 7, tzinfo=timezone.utc)
        assert anchor.observed_ts <= anchor.available_ts <= command.context.decision_ts
        assert anchor.evidence_refs[0] in command.context.evidence.refs()


def test_at_least_one_real_company_has_supported_market_gap() -> None:
    results = [_run_v1_6_02_case(company_id) for company_id in REAL_COMPANY_IDS]
    gaps = [item.snapshot.require(VALUATION_MARKET_GAP) for item in results]

    assert any(item.comparison_status == "PASS" for item in gaps)
    assert all(item.comparison_status == "PASS" or item.reason_codes for item in gaps)
    controlled = results[0].snapshot.require(VALUATION_EXECUTION)
    assert controlled.execution_source == "CONTROLLED"
    assert controlled.validation_status == "PASS"
