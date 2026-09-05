from research_os.decision.engine import DecisionEngine
from research_os.decision.models import (
    DecisionContext,
    DecisionDerivation,
    DecisionDimensionAssessment,
    DecisionInputAssessment,
    DecisionStateRecord,
)

__all__ = [
    "DecisionContext",
    "DecisionContextBuilder",
    "DecisionDerivation",
    "DecisionDimensionAssessment",
    "DecisionEngine",
    "DecisionInputAssessment",
    "DecisionStateRecord",
]


def __getattr__(name: str) -> object:
    if name == "DecisionContextBuilder":
        from research_os.decision.context import DecisionContextBuilder

        return DecisionContextBuilder
    raise AttributeError(name)
