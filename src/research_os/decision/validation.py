from pydantic import TypeAdapter, ValidationError

from .models import ResearchDecisionState


_ADAPTER = TypeAdapter(ResearchDecisionState)


def validate_decision_state(value: str) -> ResearchDecisionState:
    try:
        return _ADAPTER.validate_python(value)
    except ValidationError as exc:
        raise ValueError(f"invalid ResearchDecisionState: {value}") from exc
