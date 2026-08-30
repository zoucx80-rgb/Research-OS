from datetime import datetime, timezone

from research_os.reporting import (
    EvidenceNoteBlock,
    HumanReadableCoverageGap,
    HumanReadableDecisionSummary,
    HumanReadableMonitoring,
    HumanReadableQuestionAssessment,
    HumanReadableResearchView,
    ResearchReportComposer,
    SemanticValue,
)


def _semantic(code: str, label: str | None = None) -> SemanticValue:
    return SemanticValue(label=label or code, explanation=f"{code} explanation", code=code)


def _summary() -> HumanReadableDecisionSummary:
    return HumanReadableDecisionSummary.model_construct(
        company_id="synthetic:monitoring-evidence",
        business_model=_semantic("hospitality", "酒店业务"),
        primary_thesis="等待关键经营证据验证扩张质量。",
        thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
        fundamental_state=_semantic("UNCERTAIN", "基本面方向尚不确定"),
        expectation_state=_semantic("MIXED", "市场预期信号混合"),
        valuation_state=_semantic("UNRELIABLE", "估值结果可靠性不足"),
        evidence_confidence=0.62,
        top_drivers=["收入"],
        top_risks=[],
        next_verification_event="下一次经营数据披露",
        research_os_version="1.5.5",
        decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
        final_status=_semantic("COMPLETE", "研究流程完整"),
        blocking_modules=[],
        module_statuses={},
        expectation_evidence_status=_semantic("PASS", "通过"),
        valuation_execution_status=_semantic("INSUFFICIENT_EVIDENCE", "证据不足"),
        core_contradiction=None,
        sections=[],
        presentation_version="semantic-report@1.0.0",
    )


def _view(
    *,
    questions=None,
    coverage_gaps=None,
    monitoring=None,
    presentation_limitations=None,
) -> HumanReadableResearchView:
    return HumanReadableResearchView.model_construct(
        company_id="synthetic:monitoring-evidence",
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        repository="zoucx80-rgb/Research-OS",
        commit_sha="d" * 40,
        research_os_version="1.5.5",
        core_api_version="1.0",
        business_model=_semantic("hospitality", "酒店业务"),
        classification_status=_semantic("classified", "业务模型已识别"),
        classification_reason=None,
        secondary_business_models=[],
        industry_plugins=[],
        methodology_plugins=[],
        coverage_gaps=list(coverage_gaps or []),
        report_contributions=[],
        question_assessments=list(questions or []),
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
        monitoring=monitoring,
        presentation_limitations=list(presentation_limitations or []),
        decision_summary=_summary(),
        presentation_version="professional-research-view@1.3.0",
    )


def test_monitoring_copies_only_canonical_conditions_without_inventing_thresholds():
    monitoring = HumanReadableMonitoring(
        next_verification_event="2026Q3经营数据披露",
        conviction_up_conditions=[],
        thesis_broken_conditions=["经营现金流连续转负"],
        key_metrics=["经营现金流"],
    )

    doc = ResearchReportComposer().compose(_view(monitoring=monitoring))
    section = next(section for section in doc.sections if section.section_id == "monitoring")
    block = section.blocks[0]

    assert block.conviction_up_conditions == []
    assert block.thesis_broken_conditions == ["经营现金流连续转负"]
    assert block.key_metrics == ["经营现金流"]


def test_main_body_evidence_note_is_concise_and_raw_ids_stay_in_audit_appendix():
    raw_id = "ev-sensitive-raw-001"
    question = HumanReadableQuestionAssessment(
        question_id="q1",
        question="门店成熟度是否改善？",
        status=_semantic("ANSWERED", "已回答"),
        answer="已有规范化证据支持回答。",
        evidence_ids=[raw_id],
    )

    doc = ResearchReportComposer().compose(_view(questions=[question]))
    main_body = str([section.model_dump(mode="json") for section in doc.sections])
    notes = [
        block
        for section in doc.sections
        for block in section.blocks
        if isinstance(block, EvidenceNoteBlock)
    ]

    assert raw_id in doc.audit_appendix.evidence_ids
    assert raw_id not in main_body
    assert notes
    assert len(notes[0].text) <= 80
    assert "审计附录" in notes[0].text
    assert notes[0].evidence_ids == []


def test_unresolved_gaps_are_classified_without_collapsing_semantics():
    questions = [
        HumanReadableQuestionAssessment(
            question_id="evidence-gap",
            question="门店成熟度是否改善？",
            status=_semantic("EVIDENCE_MISSING", "证据缺失"),
            missing_evidence_keys=["store_maturity"],
        ),
        HumanReadableQuestionAssessment(
            question_id="capability-gap",
            question="RevPAR结构如何？",
            status=_semantic("CAPABILITY_MISSING", "能力缺失"),
            missing_capabilities=["hospitality.revpar"],
        ),
        HumanReadableQuestionAssessment(
            question_id="not-applicable",
            question="制造产能利用率如何？",
            status=_semantic("NOT_APPLICABLE", "不适用"),
        ),
    ]
    coverage_gap = HumanReadableCoverageGap(
        gap_type=_semantic("industry_strategy", "缺少专业行业策略覆盖"),
        business_model=_semantic("hospitality", "酒店业务"),
        reason=_semantic("NO_COMPATIBLE_INDUSTRY_PLUGIN", "缺少兼容行业插件"),
        affected_capabilities=["industry_strategy"],
        fallback_available=True,
        missing_capability="industry_strategy",
    )

    doc = ResearchReportComposer().compose(
        _view(
            questions=questions,
            coverage_gaps=[coverage_gap],
            presentation_limitations=["租赁调整后的资本回报分析尚未实现。"],
        )
    )
    section = next(section for section in doc.sections if section.section_id == "research-gaps")
    block = section.blocks[0]

    assert block.block_type == "gap_classification"
    assert block.evidence_missing == ["门店成熟度是否改善？"]
    assert "RevPAR结构如何？" in block.capability_missing
    assert "缺少兼容行业插件" in block.capability_missing
    assert block.not_applicable == ["制造产能利用率如何？"]
    assert block.presentation_or_deferred == ["租赁调整后的资本回报分析尚未实现。"]
