from __future__ import annotations

from collections import defaultdict
from typing import Any

from research_os.reporting.document import (
    AuditAppendix,
    CapitalFundingBlock,
    CausalBridgeBlock,
    EvidenceNoteBlock,
    ExpectationForecastBlock,
    ExpectationGapBlock,
    FinancialOperatingBlock,
    GapClassificationBlock,
    InvestmentDecisionSnapshot,
    LimitationBlock,
    MonitoringBlock,
    NarrativeBlock,
    ReportSection,
    ResearchReportDocument,
    StateProvenanceBlock,
    ThesisDebateBlock,
    ValuationBlock,
    ValuationRationaleBlock,
)
from research_os.reporting.research_view_v1_5_05 import HumanReadableResearchView


class ResearchReportComposer:
    """Deterministic editorial composition over one human-readable research view."""

    version = "research-report-composer@1.1.0"

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
    _INTERNAL_ID_KEYS = {
        "evidence_id",
        "evidence_ids",
        "assumption_id",
        "assumption_ids",
    }

    @staticmethod
    def _dedup(items: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in items if item))

    @classmethod
    def _display_payload(cls, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="python")
        if isinstance(value, dict):
            return {
                key: cls._display_payload(item)
                for key, item in value.items()
                if key not in cls._INTERNAL_ID_KEYS
            }
        if isinstance(value, list):
            return [cls._display_payload(item) for item in value]
        if isinstance(value, tuple):
            return [cls._display_payload(item) for item in value]
        return value

    @classmethod
    def _valuation_execution_payload(cls, execution) -> dict[str, Any] | None:
        if execution is None:
            return None
        payload = cls._display_payload(execution)
        payload.pop("lineage", None)
        assumptions = []
        for item in payload.get("assumptions", []):
            if isinstance(item, dict):
                item = dict(item)
                item.pop("id", None)
            assumptions.append(item)
        payload["assumptions"] = assumptions
        return payload

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
    def _assumption_ids(view: HumanReadableResearchView) -> list[str]:
        if view.valuation_result is None:
            return []
        return list(dict.fromkeys(item for item in view.valuation_result.assumption_ids if item))

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

    @classmethod
    def _gap_classification(cls, view: HumanReadableResearchView) -> GapClassificationBlock | None:
        evidence_missing: list[str] = []
        capability_missing: list[str] = []
        not_applicable: list[str] = []

        for question in view.question_assessments:
            code = question.status.code
            if code == "EVIDENCE_MISSING":
                evidence_missing.append(question.question)
            elif code == "CAPABILITY_MISSING":
                capability_missing.append(question.question)
            elif code == "NOT_APPLICABLE":
                not_applicable.append(question.question)

        for gap in view.coverage_gaps:
            label = gap.reason.label or gap.reason.explanation
            gap_type = gap.gap_type.code
            if gap_type == "business_model_evidence":
                evidence_missing.append(label)
            else:
                capability_missing.append(label)

        presentation_or_deferred = [
            cls._normalize_limitation(item) for item in view.presentation_limitations if item
        ]
        block = GapClassificationBlock(
            evidence_missing=cls._dedup(evidence_missing),
            capability_missing=cls._dedup(capability_missing),
            not_applicable=cls._dedup(not_applicable),
            presentation_or_deferred=cls._dedup(presentation_or_deferred),
        )
        if not any(
            (
                block.evidence_missing,
                block.capability_missing,
                block.not_applicable,
                block.presentation_or_deferred,
            )
        ):
            return None
        return block

    @classmethod
    def _expectation_payload(cls, view: HumanReadableResearchView) -> dict:
        return cls._display_payload(view.expectation_gap)

    @classmethod
    def _valuation_payload(cls, view: HumanReadableResearchView) -> dict:
        return cls._display_payload(view.valuation_result)

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

        if view.financial_sanity is not None or view.kpi_metrics:
            sections.append(
                ReportSection(
                    section_id="financial-operating-performance",
                    title="财务与经营表现",
                    blocks=[
                        FinancialOperatingBlock(
                            financial_sanity=self._display_payload(view.financial_sanity),
                            kpi_metrics=[self._display_payload(item) for item in view.kpi_metrics],
                        )
                    ],
                )
            )

        if view.capital_efficiency is not None or view.funding_loop is not None:
            sections.append(
                ReportSection(
                    section_id="capital-funding",
                    title="资本效率与融资循环",
                    blocks=[
                        CapitalFundingBlock(
                            capital_efficiency=self._display_payload(view.capital_efficiency),
                            funding_loop=self._display_payload(view.funding_loop),
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

        if view.theses or view.thesis_signal_assessment is not None:
            sections.append(
                ReportSection(
                    section_id="thesis-debate",
                    title="投资逻辑与反证",
                    blocks=[
                        ThesisDebateBlock(
                            theses=[self._display_payload(item) for item in view.theses],
                            signal_assessment=self._display_payload(view.thesis_signal_assessment),
                        )
                    ],
                )
            )

        if view.expectation_quality is not None or view.forecast_discipline is not None:
            sections.append(
                ReportSection(
                    section_id="expectation-forecast",
                    title="市场预期与预测纪律",
                    blocks=[
                        ExpectationForecastBlock(
                            expectation_quality=self._display_payload(view.expectation_quality),
                            forecast_discipline=self._display_payload(view.forecast_discipline),
                        )
                    ],
                )
            )

        if view.expectation_gap is not None:
            sections.append(
                ReportSection(
                    section_id="expectation-gap",
                    title="市场预期差",
                    blocks=[ExpectationGapBlock(payload=self._expectation_payload(view))],
                )
            )

        if view.valuation_models or view.valuation_execution is not None:
            sections.append(
                ReportSection(
                    section_id="valuation-rationale",
                    title="估值方法与适用性",
                    blocks=[
                        ValuationRationaleBlock(
                            valuation_models=[self._display_payload(item) for item in view.valuation_models],
                            valuation_execution=self._valuation_execution_payload(view.valuation_execution),
                        )
                    ],
                )
            )

        if view.valuation_result is not None:
            sections.append(
                ReportSection(
                    section_id="valuation",
                    title="估值与情景",
                    blocks=[ValuationBlock(payload=self._valuation_payload(view))],
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

        if view.state_provenance:
            sections.append(
                ReportSection(
                    section_id="state-provenance",
                    title="状态来源",
                    blocks=[
                        StateProvenanceBlock(
                            items=[self._display_payload(item) for item in view.state_provenance]
                        )
                    ],
                )
            )

        gaps = self._gap_classification(view)
        if gaps is not None:
            sections.append(
                ReportSection(
                    section_id="research-gaps",
                    title="研究缺口分类",
                    blocks=[gaps],
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
        if self._evidence_ids(view):
            sections.append(
                ReportSection(
                    section_id="evidence-traceability",
                    title="证据追溯",
                    blocks=[
                        EvidenceNoteBlock(
                            text="关键结论保留规范化证据追溯；完整证据索引见审计附录。",
                            evidence_ids=[],
                        )
                    ],
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
                assumption_ids=self._assumption_ids(view),
            ),
            composition_version=self.version,
        )
