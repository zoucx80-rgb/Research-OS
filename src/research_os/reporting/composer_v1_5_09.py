from __future__ import annotations

from research_os.reporting.composer import ResearchReportComposer as _PreviousComposer
from research_os.reporting.document import FinancialOperatingBlock, ReportSection


class ResearchReportComposer(_PreviousComposer):
    """v1.5.09 additive composition of canonical financial facts."""

    version = "research-report-composer@1.2.0"

    @classmethod
    def _core_financial_facts(cls, view) -> list[dict]:
        return [
            cls._display_payload(item)
            for item in list(getattr(view, "core_financial_facts", []) or [])
        ]

    @staticmethod
    def _evidence_ids(view) -> list[str]:
        ids = list(_PreviousComposer._evidence_ids(view))
        for item in list(getattr(view, "core_financial_facts", []) or []):
            ids.extend(getattr(item, "evidence_ids", []) or [])
        return list(dict.fromkeys(item for item in ids if item))

    def _sections(self, view) -> list[ReportSection]:
        sections = list(super()._sections(view))
        core_facts = self._core_financial_facts(view)
        if not core_facts:
            return sections

        for index, section in enumerate(sections):
            if section.section_id != "financial-operating-performance":
                continue
            block = section.blocks[0]
            sections[index] = ReportSection(
                section_id=section.section_id,
                title=section.title,
                blocks=[
                    FinancialOperatingBlock(
                        financial_sanity=block.financial_sanity,
                        core_financial_facts=core_facts,
                        kpi_metrics=list(block.kpi_metrics),
                    )
                ],
            )
            return sections

        insert_at = 1 if sections and sections[0].section_id == "core-investment-judgment" else 0
        sections.insert(
            insert_at,
            ReportSection(
                section_id="financial-operating-performance",
                title="财务与经营表现",
                blocks=[FinancialOperatingBlock(core_financial_facts=core_facts)],
            ),
        )
        return sections
