from research_os.expectations.surprise import decompose_surprise

def test_profit_beat_with_cfo_miss_is_quality_miss():
    r=decompose_surprise(actual={"net_profit":5.1,"cfo":-175,"inventory":183},expected={"net_profit":4.5,"cfo":-40,"inventory":130},period="2026H1")
    assert r.net_profit_surprise>0
    assert r.cfo_surprise<0
    assert r.label=="HEADLINE_BEAT_QUALITY_MISS"
