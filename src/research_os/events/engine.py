from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EventType = Literal[
    "financial_report",
    "guidance",
    "major_order",
    "capacity",
    "pricing",
    "raw_material",
    "financing",
    "share_issue",
    "buyback",
    "management_change",
    "regulation",
    "customer",
    "supplier",
    "industry_price",
    "consensus_revision",
]
Materiality = Literal["low", "medium", "high"]


class ResearchEvent(BaseModel):
    event_type: EventType
    company_id: str
    payload: dict = Field(default_factory=dict)


class EventImpact(BaseModel):
    affected_driver_types: list[str]
    affected_theses: list[str] = Field(default_factory=list)
    materiality: Materiality
    direction: str
    confidence_grade: str
    next_required_check: str


class EventEngine:
    MAP: dict[EventType, tuple[list[str], str, Materiality]] = {
        "share_issue": (["financing", "dilution"], "negative", "high"),
        "financing": (["financing"], "conditional", "medium"),
        "financial_report": (
            ["demand", "margin", "working_capital", "financing"],
            "mixed",
            "high",
        ),
        "major_order": (["demand", "revenue"], "positive", "medium"),
        "capacity": (["capacity", "capex"], "conditional", "medium"),
        "pricing": (["price", "margin"], "conditional", "medium"),
        "raw_material": (["cost", "margin"], "conditional", "medium"),
        "buyback": (["capital_allocation"], "positive", "medium"),
        "management_change": (["governance"], "conditional", "medium"),
        "regulation": (["regulation"], "conditional", "high"),
        "customer": (["demand", "concentration"], "conditional", "medium"),
        "supplier": (["supply", "concentration"], "conditional", "medium"),
        "industry_price": (["price", "margin"], "conditional", "medium"),
        "guidance": (["expectations"], "conditional", "medium"),
        "consensus_revision": (["expectations"], "conditional", "medium"),
    }

    def map_impact(self, event: ResearchEvent) -> EventImpact:
        drivers, direction, materiality = self.MAP[event.event_type]
        return EventImpact(
            affected_driver_types=drivers,
            materiality=materiality,
            direction=direction,
            confidence_grade=(
                "A"
                if event.event_type in {"financial_report", "share_issue", "buyback"}
                else "D"
            ),
            next_required_check="next material disclosure or scheduled reporting event",
        )
