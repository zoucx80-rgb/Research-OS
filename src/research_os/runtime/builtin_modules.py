from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any

from research_os.capital.engine import CapitalEfficiencyEngine
from research_os.decision.engine import DecisionEngine
from research_os.decision.models import DecisionContext
from research_os.decision.validation import validate_decision_state
from research_os.drivers.graph import DriverGraph
from research_os.events.validation import NextVerificationEventValidator
from research_os.expectations.models import ExpectationService
from research_os.expectations.validation import ExpectationEvidenceValidator
from research_os.ledger.service import Claim, EvidenceLedger
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolver
from research_os.preflight.validator import PreflightValidator
from research_os.router.classifier import BusinessModelRouter
from research_os.runtime.context import ResearchContext
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.runtime.state import ResearchStateView
from research_os.thesis.service import ThesisService
from research_os.validation.financial import FinancialSanityValidator
from research_os.valuation.execution import ValuationExecutionValidator
from research_os.valuation.router import ValuationContext, ValuationRouter


_GRADE_SCORE = {"A": 1.0, "B": 0.9, "C": 0.75, "D": 0.5, "E": 0.3}


def _status_artifact(
    module_id: str,
    status: str,
    key: str,
    value: Any,
    *,
    evidence_ids=None,
    diagnostics=None,
):
    return ModuleResult(
        module_id=module_id,
        status=status,
        artifacts={key: value},
        evidence_ids=list(evidence_ids or []),
        diagnostics=list(diagnostics or []),
    )


class RepositoryPreflightModule:
    spec = ModuleSpec(
        module_id="core:repository-preflight",
        module_version="1.0.0",
        provides={"validation.repository_preflight"},
    )

    def __init__(
        self,
        validator: PreflightValidator | None = None,
        inputs: ResearchInputs | None = None,
    ):
        self.validator = validator or PreflightValidator()
        self.inputs = inputs or ResearchInputs()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        evidence = self.inputs.preflight
        if evidence is None:
            return _status_artifact(
                self.spec.module_id,
                "INSUFFICIENT_EVIDENCE",
                "validation.repository_preflight",
                None,
            )
        try:
            result = self.validator.validate(evidence)
        except ValueError as exc:
            return _status_artifact(
                self.spec.module_id,
                "FAIL",
                "validation.repository_preflight",
                None,
                diagnostics=[str(exc)],
            )
        return _status_artifact(
            self.spec.module_id,
            "PASS",
            "validation.repository_preflight",
            result,
        )


class PITLineageModule:
    spec = ModuleSpec(
        module_id="core:pit-lineage",
        module_version="1.0.0",
        provides={"evidence.pit", "validation.lineage"},
    )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        evidence = context.evidence.as_of(context.decision_ts)
        if not evidence:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "evidence.pit": [],
                    "validation.lineage": {"status": "INSUFFICIENT_EVIDENCE"},
                },
                diagnostics=["no evidence available at decision_ts"],
            )

        as_of_ids = {item.evidence_id for item in evidence}
        errors: list[str] = []
        for fact, value in context.facts.as_mapping().items():
            ids = context.facts.evidence_ids(fact)
            if not ids:
                errors.append(f"fact {fact!r} has no evidence lineage")
                continue
            supported = False
            for evidence_id in ids:
                item = context.evidence.get(evidence_id)
                if item is not None and evidence_id in as_of_ids and item.value == value:
                    supported = True
                    break
            if not supported:
                errors.append(f"fact {fact!r} is not supported by as-of evidence")

        status = "FAIL" if errors else "PASS"
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            artifacts={
                "evidence.pit": evidence,
                "validation.lineage": {"status": status, "errors": errors},
            },
            evidence_ids=[item.evidence_id for item in evidence],
            diagnostics=errors,
        )


