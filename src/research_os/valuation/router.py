from pydantic import BaseModel, Field
from .fitness import ModelFitnessInputs, fitness_score

class RoutedModel(BaseModel):
    model_name: str
    score: float
    status: str

class ValuationContext(BaseModel):
    business_model: str
    models: dict[str,ModelFitnessInputs]

class ValuationRoutingResult(BaseModel):
    models: dict[str,RoutedModel]
    primary_models: list[str]=Field(default_factory=list)
    secondary_models: list[str]=Field(default_factory=list)
    disagreement_diagnosis: str

class ValuationRouter:
    def route(self,context:ValuationContext)->ValuationRoutingResult:
        scores={name:fitness_score(inp) for name,inp in context.models.items()}
        if not scores: return ValuationRoutingResult(models={},disagreement_diagnosis="No applicable valuation model")
        max_score=max(scores.values())
        routed={}; primary=[]; secondary=[]
        for name,score in scores.items():
            # Model-specific business semantics overlay the generic multiplicative score.
            adjusted=score
            if context.business_model=="distributor" and name=="dcf" and context.models[name].cash_flow_visibility<.5:
                adjusted*=.5
            if adjusted>=max_score*.85 and adjusted>=.18: status="PRIMARY"; primary.append(name)
            elif adjusted>=max_score*.55 and adjusted>=.08: status="SECONDARY"; secondary.append(name)
            elif adjusted>=.03: status="SANITY_CHECK"
            elif adjusted>0: status="LOW_CONFIDENCE"
            else: status="NOT_APPLICABLE"
            routed[name]=RoutedModel(model_name=name,score=adjusted,status=status)
        # Re-evaluate primary relative to adjusted score so penalized models cannot remain primary.
        adj_max=max(m.score for m in routed.values())
        primary=[]; secondary=[]
        for name,m in routed.items():
            if m.score>=adj_max*.85 and m.score>=.18: m.status="PRIMARY"; primary.append(name)
            elif m.score>=adj_max*.55 and m.score>=.08: m.status="SECONDARY"; secondary.append(name)
            elif m.status=="PRIMARY": m.status="SANITY_CHECK"
        ordered=sorted(routed,key=lambda n:routed[n].score,reverse=True)
        diag="; ".join(f"{n}:{routed[n].status}:{routed[n].score:.3f}" for n in ordered)
        return ValuationRoutingResult(models=routed,primary_models=primary,secondary_models=secondary,disagreement_diagnosis=diag)
