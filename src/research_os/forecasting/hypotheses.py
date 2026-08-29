from pydantic import BaseModel
class Hypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    economic_mechanism: str
    features: list[str]
    target: str
    expected_direction: str
    test_method: str
    benchmark: str
    registered_before_run: bool=True
