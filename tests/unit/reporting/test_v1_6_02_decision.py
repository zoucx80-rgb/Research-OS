from __future__ import annotations

from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef
from research_os.decision.models import (
    DecisionDerivation,
    DecisionDimensionAssessment,
)
from research_os.reporting.projectors import project_artifact


def test_decision_projection_explains_support_blockers_and_upgrade_evidence() -> None:
    reference = EvidenceRef(
        evidence_id="ev:decision:report",
        revision=1,
        content_fingerprint="a" * 64,
    )
    derivation = DecisionDerivation(
        domain_status="SUPPORTED",
        rule_id="material_funding_risk",
        rule_version="2.0.2",
        input_states=(
            DecisionDimensionAssessment(
                dimension="funding_loop",
                state="debt_funded",
                availability="AVAILABLE",
                artifact_ids=("capital.funding_loop",),
                evidence_refs=(reference,),
            ),
        ),
        output_state="RISK_REVIEW",
        supporting_reason_codes=("QUANTITATIVE_FUNDING_BRIDGE",),
        blocking_reason_codes=("MATERIAL_FUNDING_RISK",),
        evidence_refs=(reference,),
    )

    payload = project_artifact("decision.derivation", derivation).payload

    assert payload["形成规则"] == "material_funding_risk@2.0.2"
    assert payload["支持因素"]
    assert payload["阻塞因素"]
    assert payload["证据置信度"] if "证据置信度" in payload else Decimal("0") == 0
    assert not any(term in str(payload) for term in ("下单", "买入数量", "目标仓位"))
