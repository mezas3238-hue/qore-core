import ast
import inspect

import qore.infrastructure.cibo_sovereign_capital_runtime as module


def test_every_sovereign_decision_constructor_carries_capital_science() -> None:
    tree = ast.parse(inspect.getsource(module))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "CiboSovereignCapitalDecision"
    ]

    assert calls
    for call in calls:
        keywords = {item.arg for item in call.keywords}
        assert "capital_science" in keywords
