from pydantic import BaseModel, Field

from research_os.completion.models import FinalStatus, ModuleStatus, ResearchCompletionResult
from research_os.decision.models import ResearchDecisionState


class DecisionSummary(BaseModel):
    company_id: str
    business_model: str
    primary_thesis: str
    thesis_state: str
    fundamental_state: str
    expectation_state: str
    valuation_state: str
    evidence_confidence: str | float
    top_drivers: list[str]
    top_risks: list[str]
    next_verification_event: str
    research_os_version: str
    decision_state: ResearchDecisionState | None = None
    final_status: FinalStatus = "INCOMPLETE"
    blocking_modules: list[str] = Field(default_factory=list)
    module_statuses: dict[str, ModuleStatus] = Field(default_factory=dict)
    expectation_evidence_status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
    valuation_execution_status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
    core_contradiction: str | None = None
    sections: list[str] = Field(default_factory=list)


class DecisionSummaryBuilder:
    SECTIONS = ["Decision", "Drivers", "FinancialCapital", "ExpectationsForecast", "Valuation", "Evidence"]

    def build(self, c: dict) -> DecisionSummary:
        claims = c.get("supporting_claim_ids", [])
        contradiction = c.get("core_contradiction") if claims else None
        completion_raw = c.get("completion")
        completion = None
        if completion_raw is not None:
            completion = completion_raw if isinstance(completion_raw, ResearchCompletionResult) else ResearchCompletionResult.model_validate(completion_raw)

        if completion is not None:
            final_status = completion.final_status
            blocking_modules = list(completion.blocking_modules)
            module_statuses = dict(completion.module_statuses)
            expectation_status = module_statuses.get("Expectation Evidence", "INSUFFICIENT_EVIDENCE")
            valuation_execution_status = module_statuses.get("Valuation Execution", "INSUFFICIENT_EVIDENCE")
        else:
            final_status = c.get("final_status", "INCOMPLETE")
            blocking_modules = list(c.get("blocking_modules", []))
            module_statuses = dict(c.get("module_statuses", {}))
            expectation_status = c.get("expectation_evidence_status", "INSUFFICIENT_EVIDENCE")
            valuation_execution_status = c.get("valuation_execution_status", "INSUFFICIENT_EVIDENCE")

        return DecisionSummary(
            company_id=c["company_id"],
            business_model=c["business_model"],
            primary_thesis=c["primary_thesis"],
            thesis_state=c["thesis_state"],
            fundamental_state=c["fundamental_state"],
            expectation_state=c["expectation_state"],
            valuation_state=c["valuation_state"],
            evidence_confidence=c["evidence_confidence"],
            top_drivers=list(c.get("top_drivers", []))[:3],
            top_risks=list(c.get("top_risks", []))[:3],
            next_verification_event=c["next_verification_event"],
            research_os_version=c.get("research_os_version", "1.2.0"),
            decision_state=c.get("decision_state"),
            final_status=final_status,
            blocking_modules=blocking_modules,
            module_statuses=module_statuses,
            expectation_evidence_status=expectation_status,
            valuation_execution_status=valuation_execution_status,
            core_contradiction=contradiction,
            sections=self.SECTIONS,
        )


class ResearchReportModel(BaseModel):
    sections: list[str]

    @classmethod
    def standard(cls):
        return cls(sections=[
            "Executive Decision Summary",
            "Business Model Classification",
            "Core Driver Tree",
            "Industry / Competitive Context",
            "Financial Quality",
            "Capital Efficiency & Funding Loop",
            "Segment / Product / Unit Economics",
            "Thesis",
            "Anti-Thesis",
            "Falsifiers",
            "Expectation Gap",
            "Forecast & Statistical Validation",
            "Valuation Router & Model Fitness",
            "Scenario Analysis",
            "Risk Register",
            "Monitoring Checklist",
            "Evidence Ledger",
            "Version & Data Snapshot",
        ])
