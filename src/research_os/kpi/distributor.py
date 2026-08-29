from .base import MetricResult
from .finance_core import safe_ratio

def days(avg_balance,flow):
    r=safe_ratio(avg_balance,flow); return None if r is None else r*365

class DistributorPack:
    pack_id="distributor"; pack_version="distributor@1.0.0"; formula_version="distributor-core@1.0.0"
    def calculate(self,f):
        dso=days(f.get("avg_ar"),f.get("revenue")); dio=days(f.get("avg_inventory"),f.get("cogs")); dpo=days(f.get("avg_ap"),f.get("cogs"))
        ccc=None if None in (dso,dio,dpo) else dso+dio-dpo
        nwc=None if None in (f.get("ar"),f.get("inventory"),f.get("ap")) else f["ar"]+f["inventory"]-f["ap"]
        vals={"dso_days":dso,"dio_days":dio,"dpo_days":dpo,"ccc_days":ccc,
              "nwc_intensity":safe_ratio(nwc,f.get("revenue")),
              "incremental_nwc_intensity":safe_ratio(f.get("delta_nwc"),f.get("delta_revenue")),
              "short_debt_to_inventory":safe_ratio(f.get("short_debt"),f.get("inventory")),
              "short_debt_to_equity":safe_ratio(f.get("short_debt"),f.get("equity")),
              "interest_to_gross_profit":safe_ratio(f.get("interest_expense"),f.get("gross_profit")),
              "cash_conversion":safe_ratio(f.get("ocf"),f.get("net_profit")) if (f.get("net_profit") or 0)>0 else None,
              "roic":safe_ratio(f.get("nopat"),f.get("avg_invested_capital"))}
        return [MetricResult(metric_id=k,value=v,formula_version=self.formula_version,status="valid" if v is not None else "missing") for k,v in vals.items()]
