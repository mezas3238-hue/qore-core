from __future__ import annotations

import ast
import json

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _DYNAMIC_EXECUTION_CALL_NAMES,
    _FULL_CLOSURE_ORACLE_PATH,
    _GETATTR_HELPER,
    _UNKNOWN,
    _VARS_HELPER,
    _Atom,
    _contains_kind,
    _owner_paths,
    _static_strings,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r14_guards import (
    _key_tokens,
    _merge_values,
    _R14DynamicExecutionScanner,
    _static_indices,
)

_STRUCTURAL_KINDS = {
    "builtins-index",
    "builtins-key",
    "container-kind",
    "dangerous-index",
    "dangerous-key",
    "selected-slot",
    "sequence-length",
}


def _selected_slot_atom(token: str, value_atom: _Atom) -> _Atom:
    payload = json.dumps(
        [token, value_atom.kind, value_atom.text],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return _Atom("selected-slot", payload)


def _decode_selected_slot(atom: _Atom) -> tuple[str, _Atom] | None:
    if atom.kind != "selected-slot" or atom.text is None:
        return None
    payload = json.loads(atom.text)
    if not isinstance(payload, list) or len(payload) != 3:
        return None
    token_value, kind_value, text_value = payload
    if not isinstance(token_value, str) or not isinstance(kind_value, str):
        return None
    if text_value is not None and not isinstance(text_value, str):
        return None
    return token_value, _Atom(kind_value, text_value)


def _semantic_atoms(value: _Value) -> _Value:
    return frozenset(atom for atom in value if atom.kind not in _STRUCTURAL_KINDS)


def _container_kind(value: _Value) -> str | None:
    kinds = {
        atom.text
        for atom in value
        if atom.kind == "container-kind" and atom.text is not None
    }
    if len(kinds) == 1:
        return next(iter(kinds))
    return None


def _sequence_length(value: _Value) -> int | None:
    lengths = {
        int(atom.text)
        for atom in value
        if atom.kind == "sequence-length" and atom.text is not None
    }
    if len(lengths) == 1:
        return next(iter(lengths))
    return None


def _selection_tokens(receiver: _Value, key: _Value) -> set[str]:
    kind = _container_kind(receiver)
    tokens = {f"s:{item}" for item in _static_strings(key)}
    length = _sequence_length(receiver)

    for index in _static_indices(key):
        resolved = index
        if kind == "sequence" and index < 0 and length is not None:
            resolved = length + index
        tokens.add(f"i:{resolved}")
    return tokens


def _selected_slots(receiver: _Value, key: _Value) -> tuple[bool, _Value]:
    wanted_tokens = _selection_tokens(receiver, key)
    selected: set[_Atom] = set()
    matched = False

    for atom in receiver:
        decoded = _decode_selected_slot(atom)
        if decoded is None:
            continue
        token, value_atom = decoded
        if token in wanted_tokens:
            matched = True
            selected.add(value_atom)

    if not matched:
        return False, _UNKNOWN
    return True, frozenset(selected) if selected else _UNKNOWN


def _builtins_member_value(key: _Value) -> _Value:
    result: set[_Atom] = set()
    for name in _static_strings(key):
        if name in _DYNAMIC_EXECUTION_CALL_NAMES:
            result.add(_Atom("dangerous"))
        elif name == "getattr":
            result.update(_GETATTR_HELPER)
        elif name == "vars":
            result.update(_VARS_HELPER)
        elif name == "__dict__":
            result.add(_Atom("builtins"))
        else:
            result.add(_Atom("unknown"))
    return frozenset(result) if result else _UNKNOWN


def _selected_static_value(receiver: _Value, key: _Value) -> tuple[bool, _Value]:
    kind = _container_kind(receiver)
    if kind is not None:
        return _selected_slots(receiver, key)
    if _contains_kind(receiver, "builtins"):
        return True, _builtins_member_value(key)
    return False, _UNKNOWN


def _value_from_itemgetter_token(token: str) -> _Value:
    if token.startswith("s:"):
        return frozenset({_Atom("string", token[2:])})
    if token.startswith("i:"):
        return frozenset({_Atom("integer", token[2:])})
    return _UNKNOWN


class _R15DynamicExecutionScanner(_R14DynamicExecutionScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, (ast.Tuple, ast.List)):
            values = [
                self._scan_expression(element, environment)
                for element in node.elts
            ]
            metadata: set[_Atom] = {
                _Atom("container-kind", "sequence"),
                _Atom("sequence-length", str(len(values))),
            }
            for index, value in enumerate(values):
                token = f"i:{index}"
                for value_atom in value:
                    metadata.add(_selected_slot_atom(token, value_atom))
                if _contains_kind(value, "dangerous"):
                    metadata.add(_Atom("dangerous-index", str(index)))
                if _contains_kind(value, "builtins"):
                    metadata.add(_Atom("builtins-index", str(index)))

            flattened = [_semantic_atoms(value) for value in values]
            return _merge_values(*flattened, frozenset(metadata))

        if isinstance(node, ast.Dict):
            pairs: list[tuple[_Value, _Value]] = []
            for key_node, value_node in zip(
                node.keys,
                node.values,
                strict=True,
            ):
                key_value = (
                    self._scan_expression(key_node, environment)
                    if key_node is not None
                    else _UNKNOWN
                )
                value = self._scan_expression(value_node, environment)
                pairs.append((key_value, value))

            selected_by_token: dict[str, _Value] = {}
            for key_value, value in pairs:
                for token in _key_tokens(key_value):
                    selected_by_token[token] = value

            mapping_metadata: set[_Atom] = {_Atom("container-kind", "mapping")}
            for token, selected_value in selected_by_token.items():
                for value_atom in selected_value:
                    mapping_metadata.add(_selected_slot_atom(token, value_atom))
                if _contains_kind(selected_value, "dangerous"):
                    mapping_metadata.add(_Atom("dangerous-key", token))
                if _contains_kind(selected_value, "builtins"):
                    mapping_metadata.add(_Atom("builtins-key", token))

            flattened = [
                _semantic_atoms(item)
                for pair in pairs
                for item in pair
            ]
            return _merge_values(*flattened, frozenset(mapping_metadata))

        return super()._scan_expression(node, environment)

    def _evaluate_subscript(
        self,
        node: ast.Subscript,
        environment: dict[str, _Value],
    ) -> _Value:
        receiver = self._scan_expression(node.value, environment)
        key = self._scan_expression(node.slice, environment)
        handled, selected = _selected_static_value(receiver, key)
        if handled:
            return selected
        return super()._evaluate_subscript(node, environment)

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
            arguments = [
                self._scan_expression(argument, environment)
                for argument in node.args
            ]
            for keyword in node.keywords:
                self._scan_expression(keyword.value, environment)

            if _container_kind(receiver) == "mapping":
                matched, selected = _selected_slots(receiver, arguments[0])
                if matched:
                    return selected
                if node.func.attr == "get" and len(arguments) >= 2:
                    return arguments[1]
                return _UNKNOWN

            handled, selected = _selected_static_value(receiver, arguments[0])
            if handled:
                return selected

        return super()._evaluate_call(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text == "getitem"
            and len(arguments) >= 2
        ):
            handled, selected = _selected_static_value(arguments[0], arguments[1])
            if handled:
                return selected

        if (
            helper.kind == "itemgetter"
            and helper.text is not None
            and arguments
        ):
            key = _value_from_itemgetter_token(helper.text)
            handled, selected = _selected_static_value(arguments[0], key)
            if handled:
                return selected

        if (
            helper.kind == "helper"
            and helper.text in {"builtins-map:get", "builtins-map:__getitem__"}
            and arguments
        ):
            selected = _builtins_member_value(arguments[0])
            if (
                helper.text == "builtins-map:get"
                and selected == _UNKNOWN
                and len(arguments) >= 2
            ):
                return arguments[1]
            return selected

        result = super()._evaluate_special_call(helper, arguments)
        additions: list[_Atom] = []

        if (
            helper.kind == "helper"
            and helper.text == "getattr"
            and len(arguments) >= 2
            and _contains_kind(arguments[0], "builtins")
        ):
            for attribute_name in _static_strings(arguments[1]):
                if attribute_name == "getattr":
                    additions.extend(_GETATTR_HELPER)
                elif attribute_name == "vars":
                    additions.extend(_VARS_HELPER)

        if (
            helper.kind == "attrgetter"
            and arguments
            and _contains_kind(arguments[0], "builtins")
        ):
            if helper.text == "getattr":
                additions.extend(_GETATTR_HELPER)
            elif helper.text == "vars":
                additions.extend(_VARS_HELPER)

        return _merge_values(result, frozenset(additions)) if additions else result


def _r15_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R15DynamicExecutionScanner().scan(source)


def test_r15_mapping_methods_propagate_exact_selected_builtins() -> None:
    source = """\
import builtins as b
{"ns": b}.get("ns").eval("1+1")
{"ns": b}.__getitem__("ns").exec("pass")
{"ns": b}["ns"].__import__("math")
"""

    assert _r15_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
        "call:4",
    )


