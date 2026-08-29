from fastapi import FastAPI, HTTPException
class ResearchReadStore:
    def __init__(self): self._data={}
    def put(self,section,company_id,value): self._data[(section,company_id)]=value
    def get(self,section,company_id): return self._data.get((section,company_id))

def create_app(store:ResearchReadStore|None=None)->FastAPI:
    app=FastAPI(title="Research OS",version="1.1.0"); store=store or ResearchReadStore()
    sections=["business-model","drivers","kpi-pack","capital-efficiency","funding-loop","theses","expectations","valuation/fitness","decision-state","evidence-ledger","research-snapshot"]
    def endpoint(section):
        def read(company_id:str):
            v=store.get(section,company_id)
            if v is None: raise HTTPException(status_code=404,detail="research view not found")
            return v
        return read
    for sec in sections:
        app.add_api_route(f"/companies/{{company_id}}/{sec}",endpoint(sec),methods=["GET"],name=sec.replace('/','-'))
    return app
