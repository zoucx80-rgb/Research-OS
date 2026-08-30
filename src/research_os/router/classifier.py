import re
from collections import defaultdict

from research_os.domain.evidence import Evidence

from .models import BusinessModelProfile


class BusinessModelRouter:
    version = "router@1.2.0"
    LEASE_MATERIALITY_THRESHOLD = 0.20

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
                "h1",
                "h2",
                "q1",
                "q2",
                "q3",
                "q4",
                "interim",
                "半年度",
                "半年",
                "季度",
            )
        ):
            return False
        if period in {"annual", "year", "yearly", "年度", "年报"}:
            return True
        if re.fullmatch(r"20\d{2}", period):
            return True
        if re.fullmatch(r"fy20\d{2}", period):
            return True
        if re.fullmatch(r"20\d{2}(?:fy|a|annual)", period):
            return True
        return False

    def classify(self, company_id: str, evidence: list[Evidence]) -> BusinessModelProfile:
        records = {e.source_table or e.evidence_id: e for e in evidence}
        values = {key: item.value for key, item in records.items()}
        scores = defaultdict(float)

        raw_desc = values.get("business_description")
        desc = "" if raw_desc is None else str(raw_desc).strip().lower()
        if any(x in desc for x in ("distribution", "distributor", "分销", "流通")):
            scores["distributor"] += 0.5
        if any(x in desc for x in ("manufacturing", "manufacturer", "制造", "生产")):
            scores["manufacturing"] += 0.5
        if any(x in desc for x in ("software", "saas", "subscription", "cloud", "软件", "订阅")):
            scores["software"] += 0.7
        if any(x in desc for x in ("consumer", "brand", "retail", "food", "beverage", "消费", "品牌", "零售")):
            scores["consumer"] += 0.7
        if any(x in desc for x in ("mining", "resource", "commodity", "copper", "coal", "oil", "资源", "矿业", "煤炭", "油气")):
            scores["resource"] += 0.7
        if any(x in desc for x in ("epc", "engineering project", "system integration", "工程", "项目制", "系统集成")):
            scores["project"] += 0.7
        if any(x in desc for x in ("bank", "insurance", "brokerage", "financial services", "deposits", "loans", "银行", "保险", "券商")):
            scores["financial"] += 0.7
        if any(x in desc for x in ("hotel", "hospitality", "lodging", "accommodation", "酒店", "住宿")):
            scores["hospitality"] += 0.7

        inv = values.get("inventory_to_revenue")
        fa = values.get("fixed_asset_to_assets")
        gm = values.get("gross_margin")
        rou = values.get("right_of_use_assets_to_assets")
        lease_liabilities = values.get("lease_liabilities_to_assets")
        lease_heavy = any(
            isinstance(value, (int, float)) and value >= self.LEASE_MATERIALITY_THRESHOLD
            for value in (rou, lease_liabilities)
        )

        if (
            isinstance(inv, (int, float))
            and inv >= 0.15
            and self._is_annual_period(records.get("inventory_to_revenue"))
        ):
            scores["distributor"] += 0.2
        if isinstance(fa, (int, float)) and fa <= 0.08 and not lease_heavy:
            scores["distributor"] += 0.15
        if isinstance(gm, (int, float)) and gm <= 0.10:
            scores["distributor"] += 0.15
        if isinstance(fa, (int, float)) and fa >= 0.20:
            scores["manufacturing"] += 0.25
        if isinstance(gm, (int, float)) and gm >= 0.15:
            scores["manufacturing"] += 0.15

        if scores:
            classification_status = "classified"
            classification_reason = "supported_business_model_signal"
        else:
            scores["unknown"] = 0.5
            if desc:
                classification_status = "unsupported_taxonomy"
                classification_reason = "no_supported_business_model_match"
            else:
                classification_status = "insufficient_evidence"
                classification_reason = "no_usable_business_model_evidence"

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary, score = ranked[0]
        secondary = [m for m, s in ranked[1:] if s >= 0.3]
        return BusinessModelProfile(
            company_id=company_id,
            primary_model=primary,
            secondary_models=secondary,
            confidence=min(1.0, max(0.5, score)),
            evidence_ids=[e.evidence_id for e in evidence],
            router_version=self.version,
            classification_status=classification_status,
            classification_reason=classification_reason,
            lease_heavy=lease_heavy,
        )
