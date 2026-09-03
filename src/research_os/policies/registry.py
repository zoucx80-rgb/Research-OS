from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from decimal import Decimal

from research_os.contracts.policies import PolicySelection, PolicySnapshot
from research_os.policies.models import PolicyDefinition, PolicyOverride, PolicyParameter


class PolicyRegistryConflictError(ValueError):
    pass


def _canonical_value(value: object) -> object:
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {
            "type": "datetime",
            "value": value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    if isinstance(value, PolicyParameter):
        return {
            field_name: _canonical_value(getattr(value, field_name))
            for field_name in type(value).model_fields
        }
    if isinstance(value, PolicyDefinition):
        return {
            "policy_id": value.policy_id,
            "policy_version": value.policy_version,
            "policy_type": value.policy_type,
            "applicability": sorted(value.applicability),
            "parameters": _canonical_value(value.parameters),
            "rationale": value.rationale,
            "source": value.source,
        }
    if isinstance(value, PolicyOverride):
        return {
            "policy_id": value.policy_id,
            "base_policy_version": value.base_policy_version,
            "operator": value.operator,
            "reason": value.reason,
            "override_ts": _canonical_value(value.override_ts),
            "parameters": _canonical_value(value.parameters),
        }
    if isinstance(value, Mapping):
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonical_value(item) for item in value]
        return sorted(
            items,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    return value


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class PolicyRegistry:
    __slots__ = ("_definitions", "_overrides", "definitions", "overrides", "fingerprint")
    _definitions: dict[str, PolicyDefinition]
    _overrides: dict[str, PolicyOverride]
    definitions: tuple[PolicyDefinition, ...]
    overrides: tuple[PolicyOverride, ...]
    fingerprint: str

    def __init__(
        self,
        definitions: Iterable[PolicyDefinition] = (),
        *,
        overrides: Iterable[PolicyOverride] = (),
    ) -> None:
        by_id: dict[str, PolicyDefinition] = {}
        for definition in definitions:
            if definition.policy_id in by_id:
                raise PolicyRegistryConflictError(
                    f"duplicate policy ID/version: {definition.policy_id}"
                )
            by_id[definition.policy_id] = definition
        overrides_by_id: dict[str, PolicyOverride] = {}
        for override in overrides:
            base_definition = by_id.get(override.policy_id)
            if (
                base_definition is None
                or base_definition.policy_version != override.base_policy_version
            ):
                raise ValueError(f"override base policy does not match: {override.policy_id}")
            if override.policy_id in overrides_by_id:
                raise PolicyRegistryConflictError(
                    f"duplicate policy override: {override.policy_id}"
                )
            unknown = set(override.parameters) - set(base_definition.parameters)
            if unknown:
                raise ValueError(
                    f"override contains unknown parameters for {override.policy_id}: "
                    + ", ".join(sorted(unknown))
                )
            for name, parameter in override.parameters.items():
                base = base_definition.parameters[name]
                if (parameter.value_type, parameter.unit) != (
                    base.value_type,
                    base.unit,
                ):
                    raise ValueError(
                        f"override parameter type/unit mismatch: {override.policy_id}.{name}"
                    )
            overrides_by_id[override.policy_id] = override

        ordered_definitions = tuple(by_id[key] for key in sorted(by_id))
        ordered_overrides = tuple(overrides_by_id[key] for key in sorted(overrides_by_id))
        object.__setattr__(self, "_definitions", by_id)
        object.__setattr__(self, "_overrides", overrides_by_id)
        object.__setattr__(self, "definitions", ordered_definitions)
        object.__setattr__(self, "overrides", ordered_overrides)
        object.__setattr__(
            self,
            "fingerprint",
            _fingerprint((ordered_definitions, ordered_overrides)),
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("PolicyRegistry is immutable")

    def get(self, policy_id: str) -> PolicyDefinition | None:
        return self._definitions.get(policy_id)

    def require(self, policy_id: str) -> PolicyDefinition:
        definition = self.get(policy_id)
        if definition is None:
            raise KeyError(f"undefined policy: {policy_id}")
        return definition

    def parameters(self, policy_id: str) -> Mapping[str, PolicyParameter]:
        definition = self.require(policy_id)
        override = self._overrides.get(policy_id)
        if override is None:
            return definition.parameters
        return {**definition.parameters, **override.parameters}

    def value(self, policy_id: str, parameter: str) -> object:
        try:
            return self.parameters(policy_id)[parameter].value
        except KeyError as exc:
            raise KeyError(f"undefined policy parameter: {policy_id}.{parameter}") from exc

    def decimal_value(self, policy_id: str, parameter: str) -> Decimal:
        value = self.value(policy_id, parameter)
        if not isinstance(value, Decimal):
            raise TypeError(f"policy value is not decimal: {policy_id}.{parameter}")
        return value

    def integer_value(self, policy_id: str, parameter: str) -> int:
        value = self.value(policy_id, parameter)
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"policy value is not integer: {policy_id}.{parameter}")
        return value

    def boolean_value(self, policy_id: str, parameter: str) -> bool:
        value = self.value(policy_id, parameter)
        if not isinstance(value, bool):
            raise TypeError(f"policy value is not boolean: {policy_id}.{parameter}")
        return value

    def snapshot(self) -> PolicySnapshot:
        selections = tuple(
            PolicySelection(
                policy_id=definition.policy_id,
                policy_version=definition.policy_version,
                parameters_fingerprint=_fingerprint(
                    {
                        "parameters": self.parameters(definition.policy_id),
                        "override": self._overrides.get(definition.policy_id),
                    }
                ),
            )
            for definition in self.definitions
        )
        return PolicySnapshot(policies=selections)


__all__ = ["PolicyRegistry", "PolicyRegistryConflictError"]
