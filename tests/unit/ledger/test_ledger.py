from datetime import datetime, timezone
import pytest
from research_os.ledger.service import EvidenceLedger, ClaimValidationError, Claim


def test_material_claim_requires_evidence():
    with pytest.raises(ClaimValidationError):
        EvidenceLedger().add_claim(
            Claim(
                claim_id="c1",
                company_id="X",
                claim_text="Growth is debt funded",
                claim_type="risk",
                confidence_grade="B",
                evidence_ids=[],
            )
        )


def test_expired_claim_is_not_current():
    l = EvidenceLedger()
    l.add_claim(
        Claim(
            claim_id="c",
            company_id="X",
            claim_text="x",
            claim_type="risk",
            confidence_grade="B",
            evidence_ids=["e"],
            valid_until=datetime(2026, 9, 1, tzinfo=timezone.utc),
            next_verification_event="next quarterly report",
        )
    )
    assert l.current_claims("X", datetime(2026, 9, 30, tzinfo=timezone.utc)) == []


def test_material_research_conclusion_requires_expiry_and_next_verification():
    with pytest.raises(ClaimValidationError):
        EvidenceLedger().add_claim(
            Claim(
                claim_id="timeless",
                company_id="X",
                claim_text="Growth is debt funded",
                claim_type="risk",
                confidence_grade="B",
                evidence_ids=["e1"],
            )
        )