class FinancialSanityModule:
    spec = ModuleSpec(
        module_id="core:financial-sanity",
        module_version="1.0.0",
        requires={"evidence.pit"},
        provides={"validation.financial"},
    )

    def __init__(
        self,
        validator: FinancialSanityValidator | None = None,
        inputs: ResearchInputs | None = None,
    ):
        self.validator = validator or FinancialSanityValidator()
        self.inputs = inputs or ResearchInputs()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        result = self.validator.validate_fact_mapping(
            context.facts.as_mapping(),
            unit=self.inputs.financial_unit,
        )
        if self.inputs.financial_observations:
            consistency = self.validator.check_consistency(list(self.inputs.financial_observations))
            result.errors.extend(consistency.errors)
            if consistency.status == "FAIL":
                result.status = "FAIL"
        status = "FAIL" if result.status == "FAIL" else "PASS"
        return _status_artifact(
            self.spec.module_id,
            status,
            "validation.financial",
            result,
            diagnostics=result.errors,
        )


class BusinessModelModule:
    spec = ModuleSpec(
        module_id="core:business-model",
        module_version="1.0.0",
        requires={"evidence.pit"},
        provides={"business_model.profile"},
    )

    def __init__(self, router: BusinessModelRouter | None = None):
        self.router = router or BusinessModelRouter()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        evidence = state.get("evidence.pit", [])
        if not evidence:
            return _status_artifact(
                self.spec.module_id,
                "INSUFFICIENT_EVIDENCE",
                "business_model.profile",
                None,
            )
        profile = self.router.classify(context.company.company_id, list(evidence))
        return _status_artifact(
            self.spec.module_id,
            "PASS",
            "business_model.profile",
            profile,
            evidence_ids=profile.evidence_ids,
        )


class StrategyResolutionModule:
    spec = ModuleSpec(
        module_id="core:strategy-resolution",
        module_version="1.0.0",
        requires={"business_model.profile"},
        provides={"strategy.resolution"},
    )

    def __init__(
        self,
        *,
        registry: PluginRegistry,
        resolver: StrategyResolver | None = None,
    ):
        self.registry = registry
        self.resolver = resolver or StrategyResolver()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        profile = state.get("business_model.profile")
        if profile is None:
            return _status_artifact(
                self.spec.module_id,
                "INSUFFICIENT_EVIDENCE",
                "strategy.resolution",
                None,
            )
        resolution = self.resolver.resolve(profile, context, self.registry)
        primary_gap = any(
            gap.gap_type == "industry_strategy"
            and gap.business_model == profile.primary_model
            for gap in resolution.coverage_gaps
        )
        status = (
            "INSUFFICIENT_EVIDENCE"
            if primary_gap or not resolution.industry_plugins
            else "PASS"
        )
        return _status_artifact(
            self.spec.module_id,
            status,
            "strategy.resolution",
            resolution,
            evidence_ids=profile.evidence_ids,
        )


class IndustryKpiModule:
    spec = ModuleSpec(
        module_id="core:industry-kpi",
        module_version="1.0.0",
        requires={"business_model.profile", "strategy.resolution"},
        provides={"kpi.metrics", "kpi.pack_ids", "validation.kpi"},
    )

    def __init__(self, *, registry: PluginRegistry):
        self.registry = registry

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        profile = state.get("business_model.profile")
        resolution = state.get("strategy.resolution")
        if profile is None or resolution is None or not resolution.industry_plugins:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "kpi.metrics": [],
                    "kpi.pack_ids": [],
                    "validation.kpi": {"status": "INSUFFICIENT_EVIDENCE"},
                },
                diagnostics=["no resolved industry strategy plugin"],
            )

        metrics = []
        pack_ids: list[str] = []
        evidence_ids: set[str] = set()
        child_statuses: list[str] = []

        for resolved in resolution.industry_plugins:
            plugin = self.registry.get(resolved.plugin_id)
            if plugin is None:
                child_statuses.append("FAIL")
                continue
            pack = getattr(plugin, "_pack", None)
            pack_id = getattr(
                pack,
                "pack_id",
                resolved.plugin_id.removeprefix("industry:"),
            )
            pack_ids.append(pack_id)
            dependencies = getattr(pack, "metric_dependencies", {})

            for module in plugin.modules():
                result = module.run(context, state)
                child_statuses.append(result.status)
                evidence_ids.update(result.evidence_ids)
                for metric in result.artifacts.get("kpi.metrics", []):
                    ids = sorted(
                        {
                            evidence_id
                            for fact in dependencies.get(metric.metric_id, [])
                            for evidence_id in context.facts.evidence_ids(fact)
                        }
                    )
                    metrics.append(
                        metric.model_copy(update={"evidence_ids": ids})
                        if ids
                        else metric
                    )

        primary_gap = any(
            gap.gap_type == "industry_strategy"
            and gap.business_model == profile.primary_model
            for gap in resolution.coverage_gaps
        )
        if primary_gap or not pack_ids:
            status = "INSUFFICIENT_EVIDENCE"
        elif "FAIL" in child_statuses:
            status = "FAIL"
        elif "INSUFFICIENT_EVIDENCE" in child_statuses:
            status = "INSUFFICIENT_EVIDENCE"
        else:
            status = "PASS"

        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            artifacts={
                "kpi.metrics": metrics,
                "kpi.pack_ids": pack_ids,
                "validation.kpi": {"status": status},
            },
            evidence_ids=sorted(evidence_ids),
        )


