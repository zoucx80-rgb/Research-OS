from .models import DecisionContext, DecisionStateRecord


class DecisionEngine:
    def evaluate(self, c: DecisionContext) -> DecisionStateRecord:
        reasons = []
        if c.evidence_confidence < .4 or not c.evidence_ids:
            state = "INSUFFICIENT_EVIDENCE"
            reasons.append("LOW_EVIDENCE_CONFIDENCE")
        elif c.thesis_state == "FALSIFIED":
            state = "THESIS_BROKEN"
            reasons.append("THESIS_FALSIFIED")
        elif c.material_risk or (
            c.fundamental_state == "DETERIORATING"
            and c.expectation_state in {"UNDER_EXPECTED", "MIXED"}
        ):
            state = "RISK_REVIEW"
            reasons.append("FUNDAMENTAL_RISK")
        elif (
            c.fundamental_state == "IMPROVING"
            and c.valuation_state == "CHEAP"
            and c.thesis_state == "STRENGTHENING"
            and c.expectation_state == "OVER_EXPECTED"
        ):
            state = "HIGH_CONVICTION_WATCH"
            reasons.append("MULTI_DIMENSION_CONFIRMATION")
        elif (
            c.fundamental_state == "IMPROVING"
            and c.valuation_state == "CHEAP"
            and c.thesis_state in {"ACTIVE", "STRENGTHENING"}
        ):
            state = "ACCUMULATION_CANDIDATE"
            reasons.append("CHEAP_AND_IMPROVING")
        elif (
            c.thesis_state in {"WEAKENING", "UNRESOLVED"}
            or c.fundamental_state == "UNCERTAIN"
        ):
            state = "WAIT_FOR_CONFIRMATION"
            reasons.append("CONFIRMATION_REQUIRED")
        else:
            state = "HOLD_AND_MONITOR"
            reasons.append("NO_MATERIAL_STATE_CHANGE")
        return DecisionStateRecord(
            company_id=c.company_id,
            state=state,
            decision_ts=c.decision_ts,
            evidence_ids=c.evidence_ids,
            claim_ids=c.claim_ids,
            reason_codes=reasons,
            research_os_version=c.research_os_version,
            fundamental_state=c.fundamental_state,
            valuation_state=c.valuation_state,
            expectation_state=c.expectation_state,
            thesis_state=c.thesis_state,
            evidence_confidence=c.evidence_confidence,
        )
