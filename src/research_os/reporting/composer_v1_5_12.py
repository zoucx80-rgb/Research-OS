from __future__ import annotations

from research_os.reporting.composer_v1_5_10 import (
    ResearchReportComposer as _PreviousComposer,
)
from research_os.reporting.document import (
    ReportSection,
    ResearchCompletenessBlock,
    ValuationRationaleBlock,
)
from research_os.semantics.preservation import SemanticPreservationValidator


class ResearchReportComposer(_PreviousComposer):
    """v1.5.12 composition that carries semantic fingerprints and reconciliation."""

    version = "research-report-composer@1.4.0"

    _ARTIFACT_BY_SECTION = {
        section_id: artifact_id
        for artifact_id, section_id, _title, _kind in _PreviousComposer._SECTIONS
    }

    @classmethod
    def _completeness_sections(cls, view) -> list[ReportSection]:
        sections = list(super()._completeness_sections(view))
        preservation = dict(getattr(view, "semantic_preservation", {}) or {})
        protected_sections = {
            section.section_id
            for section in sections
            if section.section_id in {"sensitivity-scenarios", "monitoring-calendar"}
        }
        if protected_sections and preservation.get("status") != "PASS":
            raise ValueError(
                "semantic preservation validation is required for protected payloads"
            )
        result: list[ReportSection] = []
        for section in sections:
            block = section.blocks[0]
            if not isinstance(block, ResearchCompletenessBlock):
                result.append(section)
                continue

            if section.section_id == "sensitivity-scenarios":
                actual = SemanticPreservationValidator.sensitivity_fingerprint(
                    block.payload
                )
                expected = preservation.get("sensitivity_fingerprint")
                if expected is None:
                    raise ValueError("sensitivity semantic fingerprint is required")
                if actual != expected:
                    raise ValueError("sensitivity semantic fingerprint mismatch")
                semantic_fingerprint = actual
            elif section.section_id == "monitoring-calendar":
                actual = SemanticPreservationValidator.monitoring_fingerprint(
                    block.payload
                )
                expected = preservation.get("monitoring_fingerprint")
                if expected is None:
                    raise ValueError("monitoring semantic fingerprint is required")
                if actual != expected:
                    raise ValueError("monitoring semantic fingerprint mismatch")
                semantic_fingerprint = actual
            else:
                semantic_fingerprint = (
                    SemanticPreservationValidator.fingerprint(block.payload)
                    if block.payload not in (None, [], (), {})
                    else None
                )

            result.append(
                ReportSection(
                    section_id=section.section_id,
                    title=section.title,
                    blocks=[
                        block.model_copy(
                            update={
                                "semantic_fingerprint": semantic_fingerprint
                            }
                        )
                    ],
                )
            )
        return result

    def _sections(self, view) -> list[ReportSection]:
        sections = list(super()._sections(view))
        reconciliation = getattr(view, "valuation_reconciliation", None)
        rationales = list(getattr(view, "valuation_model_rationales", []) or [])
        if reconciliation or rationales:
            display = self._display_payload(reconciliation)
            rationale_display = [self._display_payload(item) for item in rationales]
            for index, section in enumerate(sections):
                if section.section_id != "valuation-rationale":
                    continue
                block = section.blocks[0]
                sections[index] = ReportSection(
                    section_id=section.section_id,
                    title=section.title,
                    blocks=[
                        block.model_copy(update={"valuation_reconciliation": display})
                    ],
                )
                break
            else:
                insert_at = next(
                    (
                        index
                        for index, section in enumerate(sections)
                        if section.section_id == "valuation"
                    ),
                    len(sections),
                )
                sections.insert(
                    insert_at,
                    ReportSection(
                        section_id="valuation-rationale",
                        title="估值方法与适用性",
                        blocks=[
                            ValuationRationaleBlock(
                                valuation_model_rationales=rationale_display,
                                valuation_reconciliation=display,
                            )
                        ],
                    ),
                )

            for index, section in enumerate(sections):
                if section.section_id != "valuation-rationale":
                    continue
                block = section.blocks[0]
                sections[index] = ReportSection(
                    section_id=section.section_id,
                    title=section.title,
                    blocks=[
                        block.model_copy(
                            update={
                                "valuation_model_rationales": rationale_display,
                                "valuation_reconciliation": display,
                            }
                        )
                    ],
                )
                break

        cycle = getattr(view, "cycle_assessment", None)
        moat = getattr(view, "moat_assessment", None)
        if cycle or moat:
            payload = {
                "cycle": self._display_payload(cycle),
                "moat": self._display_payload(moat),
            }
            insert_at = next(
                (
                    index
                    for index, section in enumerate(sections)
                    if section.section_id in {"state-provenance", "research-gaps"}
                ),
                len(sections),
            )
            sections.insert(
                insert_at,
                ReportSection(
                    section_id="semantic-claims",
                    title="主张强度与语义边界",
                    blocks=[
                        ResearchCompletenessBlock(
                            kind="semantic_claims",
                            payload=payload,
                            semantic_fingerprint=(
                                SemanticPreservationValidator.fingerprint(payload)
                            ),
                        )
                    ],
                ),
            )
        return sections
