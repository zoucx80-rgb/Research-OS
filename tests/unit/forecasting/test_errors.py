from research_os.forecasting.errors import close_forecast

def test_closed_forecast_records_absolute_error():
    r=close_forecast(metric="revenue",predicted=100,actual=92,period="2026Q3",attribution="demand_error")
    assert r.error==-8 and r.absolute_error==8
