from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from research_os.completion.models import ResearchCompletionResult
from research_os.plugins.resolver import StrategyResolution
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.runtime.modules import ModuleResult
from research_os.snapshots.service import ResearchSnapshot


class ComponentFingerprint(BaseModel):
    model_config = ConfigDict(frozen=True)

    component_id: str
    component_type: str
    component_version: str
    api_version: str | None = None


class ResearchRunResult(BaseModel):
    """Canonical v1.3 research result consumed by snapshots, reports and facades."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    business_model: BusinessModelProfile
    strategy_resolution: StrategyResolution
    module_results: dict[str, ModuleResult]
    artifacts: dict[str, Any]
    completion: ResearchCompletionResult
    component_fingerprints: list[ComponentFingerprint]
    snapshot: ResearchSnapshot
