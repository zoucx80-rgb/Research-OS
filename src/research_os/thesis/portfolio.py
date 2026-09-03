from __future__ import annotations

from research_os.contracts.artifact_values import Thesis, ThesisPortfolio
from research_os.contracts.evidence import EvidenceRef
from research_os.policies import PolicyRegistry, builtin_policy_registry


class ThesisPortfolioBuilder:
    def __init__(self, *, policy_registry: PolicyRegistry | None = None) -> None:
        self._policy = policy_registry or builtin_policy_registry()

    def build(self, theses: tuple[Thesis, ...]) -> ThesisPortfolio:
        ordered = tuple(sorted(theses, key=lambda item: item.thesis_key))
        if len({item.thesis_key for item in ordered}) != len(ordered):
            raise ValueError("thesis portfolio contains duplicate thesis keys")
        minimum_confidence = float(
            self._policy.decimal_value("thesis_formation", "minimum_primary_confidence")
        )
        minimum_evidence = self._policy.integer_value(
            "thesis_formation", "minimum_primary_evidence"
        )
        positive = tuple(item for item in ordered if item.status in {"active", "strengthening"})
        eligible = tuple(
            item
            for item in positive
            if item.claim_strength in {"SUPPORTED", "STRONG", "CONFIRMED"}
            and (item.confidence or 0) >= minimum_confidence
            and len(item.evidence_refs) >= minimum_evidence
        )
        ranked = tuple(
            sorted(
                eligible,
                key=lambda item: (
                    0 if item.status == "strengthening" else 1,
                    -(item.confidence or 0),
                    -len(item.evidence_refs),
                    item.thesis_key,
                ),
            )
        )
        primary = ranked[0] if ranked else None
        supporting = tuple(item for item in positive if item != primary)
        conflicting = tuple(item for item in ordered if item.status == "weakening")
        unresolved = tuple(
            item for item in ordered if item.status in {"new", "unresolved", "expired"}
        )
        falsified = tuple(item for item in ordered if item.status == "falsified")
        references: dict[tuple[str, int, str], EvidenceRef] = {}
        for item in ordered:
            for reference in item.evidence_refs:
                references[
                    (
                        reference.evidence_id,
                        reference.revision,
                        reference.content_fingerprint,
                    )
                ] = reference
        return ThesisPortfolio(
            primary=primary,
            supporting=supporting,
            conflicting=conflicting,
            unresolved=unresolved,
            falsified=falsified,
            domain_status="SUPPORTED" if primary is not None else "INSUFFICIENT_EVIDENCE",
            evidence_refs=tuple(references[key] for key in sorted(references)),
        )


def portfolio_theses(portfolio: ThesisPortfolio) -> tuple[Thesis, ...]:
    values = (
        (() if portfolio.primary is None else (portfolio.primary,))
        + portfolio.supporting
        + portfolio.conflicting
        + portfolio.unresolved
        + portfolio.falsified
    )
    return tuple(sorted(values, key=lambda item: item.thesis_key))


__all__ = ["ThesisPortfolioBuilder", "portfolio_theses"]
