from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StateSource = Literal[
    "derived",
    "analyst_assumption",
    "external_model",
    "manual_override",
]


class StateInput(BaseModel):
    """A high-level research state together with its provenance."""

    model_config = ConfigDict(frozen=True)

    value: str
    source: StateSource
    evidence_ids: list[str] = Field(default_factory=list)
    method: str | None = None


def resolve_state_input(explicit: StateInput | None, legacy_value: str) -> StateInput:
    if explicit is not None:
        return explicit
    return StateInput(
        value=legacy_value,
        source="analyst_assumption",
        method="legacy ResearchInputs string field",
    )
