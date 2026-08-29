from collections import defaultdict
from research_os.domain.evidence import Evidence
from .models import BusinessModelProfile

class BusinessModelRouter:
    version="router@1.0.0"
    def classify(self,company_id: str,evidence: list[Evidence])->BusinessModelProfile:
        values={e.source_table or e.evidence_id:e.value for e in evidence}
        scores=defaultdict(float)
        desc=str(values.get("business_description","")).lower()
        if any(x in desc for x in ("distribution","distributor","分销","流通")): scores["distributor"]+=0.5
        if any(x in desc for x in ("manufacturing","manufacturer","制造","生产")): scores["manufacturing"]+=0.5
        if any(x in desc for x in ("software","saas","subscription","cloud","软件","订阅")): scores["software"]+=0.7
        if any(x in desc for x in ("consumer","brand","retail","food","beverage","消费","品牌","零售")): scores["consumer"]+=0.7
        if any(x in desc for x in ("mining","resource","commodity","copper","coal","oil","资源","矿业","煤炭","油气")): scores["resource"]+=0.7
        if any(x in desc for x in ("epc","engineering project","system integration","工程","项目制","系统集成")): scores["project"]+=0.7
        if any(x in desc for x in ("bank","insurance","brokerage","financial services","deposits","loans","银行","保险","券商")): scores["financial"]+=0.7
        inv=values.get("inventory_to_revenue")
        fa=values.get("fixed_asset_to_assets")
        gm=values.get("gross_margin")
        if isinstance(inv,(int,float)) and inv>=0.15: scores["distributor"]+=0.2
        if isinstance(fa,(int,float)) and fa<=0.08: scores["distributor"]+=0.15
        if isinstance(gm,(int,float)) and gm<=0.10: scores["distributor"]+=0.15
        if isinstance(fa,(int,float)) and fa>=0.20: scores["manufacturing"]+=0.25
        if isinstance(gm,(int,float)) and gm>=0.15: scores["manufacturing"]+=0.15
        if not scores: scores["unknown"]=0.5
        ranked=sorted(scores.items(),key=lambda x:x[1],reverse=True)
        primary,score=ranked[0]
        secondary=[m for m,s in ranked[1:] if s>=0.3]
        return BusinessModelProfile(company_id=company_id,primary_model=primary,
            secondary_models=secondary,confidence=min(1.0,max(0.5,score)),
            evidence_ids=[e.evidence_id for e in evidence],router_version=self.version)
