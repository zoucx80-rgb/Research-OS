from datetime import date
import pytest
from research_os.thesis.models import Thesis, Falsifier
from research_os.thesis.state_machine import transition_thesis, ThesisTransitionError

def test_active_thesis_requires_falsifier_and_next_check():
    with pytest.raises(ValueError):
        Thesis(thesis_id="t1",company_id="X",title="Growth",statement="s",mechanism="m",status="active",falsifiers=[],next_check_date=None)

def test_falsified_thesis_is_terminal():
    t=Thesis(thesis_id="t1",company_id="X",title="Growth",statement="s",mechanism="m",status="falsified",falsifiers=[Falsifier(metric="cfo",operator="<",threshold=0)],next_check_date=date(2026,9,30))
    with pytest.raises(ThesisTransitionError): transition_thesis(t,"active")
