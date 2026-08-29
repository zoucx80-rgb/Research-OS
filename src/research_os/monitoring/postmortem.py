from pydantic import BaseModel, Field

class ResearchPostMortem(BaseModel):
    forecast_hit_summary: dict
    driver_errors: dict
    thesis_changes: dict
    valuation_error_ranking: list[dict]
    process_change_candidates: list[str]=Field(default_factory=list)

class PostMortemService:
    def build(self,previous:dict,current:dict)->ResearchPostMortem:
        prev_f=previous.get("forecasts",[]); cur_f=current.get("forecasts",[])
        prev_hits=sum(1 for x in prev_f if x.get("hit")); cur_hits=sum(1 for x in cur_f if x.get("hit"))
        pdrivers=previous.get("drivers",{}); cdrivers=current.get("drivers",{})
        driver_errors={k:{"previous":pdrivers.get(k),"current":cdrivers.get(k)} for k in set(pdrivers)|set(cdrivers) if pdrivers.get(k)!=cdrivers.get(k)}
        pth=previous.get("theses",{}); cth=current.get("theses",{})
        thesis_changes={k:{"previous":pth.get(k),"current":cth.get(k)} for k in set(pth)|set(cth) if pth.get(k)!=cth.get(k)}
        pval=previous.get("valuations",{}); cval=current.get("valuations",{})
        ranking=sorted([{"model":k,"change":abs((cval.get(k) or 0)-(pval.get(k) or 0))} for k in set(pval)|set(cval)],key=lambda x:x["change"],reverse=True)
        changes=[]
        if thesis_changes: changes.append("review_thesis_assumptions")
        if driver_errors: changes.append("review_driver_parameters")
        return ResearchPostMortem(forecast_hit_summary={"previous_hits":prev_hits,"current_hits":cur_hits},driver_errors=driver_errors,thesis_changes=thesis_changes,valuation_error_ranking=ranking,process_change_candidates=changes)