class CapitalEfficiencyModule:
    spec = ModuleSpec(
        module_id="core:capital-efficiency",
        module_version="1.0.0",
        requires={"kpi.metrics"},
        provides={"capital.efficiency", "validation.capital"},
    )

    def __init__(self, engine: CapitalEfficiencyEngine | None = None):
        self.engine = engine or CapitalEfficiencyEngine()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        facts = dict(context.facts.as_mapping())
        if facts.get("operating_cash_flow") is None and facts.get("ocf") is not None:
            facts["operating_cash_flow"] = facts["ocf"]
        result = self.engine.calculate(facts)
        metrics = state.get("kpi.metrics", []) or []
        valid_kpi = any(
            metric.status == "valid"
            and metric.metric_id
            in {"roic", "incremental_roic", "incremental_nwc_intensity"}
            for metric in metrics
        )
        status = (
            "PASS"
            if valid_kpi
            or any(
                value is not None
                for value in (result.roic, result.incremental_roic, result.iwcr)
            )
            else "INSUFFICIENT_EVIDENCE"
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            artifacts={
                "capital.efficiency": result,
                "validation.capital": {"status": status},
            },
        )


class FundingLoopModule:
    spec = ModuleSpec(
        module_id="core:funding-loop",
        module_version="1.0.0",
        requires={"kpi.metrics"},
        provides={"capital.funding_loop", "validation.funding"},
    )

    def __init__(self, engine: CapitalEfficiencyEngine | None = None):
        self.engine = engine or CapitalEfficiencyEngine()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        facts = dict(context.facts.as_mapping())
        if facts.get("operating_cash_flow") is None and facts.get("ocf") is not None:
            facts["operating_cash_flow"] = facts["ocf"]
        result = self.engine.funding_loop(facts)
        status = (
            "INSUFFICIENT_EVIDENCE"
            if result.funding_state == "unknown"
            else "PASS"
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            artifacts={
                "capital.funding_loop": result,
                "validation.funding": {"status": status},
            },
        )


class DriverThesisModule:
    spec = ModuleSpec(
        module_id="core:driver-thesis",
        module_version="1.0.0",
        requires={"evidence.pit", "kpi.pack_ids"},
        provides={
            "drivers.graph",
            "thesis.items",
            "claims.items",
            "validation.thesis",
        },
    )

    def __init__(
        self,
        theses: ThesisService | None = None,
        ledger: EvidenceLedger | None = None,
    ):
        self.theses = theses or ThesisService()
        self.ledger = ledger or EvidenceLedger()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        evidence = list(state.get("evidence.pit", []) or [])
        pack_ids = list(state.get("kpi.pack_ids", []) or [])
        if not evidence:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "drivers.graph": None,
                    "thesis.items": [],
                    "claims.items": [],
                    "validation.thesis": {"status": "INSUFFICIENT_EVIDENCE"},
                },
            )

        drivers = DriverGraph.build(
            context.company.company_id,
            pack_ids,
            evidence,
        )
        theses = self.theses.evaluate(
            context.company.company_id,
            evidence,
            drivers,
        )
        claims = []
        for thesis in theses:
            valid_until = None
            if thesis.next_check_date:
                valid_until = datetime.combine(
                    thesis.next_check_date,
                    time.max,
                    tzinfo=timezone.utc,
                )
            claim = Claim(
                claim_id=f"claim:{thesis.thesis_id}:{context.decision_ts.isoformat()}",
                company_id=context.company.company_id,
                claim_text=thesis.statement,
                claim_type="thesis",
                confidence_grade="D",
                evidence_ids=thesis.supporting_evidence
                or [item.evidence_id for item in evidence],
                assumptions=[thesis.mechanism, thesis.anti_thesis or ""],
                falsifiers=[f.label() for f in thesis.falsifiers],
                valid_from=context.decision_ts,
                valid_until=valid_until,
                next_verification_event=(
                    f"next check: {thesis.next_check_date}"
                    if thesis.next_check_date
                    else "next material disclosure"
                ),
            )
            claims.append(self.ledger.add_claim(claim))

        status = "PASS" if theses else "INSUFFICIENT_EVIDENCE"
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            artifacts={
                "drivers.graph": drivers,
                "thesis.items": theses,
                "claims.items": claims,
                "validation.thesis": {"status": status},
            },
            evidence_ids=[item.evidence_id for item in evidence],
        )


