from datetime import date, timedelta
from .models import Thesis, Falsifier

OPS={"<":lambda a,b:a<b,"<=":lambda a,b:a<=b,">":lambda a,b:a>b,">=":lambda a,b:a>=b,"==":lambda a,b:a==b}

class ThesisService:
    def evaluate_existing(self,thesis:Thesis,evidence)->Thesis:
        vals={e.source_table or e.evidence_id:e.value for e in evidence}
        triggered=[]
        for f in thesis.falsifiers:
            v=vals.get(f.metric)
            if isinstance(v,(int,float)) and OPS[f.operator](v,f.threshold): triggered.append(f.label())
        if not triggered: return thesis
        status="falsified" if len(triggered)>=2 else "weakening"
        return thesis.model_copy(update={"status":status,"triggered_falsifiers":triggered})
    def evaluate(self,company_id,evidence,drivers):
        vals={e.source_table or e.evidence_id:e.value for e in evidence}
        next_date=max((e.publish_ts.date() for e in evidence),default=date.today())+timedelta(days=100)
        if any(n.driver_type=="financing" for n in drivers.nodes):
            f=[Falsifier(metric="cfo",operator="<",threshold=0)]
            t=Thesis(thesis_id=f"{company_id}:cash-quality",company_id=company_id,title="Growth converts to cash",
                statement="Growth should improve cash generation rather than depend indefinitely on external funding.",
                mechanism="Revenue growth must translate through working-capital efficiency into operating cash flow.",status="active",
                supporting_drivers=[n.driver_id for n in drivers.nodes if n.driver_type in {"working_capital","financing"}],
                supporting_evidence=[e.evidence_id for e in evidence],falsifiers=f,verification_metrics=["cfo","ccc_days"],next_check_date=next_date,confidence=.7)
            return [self.evaluate_existing(t,evidence)]
        return [Thesis(thesis_id=f"{company_id}:fundamentals",company_id=company_id,title="Fundamentals improve",
            statement="Operating fundamentals improve.",mechanism="Revenue and margins translate into cash.",status="active",
            supporting_evidence=[e.evidence_id for e in evidence],falsifiers=[Falsifier(metric="cfo",operator="<",threshold=0)],
            verification_metrics=["cfo"],next_check_date=next_date,confidence=.6)]
