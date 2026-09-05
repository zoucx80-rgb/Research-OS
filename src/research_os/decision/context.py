from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, cast

from research_os.contracts.artifact_values import AssumptionRef, ThesisPortfolio
from research_os.contracts.artifacts import ArtifactKey
from research_os.contracts.evidence import EvidenceRef
from research_os.decision.models import (
    DecisionContext,
    DecisionDimensionAssessment,
    DecisionInputAssessment,
    ExpectationState,
    FundamentalState,
    ThesisState,
    ValuationState,
)
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import (
    CAPITAL_EFFICIENCY,
    CAPITAL_FUNDING_LOOP,
    EXPECTATION_GAP,
    FINANCIAL_TEMPORAL_ANALYSIS,
    FORECAST_BENCHMARK_EVIDENCE,
    RESEARCH_SUFFICIENCY,
    SCENARIO_SENSITIVITIES,
    SEMANTIC_CLAIMS,
    THESIS_PORTFOLIO,
    THESIS_SEMANTIC_SIGNAL_ASSESSMENT,
    VALUATION_MARKET_GAP,
    VALUATION_RECONCILIATION,
)
from research_os.runtime.state import ResearchStateView


class DecisionContextBuilder:
    """Translate canonical artifacts into one deterministic decision input."""

    _DIMENSION_KEYS = (
        ("financial_temporal", FINANCIAL_TEMPORAL_ANALYSIS),
        ("capital_efficiency", CAPITAL_EFFICIENCY),
        ("funding_loop", CAPITAL_FUNDING_LOOP),
        ("thesis_portfolio", THESIS_PORTFOLIO),
        ("semantic_signals", THESIS_SEMANTIC_SIGNAL_ASSESSMENT),
        ("expectation_gap", EXPECTATION_GAP),
        ("forecast_quality", FORECAST_BENCHMARK_EVIDENCE),
        ("valuation_reconciliation", VALUATION_RECONCILIATION),
        ("valuation_market_gap", VALUATION_MARKET_GAP),
        ("scenario", SCENARIO_SENSITIVITIES),
        ("research_sufficiency", RESEARCH_SUFFICIENCY),
    )

    def build(
        self,
        context: ResearchContext,
        state: ResearchStateView,
    ) -> tuple[DecisionContext, DecisionInputAssessment]:
        values: dict[str, Any] = {
            name: state.get(cast(ArtifactKey[Any], key))
            for name, key in self._DIMENSION_KEYS
        }
        portfolio = values["thesis_portfolio"]
        if not isinstance(portfolio, ThesisPortfolio):
            portfolio = ThesisPortfolio()
        dimensions = tuple(
            self._dimension(name, key.artifact_id, values[name])
            for name, key in self._DIMENSION_KEYS
        )
        sufficiency = values["research_sufficiency"]
        sufficiency_state = cast(
            Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"],
            getattr(sufficiency, "overall_status", "INSUFFICIENT_EVIDENCE"),
        )
        confidence = self._evidence_confidence(portfolio, sufficiency_state)
        blocking_reasons = tuple(getattr(sufficiency, "blocking_gap_keys", ()))
        evidence_refs = self._evidence_refs(dimensions)
        assumption_refs = self._assumption_refs(dimensions)
        assessment = DecisionInputAssessment(
            domain_status=(
                "SUPPORTED"
                if any(item.availability == "AVAILABLE" for item in dimensions)
                else "INSUFFICIENT_EVIDENCE"
            ),
            dimensions=dimensions,
            evidence_confidence=confidence,
            blocking_reason_codes=blocking_reasons,
            evidence_refs=evidence_refs,
            assumption_refs=assumption_refs,
        )
        funding = values["funding_loop"]
        semantic = values["semantic_signals"]
        temporal = values["financial_temporal"]
        market_gap = values["valuation_market_gap"]
        expectation = values["expectation_gap"]
        forecast = values["forecast_quality"]
        scenario = values["scenario"]
        claims = state.get(SEMANTIC_CLAIMS)
        return (
            DecisionContext(
                company_id=context.company.company_id,
                fundamental_state=self._fundamental_state(funding, semantic, temporal),
                valuation_state=self._valuation_state(market_gap),
                expectation_state=self._expectation_state(expectation),
                thesis_portfolio=portfolio,
                evidence_confidence=float(confidence),
                claim_ids=tuple(
                    item.claim_key for item in getattr(claims, "claims", ())
                ),
                decision_ts=context.decision_ts,
                material_funding_risk=self._material_funding_risk(funding),
                forecast_state=self._forecast_state(forecast),
                sufficiency_state=sufficiency_state,
                scenario_state=(
                    "AVAILABLE" if getattr(scenario, "cases", ()) else "UNAVAILABLE"
                ),
            ),
            assessment,
        )

    @staticmethod
    def _dimension(
        name: str,
        artifact_id: str,
        value: object | None,
    ) -> DecisionDimensionAssessment:
        if value is None:
            return DecisionDimensionAssessment(
                dimension=name,
                state="UNAVAILABLE",
                availability="INSUFFICIENT_EVIDENCE",
                artifact_ids=(artifact_id,),
                reason_codes=("ARTIFACT_MISSING",),
            )
        domain_status = getattr(value, "domain_status", "INSUFFICIENT_EVIDENCE")
        state = DecisionContextBuilder._dimension_state(name, value)
        reasons = tuple(
            sorted(
                set(
                    getattr(value, "reason_codes", ())
                    or getattr(value, "unresolved_gaps", ())
                    or getattr(value, "blocking_gap_keys", ())
                )
            )
        )
        return DecisionDimensionAssessment(
            dimension=name,
            state=state,
            availability=(
                "AVAILABLE" if domain_status == "SUPPORTED" else "INSUFFICIENT_EVIDENCE"
            ),
            artifact_ids=(artifact_id,),
            reason_codes=reasons or (() if domain_status == "SUPPORTED" else ("UNSUPPORTED",)),
            evidence_refs=tuple(getattr(value, "evidence_refs", ())),
            assumption_refs=tuple(getattr(value, "assumption_refs", ())),
        )

    @staticmethod
    def _dimension_state(name: str, value: object) -> str:
        attributes = {
            "financial_temporal": "temporal_coverage",
            "funding_loop": "funding_state",
            "semantic_signals": "assessment_status",
            "expectation_gap": "direction",
            "valuation_reconciliation": "reconciliation_status",
            "valuation_market_gap": "state",
            "research_sufficiency": "overall_status",
        }
        if name == "capital_efficiency":
            roic = getattr(value, "roic", None)
            return "UNKNOWN" if roic is None else ("POSITIVE" if roic >= 0 else "NEGATIVE")
        if name == "thesis_portfolio":
            return DecisionContextBuilder._thesis_state(value)
        if name == "forecast_quality":
            return DecisionContextBuilder._forecast_state(value)
        if name == "scenario":
            return "AVAILABLE" if getattr(value, "cases", ()) else "UNAVAILABLE"
        return str(getattr(value, attributes[name], "UNKNOWN") or "UNKNOWN")

    @staticmethod
    def _thesis_state(portfolio: object) -> ThesisState:
        if getattr(portfolio, "falsified", ()):
            return "FALSIFIED"
        if getattr(portfolio, "conflicting", ()):
            return "WEAKENING"
        primary = getattr(portfolio, "primary", None)
        if getattr(portfolio, "unresolved", ()) or primary is None:
            return "UNRESOLVED"
        states: dict[str, ThesisState] = {
            "strengthening": "STRENGTHENING",
            "active": "ACTIVE",
            "weakening": "WEAKENING",
            "falsified": "FALSIFIED",
        }
        return states.get(primary.status, "UNRESOLVED")

    @staticmethod
    def _fundamental_state(
        funding: object | None,
        semantic: object | None,
        temporal: object | None,
    ) -> FundamentalState:
        if DecisionContextBuilder._material_funding_risk(funding):
            return "DETERIORATING"
        signals = tuple(getattr(semantic, "signals", ()))
        directions = {item.direction for item in signals}
        if "NEGATIVE" in directions:
            return "DETERIORATING"
        if "POSITIVE" in directions:
            return "IMPROVING"
        trends = {
            item.trend_state
            for item in getattr(temporal, "assessments", ())
            if item.comparison_status == "PASS"
        }
        if trends == {"RISING"}:
            return "IMPROVING"
        if trends == {"FALLING"}:
            return "DETERIORATING"
        if trends and trends <= {"RISING", "FALLING", "STABLE"}:
            return "STABLE"
        funding_state = getattr(funding, "funding_state", None)
        return "STABLE" if funding_state in {"self_funded", "mixed"} else "UNCERTAIN"

    @staticmethod
    def _valuation_state(market_gap: object | None) -> ValuationState:
        if (
            getattr(market_gap, "domain_status", None) != "SUPPORTED"
            or getattr(market_gap, "comparison_status", None) != "PASS"
        ):
            return "UNRELIABLE"
        states: dict[str, ValuationState] = {
            "UNDERVALUED": "CHEAP",
            "FAIR": "FAIR",
            "OVERVALUED": "EXPENSIVE",
        }
        return states.get(getattr(market_gap, "state", "UNKNOWN"), "UNRELIABLE")

    @staticmethod
    def _expectation_state(gap: object | None) -> ExpectationState:
        states: dict[str, ExpectationState] = {
            "BELOW_MARKET": "UNDER_EXPECTED",
            "UNDER_EXPECTED": "UNDER_EXPECTED",
            "NEGATIVE": "UNDER_EXPECTED",
            "ABOVE_MARKET": "OVER_EXPECTED",
            "OVER_EXPECTED": "OVER_EXPECTED",
            "POSITIVE": "OVER_EXPECTED",
            "IN_LINE": "IN_LINE",
            "INLINE": "IN_LINE",
            "MIXED": "MIXED",
        }
        return states.get(str(getattr(gap, "direction", "UNKNOWN")).upper(), "UNKNOWN")

    @staticmethod
    def _forecast_state(
        forecast: object | None,
    ) -> Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "UNKNOWN"]:
        if forecast is None:
            return "UNKNOWN"
        if getattr(forecast, "domain_status", None) != "SUPPORTED":
            return "INSUFFICIENT_EVIDENCE"
        passed = bool(
            getattr(forecast, "out_of_sample", False)
            and getattr(forecast, "pit_compliant", False)
            and getattr(forecast, "stable", False)
            and getattr(forecast, "improvement", Decimal("0")) > 0
        )
        return "PASS" if passed else "FAIL"

    @staticmethod
    def _material_funding_risk(funding: object | None) -> bool:
        return getattr(funding, "funding_state", None) in {"stressed", "debt_funded"} and bool(
            set(getattr(funding, "reason_codes", ()))
            & {"NEGATIVE_OCF", "MATERIAL_FACTORING_EXPOSURE"}
        )

    @staticmethod
    def _evidence_confidence(portfolio: ThesisPortfolio, sufficiency_state: str) -> Decimal:
        if portfolio.primary is None:
            return Decimal("0")
        confidence = Decimal(str(portfolio.primary.confidence or 0))
        cap = {
            "SUFFICIENT": Decimal("1"),
            "LIMITED": Decimal("0.75"),
            "INSUFFICIENT_EVIDENCE": Decimal("0.50"),
        }.get(sufficiency_state, Decimal("0.50"))
        return min(confidence, cap)

    @staticmethod
    def _evidence_refs(
        dimensions: tuple[DecisionDimensionAssessment, ...],
    ) -> tuple[EvidenceRef, ...]:
        values = {
            (item.evidence_id, item.revision, item.content_fingerprint): item
            for dimension in dimensions
            for item in dimension.evidence_refs
        }
        return tuple(values[key] for key in sorted(values))

    @staticmethod
    def _assumption_refs(
        dimensions: tuple[DecisionDimensionAssessment, ...],
    ) -> tuple[AssumptionRef, ...]:
        values = {
            (item.assumption_key, item.assumption_version, item.content_fingerprint): item
            for dimension in dimensions
            for item in dimension.assumption_refs
        }
        return tuple(values[key] for key in sorted(values))


__all__ = ["DecisionContextBuilder"]
