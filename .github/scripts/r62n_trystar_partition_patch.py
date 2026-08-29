from pathlib import Path

path = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = path.read_text()

old_match = (
    "                match = _r62n_handler_match(\n"
    "                    _r62n_exception_name(raised_outcome.state),\n"
    "                    handler.type,\n"
    "                    raised_outcome.state[0],\n"
    "                )\n"
    "                if match is False:\n"
    "                    next_unhandled.append(raised_outcome)\n"
    "                    continue\n"
)
new_match = (
    "                if isinstance(node, ast.TryStar):\n"
    "                    may_handle, fully_handled = _r62n_trystar_handler_partition(\n"
    "                        _r62n_exception_group_members(raised_outcome.state),\n"
    "                        handler.type,\n"
    "                        raised_outcome.state[0],\n"
    "                    )\n"
    "                    match: bool | None = True if may_handle else False\n"
    "                else:\n"
    "                    match = _r62n_handler_match(\n"
    "                        _r62n_exception_name(raised_outcome.state),\n"
    "                        handler.type,\n"
    "                        raised_outcome.state[0],\n"
    "                    )\n"
    "                    fully_handled = match is True\n"
    "                if match is False:\n"
    "                    next_unhandled.append(raised_outcome)\n"
    "                    continue\n"
)
if text.count(old_match) != 1:
    raise SystemExit(f"unexpected failed-star handler match count: {text.count(old_match)}")
text = text.replace(old_match, new_match, 1)

old_tail = (
    "                if match is None:\n"
    "                    next_unhandled.append(raised_outcome)\n"
    "            unhandled = next_unhandled\n\n"
    "        if node.finalbody:\n"
    "            for raised_outcome in unhandled:\n"
    "                final_environment = raised_outcome.state[0].copy()\n"
    "                final_environment.pop(_R62N_EXCEPTION_TAG, None)\n"
    "                self._scan_block(node.finalbody, final_environment)\n\n"
)
new_tail = (
    "                if match is None or not fully_handled:\n"
    "                    next_unhandled.append(raised_outcome)\n"
    "            unhandled = next_unhandled\n\n"
    "        if node.finalbody:\n"
    "            for raised_outcome in unhandled:\n"
    "                final_environment = raised_outcome.state[0].copy()\n"
    "                final_environment.pop(_R62N_EXCEPTION_TAG, None)\n"
    "                self._scan_block(node.finalbody, final_environment)\n\n"
    "        if isinstance(node, ast.TryStar):\n"
    "            completed = _r62n_process_try(\n"
    "                node,\n"
    "                initial,\n"
    "                top_index=0,\n"
    "                timeline={},\n"
    "                observations={},\n"
    "                precision_lost=[False],\n"
    "            )\n"
    "            normal_environments = [\n"
    "                outcome.state[0]\n"
    "                for outcome in completed\n"
    "                if outcome.kind == \"normal\"\n"
    "            ]\n"
    "            if normal_environments:\n"
    "                environment.clear()\n"
    "                self._merge_environments(\n"
    "                    environment,\n"
    "                    *normal_environments,\n"
    "                )\n\n"
)
if text.count(old_tail) != 1:
    raise SystemExit(f"unexpected failed-star tail count: {text.count(old_tail)}")
text = text.replace(old_tail, new_tail, 1)

old_scan = (
    "        if isinstance(node, (ast.Try, ast.TryStar)):\n"
    "            self._scan_flow_failed_star_exception_paths(node, environment)\n"
)
new_scan = (
    "        if (\n"
    "            isinstance(node, ast.TryStar)\n"
    "            and any(\n"
    "                _r62n_contains_runtime_unknown_star(statement)\n"
    "                for statement in node.body\n"
    "            )\n"
    "        ):\n"
    "            original_environment = environment.copy()\n"
    "            self._scan_flow_failed_star_exception_paths(node, environment)\n"
    "            successor_environment = environment.copy()\n"
    "            generic_environment = original_environment.copy()\n"
    "            super()._scan_statement(node, generic_environment)\n"
    "            environment.clear()\n"
    "            environment.update(successor_environment)\n"
    "            return\n"
    "        if isinstance(node, ast.Try):\n"
    "            self._scan_flow_failed_star_exception_paths(node, environment)\n"
)
if text.count(old_scan) != 1:
    raise SystemExit(f"unexpected scan dispatch count: {text.count(old_scan)}")
text = text.replace(old_scan, new_scan, 1)

anchor = "\ndef test_r62n_unknown_star_import_taints_new_call_names() -> None:\n"
if text.count(anchor) != 1:
    raise SystemExit(f"unexpected TryStar regression anchor count: {text.count(anchor)}")
regression = r'''
def test_r62n_failed_star_trystar_partial_groups_and_safe_successors() -> None:
    module_name = "qore_r62n_trystar_partition_regression"
    module = _R62NStarImportModule(module_name)
    module.__all__ = ["b", "missing"]
    module.b = _py_builtins.eval
    sys.modules[module_name] = module
    try:
        handler_safe = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        b = lambda _: 3\n"
            "except* AttributeError:\n"
            "    result = b(\"abc\")\n"
        )
        downstream_safe = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        b = lambda _: 3\n"
            "except* AttributeError:\n"
            "    pass\n"
            "result = b(\"abc\")\n"
        )
        first_handler_danger = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        raise ExceptionGroup(\"eg\", [AttributeError(\"a\"), ValueError(\"v\")])\n"
            "except* AttributeError:\n"
            "    result = b(\"1+1\")\n"
            "except* ValueError:\n"
            "    pass\n"
        )
        second_handler_danger = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        raise ExceptionGroup(\"eg\", [AttributeError(\"a\"), ValueError(\"v\")])\n"
            "except* AttributeError:\n"
            "    pass\n"
            "except* ValueError:\n"
            "    result = b(\"1+1\")\n"
        )
        assert _runtime_result(handler_safe) == 3
        assert _runtime_result(downstream_safe) == 3
        assert _runtime_result(first_handler_danger) == 2
        assert _runtime_result(second_handler_danger) == 2
        assert _r62n_dynamic_execution_markers_from_source(handler_safe) == ()
        assert _r62n_dynamic_execution_markers_from_source(downstream_safe) == ()
        assert "call:8" in _r62n_dynamic_execution_markers_from_source(
            first_handler_danger
        )
        assert "call:10" in _r62n_dynamic_execution_markers_from_source(
            second_handler_danger
        )

        module.__all__ = ["b"]
        module.b = len
        body_danger = (
            "try:\n"
            f"    from {module_name} import *\n"
            "    result = eval(\"1+1\")\n"
            "except* AttributeError:\n"
            "    result = 3\n"
        )
        assert _runtime_result(body_danger) == 2
        assert "call:3" in _r62n_dynamic_execution_markers_from_source(body_danger)
    finally:
        sys.modules.pop(module_name, None)


'''
text = text.replace(anchor, "\n" + regression + anchor.lstrip("\n"), 1)
path.write_text(text)
