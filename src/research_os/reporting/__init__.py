"""Report contribution contracts exposed to Core/Plugin API 2.0.

The v1 report composer is intentionally not imported here. Reporting migration is
owned by M4 and must not make the M1 runtime depend on the retired v1 result model.
"""

from .contributions import ReportContribution, ResearchQuestionSpec

__all__ = ["ReportContribution", "ResearchQuestionSpec"]
