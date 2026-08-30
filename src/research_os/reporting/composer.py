from __future__ import annotations

from collections import defaultdict

from research_os.reporting.document import (
    AuditAppendix,
    CausalBridgeBlock,
    ExpectationGapBlock,
    InvestmentDecisionSnapshot,
    LimitationBlock,
    MonitoringBlock,
    NarrativeBlock,
    ReportSection,
    ResearchReportDocument,
    ValuationBlock,
)
from research_os.reporting.research_view_v1_5_05 import HumanReadableResearchView


class ResearchReportComposer:
    """Deterministic editorial composition over one human-readable research view."""

    version = "research-report-composer@1.0.0"

    _BRIDGE_LABELS = {
        "Revenue": "收入",
        "Gross Profit": "毛利",
        "Working Capital": "营运资金",
        "Financing Requirement": "融资需求",
        "Financing Cost": "融资成本",
        "Credit / Inventory Loss": "信用/存货损失",
        "Net Profit / Cash Economics": "净利润/现金经济性",
        "Valuation": "估值",
    }

    @staticmethod
    def _normalize_limitation(text: str) -> str:
        if "租赁" in text and any(
            marker in text for marker in ("使用权资产", "租赁负债", "轻资产", "低资本占用")
        ):
            return (
                "租赁项目具有重要性；当前未进行租赁调整后的资本回报或估值分析，"
                "资产结构与现金表现需在租赁口径下复核。"
            )
        if "没有可用于该模型的专业行业策略插件" in text:
            return "已识别主要业务模型，但当前版本没有兼容的行业策略插件。"
        return text

    @classmethod
    def _limitations(cls, view: HumanReadableResearchView) -> list[str]:
        items: list[str] = []
        raw_items = list(view.presentation_limitations)
        for gap in view.coverage_gaps:
            text = gap.reason.explanation or gap.reason.label
            if text:
                raw_items.append(text)
        for text in raw_items:
            normalized = cls._normalize_limitation(text)
            if normalized and normalized not in items:
                items.append(normalized)
        return items

    @staticmethod
    def _evidence_ids(view: HumanReadableResearchView) -> list[str]:
        ids: list[str] = []
        for metric in view.kpi_metrics:
            ids.extend(metric.evidence_ids)
        for question in view.question_assessments:
            ids.extend(question.evidence_ids)
        if view.driver_graph is not None:
            for node in view.driver_graph.nodes:
                ids.extend(node.evidence_ids)
        if view.expectation_gap is not None:
            ids.extend(view.expectation_gap.evidence_ids)
        if view.valuation_result is not None:
            ids.extend(view.valuation_result.evidence_ids)
        for item in view.state_provenance:
            ids.extend(item.evidence_ids)
        if view.next_verification_event is not None:
            ids.extend(view.next_verification_event.evidence_ids)
        return list(dict.fromkeys(item for item in ids if item))

    @staticmethod
    def _material_risks(view: HumanReadableResearchView):
        result = []
        seen: set[str] = set()
        for item in view.decision_summary.top_risks:
            key = item.code or item.label
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
            if len(result) == 3:
                break
        return result

    @classmethod
    def _valuation_bridge(cls, view: HumanReadableResearchView) -> list[str]:
        execution = view.valuation_execution
        if execution is None or not execution.driver_bridge:
            return []
        steps = [cls._BRIDGE_LABELS.get(step, step) for step in execution.driver_bridge]
        return list(dict.fromkeys(step for step in steps if step))

    @staticmethod
    def _graph_bridge(view: HumanReadableResearchView) -> list[str]:
        graph = view.driver_graph
        if graph is None or not graph.edges:
            return []

        labels = {node.driver_id: node.label for node in graph.nodes}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.from_driver in labels and edge.to_driver in labels:
                adjacency[edge.from_driver].append(edge.to_driver)

        def longest_from(driver_id: str, visited: frozenset[str]) -> list[str]:
            best = [driver_id]
            for target in adjacency.get(driver_id, []):
                if target in visited:
                    continue
                candidate = [driver_id, *longest_from(target, visited | {target})]
                if len(candidate) > len(best):
                    best = candidate
            return best

        best_path: list[str] = []
        for node in graph.nodes:
            candidate = longest_from(node.driver_id, frozenset({node.driver_id}))
            if len(candidate) > len(best_path):
                best_path = candidate
        if len(best_path) < 2:
            return []
        return [labels[driver_id] for driver_id in best_path]

    @classmethod
    def _causal_bridge(cls, view: HumanReadableResearchView) -> list[str]:
        return cls._valuation_bridge(view) or cls._graph_bridge(view)

    def _snapshot(self, view: HumanReadableResearchView) -> InvestmentDecisionSnapshot:
        summary = view.decision_summary
        limitations = self._limitations(view)
        return InvestmentDecisionSnapshot(
            company_id=view.company_id,
            decision_ts=view.decision_ts,
            business_model=view.business_model,
            decision_state=summary.decision_state,
            fundamental_state=summary.fundamental_state,
            thesis_state=summary.thesis_state,
            expectation_state=summary.expectation_state,
            valuation_state=summary.valuation_state,
            primary_thesis=summary.primary_thesis,
            material_drivers=list(summary.top_drivers[:5]),
            material_risks=self._material_risks(view),
            evidence_confidence=summary.evidence_confidence,
            next_verification_event=summary.next_verification_event,
            material_limitation_count=len(limitations),
            top_limitation=limitations[0] if limitations else None,
        )

    def _sections(self, view: HumanReadableResearchView) -> list[ReportSection]:
        sections: list[ReportSection] = []
        if view.decision_summary.primary_thesis:
            sections.append(
                ReportSection(
                    section_id="core-investment-judgment",
                    title="核心投资判断",
                    blocks=[
                        NarrativeBlock(
                            title="核心投资逻辑",
                            text=view.decision_summary.primary_thesis,
                        )
                    ],
                )
            )
        causal_bridge = self._causal_bridge(view)
        if causal_bridge:
            sections.append(
                ReportSection(
                    section_id="causal-bridge",
                    title="关键因果链",
                    blocks=[CausalBridgeBlock(steps=causal_bridge)],
                )
            )
        if view.expectation_gap is not None:
            sections.append(
                ReportSection(
                    section_id="expectation-gap",
                    title="市场预期差",
                    blocks=[ExpectationGapBlock(payload=view.expectation_gap.model_dump(mode="python"))],
                )
            )
        if view.valuation_result is not None:
            sections.append(
                ReportSection(
                    section_id="valuation",
                    title="估值与情景",
                    blocks=[ValuationBlock(payload=view.valuation_result.model_dump(mode="python"))],
                )
            )
        if view.monitoring is not None:
            sections.append(
                ReportSection(
                    section_id="monitoring",
                    title="监控与验证",
                    blocks=[
                        MonitoringBlock(
                            next_verification_event=view.monitoring.next_verification_event,
                            conviction_up_conditions=list(view.monitoring.conviction_up_conditions),
                            thesis_broken_conditions=list(view.monitoring.thesis_broken_conditions),
                            key_metrics=list(view.monitoring.key_metrics),
                        )
                    ],
                )
            )
        limitations = self._limitations(view)
        if limitations:
            sections.append(
                ReportSection(
                    section_id="material-limitations",
                    title="关键研究限制",
                    blocks=[LimitationBlock(items=limitations)],
                )
            )
        return [section for section in sections if section.blocks]

    def compose(self, view: HumanReadableResearchView) -> ResearchReportDocument:
        if not isinstance(view, HumanReadableResearchView):
            raise TypeError("ResearchReportComposer.compose requires HumanReadableResearchView")

        summary = view.decision_summary
        return ResearchReportDocument(
            metadata={
                "company_id": view.company_id,
                "decision_ts": view.decision_ts,
                "business_model": view.business_model.label,
            },
            decision_snapshot=self._snapshot(view),
            sections=self._sections(view),
            audit_appendix=AuditAppendix(
                repository=view.repository,
                repository_commit=view.commit_sha,
                research_os_version=view.research_os_version,
                core_api_version=view.core_api_version,
                presentation_version=view.presentation_version,
                industry_plugins=[item.model_dump(mode="python") for item in view.industry_plugins],
                methodology_plugins=[item.model_dump(mode="python") for item in view.methodology_plugins],
                module_statuses={
                    name: status.model_dump(mode="python")
                    for name, status in summary.module_statuses.items()
                },
                evidence_ids=self._evidence_ids(view),
            ),
            composition_version=self.version,
        )
