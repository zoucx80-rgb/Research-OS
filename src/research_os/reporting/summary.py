from pydantic import BaseModel, Field
class DecisionSummary(BaseModel):
    company_id: str
    business_model: str
    primary_thesis: str
    thesis_state: str
    fundamental_state: str
    expectation_state: str
    valuation_state: str
    evidence_confidence: str|float
    top_drivers: list[str]
    top_risks: list[str]
    next_verification_event: str
    research_os_version: str
    core_contradiction: str|None=None
    sections: list[str]=Field(default_factory=list)
class DecisionSummaryBuilder:
    SECTIONS=["Decision","Drivers","FinancialCapital","ExpectationsForecast","Valuation","Evidence"]
    def build(self,c:dict)->DecisionSummary:
        claims=c.get("supporting_claim_ids",[])
        contradiction=c.get("core_contradiction") if claims else None
        return DecisionSummary(company_id=c["company_id"],business_model=c["business_model"],primary_thesis=c["primary_thesis"],
            thesis_state=c["thesis_state"],fundamental_state=c["fundamental_state"],expectation_state=c["expectation_state"],valuation_state=c["valuation_state"],
            evidence_confidence=c["evidence_confidence"],top_drivers=list(c.get("top_drivers",[]))[:3],top_risks=list(c.get("top_risks",[]))[:3],
            next_verification_event=c["next_verification_event"],research_os_version=c.get("research_os_version","1.1.0"),core_contradiction=contradiction,sections=self.SECTIONS)
