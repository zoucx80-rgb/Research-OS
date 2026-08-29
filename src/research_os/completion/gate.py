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


class ResearchCompletionGate:
    def evaluate(self, item: ResearchCompletionInput) -> ResearchCompletionResult:
        blocking: list[str] = []
        claims = {value.lower() for value in item.claimed_conclusions}
        for module in REQUIRED_MODULES:
            status = item.module_statuses.get(module)
            if status is None or status == "FAIL":
                blocking.append(module)
                continue
            if status == "INSUFFICIENT_EVIDENCE":
                if module == "Expectation Evidence":
                    if claims & {"expectation", "expectation_gap", "beat", "miss", "priced_in"}:
                        blocking.append(module)
                elif module == "Valuation Execution":
                    if claims & {"valuation", "decision_state"}:
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
