from datetime import datetime, timezone

from research_os.reporting import HumanReadableDecisionSummary, HumanReadableResearchView, SemanticValue
from research_os.reporting.composer import ResearchReportComposer
from research_os.reporting.document import ResearchReportDocument


def _semantic(code: str, label: str | None = None) -> SemanticValue:
    return SemanticValue(label=label or code, explanation=f"{code} explanation", code=code)


def _decision_summary(*, decision_code="WAIT_FOR_CONFIRMATION", drivers=None, risks=None):
    return HumanReadableDecisionSummary.model_construct(
        company_id="synthetic:composer",
        business_model=_semantic("manufacturing", "制造业务"),
        primary_thesis="产品结构改善能否转化为可持续现金回报。",
        thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
        fundamental_state=_semantic("UNCERTAIN", "基本面方向尚不确定"),
        expectation_state=_semantic("MIXED", "市场预期信号混合"),
        valuation_state=_semantic("UNRELIABLE", "估值结果可靠性不足"),
        evidence_confidence=0.78,
        top_drivers=list(drivers or ["产品结构", "毛利率", "经营现金流"]),
        top_risks=list(risks or [_semantic("NEGATIVE_OCF", "经营现金流为负")]),
        next_verification_event="下一次重大信息披露",
        research_os_version="1.5.5",
        decision_state=_semantic(decision_code, "等待进一步确认"),
        final_status=_semantic("COMPLETE", "研究流程完整"),
        blocking_modules=[],
        module_statuses={},
        expectation_evidence_status=_semantic("PASS", "通过"),
        valuation_execution_status=_semantic("PASS", "通过"),
        core_contradiction=None,
        sections=[],
        presentation_version="semantic-report@1.0.0",
    )


def _view(*, decision_code="WAIT_FOR_CONFIRMATION", drivers=None, risks=None):
    return HumanReadableResearchView.model_construct(
        company_id="synthetic:composer",
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        repository="zoucx80-rgb/Research-OS",
        commit_sha="a" * 40,
        research_os_version="1.5.5",
        core_api_version="1.0",
        business_model=_semantic("manufacturing", "制造业务"),
        classification_status=_semantic("classified", "业务模型已识别"),
        classification_reason=None,
        secondary_business_models=[],
        industry_plugins=[],
        methodology_plugins=[],
        coverage_gaps=[],
        report_contributions=[],
        question_assessments=[],
        financial_sanity=None,
        kpi_metrics=[],
        capital_efficiency=None,
        funding_loop=None,
        driver_graph=None,
        theses=[],
        thesis_signal_assessment=None,
        expectation_quality=None,
        forecast_discipline=None,
        valuation_models=[],
        valuation_execution=None,
        state_provenance=[],
        next_verification_event=None,
        expectation_gap=None,
        valuation_result=None,
        monitoring=None,
        presentation_limitations=[],
        decision_summary=_decision_summary(
            decision_code=decision_code,
            drivers=drivers,
            risks=risks,
        ),
        presentation_version="professional-research-view@1.3.0",
    )


def test_composer_copies_canonical_decision_state_without_mutating_view():
    view = _view(decision_code="WAIT_FOR_CONFIRMATION")
    before = view.model_dump(mode="json")

    doc = ResearchReportComposer().compose(view)

    assert isinstance(doc, ResearchReportDocument)
    assert doc.decision_snapshot.decision_state.code == "WAIT_FOR_CONFIRMATION"
    assert doc.decision_snapshot.primary_thesis == view.decision_summary.primary_thesis
    assert view.model_dump(mode="json") == before


def test_empty_sections_are_omitted():
    doc = ResearchReportComposer().compose(_view())

    assert all(section.blocks for section in doc.sections)
    assert all(section.title.strip() for section in doc.sections)


def test_audit_metadata_is_outside_main_body():
    view = _view()
    doc = ResearchReportComposer().compose(view)

    main_body = str([section.model_dump(mode="json") for section in doc.sections])
    assert view.commit_sha not in main_body
    assert view.repository not in main_body
    assert doc.audit_appendix.repository == view.repository
    assert doc.audit_appendix.repository_commit == view.commit_sha
    assert doc.audit_appendix.presentation_version == view.presentation_version


def test_decision_snapshot_caps_drivers_and_risks_for_first_page():
    view = _view(
        drivers=[f"driver-{i}" for i in range(8)],
        risks=[_semantic(f"RISK_{i}", f"risk-{i}") for i in range(6)],
    )
    snapshot = ResearchReportComposer().compose(view).decision_snapshot

    assert 3 <= len(snapshot.material_drivers) <= 5
    assert 1 <= len(snapshot.material_risks) <= 3
    assert snapshot.evidence_confidence == 0.78
    assert snapshot.next_verification_event == "下一次重大信息披露"


def test_composer_rejects_raw_objects_instead_of_becoming_second_semantic_path():
    composer = ResearchReportComposer()

    try:
        composer.compose({"decision_state": "WAIT_FOR_CONFIRMATION"})
    except TypeError as exc:
        assert "HumanReadableResearchView" in str(exc)
    else:
        raise AssertionError("raw dict must not be accepted by ResearchReportComposer")
