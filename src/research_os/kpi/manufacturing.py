from research_os.period.models import ReportingPeriod
from research_os.period.resolver import resolve_period_days

from .base import MetricResult
from .finance_core import average, dupont, safe_ratio, turnover_days


class ManufacturingPack:
    pack_id = "manufacturing"
    pack_version = "manufacturing@1.1.0"
    formula_version = "finance-core@2.1.0"
    eligible_business_models = ("manufacturing", "manufacturer")
    required_facts = frozenset({"revenue", "net_profit_parent", "assets_begin", "assets_end", "equity_begin", "equity_end"})
    optional_facts = frozenset({
        "ocf", "ar_begin", "ar_end", "inventory_begin", "inventory_end", "cogs", "capex_cash", "ppe_begin", "ppe_end",
        "period_type", "period_start", "period_end", "period_days", "is_cumulative", "reporting_period",
    })
    missing_policy = "preserve_missing"
    valuation_preferences = ("pe", "ev_ebitda", "pb", "sotp", "dcf")
    metric_dependencies = {
        "roe": ["revenue", "net_profit_parent", "assets_begin", "assets_end", "equity_begin", "equity_end"],
        "net_margin": ["revenue", "net_profit_parent"],
        "asset_turnover": ["revenue", "assets_begin", "assets_end"],
        "equity_multiplier": ["assets_begin", "assets_end", "equity_begin", "equity_end"],
        "cash_conversion_parent": ["ocf", "net_profit_parent"],
        "ar_days": ["ar_begin", "ar_end", "revenue"],
        "inventory_days": ["inventory_begin", "inventory_end", "cogs"],
        "simple_fcf": ["ocf", "capex_cash"],
        "fixed_asset_turnover": ["revenue", "ppe_begin", "ppe_end"],
        "capex_intensity": ["capex_cash", "revenue"],
    }

    @staticmethod
    def _period_label(period: ReportingPeriod) -> str | None:
        if period.period_end is not None:
            return f"{period.period_end.year}{period.period_type}"
        return period.period_type or None

    def calculate(self, f):
        period = ReportingPeriod.from_facts(f)
        period_days = resolve_period_days(period)
        period_reason = "PERIOD_LENGTH_REQUIRED" if period_days is None else None
        period_label = self._period_label(period)
        d = dupont(
            f.get("revenue"),
            f.get("net_profit_parent"),
            f.get("assets_begin"),
            f.get("assets_end"),
            f.get("equity_begin"),
            f.get("equity_end"),
        )
        vals = {
            **d,
            "cash_conversion_parent": safe_ratio(f.get("ocf"), f.get("net_profit_parent")) if (f.get("net_profit_parent") or 0) > 0 else None,
            "ar_days": turnover_days(f.get("ar_begin"), f.get("ar_end"), f.get("revenue"), period),
            "inventory_days": turnover_days(f.get("inventory_begin"), f.get("inventory_end"), f.get("cogs"), period),
            "simple_fcf": None if f.get("ocf") is None or f.get("capex_cash") is None else f["ocf"] - f["capex_cash"],
            "fixed_asset_turnover": safe_ratio(f.get("revenue"), average(f.get("ppe_begin"), f.get("ppe_end"))),
            "capex_intensity": safe_ratio(f.get("capex_cash"), f.get("revenue")),
        }
        percent_metrics = {"roe", "net_margin", "capex_intensity"}
        multiple_metrics = {"asset_turnover", "equity_multiplier", "cash_conversion_parent", "fixed_asset_turnover"}
        day_metrics = {"ar_days", "inventory_days"}
        period_sensitive = day_metrics
        results = []
        for metric_id, value in vals.items():
            if metric_id in percent_metrics:
                unit = "percent"
            elif metric_id in multiple_metrics:
                unit = "x"
            elif metric_id in day_metrics:
                unit = "days"
            elif metric_id == "simple_fcf":
                unit = "currency"
            else:
                unit = None
            results.append(
                MetricResult(
                    metric_id=metric_id,
                    value=value,
                    unit=unit,
                    formula_version=self.formula_version,
                    status="valid" if value is not None else "missing",
                    reason_code=(period_reason if value is None and metric_id in period_sensitive else None),
                    period_label=period_label,
                    period_days=period_days,
                    annualized=False,
                )
            )
        return results