class ExpectationModule:
    spec = ModuleSpec(
        module_id="core:expectation",
        module_version="1.0.0",
        provides={"expectation.snapshot", "validation.expectation"},
    )

    def __init__(
        self,
        service: ExpectationService | None = None,
        validator: ExpectationEvidenceValidator | None = None,
        inputs: ResearchInputs | None = None,
    ):
        self.service = service or ExpectationService()
        self.validator = validator or ExpectationEvidenceValidator()
        self.inputs = inputs or ResearchInputs()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        vintage = self.inputs.expectation_vintage
        if vintage is None:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "expectation.snapshot": None,
                    "validation.expectation": {"status": "INSUFFICIENT_EVIDENCE"},
                },
            )

        self.service.add(vintage)
        snapshot = self.service.snapshot(
            context.company.company_id,
            context.decision_ts,
            expectation_type=vintage.expectation_type,
        )
        assessment = self.validator.assess(
            conclusion=self.inputs.expectation_conclusion,
            evidence=self.inputs.expectation_evidence,
            decision_ts=context.decision_ts,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=assessment.status,
            artifacts={
                "expectation.snapshot": snapshot,
                "validation.expectation": {"status": assessment.status},
            },
            diagnostics=list(assessment.errors),
        )


class ForecastDisciplineModule:
    spec = ModuleSpec(
        module_id="core:forecast-discipline",
        module_version="1.0.0",
        provides={"forecast.discipline"},
    )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        return _status_artifact(
            self.spec.module_id,
            "NOT_APPLICABLE",
            "forecast.discipline",
            {
                "status": "NOT_APPLICABLE",
                "reason": "no promoted forecast methodology",
            },
        )


class ValuationModule:
    spec = ModuleSpec(
        module_id="core:valuation",
        module_version="1.0.0",
        requires={"business_model.profile"},
        provides={"valuation.routing", "validation.valuation"},
    )

    def __init__(
        self,
        router: ValuationRouter | None = None,
        execution_validator: ValuationExecutionValidator | None = None,
        inputs: ResearchInputs | None = None,
    ):
        self.router = router or ValuationRouter()
        self.execution_validator = execution_validator or ValuationExecutionValidator()
        self.inputs = inputs or ResearchInputs()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        profile = state.get("business_model.profile")
        models = self.inputs.valuation_models
        if profile is None or not models:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "valuation.routing": None,
                    "validation.valuation": {"status": "INSUFFICIENT_EVIDENCE"},
                },
            )

        routing = self.router.route(
            ValuationContext(
                business_model=profile.primary_model,
                models=models,
            )
        )
        status = "PASS" if routing.primary_models else "INSUFFICIENT_EVIDENCE"
        execution = self.inputs.valuation_execution
        if execution is not None:
            execution_result = self.execution_validator.validate(execution)
            if execution_result.status == "VALUATION_GATE_FAIL":
                status = "FAIL"
            elif execution_result.status != "PASS":
                status = "INSUFFICIENT_EVIDENCE"
            else:
                selected = routing.models.get(execution.selected_model)
                if selected is None or selected.status in {
                    "NOT_APPLICABLE",
                    "LOW_CONFIDENCE",
                }:
                    status = "FAIL"

        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            artifacts={
                "valuation.routing": routing,
                "validation.valuation": {"status": status},
            },
        )


