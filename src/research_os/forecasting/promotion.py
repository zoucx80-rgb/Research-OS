from typing import Literal
from pydantic import BaseModel
ModelStage=Literal["experimental","candidate","validated","production","degraded","retired"]
class PromotionDecision(BaseModel):
    current_stage: ModelStage
    next_stage: ModelStage
    reason: str

def decide_promotion(*,current_stage:ModelStage,model_mae:float,benchmark_mae:float,pit_compliant:bool,stable:bool,hypothesis_registered:bool)->PromotionDecision:
    if not pit_compliant: return PromotionDecision(current_stage=current_stage,next_stage=current_stage,reason="PIT compliance failed")
    if not hypothesis_registered: return PromotionDecision(current_stage=current_stage,next_stage=current_stage,reason="hypothesis was not preregistered")
    if model_mae>=benchmark_mae: return PromotionDecision(current_stage=current_stage,next_stage=current_stage,reason="model did not beat benchmark")
    if not stable: return PromotionDecision(current_stage=current_stage,next_stage=current_stage,reason="stability gate failed")
    if current_stage=="experimental": nxt="candidate"
    elif current_stage=="candidate": nxt="validated"
    elif current_stage=="validated": nxt="production"
    else: nxt=current_stage
    return PromotionDecision(current_stage=current_stage,next_stage=nxt,reason="all promotion gates passed")
