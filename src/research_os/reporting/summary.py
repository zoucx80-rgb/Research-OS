from pydantic import BaseModel, Field, model_validator

from research_os.completion.models import FinalStatus, ModuleStatus
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
    expectation_evidence_status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
    valuation_execution_status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
    core_contradiction: str | None = None
    sections: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_completed_report(self):
        if self.final_status != "COMPLETE":
            return self
        if self.decision_state is None:
            raise ValueError("a COMPLETE report requires a legal ResearchDecisionState")
        if self.expectation_evidence_status != "PASS":
            raise ValueError("a COMPLETE report requires validated expectation evidence")
        if self.valuation_execution_status != "PASS":
            raise ValueError("a COMPLETE report requires validated valuation execution")
        return self


class DecisionSummaryBuilder:
    SECTIONS = ["Decision", "Drivers", "FinancialCapital", "ExpectationsForecast", "Valuation", "Evidence"]

    def build(self, c: dict) -> DecisionSummary:
        claims = c.get("supporting_claim_ids", [])
        contradiction = c.get("core_contradiction") if claims else None
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
            final_status=c.get("final_status", "INCOMPLETE"),
            expectation_evidence_status=c.get("expectation_evidence_status", "INSUFFICIENT_EVIDENCE"),
            valuation_execution_status=c.get("valuation_execution_status", "INSUFFICIENT_EVIDENCE"),
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
