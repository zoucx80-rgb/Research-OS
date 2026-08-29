from .base import MetricResult
from .finance_core import dupont,safe_ratio,turnover_days,average

class ManufacturingPack:
    pack_id="manufacturing"; pack_version="manufacturing@1.0.0"; formula_version="finance-core@2.0.0"
    def calculate(self,f):
        d=dupont(f.get("revenue"),f.get("net_profit_parent"),f.get("assets_begin"),f.get("assets_end"),f.get("equity_begin"),f.get("equity_end"))
        vals={**d,
            "cash_conversion_parent":safe_ratio(f.get("ocf"),f.get("net_profit_parent")) if (f.get("net_profit_parent") or 0)>0 else None,
            "ar_days":turnover_days(f.get("ar_begin"),f.get("ar_end"),f.get("revenue")),
            "inventory_days":turnover_days(f.get("inventory_begin"),f.get("inventory_end"),f.get("cogs")),
            "simple_fcf":None if f.get("ocf") is None or f.get("capex_cash") is None else f["ocf"]-f["capex_cash"],
            "fixed_asset_turnover":safe_ratio(f.get("revenue"),average(f.get("ppe_begin"),f.get("ppe_end"))),
            "capex_intensity":safe_ratio(f.get("capex_cash"),f.get("revenue")),
        }
        return [MetricResult(metric_id=k,value=v,formula_version=self.formula_version,status="valid" if v is not None else "missing") for k,v in vals.items()]
