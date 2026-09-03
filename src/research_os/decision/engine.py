from __future__ import annotations

from research_os.contracts.evidence import EvidenceRef
from research_os.decision.aggregation import DecisionAggregationPolicy
from research_os.decision.models import (
    DecisionContext,
    DecisionStateRecord,
    ResearchDecisionState,
    ThesisState,
)
from research_os.thesis.portfolio import portfolio_theses


class DecisionEngine:
    def __init__(
        self,
        *,
        aggregation_policy: DecisionAggregationPolicy | None = None,
    ) -> None:
        self._aggregation = aggregation_policy or DecisionAggregationPolicy()

    @staticmethod
    def _thesis_state(context: DecisionContext) -> ThesisState:
        portfolio = context.thesis_portfolio
        if portfolio.falsified:
            return "FALSIFIED"
        if portfolio.conflicting:
            return "WEAKENING"
        if portfolio.unresolved or portfolio.primary is None:
            return "UNRESOLVED"
        states: dict[str, ThesisState] = {
            "strengthening": "STRENGTHENING",
            "active": "ACTIVE",
            "weakening": "WEAKENING",
            "falsified": "FALSIFIED",
        }
        return states.get(portfolio.primary.status, "UNRESOLVED")

    def evaluate(self, context: DecisionContext) -> DecisionStateRecord:
        theses = portfolio_theses(context.thesis_portfolio)
        references: dict[tuple[str, int, str], EvidenceRef] = {
            (ref.evidence_id, ref.revision, ref.content_fingerprint): ref
            for thesis in theses
            for ref in thesis.evidence_refs
        }
        evidence_refs = tuple(references[key] for key in sorted(references))
        thesis_state = self._thesis_state(context)
        reasons: tuple[str, ...]
        state: ResearchDecisionState
        if (
            context.evidence_confidence
            < self._aggregation.minimum_evidence_confidence
            or not evidence_refs
        ):
            state = "INSUFFICIENT_EVIDENCE"
            reasons = ("LOW_EVIDENCE_CONFIDENCE",)
        elif self._aggregation.has_falsified_thesis(context.thesis_portfolio):
            state = "THESIS_BROKEN"
            reasons = ("THESIS_FALSIFIED",)
        elif (
            context.material_funding_risk
            and self._aggregation.material_funding_risk_veto
        ):
            state = "RISK_REVIEW"
            reasons = ("MATERIAL_FUNDING_RISK",)
        elif self._aggregation.has_unresolved_conflict(context.thesis_portfolio):
            state = "WAIT_FOR_CONFIRMATION"
            reasons = ("PORTFOLIO_CONFLICT_UNRESOLVED",)
        elif (
            context.fundamental_state == "DETERIORATING"
            and context.expectation_state in {"UNDER_EXPECTED", "MIXED"}
        ):
            state = "RISK_REVIEW"
            reasons = ("FUNDAMENTAL_RISK",)
        elif (
            context.fundamental_state == "IMPROVING"
            and context.valuation_state == "CHEAP"
            and thesis_state == "STRENGTHENING"
            and context.expectation_state == "OVER_EXPECTED"
        ):
            state = "HIGH_CONVICTION_WATCH"
            reasons = ("MULTI_DIMENSION_CONFIRMATION",)
        elif (
            context.fundamental_state == "IMPROVING"
            and context.valuation_state == "CHEAP"
            and thesis_state in {"ACTIVE", "STRENGTHENING"}
        ):
            state = "ACCUMULATION_CANDIDATE"
            reasons = ("CHEAP_AND_IMPROVING",)
        elif thesis_state in {"WEAKENING", "UNRESOLVED"} or context.fundamental_state == "UNCERTAIN":
            state = "WAIT_FOR_CONFIRMATION"
            reasons = ("CONFIRMATION_REQUIRED",)
        else:
            state = "HOLD_AND_MONITOR"
            reasons = ("NO_MATERIAL_STATE_CHANGE",)
        return DecisionStateRecord(
            company_id=context.company_id,
            state=state,
            decision_ts=context.decision_ts,
            used_thesis_ids=self._aggregation.thesis_ids(context.thesis_portfolio),
            used_claim_ids=tuple(sorted(set(context.claim_ids))),
            evidence_refs=evidence_refs,
            reason_codes=reasons,
            research_os_version=context.research_os_version,
            fundamental_state=context.fundamental_state,
            valuation_state=context.valuation_state,
            expectation_state=context.expectation_state,
            thesis_state=thesis_state,
            evidence_confidence=context.evidence_confidence,
        )


__all__ = ["DecisionEngine"]
