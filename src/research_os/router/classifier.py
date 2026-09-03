from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef, evidence_content_fingerprint
from research_os.contracts.values import Ratio
from research_os.domain.evidence import Evidence
from research_os.policies import PolicyRegistry, builtin_policy_registry
from research_os.router.models import (
    BusinessModelProfile,
    ClassificationStatus,
    ConfidenceBand,
    RoutingCandidate,
)


def _numeric(value: object) -> float | None:
    if isinstance(value, Ratio):
        return float(value.decimal_value)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    return None


class BusinessModelRouter:
    version = "router@2.0.0"

    def __init__(self, *, policy_registry: PolicyRegistry | None = None) -> None:
        self._policy = policy_registry or builtin_policy_registry()

    @staticmethod
    def _is_annual_period(item: Evidence | None) -> bool:
        if item is None or item.period is None:
            return False
        period = str(item.period).strip().lower().replace(" ", "")
        if not period:
            return False
        if any(
            token in period
            for token in (
                "h1", "h2", "q1", "q2", "q3", "q4", "interim",
                "半年度", "半年", "季度",
            )
        ):
            return False
        return bool(
            period in {"annual", "year", "yearly", "年度", "年报"}
            or re.fullmatch(r"20\d{2}", period)
            or re.fullmatch(r"fy20\d{2}", period)
            or re.fullmatch(r"20\d{2}(?:fy|a|annual)", period)
        )

    @staticmethod
    def _reference(item: Evidence) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=item.evidence_id,
            revision=item.revision_no,
            content_fingerprint=evidence_content_fingerprint(item),
        )

    def classify(
        self,
        company_id: str,
        evidence: Iterable[Evidence],
    ) -> BusinessModelProfile:
        records = {item.source_table or item.evidence_id: item for item in evidence}
        values = {key: item.value for key, item in records.items()}
        scores: defaultdict[str, float] = defaultdict(float)
        support: defaultdict[str, dict[str, EvidenceRef]] = defaultdict(dict)

        def threshold(name: str) -> float:
            return float(
                self._policy.decimal_value("business_model_routing", name)
            )

        def add(model_id: str, weight_name: str, evidence_key: str) -> None:
            item = records.get(evidence_key)
            if item is None:
                return
            scores[model_id] += threshold(weight_name)
            reference = self._reference(item)
            support[model_id][reference.evidence_id] = reference

        raw_description = values.get("business_description")
        description = "" if raw_description is None else str(raw_description).strip().lower()
        description_rules = (
            ("distributor", "description_general_weight", ("distribution", "distributor", "分销", "流通")),
            ("manufacturing", "description_general_weight", ("manufacturing", "manufacturer", "制造", "生产")),
            ("software", "description_specialized_weight", ("software", "saas", "subscription", "cloud", "软件", "订阅")),
            ("consumer", "description_specialized_weight", ("consumer", "brand", "retail", "food", "beverage", "消费", "品牌", "零售")),
            ("resource", "description_specialized_weight", ("mining", "resource", "commodity", "copper", "coal", "oil", "资源", "矿业", "煤炭", "油气")),
            ("project", "description_specialized_weight", ("epc", "engineering project", "system integration", "工程", "项目制", "系统集成")),
            ("financial", "description_specialized_weight", ("bank", "insurance", "brokerage", "financial services", "deposits", "loans", "银行", "保险", "券商")),
            ("hospitality", "description_specialized_weight", ("hotel", "hospitality", "lodging", "accommodation", "酒店", "住宿")),
        )
        for model_id, weight, terms in description_rules:
            if description and any(term in description for term in terms):
                add(model_id, weight, "business_description")

        inventory = values.get("inventory_to_revenue")
        fixed_assets = values.get("fixed_asset_to_assets")
        gross_margin = values.get("gross_margin")
        lease_values = (
            _numeric(values.get("right_of_use_assets_to_assets")),
            _numeric(values.get("lease_liabilities_to_assets")),
        )
        lease_heavy = any(
            value is not None and value >= threshold("lease_materiality")
            for value in lease_values
        )
        inventory_value = _numeric(inventory)
        fixed_assets_value = _numeric(fixed_assets)
        gross_margin_value = _numeric(gross_margin)
        if (
            inventory_value is not None
            and inventory_value >= threshold("inventory_to_revenue_distributor")
            and self._is_annual_period(records.get("inventory_to_revenue"))
        ):
            add("distributor", "inventory_signal_weight", "inventory_to_revenue")
        if (
            fixed_assets_value is not None
            and fixed_assets_value <= threshold("asset_light_maximum")
            and not lease_heavy
        ):
            add("distributor", "asset_light_signal_weight", "fixed_asset_to_assets")
        if (
            gross_margin_value is not None
            and gross_margin_value <= threshold("low_gross_margin_maximum")
        ):
            add("distributor", "low_margin_signal_weight", "gross_margin")
        if (
            fixed_assets_value is not None
            and fixed_assets_value >= threshold("asset_heavy_minimum")
        ):
            add("manufacturing", "asset_heavy_signal_weight", "fixed_asset_to_assets")
        if (
            gross_margin_value is not None
            and gross_margin_value >= threshold("manufacturing_margin_minimum")
        ):
            add("manufacturing", "manufacturing_margin_weight", "gross_margin")

        if not scores:
            status: ClassificationStatus = (
                "UNSUPPORTED_TAXONOMY" if description else "INSUFFICIENT_EVIDENCE"
            )
            reason = (
                "NO_SUPPORTED_BUSINESS_MODEL_MATCH"
                if description
                else "NO_USABLE_BUSINESS_MODEL_EVIDENCE"
            )
            return BusinessModelProfile(
                company_id=company_id,
                primary_model="unknown",
                classification_status=status,
                classification_reason=reason,
                lease_heavy=lease_heavy,
                router_version=self.version,
            )

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        top_model, top_score = ranked[0]
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
        gap = max(0.0, top_score - runner_up_score)
        unresolved = (
            len(ranked) > 1 and gap < threshold("minimum_candidate_gap")
        )
        primary_model = "unknown" if unresolved else top_model
        status = "UNRESOLVED" if unresolved else "CLASSIFIED"
        reason = (
            "CANDIDATE_GAP_BELOW_POLICY"
            if unresolved
            else "SUPPORTED_BUSINESS_MODEL_SIGNAL"
        )
        used = {
            reference.evidence_id: reference
            for candidate_support in support.values()
            for reference in candidate_support.values()
        }
        coverage = min(1.0, len(used) / 4)
        if coverage >= threshold("high_confidence_coverage"):
            confidence_band: ConfidenceBand = "HIGH"
        elif coverage >= threshold("medium_confidence_coverage"):
            confidence_band = "MEDIUM"
        else:
            confidence_band = "LOW"
        top_positive = tuple(
            support[top_model][key] for key in sorted(support[top_model])
        )
        top_counter = tuple(
            reference
            for model_id, candidate_support in sorted(support.items())
            if model_id != top_model
            for _, reference in sorted(candidate_support.items())
            if reference.evidence_id not in support[top_model]
        )
        candidates = tuple(
            RoutingCandidate(
                model_id=model_id,
                rule_match_score=score,
                positive_evidence=tuple(
                    candidate_support[key] for key in sorted(candidate_support)
                ),
                counter_evidence=tuple(
                    reference
                    for other_model, other_support in sorted(support.items())
                    if other_model != model_id
                    for key, reference in sorted(other_support.items())
                    if key not in candidate_support
                ),
            )
            for model_id, score in ranked
            for candidate_support in (support[model_id],)
        )
        secondary = tuple(
            model_id
            for model_id, score in ranked[1:]
            if score >= threshold("secondary_score_minimum")
        )
        return BusinessModelProfile(
            company_id=company_id,
            primary_model=primary_model,
            secondary_models=secondary,
            rule_match_score=top_score,
            usable_evidence_coverage=coverage,
            confidence_band=confidence_band,
            ambiguity=max(0.0, 1.0 - min(1.0, gap)),
            candidates=candidates,
            positive_evidence=top_positive,
            counter_evidence=top_counter,
            evidence_refs=tuple(used[key] for key in sorted(used)),
            router_version=self.version,
            classification_status=status,
            classification_reason=reason,
            lease_heavy=lease_heavy,
        )


__all__ = ["BusinessModelRouter"]
