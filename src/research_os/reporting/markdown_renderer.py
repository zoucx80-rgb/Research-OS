from __future__ import annotations

import json
from typing import Any

from .models import MarkdownRenderResult, ResearchReportDocument


_LINEAGE_KEYS = frozenset(
    {
        "evidence_ref",
        "evidence_refs",
        "evidence_id",
        "evidence_ids",
        "assumption_ref",
        "assumption_refs",
        "assumption_id",
        "assumption_ids",
    }
)


def _visible(value: Any) -> Any:
    """Remove audit-only lineage and empty values from investor-visible content."""
    if isinstance(value, dict):
        return {
            str(key): projected
            for key, item in value.items()
            if str(key) not in _LINEAGE_KEYS
            and (projected := _visible(item)) not in (None, "", [], {}, ())
        }
    if isinstance(value, list):
        return [
            projected
            for item in value
            if (projected := _visible(item)) not in (None, "", [], {}, ())
        ]
    return value


def _label(value: object) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def _render_payload(value: Any, *, indent: int = 0) -> list[str]:
    value = _visible(value)
    if value in (None, "", [], {}, ()):
        return []
    prefix = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            projected = _visible(item)
            if projected in (None, "", [], {}, ()):
                continue
            if isinstance(projected, (dict, list)):
                lines.append(f"{prefix}- **{key}**")
                lines.extend(_render_payload(projected, indent=indent + 1))
            else:
                lines.append(f"{prefix}- **{key}**：{_label(projected)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            projected = _visible(item)
            if projected in (None, "", [], {}, ()):
                continue
            if isinstance(projected, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_render_payload(projected, indent=indent + 1))
            else:
                lines.append(f"{prefix}- {_label(projected)}")
        return lines
    return [f"{prefix}- {_label(value)}"]


class ResearchReportMarkdownRenderer:
    """Pure presentation renderer for the frozen v2 report document."""

    version = "research-report-markdown@2.0.0"

    def render(self, document: ResearchReportDocument) -> str:
        if not isinstance(document, ResearchReportDocument):
            raise TypeError("ResearchReportMarkdownRenderer.render requires ResearchReportDocument")
        lines = [
            f"# Research OS 专业研究报告｜{document.company_id}",
            "",
            f"- 决策时点：{document.decision_ts.isoformat()}",
            f"- 执行完成度：{document.execution_completion}",
            f"- 研究就绪度：{document.research_readiness}",
            "",
        ]
        for section in document.sections:
            lines.extend((f"## {section.title}", ""))
            for artifact in section.artifacts:
                lines.extend(
                    (
                        f"### {artifact.title}",
                        f"Schema: `{artifact.schema_version}`",
                        "",
                    )
                )
                rendered = _render_payload(artifact.payload)
                lines.extend(rendered or ["- 当前类型化产物未提供可展示值。"])
                lines.append("")

        lines.extend(
            (
                "## 审计附录",
                "",
                f"- Research OS：`{document.research_os_version}`",
                f"- Core API：`{document.core_api_version}`",
                f"- Plugin API：`{document.plugin_api_version}`",
                f"- Snapshot Schema：`{document.snapshot_schema_version}`",
                f"- Semantic Fingerprint：`{document.semantic_fingerprint}`",
                "",
            )
        )
        for audit_artifact in document.audit_appendix:
            lines.extend(
                (
                    f"### {audit_artifact.artifact_id}@{audit_artifact.schema_version}",
                    f"- Type：`{audit_artifact.type_id}`",
                    f"- Producers：{', '.join(audit_artifact.producer_ids) or '—'}",
                    f"- Value Fingerprint：`{audit_artifact.value_fingerprint}`",
                )
            )
            if audit_artifact.evidence_refs:
                lines.append("- Evidence lineage：")
                for reference in audit_artifact.evidence_refs:
                    lines.append(
                        "  - "
                        f"`{reference.evidence_id}` / revision `{reference.revision}` / "
                        f"fingerprint `{reference.content_fingerprint}`"
                    )
            else:
                lines.append("- Evidence lineage：—")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


class MarkdownArtifactRenderer:
    """Reporting-level Markdown artifact retaining the semantic fingerprint."""

    version = ResearchReportMarkdownRenderer.version

    def __init__(self, renderer: ResearchReportMarkdownRenderer | None = None) -> None:
        self._renderer = renderer or ResearchReportMarkdownRenderer()
        self.version = self._renderer.version

    def render(self, document: ResearchReportDocument) -> MarkdownRenderResult:
        if not isinstance(document, ResearchReportDocument):
            raise TypeError("MarkdownArtifactRenderer.render requires ResearchReportDocument")
        return MarkdownRenderResult(
            content=self._renderer.render(document),
            semantic_fingerprint=document.semantic_fingerprint,
            renderer_version=self.version,
        )
