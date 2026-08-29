from typing import Any

from pydantic import BaseModel, Field

from research_os.completion.models import FinalStatus, ModuleStatus
from research_os.decision.models import DecisionContext, DecisionStateRecord, ResearchDecisionState
from research_os.runtime.result import ResearchRunResult


class DecisionSummary(BaseModel):
    company_id: str
    business_model: str
    primary_thesis: str
    thesis_state: str
    fundamental_state: str
    expectation_state: str
    valuation_state: str
    evidence_confidence: str | float
    top_drivers: list[str]
    top_risks: list[str]
    next_verification_event: str
    research_os_version: str
    decision_state: ResearchDecisionState | None = None
    final_status: FinalStatus = "INCOMPLETE"
    blocking_modules: list[str] = Field(default_factory=list)
    module_statuses: dict[str, ModuleStatus] = Field(default_factory=dict)
    expectation_evidence_status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
    valuation_execution_status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
    core_contradiction: str | None = None
    sections: list[str] = Field(default_factory=list)


class DecisionSummaryBuilder:
    SECTIONS = ["Decision", "Drivers", "FinancialCapital", "ExpectationsForecast", "Valuation", "Evidence"]

    @staticmethod
    def _as_decision_context(value: Any) -> DecisionContext | None:
        if value is None:
            return None
        if isinstance(value, DecisionContext):
            return value
        try:
            return DecisionContext.model_validate(value)
        except Exception:
            return None

    @staticmethod
    def _as_decision_record(value: Any) -> DecisionStateRecord | None:
        if value is None:
            return None
        if isinstance(value, DecisionStateRecord):
            return value
        try:
            return DecisionStateRecord.model_validate(value)
        except Exception:
            return None

    @staticmethod
    def _first(items: Any):
        values = list(items or [])
        return values[0] if values else None

    @staticmethod
    def _get(value: Any, field: str, default=None):
        if value is None:
            return default
        if isinstance(value, dict):
            return value.get(field, default)
        return getattr(value, field, default)

    def _top_drivers(self, artifacts: dict[str, Any]) -> list[str]:
        graph = artifacts.get("drivers.graph")
        nodes = list(self._get(graph, "nodes", []) or [])
        if not nodes:
            return []
        critical = [node for node in nodes if self._get(node, "critical", False)]
        selected = critical or nodes
        return [
            str(self._get(node, "name", self._get(node, "driver_id", "")))
            for node in selected[:3]
            if self._get(node, "name", self._get(node, "driver_id", ""))
        ]

    def _top_risks(
        self,
        artifacts: dict[str, Any],
        record: DecisionStateRecord | None,
    ) -> list[str]:
        risks: list[str] = []
        funding = artifacts.get("capital.funding_loop")
        risks.extend(str(x) for x in list(self._get(funding, "reason_codes", []) or []))
        if record is not None:
            risks.extend(str(x) for x in record.reason_codes)
        deduped: list[str] = []
        for risk in risks:
            if risk and risk not in deduped:
                deduped.append(risk)
        return deduped[:3]

    def _next_verification_event(self, artifacts: dict[str, Any]) -> str:
        event = artifacts.get("temporal.event")
        event_name = self._get(event, "event_name")
        if event_name:
            return str(event_name)

        claim = self._first(artifacts.get("claims.items"))
        claim_event = self._get(claim, "next_verification_event")
        if claim_event:
            return str(claim_event)

        thesis = self._first(artifacts.get("thesis.items"))
        next_check = self._get(thesis, "next_check_date")
        return str(next_check) if next_check else ""

    def build(self, result: ResearchRunResult) -> DecisionSummary:
        if not isinstance(result, ResearchRunResult):
            raise TypeError("DecisionSummaryBuilder.build requires ResearchRunResult")

        artifacts = result.artifacts
        completion = result.completion
        module_statuses = dict(completion.module_statuses)
        context = self._as_decision_context(artifacts.get("decision.context"))
        record = self._as_decision_record(artifacts.get("decision.record"))
        thesis = self._first(artifacts.get("thesis.items"))
        claims = list(artifacts.get("claims.items", []) or [])

        primary_thesis = str(self._get(thesis, "statement", "") or "")
        thesis_state = (
            context.thesis_state
            if context is not None
            else (
                record.thesis_state
                if record is not None and record.thesis_state is not None
                else str(self._get(thesis, "status", "UNKNOWN")).upper()
            )
        )
        fundamental_state = (
            context.fundamental_state
            if context is not None
            else (
                record.fundamental_state
                if record is not None and record.fundamental_state is not None
                else "UNCERTAIN"
            )
        )
        expectation_state = (
            context.expectation_state
            if context is not None
            else (
                record.expectation_state
                if record is not None and record.expectation_state is not None
                else "MIXED"
            )
        )
        valuation_state = (
            context.valuation_state
            if context is not None
            else (
                record.valuation_state
                if record is not None and record.valuation_state is not None
                else "UNRELIABLE"
            )
        )
        evidence_confidence = (
            context.evidence_confidence
            if context is not None
            else (
                record.evidence_confidence
                if record is not None and record.evidence_confidence is not None
                else 0.0
            )
        )

        contradiction = artifacts.get("core_contradiction") if claims else None
        return DecisionSummary(
            company_id=result.company.company_id,
            business_model=result.business_model.primary_model,
            primary_thesis=primary_thesis,
            thesis_state=thesis_state,
            fundamental_state=fundamental_state,
            expectation_state=expectation_state,
            valuation_state=valuation_state,
            evidence_confidence=evidence_confidence,
            top_drivers=self._top_drivers(artifacts),
            top_risks=self._top_risks(artifacts, record),
            next_verification_event=self._next_verification_event(artifacts),
            research_os_version=result.baseline.research_os_version,
            decision_state=record.state if record is not None else None,
            final_status=completion.final_status,
            blocking_modules=list(completion.blocking_modules),
            module_statuses=module_statuses,
            expectation_evidence_status=module_statuses.get(
                "Expectation Evidence",
                "INSUFFICIENT_EVIDENCE",
            ),
            valuation_execution_status=module_statuses.get(
                "Valuation Execution",
                "INSUFFICIENT_EVIDENCE",
            ),
            core_contradiction=str(contradiction) if contradiction is not None else None,
            sections=self.SECTIONS,
        )


class ResearchReportModel(BaseModel):
    sections: list[str]

    @classmethod
    def standard(cls):
        return cls(sections=[
            "Executive Decision Summary",
            "Business Model Classification",
            "Core Driver Tree",
            "Industry / Competitive Context",
            "Financial Quality",
            "Capital Efficiency & Funding Loop",
            "Segment / Product / Unit Economics",
            "Thesis",
            "Anti-Thesis",
            "Falsifiers",
            "Expectation Gap",
            "Forecast & Statistical Validation",
            "Valuation Router & Model Fitness",
            "Scenario Analysis",
            "Risk Register",
            "Monitoring Checklist",
            "Evidence Ledger",
            "Version & Data Snapshot",
        ])
