from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, Field

from research_os.router.models import BusinessModelProfile


class MetricResult(BaseModel):
    metric_id: str
    value: float | None
    unit: str | None = None
    status: str = "valid"
    formula_version: str
    evidence_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = None


class KpiPack(Protocol):
    pack_id: str
    pack_version: str
    eligible_business_models: tuple[str, ...]
    required_facts: frozenset[str]
    optional_facts: frozenset[str]
    missing_policy: str
    valuation_preferences: tuple[str, ...]

    def calculate(self, facts: Mapping[str, Any]) -> list[MetricResult]: ...


class CorePack:
    pack_id = "core"
    pack_version = "core@1.0.0"
    eligible_business_models = ("all",)
    required_facts = frozenset()
    optional_facts = frozenset()
    missing_policy = "preserve_missing"
    valuation_preferences = ()

    def calculate(self, facts):
        return []


@dataclass(frozen=True)
class KpiPackResolution:
    packs: list[Any]
    specialized_packs: list[Any]
    requested_models: list[str]
    unsupported_models: list[str]
    primary_supported: bool


class KpiPackRegistry:
    """Deprecated v1.x compatibility facade; v1.3 runtime resolves industry plugins."""

    MODEL_TO_PACK = {
        "manufacturer": "manufacturing",
        "manufacturing": "manufacturing",
        "distributor": "distributor",
    }

    def __init__(self, packs):
        self.packs = {p.pack_id: p for p in packs}

    @classmethod
    def default(cls):
        from .manufacturing import ManufacturingPack
        from .distributor import DistributorPack

        return cls([CorePack(), ManufacturingPack(), DistributorPack()])

    def resolve_with_status(self, profile: BusinessModelProfile) -> KpiPackResolution:
        requested = [profile.primary_model, *profile.secondary_models]
        specialized = []
        unsupported = []
        for model in requested:
            pack_id = self.MODEL_TO_PACK.get(model, model)
            pack = self.packs.get(pack_id)
            if pack is None or pack_id == "core":
                if model not in unsupported:
                    unsupported.append(model)
                continue
            if all(existing.pack_id != pack.pack_id for existing in specialized):
                specialized.append(pack)

        primary_pack_id = self.MODEL_TO_PACK.get(profile.primary_model, profile.primary_model)
        primary_supported = primary_pack_id in self.packs and primary_pack_id != "core"
        core = self.packs.get("core")
        packs = ([core] if core is not None else []) + specialized
        return KpiPackResolution(
            packs=packs,
            specialized_packs=specialized,
            requested_models=requested,
            unsupported_models=unsupported,
            primary_supported=primary_supported,
        )

    def resolve(self, profile: BusinessModelProfile):
        return self.resolve_with_status(profile).packs
