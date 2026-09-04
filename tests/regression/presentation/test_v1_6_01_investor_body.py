from datetime import datetime, timezone

from research_os.reporting import (
    AuditArtifactLineage,
    MarkdownArtifactRenderer,
    ReportArtifactBlock,
    ReportSection,
    ResearchReportDocument,
)


def _document() -> ResearchReportDocument:
    return ResearchReportDocument(
        company_id="synthetic:v1.6.01:presentation",
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        research_os_version="1.6.01",
        core_api_version="2.0",
        plugin_api_version="2.0",
        snapshot_schema_version="2.0",
        execution_completion="COMPLETE",
        research_readiness="NOT_READY",
        semantic_fingerprint="a" * 64,
        sections=(
            ReportSection(
                section_id="decision",
                title="投资决策快照",
                artifacts=(
                    ReportArtifactBlock(
                        artifact_id="decision.record",
                        title="研究决策",
                        schema_version="2.0",
                        payload={
                            "状态": "风险审查",
                            "核心原因": "经营现金流为负；融资循环存在重大风险",
                        },
                    ),
                ),
            ),
            ReportSection(
                section_id="methodology",
                title="方法与限制",
                artifacts=(
                    ReportArtifactBlock(
                        artifact_id="methodology.disclosure",
                        title="研究限制",
                        schema_version="2.0",
                        payload={"限制": ["行业插件覆盖不足，相关行业 KPI 不做推断。"]},
                    ),
                ),
            ),
        ),
        audit_appendix=(
            AuditArtifactLineage(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="DecisionStateRecord",
                producer_ids=("core:portfolio-decision",),
                value_fingerprint="b" * 64,
            ),
        ),
    )


def test_investor_body_is_decision_first_and_has_no_machine_metadata_leakage() -> None:
    markdown = MarkdownArtifactRenderer().render(_document()).content
    body, audit = markdown.split("## 审计附录", maxsplit=1)

    assert body.index("## 投资决策快照") < body.index("## 方法与限制")
    for forbidden in (
        "Schema:",
        "source_url",
        "plugin_id",
        "NEGATIVE_OCF",
        "MATERIAL_FUNDING_RISK",
    ):
        assert forbidden not in body
    assert "a" * 64 not in body
    assert "b" * 64 not in body
    assert "b" * 64 in audit
    assert "<!-- section-id:decision -->" in body
    assert "- 执行完成度：执行完成" in body
    assert "- 研究就绪度：研究未就绪" in body
    assert "- 决策时点：2026-08-30" in body
    assert "2026-08-30T00:00:00+00:00" not in body
    assert "- **核心原因**：经营现金流为负；融资循环存在重大风险" in body
