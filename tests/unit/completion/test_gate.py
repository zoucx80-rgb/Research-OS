import importlib
import importlib.util


def _load(name: str):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, f"missing required module {name}"
    return importlib.import_module(name)


def _all_pass(m):
    return {name: "PASS" for name in m.REQUIRED_MODULES}


def test_tool_completion_does_not_override_incomplete_valuation():
    models = _load("research_os.completion.models")
    gate = _load("research_os.completion.gate")
    statuses = _all_pass(gate)
    statuses["Valuation Execution"] = "INSUFFICIENT_EVIDENCE"
    result = gate.ResearchCompletionGate().evaluate(models.ResearchCompletionInput(
        module_statuses=statuses,
        tool_completed=True,
        claimed_conclusions=["valuation", "decision_state"],
    ))
    assert result.final_status == "INCOMPLETE"
    assert "Valuation Execution" in result.blocking_modules


def test_all_required_modules_pass_is_complete():
    models = _load("research_os.completion.models")
    gate = _load("research_os.completion.gate")
    result = gate.ResearchCompletionGate().evaluate(models.ResearchCompletionInput(
        module_statuses=_all_pass(gate),
        tool_completed=False,
        claimed_conclusions=[],
    ))
    assert result.final_status == "COMPLETE"
