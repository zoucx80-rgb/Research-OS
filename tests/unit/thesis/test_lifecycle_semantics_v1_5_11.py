from datetime import date, datetime, timezone

from research_os.domain.evidence import Evidence
from research_os.drivers.graph import DriverGraph
from research_os.thesis.models import Falsifier, Thesis
from research_os.thesis.semantic_service_v1_5_11 import SemanticThesisService


def metric(name, value):
    return Evidence(
        evidence_id=f"ev:{name}",
        company_id="GENERIC",
        evidence_type="calculated_metric",
        source_table=name,
        value=value,
        publish_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )


def graph(evidence):
    return DriverGraph.build("GENERIC", ["manufacturing"], evidence)


def test_mixed_evidence_without_prior_thesis_is_unresolved_not_weakening():
    evidence = [metric("revenue_growth", 0.15), metric("margin_change", -0.03), metric("ocf", 100.0)]
    theses = SemanticThesisService().evaluate("GENERIC", evidence, graph(evidence))
    assert len(theses) == 1
    thesis = theses[0]
    assert thesis.status == "unresolved"
    assert thesis.falsifiers == []
    assert thesis.resolution_conditions
    assert thesis.conviction_up_conditions
    assert thesis.deterioration_conditions


def test_explicit_prior_directional_thesis_can_weaken_under_contradictory_evidence():
    prior = Thesis(
        thesis_id="GENERIC:prior",
        company_id="GENERIC",
        title="Margin recovery",
        statement="Margins recover while growth converts to cash.",
        mechanism="Pricing and mix support margin and cash conversion.",
        anti_thesis="Margin recovery reverses and cash conversion deteriorates.",
        status="active",
        falsifiers=[Falsifier(metric="margin_change", operator="<", threshold=0)],
        next_check_date=date(2026, 10, 31),
    )
    evidence = [metric("revenue_growth", 0.08), metric("margin_change", -0.02), metric("ocf", 50.0)]
    theses = SemanticThesisService(prior_theses=(prior,)).evaluate("GENERIC", evidence, graph(evidence))
    assert len(theses) == 1
    assert theses[0].status == "weakening"
    assert theses[0].thesis_id == prior.thesis_id


def test_unresolved_thesis_does_not_invent_thesis_broken_condition():
    evidence = [metric("revenue_growth", 0.10), metric("margin_change", -0.01), metric("ocf", 10.0)]
    thesis = SemanticThesisService().evaluate("GENERIC", evidence, graph(evidence))[0]
    assert thesis.status == "unresolved"
    assert thesis.falsifiers == []
    assert thesis.triggered_falsifiers == []
