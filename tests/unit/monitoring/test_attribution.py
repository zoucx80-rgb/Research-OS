from __future__ import annotations

import pytest

from research_os.contracts.evidence import EvidenceRef
from research_os.monitoring.attribution import (
    AnalysisMethodRef,
    AttributionRequest,
    PriorStatementRef,
    attribute_error,
)


def _ref(name: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=name,
        revision=1,
        content_fingerprint="e" * 64,
    )


def _request(category: str) -> AttributionRequest:
    return AttributionRequest(
        attribution_id=f"attribution:{category.lower()}",
        proposed_category=category,
        prior_statement=PriorStatementRef(
            run_id="run:prior",
            artifact_key="forecast.revenue",
            statement_key="revenue:2026Q1",
            statement="Revenue should grow 10%.",
            evidence_refs=(_ref("prior:revenue"),),
        ),
        realized_evidence_refs=(_ref("realized:revenue"),),
        analysis_method=AnalysisMethodRef(
            method_id="forecast_error_bridge",
            method_version="1.0.0",
            description="Compare the frozen prediction with the mature outcome.",
        ),
        rationale="The supplied diagnostic evidence supports this category.",
        exogenous_event=category == "EXOGENOUS",
    )


@pytest.mark.parametrize(
    "category",
    [
        "DATA",
        "BASIS",
        "FORMULA",
        "MODEL",
        "ASSUMPTION",
        "DRIVER",
        "TIMING",
        "EXOGENOUS",
        "PRESENTATION",
    ],
)
def test_supported_attribution_categories_are_explicit(category: str) -> None:
    assert attribute_error(_request(category)).category == category


def test_insufficient_realized_evidence_stays_unknown() -> None:
    request = _request("MODEL").model_copy(update={"realized_evidence_refs": ()})
    result = attribute_error(request)
    assert result.category == "UNKNOWN"
    assert "insufficient" in result.rationale.lower()


def test_exogenous_event_is_not_mislabeled_as_model_error() -> None:
    request = _request("MODEL").model_copy(update={"exogenous_event": True})
    result = attribute_error(request)
    assert result.category == "EXOGENOUS"
    assert result.proposed_category == "MODEL"
