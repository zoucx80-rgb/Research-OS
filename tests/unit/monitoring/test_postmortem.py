from research_os.monitoring.postmortem import PostMortemService

def test_postmortem_answers_five_required_questions():
    p=PostMortemService().build({"forecasts":[{"hit":True}],"drivers":{"a":1},"theses":{"t":"active"},"valuations":{"pe":10}},
                                {"forecasts":[{"hit":False}],"drivers":{"a":2},"theses":{"t":"weakening"},"valuations":{"pe":8}})
    assert p.forecast_hit_summary is not None
    assert p.driver_errors is not None
    assert p.thesis_changes is not None
    assert p.valuation_error_ranking is not None
    assert p.process_change_candidates is not None