def test_r15_builtins_helper_identity_survives_mapping_and_operator_access() -> None:
    source = """\
import builtins
import operator
builtins.__dict__.get("getattr")(builtins, "eval")("1+1")
operator.getitem(vars(builtins), "vars")(builtins)["exec"]("pass")
operator.itemgetter("getattr")(builtins.__dict__)(builtins, "__import__")("math")
operator.attrgetter("vars")(builtins)(builtins)["eval"]("1+1")
"""

    assert _r15_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:4",
        "call:5",
        "call:6",
    )


def test_r15_bound_builtins_mapping_alias_preserves_helper_identity() -> None:
    source = """\
import builtins
getter = builtins.__dict__.get
getter("getattr")(builtins, "eval")("1+1")
item = vars(builtins).__getitem__
item("vars")(builtins)["__import__"]("math")
"""

    assert _r15_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:5",
    )


def test_r15_mapping_get_static_default_propagates_dangerous_callable() -> None:
    source = """\
{}.get("missing", eval)("1+1")
{"present": len}.get("present", eval)("x")
"""

    assert _r15_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r15_duplicate_bool_integer_keys_use_python_last_write_wins() -> None:
    safe_source = """\
{False: eval, 0: len}[False]("x")
{True: eval, 1: len}.get(True)("x")
"""
    dangerous_source = """\
{0: len, False: eval}[0]("1+1")
{1: len, True: eval}.get(1)("1+1")
"""

    assert _r15_dynamic_execution_markers_from_source(safe_source) == ()
    assert _r15_dynamic_execution_markers_from_source(dangerous_source) == (
        "call:1",
        "call:2",
    )


def test_r15_safe_mapping_selection_ignores_co_present_sensitive_values() -> None:
    source = """\
import builtins as b
{"ns": b, "safe": len}.get("safe")("x")
{"danger": eval, "safe": len}.__getitem__("safe")("x")
{"danger": eval, "safe": len}["safe"]("x")
"""

    assert _r15_dynamic_execution_markers_from_source(source) == ()


def test_r15_preserves_r14_accepted_witnesses() -> None:
    source = """\
import builtins as b
import operator
[b][0].eval("1+1")
operator.getitem([b], 0).exec("pass")
a = getattr(b.__dict__, "get")
a("eval")("1+1")
[len, eval][True]("1+1")
operator.itemgetter(True)([len, eval])("1+1")
"""

    assert _r15_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:4",
        "call:6",
        "call:7",
        "call:8",
    )


def test_r15_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r15_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
