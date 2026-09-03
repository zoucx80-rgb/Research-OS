from research_os.contracts.evidence import EvidenceRef
from research_os.monitoring.attribution import (
    AnalysisMethodRef,
    AttributionRequest,
    PriorStatementRef,
)
from research_os.monitoring.postmortem import PostMortemService


def test_postmortem_summarizes_hit_miss_and_unknown_attributions() -> None:
    reference = EvidenceRef(
        evidence_id="realized:one",
        revision=1,
        content_fingerprint="1" * 64,
    )
    statement = PriorStatementRef(
        run_id="run:prior",
        artifact_key="thesis.primary",
        statement_key="thesis:growth",
        statement="Growth quality should improve.",
        evidence_refs=(reference,),
    )
    method = AnalysisMethodRef(
        method_id="thesis_outcome_check",
        method_version="1.0.0",
        description="Compare the thesis falsifier with realized evidence.",
    )
    postmortem = PostMortemService().build(
        prior_run_id="run:prior",
        current_run_id="run:current",
        requests=(
            AttributionRequest(
                attribution_id="attribution:one",
                proposed_category="ASSUMPTION",
                prior_statement=statement,
                realized_evidence_refs=(reference,),
                analysis_method=method,
                rationale="The conversion assumption failed.",
            ),
            AttributionRequest(
                attribution_id="attribution:unknown",
                proposed_category="MODEL",
                prior_statement=statement,
                realized_evidence_refs=(),
                analysis_method=method,
                rationale="Outcome evidence has not matured.",
            ),
        ),
    )

    assert postmortem.attributed_count == 1
    assert postmortem.unknown_count == 1
    assert postmortem.category_counts == {"ASSUMPTION": 1, "UNKNOWN": 1}
