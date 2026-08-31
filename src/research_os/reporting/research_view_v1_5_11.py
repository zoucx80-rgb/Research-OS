from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from research_os.reporting.research_view_v1_5_10 import (
    HumanReadableResearchView as _PreviousResearchView,
    ResearchViewPresenter as _PreviousPresenter,
)
from research_os.runtime.result import ResearchRunResult


class HumanReadableResearchView(_PreviousResearchView):
    model_config = ConfigDict(frozen=True)

    presentation_version: str = "professional-research-view@1.6.0"


class ResearchViewPresenter(_PreviousPresenter):
    """v1.5.11 display-only integrity hardening over canonical research state."""

    version = "professional-research-view@1.6.0"

    _SEMANTIC_FACT_ALIASES = {
        "ocf": "operating_cash_flow",
        "operating_cash_flow": "operating_cash_flow",
    }

    @classmethod
    def _deduplicate_financial_facts(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        positions: dict[tuple[Any, ...], int] = {}

        for raw in rows:
            item = dict(raw)
            fact_key = str(item.get("fact_key") or "")
            canonical_key = cls._SEMANTIC_FACT_ALIASES.get(fact_key, fact_key)
            signature = (
                canonical_key,
                item.get("value"),
                item.get("unit"),
                item.get("period"),
                item.get("period_end"),
            )
            position = positions.get(signature)
            if position is None:
                positions[signature] = len(result)
                result.append(item)
                continue

            existing = dict(result[position])
            evidence_ids = list(
                dict.fromkeys(
                    [
                        *list(existing.get("evidence_ids") or []),
                        *list(item.get("evidence_ids") or []),
                    ]
                )
            )
            existing["evidence_ids"] = evidence_ids
            result[position] = existing

        return result

    def build(
        self,
        result: ResearchRunResult,
        locale: str = _PreviousPresenter._SUPPORTED_LOCALE,
    ) -> HumanReadableResearchView:
        previous = super().build(result, locale=locale)
        data = previous.model_dump(mode="python")
        typed_signals = result.artifacts.get("thesis.semantic_signal_assessment")
        data.update(
            core_financial_facts=self._deduplicate_financial_facts(
                list(data.get("core_financial_facts") or [])
            ),
            thesis_signal_assessment=(
                self._thesis_signals(typed_signals)
                if typed_signals is not None
                else data.get("thesis_signal_assessment")
            ),
            presentation_version=self.version,
        )
        return HumanReadableResearchView.model_validate(data)
