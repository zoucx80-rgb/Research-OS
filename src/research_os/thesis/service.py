from __future__ import annotations

from datetime import date, timedelta

from .models import Falsifier, Thesis, ThesisSignalAssessment


OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


class ThesisService:
    _METRIC_ALIASES = {
        "cfo": ("ocf", "operating_cash_flow", "cfo"),
        "ocf": ("ocf", "operating_cash_flow", "cfo"),
        "operating_cash_flow": ("ocf", "operating_cash_flow", "cfo"),
    }

    @staticmethod
    def _values(evidence):
        return {e.source_table or e.evidence_id: e.value for e in evidence}

    @staticmethod
    def _evidence_ids_for(evidence, keys: set[str]) -> list[str]:
        return [
            item.evidence_id
            for item in evidence
            if (item.source_table or item.evidence_id) in keys
        ]

    @classmethod
    def _value_for_metric(cls, values, metric: str):
        for key in cls._METRIC_ALIASES.get(metric, (metric,)):
            if key in values:
                return values[key]
        return None

    @staticmethod
    def _driver_evidence_ids(nodes) -> list[str]:
        result: list[str] = []
        for node in nodes:
            for evidence_id in node.evidence_ids:
                if evidence_id not in result:
                    result.append(evidence_id)
        return result

    def assess_signals(self, evidence) -> ThesisSignalAssessment:
        vals = self._values(evidence)
        positive: list[str] = []
        negative: list[str] = []
        used_keys: set[str] = set()

        directional = (
            ("revenue_growth", "收入增长", True),
            ("margin_change", "利润率改善", True),
            ("roic_change", "资本回报改善", True),
            ("ocf_growth", "经营现金流改善", True),
        )
        for key, label, higher_is_better in directional:
            value = vals.get(key)
            if not isinstance(value, (int, float)) or value == 0:
                continue
            used_keys.add(key)
            improving = value > 0 if higher_is_better else value < 0
            (positive if improving else negative).append(label)

        ocf = vals.get("ocf", vals.get("operating_cash_flow"))
        if isinstance(ocf, (int, float)):
            used_keys.add("ocf" if "ocf" in vals else "operating_cash_flow")
            if ocf > 0:
                positive.append("经营现金流为正")
            elif ocf < 0:
                negative.append("经营现金流为负")

        ar_growth = vals.get("ar_growth")
        revenue_growth = vals.get("revenue_growth")
        if isinstance(ar_growth, (int, float)) and ar_growth > 0:
            used_keys.add("ar_growth")
            if isinstance(revenue_growth, (int, float)):
                used_keys.add("revenue_growth")
                if ar_growth > revenue_growth + 0.10:
                    negative.append("应收增速显著快于收入")
            elif ar_growth >= 0.30:
                negative.append("应收增长较快")

        inventory_growth = vals.get("inventory_growth")
        if isinstance(inventory_growth, (int, float)) and inventory_growth >= 0.30:
            used_keys.add("inventory_growth")
            negative.append("存货增长较快")

        if positive and negative:
            status = "MIXED"
        elif len(positive) >= 2:
            status = "SUPPORTED"
        else:
            status = "INSUFFICIENT"

        return ThesisSignalAssessment(
            status=status,
            positive_signals=positive,
            negative_signals=negative,
            evidence_ids=self._evidence_ids_for(evidence, used_keys),
        )

    def evaluate_existing(self, thesis: Thesis, evidence) -> Thesis:
        vals = self._values(evidence)
        triggered = []
        for falsifier in thesis.falsifiers:
            value = self._value_for_metric(vals, falsifier.metric)
            if isinstance(value, (int, float)) and OPS[falsifier.operator](value, falsifier.threshold):
                triggered.append(falsifier.label())
        if not triggered:
            return thesis
        status = "falsified" if len(triggered) >= 2 else "weakening"
        return thesis.model_copy(update={"status": status, "triggered_falsifiers": triggered})

    def evaluate(self, company_id, evidence, drivers):
        vals = self._values(evidence)
        next_date = max(
            (e.publish_ts.date() for e in evidence),
            default=date.today(),
        ) + timedelta(days=100)

        if any(node.driver_type == "financing" for node in drivers.nodes):
            falsifiers = [Falsifier(metric="ocf", operator="<", threshold=0)]
            if "funding_loop_debt_share" in vals:
                falsifiers.append(
                    Falsifier(
                        metric="funding_loop_debt_share",
                        operator=">=",
                        threshold=0.6,
                        description="新增营运资金对债务融资依赖较高",
                    )
                )
            supporting_nodes = [
                node
                for node in drivers.nodes
                if node.driver_type in {"working_capital", "financing"}
            ]
            thesis = Thesis(
                thesis_id=f"{company_id}:cash-quality",
                company_id=company_id,
                title="Growth converts to cash",
                statement="Growth should improve cash generation rather than depend indefinitely on external funding.",
                mechanism="Revenue growth must translate through working-capital efficiency into operating cash flow.",
                anti_thesis="Growth remains dependent on inventory, receivables and external financing, so cash quality deteriorates.",
                status="active",
                supporting_drivers=[
                    node.driver_id
                    for node in supporting_nodes
                ],
                supporting_evidence=self._driver_evidence_ids(supporting_nodes),
                falsifiers=falsifiers,
                verification_metrics=["ocf", "ccc_days", "funding_loop_debt_share"],
                next_check_date=next_date,
                confidence=0.7,
            )
            return [self.evaluate_existing(thesis, evidence)]

        signals = self.assess_signals(evidence)
        if signals.status == "INSUFFICIENT":
            return []
        if signals.status == "MIXED":
            thesis = Thesis(
                thesis_id=f"{company_id}:mixed-operating-signals",
                company_id=company_id,
                title="Operating signals mixed",
                statement="Operating signals are mixed; wait for further confirmation before asserting directional improvement.",
                mechanism="Positive operating or cash signals are offset by contradictory margin or working-capital evidence.",
                anti_thesis="The contradictory indicators resolve consistently in one direction and establish a reliable operating trend.",
                status="weakening",
                supporting_drivers=[node.driver_id for node in drivers.nodes],
                supporting_evidence=signals.evidence_ids,
                falsifiers=[Falsifier(metric="ocf", operator="<", threshold=0)],
                verification_metrics=["revenue_growth", "margin_change", "ocf"],
                next_check_date=next_date,
                confidence=0.5,
            )
            return [self.evaluate_existing(thesis, evidence)]

        thesis = Thesis(
            thesis_id=f"{company_id}:fundamentals",
            company_id=company_id,
            title="Fundamentals improve",
            statement="Operating fundamentals improve based on multiple directional signals.",
            mechanism="Revenue, margin, capital-efficiency or cash signals consistently point toward improving operating quality.",
            anti_thesis="The apparent improvement reverses or fails to convert into sustainable cash returns.",
            status="active",
            supporting_drivers=[node.driver_id for node in drivers.nodes],
            supporting_evidence=signals.evidence_ids,
            falsifiers=[Falsifier(metric="ocf", operator="<", threshold=0)],
            verification_metrics=["revenue_growth", "margin_change", "ocf"],
            next_check_date=next_date,
            confidence=0.65,
        )
        return [self.evaluate_existing(thesis, evidence)]
