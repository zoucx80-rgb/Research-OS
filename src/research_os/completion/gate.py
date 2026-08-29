from .models import ResearchCompletionInput, ResearchCompletionResult


REQUIRED_MODULES = (
    "Repository Preflight",
    "PIT Validation",
    "Evidence Lineage",
    "Financial Sanity",
    "Business Model Router",
    "KPI Pack",
    "Capital Efficiency",
    "Funding Loop",
    "Driver Graph",
    "Thesis",
    "Anti-Thesis",
    "Falsifiers",
    "Expectation Evidence",
    "Forecast Discipline",
    "Valuation Fitness",
    "Valuation Execution",
    "Decision State",
    "Next Verification Event",
    "Temporal Consistency",
)


_CAPABILITY_ALIASES = {
    "fundamental": "FUNDAMENTAL",
    "fundamentals": "FUNDAMENTAL",
    "expectation": "EXPECTATION",
    "expectation_gap": "EXPECTATION",
    "beat": "EXPECTATION",
    "miss": "EXPECTATION",
    "priced_in": "EXPECTATION",
    "priced in": "EXPECTATION",
    "forecast": "FORECAST",
    "valuation": "VALUATION",
    "target_price": "VALUATION",
    "target price": "VALUATION",
    "fair_value": "VALUATION",
    "fair value": "VALUATION",
    "decision": "DECISION",
    "decision_state": "DECISION",
    "decision state": "DECISION",
}
_VALID_CAPABILITIES = {"FUNDAMENTAL", "EXPECTATION", "FORECAST", "VALUATION", "DECISION"}


def normalize_claim_capabilities(values: list[str]) -> set[str]:
    capabilities: set[str] = set()
    for value in values:
        text = str(value).strip()
        upper = text.upper()
        if upper in _VALID_CAPABILITIES:
            capabilities.add(upper)
            continue
        alias = _CAPABILITY_ALIASES.get(text.lower())
        if alias is not None:
            capabilities.add(alias)
    return capabilities


class ResearchCompletionGate:
    def evaluate(self, item: ResearchCompletionInput) -> ResearchCompletionResult:
        blocking: list[str] = []
        capabilities = normalize_claim_capabilities(item.claimed_conclusions)
        for module in REQUIRED_MODULES:
            status = item.module_statuses.get(module)
            if status is None or status == "FAIL":
                blocking.append(module)
                continue
            if status == "INSUFFICIENT_EVIDENCE":
                if module == "Expectation Evidence":
                    if "EXPECTATION" in capabilities:
                        blocking.append(module)
                elif module == "Valuation Execution":
                    if "VALUATION" in capabilities:
                        blocking.append(module)
                else:
                    blocking.append(module)
            elif status == "NOT_APPLICABLE" and module not in {"Forecast Discipline"}:
                blocking.append(module)
        return ResearchCompletionResult(
            final_status="INCOMPLETE" if blocking else "COMPLETE",
            blocking_modules=blocking,
            module_statuses=dict(item.module_statuses),
        )