class DecisionModule:
    spec = ModuleSpec(
        module_id="core:decision",
        module_version="1.0.0",
        requires={
            "evidence.pit",
            "thesis.items",
            "claims.items",
            "expectation.snapshot",
            "valuation.routing",
        },
        provides={"decision.record", "validation.decision"},
    )

    def __init__(
        self,
        engine: DecisionEngine | None = None,
        inputs: ResearchInputs | None = None,
    ):
        self.engine = engine or DecisionEngine()
        self.inputs = inputs or ResearchInputs()

    @staticmethod
    def _confidence(evidence) -> float:
        if not evidence:
            return 0.0
        return sum(
            _GRADE_SCORE.get(item.confidence_grade.value, 0.0)
            for item in evidence
        ) / len(evidence)

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        theses = list(state.get("thesis.items", []) or [])
        claims = list(state.get("claims.items", []) or [])
        evidence = list(state.get("evidence.pit", []) or [])
        if not theses:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "decision.record": None,
                    "validation.decision": {"status": "INSUFFICIENT_EVIDENCE"},
                },
            )

        thesis_state = theses[0].status.upper()
        if thesis_state not in {
            "STRENGTHENING",
            "ACTIVE",
            "WEAKENING",
            "FALSIFIED",
        }:
            thesis_state = "ACTIVE"

        decision = self.engine.evaluate(
            DecisionContext(
                company_id=context.company.company_id,
                fundamental_state=self.inputs.fundamental_state,
                valuation_state=self.inputs.valuation_state,
                expectation_state=self.inputs.expectation_state,
                thesis_state=thesis_state,
                evidence_confidence=self._confidence(evidence),
                evidence_ids=[item.evidence_id for item in evidence],
                claim_ids=[claim.claim_id for claim in claims],
                decision_ts=context.decision_ts,
                research_os_version=self.inputs.versions.get(
                    "research_os_version",
                    context.baseline.research_os_version,
                ),
            )
        )
        validate_decision_state(decision.state)
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            artifacts={
                "decision.record": decision,
                "validation.decision": {"status": "PASS"},
            },
            evidence_ids=[item.evidence_id for item in evidence],
        )


class TemporalModule:
    spec = ModuleSpec(
        module_id="core:temporal",
        module_version="1.0.0",
        requires={"decision.record"},
        provides={"temporal.result", "validation.temporal"},
    )

    def __init__(
        self,
        validator: NextVerificationEventValidator | None = None,
        inputs: ResearchInputs | None = None,
    ):
        self.validator = validator or NextVerificationEventValidator()
        self.inputs = inputs or ResearchInputs()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        event = self.inputs.next_verification_event
        if event is None:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "temporal.result": None,
                    "validation.temporal": {"status": "INSUFFICIENT_EVIDENCE"},
                },
            )

        used_ids = [
            item.evidence_id
            for item in context.evidence.as_of(context.decision_ts)
        ]
        result = self.validator.validate(
            event,
            reference_time=context.decision_ts,
            used_evidence_ids=used_ids,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=result.status,
            artifacts={
                "temporal.result": result,
                "validation.temporal": {"status": result.status},
            },
            evidence_ids=used_ids,
        )


def build_builtin_modules(
    *,
    registry: PluginRegistry,
    inputs: ResearchInputs | None = None,
):
    run_inputs = inputs or ResearchInputs()
    capital = CapitalEfficiencyEngine()
    return [
        RepositoryPreflightModule(inputs=run_inputs),
        PITLineageModule(),
        FinancialSanityModule(inputs=run_inputs),
        BusinessModelModule(),
        StrategyResolutionModule(registry=registry),
        IndustryKpiModule(registry=registry),
        CapitalEfficiencyModule(engine=capital),
        FundingLoopModule(engine=capital),
        DriverThesisModule(),
        ExpectationModule(inputs=run_inputs),
        ForecastDisciplineModule(),
        ValuationModule(inputs=run_inputs),
        DecisionModule(inputs=run_inputs),
        TemporalModule(inputs=run_inputs),
    ]
