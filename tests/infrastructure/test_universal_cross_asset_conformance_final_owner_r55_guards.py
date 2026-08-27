from __future__ import annotations

import ast
import builtins as _python_builtins

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r38_guards as _r38
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
import test_universal_cross_asset_conformance_final_owner_r41_guards as _r41
import test_universal_cross_asset_conformance_final_owner_r45_guards as _r45
import test_universal_cross_asset_conformance_final_owner_r52_guards as _r52
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)

_R55_PRESENT_KEY_KIND = "r55-present-key"
_R55_MAYBE_MISSING_KEY_KIND = "r55-maybe-missing-key"


def _r55_present_key_tokens(value: _Value) -> set[str]:
    return {
        atom.text
        for atom in value
        if atom.kind == _R55_PRESENT_KEY_KIND and atom.text is not None
    }


def _r55_maybe_missing_key_tokens(value: _Value) -> set[str]:
    return {
        atom.text
        for atom in value
        if atom.kind == _R55_MAYBE_MISSING_KEY_KIND and atom.text is not None
    }


def _r55_selected_slot_tokens(value: _Value) -> set[str]:
    tokens: set[str] = set()
    for atom in value:
        decoded = _r15._decode_selected_slot(atom)
        if decoded is not None:
            tokens.add(decoded[0])
    return tokens


def _r55_decorate_mapping_presence(value: _Value) -> _Value:
    if _r15._container_kind(value) != "mapping":
        return value
    present = frozenset(
        _Atom(_R55_PRESENT_KEY_KIND, token)
        for token in _r55_selected_slot_tokens(value)
    )
    return _r12._merge_values(value, present)


def _r55_merge_alternatives(*values: _Value) -> _Value:
    merged = _r52._r52_merge_alternatives(*values)
    if not values or any(_r15._container_kind(value) != "mapping" for value in values):
        return merged

    possibly_present: set[str] = set()
    definitely_present_by_value: list[set[str]] = []
    for value in values:
        present = _r55_present_key_tokens(value)
        maybe_missing = _r55_maybe_missing_key_tokens(value)
        possibly_present.update(present)
        definitely_present_by_value.append(present - maybe_missing)

    definitely_present = set.intersection(*definitely_present_by_value)
    maybe_missing = possibly_present - definitely_present
    metadata = frozenset(
        _Atom(_R55_MAYBE_MISSING_KEY_KIND, token) for token in maybe_missing
    )
    return _r12._merge_values(merged, metadata)


def _r55_key_may_be_missing(receiver: _Value, key: _Value) -> bool:
    wanted = _r41._r41_selection_tokens(receiver, key)
    return bool(wanted & _r55_maybe_missing_key_tokens(receiver))


def _r55_module_vars_value() -> _Value:
    token = "s:__builtins__"
    metadata = frozenset(
        {
            _Atom("container-kind", "mapping"),
            _Atom(_R55_PRESENT_KEY_KIND, token),
            _r15._selected_slot_atom(token, _Atom("builtins")),
        }
    )
    return metadata


