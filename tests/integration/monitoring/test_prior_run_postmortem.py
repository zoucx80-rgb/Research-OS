from __future__ import annotations

import pytest
from pydantic import ValidationError

from research_os.contracts.evidence import EvidenceRef
from research_os.monitoring.attribution import (
    AnalysisMethodRef,
    AttributionRequest,
    PriorStatementRef,
    ProcessChangeCandidate,
    ProcessChangeTarget,
)
from research_os.monitoring.postmortem import PostMortemService


def _ref(name: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=name,
        revision=1,
        content_fingerprint="f" * 64,
    )


def _request() -> AttributionRequest:
    return AttributionRequest(
        attribution_id="attribution:driver:revenue",
        proposed_category="DRIVER",
        prior_statement=PriorStatementRef(
            run_id="run:prior",
            artifact_key="forecast.revenue",
            statement_key="revenue:2026Q1",
            statement="Volume growth will offset price normalization.",
            evidence_refs=(_ref("prior:statement"),),
        ),
        realized_evidence_refs=(_ref("realized:revenue"),),
        analysis_method=AnalysisMethodRef(
            method_id="revenue_driver_bridge",
            method_version="1.0.0",
            description="Decompose revenue error into volume and price drivers.",
        ),
        rationale="Volume was the material forecast miss.",
    )


def test_prior_run_postmortem_preserves_attribution_and_specific_change_target() -> None:
    candidate = ProcessChangeCandidate(
        candidate_id="change:revenue-volume-metric",
        target=ProcessChangeTarget(
            target_type="METRIC",
            target_id="revenue_volume_growth",
        ),
        rationale="Add an availability-aware volume-growth input.",
        attribution_ids=("attribution:driver:revenue",),
    )
    postmortem = PostMortemService().build(
        prior_run_id="run:prior",
        current_run_id="run:current",
        requests=(_request(),),
        process_change_candidates=(candidate,),
    )

    assert postmortem.attributions[0].prior_statement.statement_key == "revenue:2026Q1"
    assert postmortem.attributions[0].realized_evidence_refs
    assert postmortem.attributions[0].analysis_method.method_id == "revenue_driver_bridge"
    assert postmortem.process_change_candidates[0].target.target_type == "METRIC"
    assert postmortem.model_dump(mode="json")["category_counts"] == {"DRIVER": 1}


def test_process_change_candidate_cannot_be_generic() -> None:
    with pytest.raises(ValidationError, match="target"):
        ProcessChangeTarget(target_type="PROCEDURE", target_id=" ")


def test_process_change_cannot_be_justified_by_unknown_attribution() -> None:
    request = _request().model_copy(update={"realized_evidence_refs": ()})
    candidate = ProcessChangeCandidate(
        candidate_id="change:unsupported",
        target=ProcessChangeTarget(
            target_type="PROCEDURE",
            target_id="forecast_review",
        ),
        rationale="This change has no mature outcome evidence yet.",
        attribution_ids=(request.attribution_id,),
    )

    with pytest.raises(ValueError, match="UNKNOWN"):
        PostMortemService().build(
            prior_run_id="run:prior",
            current_run_id="run:current",
            requests=(request,),
            process_change_candidates=(candidate,),
        )
