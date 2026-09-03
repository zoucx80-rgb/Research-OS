from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ClaimValidationError(ValueError):
    pass


class Claim(BaseModel):
    claim_id: str
    company_id: str
    claim_text: str
    claim_type: str
    confidence_grade: str
    evidence_ids: list[str] = Field(default_factory=list)
    formula_or_model: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    falsifiers: list[str] = Field(default_factory=list)
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None
    next_verification_event: str | None = None
    status: str = "active"


class EvidenceLedger:
    def __init__(self):
        self._claims = []

    def validate_claim(self, claim: Claim):
        if (
            claim.claim_type
            in {"risk", "thesis", "valuation", "statistical", "calculation", "fact"}
            and not claim.evidence_ids
        ):
            raise ClaimValidationError("material claim requires evidence")
        if claim.claim_type in {"risk", "thesis", "valuation", "statistical"} and (
            claim.valid_until is None or not claim.next_verification_event
        ):
            raise ClaimValidationError(
                "research conclusion requires validity horizon and next verification event"
            )
        return True

    def add_claim(self, claim: Claim):
        self.validate_claim(claim)
        self._claims.append(claim)
        return claim

    def current_claims(self, company_id: str, as_of: datetime):
        return [
            c
            for c in self._claims
            if c.company_id == company_id
            and c.valid_from <= as_of
            and (c.valid_until is None or c.valid_until >= as_of)
            and c.status == "active"
        ]
