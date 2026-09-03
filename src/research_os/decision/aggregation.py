from __future__ import annotations

from research_os.contracts.artifact_values import ThesisPortfolio
from research_os.policies import PolicyRegistry, builtin_policy_registry
from research_os.thesis.portfolio import portfolio_theses


class DecisionAggregationPolicy:
    def __init__(self, *, policy_registry: PolicyRegistry | None = None) -> None:
        self._policy = policy_registry or builtin_policy_registry()

    @property
    def minimum_evidence_confidence(self) -> float:
        return float(
            self._policy.decimal_value("decision_aggregation", "minimum_evidence_confidence")
        )

    @property
    def material_funding_risk_veto(self) -> bool:
        return self._policy.boolean_value("decision_aggregation", "material_funding_risk_veto")

    @staticmethod
    def has_falsified_thesis(portfolio: ThesisPortfolio) -> bool:
        return bool(portfolio.falsified)

    @staticmethod
    def has_unresolved_conflict(portfolio: ThesisPortfolio) -> bool:
        return bool(portfolio.conflicting or portfolio.unresolved)

    @staticmethod
    def thesis_ids(portfolio: ThesisPortfolio) -> tuple[str, ...]:
        return tuple(item.thesis_key for item in portfolio_theses(portfolio))


__all__ = ["DecisionAggregationPolicy"]
