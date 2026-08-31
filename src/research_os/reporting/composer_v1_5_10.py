from __future__ import annotations

from typing import Any

from research_os.reporting.composer_v1_5_09 import ResearchReportComposer as _PreviousComposer
from research_os.reporting.document import ResearchCompletenessBlock, ReportSection


class ResearchReportComposer(_PreviousComposer):
    """v1.5.10 editorial composition over canonical completeness artifacts."""

    version = "research-report-composer@1.3.0"

    _SECTIONS = (
        ("financial.time_series", "financial-trends", "财务趋势", "financial_time_series"),
        ("research.operating_evidence", "operating-evidence", "经营证据", "operating_evidence"),
        ("cash_flow.quality_bridge", "cash-flow-quality", "现金流质量", "cash_flow_quality"),
        ("peers.comparables", "peer-comparison", "同行与产品线比较", "peer_comparison"),
        ("expectation.consensus_distribution", "consensus-dispersion", "一致预期分布", "consensus_distribution"),
        ("scenario.sensitivities", "sensitivity-scenarios", "敏感性与情景", "sensitivity_scenarios"),
        ("monitoring.prior_run_review", "prior-run-review", "上期判断回顾", "prior_run_review"),
        ("methodology.disclosure", "methodology-disclosure", "方法说明", "methodology_disclosure"),
    )

    @classmethod
    def _collect_ids(cls, value: Any, key_name: str) -> list[str]:
        if value is None:
            return []
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="python")
        if isinstance(value, dict):
            result: list[str] = []
            for key, item in value.items():
                if key == key_name and isinstance(item, (list, tuple)):
                    result.extend(str(identifier) for identifier in item if identifier)
                else:
                    result.extend(cls._collect_ids(item, key_name))
            return result
        if isinstance(value, (list, tuple)):
            result: list[str] = []
            for item in value:
                result.extend(cls._collect_ids(item, key_name))
            return result
        return []

    @classmethod
    def _evidence_ids(cls, view) -> list[str]:
        ids = list(super()._evidence_ids(view))
        ids.extend(cls._collect_ids(getattr(view, "research_completeness", {}), "evidence_ids"))
        return cls._dedup(ids)

    @classmethod
    def _assumption_ids(cls, view) -> list[str]:
        ids = list(super()._assumption_ids(view))
        ids.extend(cls._collect_ids(getattr(view, "research_completeness", {}), "assumption_ids"))
        return cls._dedup(ids)

    @classmethod
    def _completeness_sections(cls, view) -> list[ReportSection]:
        data = dict(getattr(view, "research_completeness", {}) or {})
        sections: list[ReportSection] = []
        for artifact_id, section_id, title, kind in cls._SECTIONS:
            value = data.get(artifact_id)
            if value in (None, [], (), {}):
                continue
            sections.append(
                ReportSection(
                    section_id=section_id,
                    title=title,
                    blocks=[
                        ResearchCompletenessBlock(
                            kind=kind,
                            payload=cls._display_payload(value),
                        )
                    ],
                )
            )

        rules = data.get("monitoring.rules")
        calendar = data.get("monitoring.verification_calendar")
        if rules not in (None, [], (), {}) or calendar not in (None, [], (), {}):
            sections.insert(
                max(len(sections) - 2, 0),
                ReportSection(
                    section_id="monitoring-calendar",
                    title="监控规则与验证日历",
                    blocks=[
                        ResearchCompletenessBlock(
                            kind="monitoring_calendar",
                            payload=cls._display_payload(
                                {
                                    "rules": rules or [],
                                    "events": calendar or [],
                                }
                            ),
                        )
                    ],
                ),
            )
        return sections

    def _sections(self, view) -> list[ReportSection]:
        sections = list(super()._sections(view))
        additions = self._completeness_sections(view)
        if not additions:
            return sections
        anchors = {
            "state-provenance",
            "research-gaps",
            "material-limitations",
            "evidence-traceability",
        }
        insert_at = next(
            (index for index, section in enumerate(sections) if section.section_id in anchors),
            len(sections),
        )
        return [*sections[:insert_at], *additions, *sections[insert_at:]]
