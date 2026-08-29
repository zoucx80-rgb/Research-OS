from fastapi.testclient import TestClient
from research_os.api.app import create_app, ResearchReadStore

def test_decision_endpoint_returns_version_and_timestamp():
    store=ResearchReadStore(); store.put("decision-state","001287.SZ",{"state":"WAIT_FOR_CONFIRMATION","research_os_version":"1.1.0","decision_ts":"2026-08-29T08:00:00+00:00"})
    c=TestClient(create_app(store)); r=c.get("/companies/001287.SZ/decision-state")
    assert r.status_code==200
    body=r.json(); assert body["research_os_version"]=="1.1.0" and "decision_ts" in body and "state" in body