class _R55FallbackReachabilityScanner(_r52._R52SequenceAlternativeScanner):
    def __init__(self) -> None:
        super().__init__()
        self._r55_nested_scope_depth = 0

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.IfExp):
            self._scan_expression(node.test, environment)
            return _r55_merge_alternatives(
                self._scan_expression(node.body, environment),
                self._scan_expression(node.orelse, environment),
            )

        if isinstance(node, ast.Dict):
            return _r55_decorate_mapping_presence(
                super()._scan_expression(node, environment)
            )

        if isinstance(node, ast.Lambda):
            child_environment = environment.copy()
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            ):
                child_environment[argument.arg] = _UNKNOWN
            if node.args.vararg is not None:
                child_environment[node.args.vararg.arg] = _UNKNOWN
            if node.args.kwarg is not None:
                child_environment[node.args.kwarg.arg] = _UNKNOWN
            self._r55_nested_scope_depth += 1
            try:
                self._scan_expression(node.body, child_environment)
            finally:
                self._r55_nested_scope_depth -= 1
            return _UNKNOWN

        return super()._scan_expression(node, environment)

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        for decorator in node.decorator_list:
            self._scan_expression(decorator, environment)
        for default in node.args.defaults:
            self._scan_expression(default, environment)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self._scan_expression(keyword_default, environment)

        child_environment = environment.copy()
        for name in _r12._function_local_names(node):
            child_environment[name] = _UNKNOWN
        self._r55_nested_scope_depth += 1
        try:
            self._scan_block(node.body, child_environment)
        finally:
            self._r55_nested_scope_depth -= 1
        environment[node.name] = _UNKNOWN

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.ClassDef):
            for decorator in node.decorator_list:
                self._scan_expression(decorator, environment)
            child_environment = environment.copy()
            self._r55_nested_scope_depth += 1
            try:
                self._scan_block(node.body, child_environment)
            finally:
                self._r55_nested_scope_depth -= 1
            environment[node.name] = _UNKNOWN
            return
        super()._scan_statement(node, environment)

    def _merge_environments(
        self,
        environment: dict[str, _Value],
        *branches: dict[str, _Value],
    ) -> None:
        names = set(environment)
        for branch in branches:
            names.update(branch)
        for name in names:
            environment[name] = _r55_merge_alternatives(
                *(branch.get(name, _UNKNOWN) for branch in branches)
            )

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
        ):
            receiver = self._scan_expression(node.func.value, environment)
            if _r35._r35_failed(receiver):
                return _r35._FAILURE_VALUE

            kind = _r15._container_kind(receiver)
            if node.func.attr == "get" and _r52._r52_definitely_sequence(receiver):
                return _r35._FAILURE_VALUE

            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE
            if not arguments:
                return _UNKNOWN
            if _r39._r39_has_unknown_positional_shape(arguments):
                return _UNKNOWN

            if kind == "mapping":
                matched, selected = _r41._r41_selected_slots(
                    receiver,
                    arguments[0],
                )
                if matched:
                    if (
                        node.func.attr == "get"
                        and len(arguments) >= 2
                        and _r55_key_may_be_missing(receiver, arguments[0])
                    ):
                        return _r12._merge_values(selected, arguments[1])
                    return selected
                if not _r41._r41_selection_tokens(receiver, arguments[0]):
                    return _UNKNOWN
                if node.func.attr == "get" and len(arguments) >= 2:
                    return arguments[1]
                return _UNKNOWN

            if kind == "sequence" and node.func.attr == "__getitem__":
                matched, selected = _r38._r38_selected_slots(
                    receiver,
                    arguments[0],
                )
                return selected if matched else _UNKNOWN

            if receiver == _r12._BUILTINS_NAMESPACE:
                key = arguments[0]
                if node.func.attr == "get" and len(arguments) >= 2:
                    return _r45._r45_builtins_get_value(key, arguments[1])
                return _r45._r45_builtins_member_value(key)

            return _UNKNOWN

        return super()._evaluate_call(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if helper.kind == "helper" and helper.text == "vars" and not arguments:
            if self._r55_nested_scope_depth == 0:
                return _r55_module_vars_value()
            return _UNKNOWN

        result = super()._evaluate_special_call(helper, arguments)

        if helper.kind != "helper" or helper.text != "getattr" or len(arguments) != 3:
            return result

        target, attribute, default = arguments
        static_attributes = _r12._static_strings(attribute)

        if target == _r12._BUILTINS_NAMESPACE and static_attributes:
            if all(hasattr(_python_builtins, name) for name in static_attributes):
                return result

        if (
            target == _r12._DANGEROUS_CALLABLE
            and static_attributes == {"__call__"}
        ):
            return result

        return _r12._merge_values(result, default)


def _r55_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R55FallbackReachabilityScanner().scan(source)


def test_r55_branch_merged_mapping_missing_key_keeps_default_reachable() -> None:
    source = """\
flag = True
mapping = {} if flag else {"missing": len}
mapping.get("missing", eval)("1+1")
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r55_branch_merged_mapping_present_key_suppresses_default() -> None:
    source = """\
flag = True
mapping = {"missing": len} if flag else {"missing": str}
mapping.get("missing", eval)("x")
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ()


def test_r55_exact_mapping_presence_and_absence_keep_get_semantics() -> None:
    source = """\
{"missing": len}.get("missing", eval)("x")
{}.get("missing", eval)("1+1")
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r55_module_vars_exposes_exact_builtins_binding() -> None:
    source = 'vars()["__builtins__"].__dict__["eval"]("1+1")\n'

    assert _r55_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r55_nested_vars_does_not_invent_module_builtins_binding() -> None:
    source = """\
def f():
    return vars()["__builtins__"]

class C:
    value = vars()["__builtins__"]
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ()


def test_r55_getattr_unknown_target_keeps_positional_default_reachable() -> None:
    source = """\
class Safe:
    pass

getattr(Safe, "missing", eval)("1+1")
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r55_getattr_exact_present_builtin_does_not_use_default() -> None:
    source = """\
import builtins
getattr(builtins, "len", eval)("abc")
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ()


def test_r55_getattr_exact_missing_builtin_uses_default() -> None:
    source = """\
import builtins
getattr(builtins, "qore_definitely_missing", eval)("1+1")
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r55_expert_keyword_getattr_witness_still_fails_before_outer_call() -> None:
    source = """\
import builtins
getattr(object=builtins, name="eval")("1+1")
"""

    assert _r55_dynamic_execution_markers_from_source(source) == ()


def test_r55_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r55_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
