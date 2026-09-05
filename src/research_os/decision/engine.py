from __future__ import annotations

from typing import NamedTuple

from research_os.contracts.evidence import EvidenceRef
from research_os.decision.aggregation import DecisionAggregationPolicy
from research_os.decision.models import (
    DecisionContext,
    DecisionDerivation,
    DecisionInputAssessment,
    DecisionStateRecord,
    ResearchDecisionState,
    ThesisState,
)
from research_os.thesis.portfolio import portfolio_theses


class _RuleOutcome(NamedTuple):
    state: ResearchDecisionState
    rule_id: str
    supporting_reasons: tuple[str, ...]
    blocking_reasons: tuple[str, ...]


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

    def _evaluate_rule(self, context: DecisionContext) -> _RuleOutcome:
        thesis_state = self._thesis_state(context)
        has_thesis_evidence = any(
            thesis.evidence_refs for thesis in portfolio_theses(context.thesis_portfolio)
        )
        if (
            context.evidence_confidence < self._aggregation.minimum_evidence_confidence
            or not has_thesis_evidence
        ):
            return _RuleOutcome(
                "INSUFFICIENT_EVIDENCE",
                "insufficient_material_evidence",
                (),
                ("LOW_EVIDENCE_CONFIDENCE",),
            )
        if self._aggregation.has_falsified_thesis(context.thesis_portfolio):
            return _RuleOutcome(
                "THESIS_BROKEN", "falsified_thesis", (), ("THESIS_FALSIFIED",)
            )
        if context.material_funding_risk and self._aggregation.material_funding_risk_veto:
            return _RuleOutcome(
                "RISK_REVIEW", "material_funding_risk", (), ("MATERIAL_FUNDING_RISK",)
            )
        if self._aggregation.has_unresolved_conflict(context.thesis_portfolio):
            return _RuleOutcome(
                "WAIT_FOR_CONFIRMATION",
                "unresolved_portfolio_conflict",
                (),
                ("PORTFOLIO_CONFLICT_UNRESOLVED",),
            )
        if context.fundamental_state == "DETERIORATING" and context.expectation_state in {
            "UNDER_EXPECTED",
            "MIXED",
        }:
            return _RuleOutcome(
                "RISK_REVIEW", "deteriorating_fundamentals", (), ("FUNDAMENTAL_RISK",)
            )
        if (
            context.sufficiency_state == "INSUFFICIENT_EVIDENCE"
            and context.forecast_state != "UNKNOWN"
        ):
            return _RuleOutcome(
                "INSUFFICIENT_EVIDENCE",
                "research_sufficiency_gate",
                (),
                ("RESEARCH_SUFFICIENCY_BLOCKED",),
            )
        if (
            context.fundamental_state == "IMPROVING"
            and context.valuation_state == "CHEAP"
            and thesis_state == "STRENGTHENING"
            and context.expectation_state == "OVER_EXPECTED"
            and context.forecast_state in {"PASS", "UNKNOWN"}
        ):
            return _RuleOutcome(
                "HIGH_CONVICTION_WATCH",
                "multi_dimension_confirmation",
                ("MULTI_DIMENSION_CONFIRMATION",),
                (),
            )
        if (
            context.fundamental_state == "IMPROVING"
            and context.valuation_state == "CHEAP"
            and thesis_state in {"ACTIVE", "STRENGTHENING"}
            and context.forecast_state in {"PASS", "UNKNOWN"}
        ):
            return _RuleOutcome(
                "ACCUMULATION_CANDIDATE",
                "cheap_and_improving",
                ("CHEAP_AND_IMPROVING",),
                (),
            )
        if context.forecast_state in {"FAIL", "INSUFFICIENT_EVIDENCE"}:
            return _RuleOutcome(
                "WAIT_FOR_CONFIRMATION",
                "forecast_confirmation_required",
                (),
                ("FORECAST_CONFIRMATION_REQUIRED",),
            )
        if thesis_state in {"WEAKENING", "UNRESOLVED"} or context.fundamental_state == "UNCERTAIN":
            return _RuleOutcome(
                "WAIT_FOR_CONFIRMATION",
                "confirmation_required",
                (),
                ("CONFIRMATION_REQUIRED",),
            )
        return _RuleOutcome(
            "HOLD_AND_MONITOR",
            "hold_and_monitor",
            ("NO_MATERIAL_STATE_CHANGE",),
            (),
        )

    def _record(
        self,
        context: DecisionContext,
        outcome: _RuleOutcome,
    ) -> DecisionStateRecord:
        theses = portfolio_theses(context.thesis_portfolio)
        references: dict[tuple[str, int, str], EvidenceRef] = {
            (ref.evidence_id, ref.revision, ref.content_fingerprint): ref
            for thesis in theses
            for ref in thesis.evidence_refs
        }
        evidence_refs = tuple(references[key] for key in sorted(references))
        thesis_state = self._thesis_state(context)
        return DecisionStateRecord(
            company_id=context.company_id,
            state=outcome.state,
            decision_ts=context.decision_ts,
            used_thesis_ids=self._aggregation.thesis_ids(context.thesis_portfolio),
            used_claim_ids=tuple(sorted(set(context.claim_ids))),
            evidence_refs=evidence_refs,
            reason_codes=outcome.supporting_reasons or outcome.blocking_reasons,
            research_os_version=context.research_os_version,
            fundamental_state=context.fundamental_state,
            valuation_state=context.valuation_state,
            expectation_state=context.expectation_state,
            thesis_state=thesis_state,
            evidence_confidence=context.evidence_confidence,
        )

    def evaluate(self, context: DecisionContext) -> DecisionStateRecord:
        return self._record(context, self._evaluate_rule(context))

    def evaluate_with_derivation(
        self,
        context: DecisionContext,
        assessment: DecisionInputAssessment,
    ) -> tuple[DecisionStateRecord, DecisionDerivation]:
        outcome = self._evaluate_rule(context)
        record = self._record(context, outcome)
        return record, DecisionDerivation(
            domain_status=(
                "INSUFFICIENT_EVIDENCE"
                if record.state == "INSUFFICIENT_EVIDENCE"
                else "SUPPORTED"
            ),
            rule_id=outcome.rule_id,
            rule_version=self._aggregation.rule_version,
            input_states=assessment.dimensions,
            output_state=record.state,
            supporting_reason_codes=outcome.supporting_reasons,
            blocking_reason_codes=outcome.blocking_reasons,
            used_thesis_ids=record.used_thesis_ids,
            used_claim_ids=record.used_claim_ids,
            evidence_refs=assessment.evidence_refs,
            assumption_refs=assessment.assumption_refs,
        )


__all__ = ["DecisionEngine"]
