from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r14_guards as _r14
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r16_guards as _r16
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r37_guards as _r37
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _merge_values,
    _owner_paths,
    _static_strings,
    _Value,
)

_NONE_KEY_TOKEN = "n:none"
_EXACT_NON_STRING_KEY_KINDS = frozenset({"bool-index", "integer", "none"})


def _r38_key_tokens(value: _Value) -> set[str]:
    tokens = _r14._key_tokens(value)
    if _contains_kind(value, "none"):
        tokens.add(_NONE_KEY_TOKEN)
    return tokens


def _r38_selection_tokens(receiver: _Value, key: _Value) -> set[str]:
    kind = _r15._container_kind(receiver)
    tokens = {f"s:{item}" for item in _static_strings(key)}
    length = _r15._sequence_length(receiver)

    for index in _r14._static_indices(key):
        resolved = index
        if kind == "sequence" and index < 0 and length is not None:
            resolved = length + index
        tokens.add(f"i:{resolved}")

    if _contains_kind(key, "none"):
        tokens.add(_NONE_KEY_TOKEN)
    return tokens


def _r38_selected_slots(receiver: _Value, key: _Value) -> tuple[bool, _Value]:
    wanted_tokens = _r38_selection_tokens(receiver, key)
    selected: set[_Atom] = set()
    matched = False

    for atom in receiver:
        decoded = _r15._decode_selected_slot(atom)
        if decoded is None:
            continue
        token, value_atom = decoded
        if token in wanted_tokens:
            matched = True
            selected.add(value_atom)

    if not matched:
        return False, _UNKNOWN
    return True, frozenset(selected) if selected else _UNKNOWN


def _r38_sequence_value(values: list[_Value]) -> _Value:
    metadata: set[_Atom] = {
        _Atom("container-kind", "sequence"),
        _Atom("sequence-length", str(len(values))),
    }
    for index, value in enumerate(values):
        token = f"i:{index}"
        for value_atom in value:
            metadata.add(_r15._selected_slot_atom(token, value_atom))
        if _contains_kind(value, "dangerous"):
            metadata.add(_Atom("dangerous-index", str(index)))
        if _contains_kind(value, "builtins"):
            metadata.add(_Atom("builtins-index", str(index)))

    flattened = [_r15._semantic_atoms(value) for value in values]
    return _merge_values(*flattened, frozenset(metadata))


def _r38_builtins_get_value(key: _Value, default: _Value) -> _Value:
    inherited = _r16._r16_builtins_get_value(key, default)
    if inherited != _UNKNOWN:
        return inherited

    if key and all(atom.kind in _EXACT_NON_STRING_KEY_KINDS for atom in key):
        return default
    return _UNKNOWN


class _R38ArgumentExpansionAndMappingScanner(_r37._R37CallFailureAndIndexScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, (ast.Tuple, ast.List)):
            values: list[_Value] = []
            exact = True

            for element in node.elts:
                if isinstance(element, ast.Starred):
                    expanded = self._scan_expression(element.value, environment)
                    if _r35._r35_failed(expanded):
                        return _r35._FAILURE_VALUE
                    items = _r35._r35_exact_sequence_items(expanded)
                    if items is None:
                        exact = False
                        values.append(expanded)
                    else:
                        values.extend(items)
                    continue

                value = self._scan_expression(element, environment)
                if _r35._r35_failed(value):
                    return _r35._FAILURE_VALUE
                values.append(value)

            if not exact:
                return _merge_values(
                    _UNKNOWN,
                    *(_r15._semantic_atoms(value) for value in values),
                )
            return _r38_sequence_value(values)

        if isinstance(node, ast.Dict):
            pairs: list[tuple[_Value, _Value]] = []
            for key_node, value_node in zip(node.keys, node.values, strict=True):
                key_value = (
                    self._scan_expression(key_node, environment)
                    if key_node is not None
                    else _UNKNOWN
                )
                if _r35._r35_failed(key_value):
                    return _r35._FAILURE_VALUE

                value = self._scan_expression(value_node, environment)
                if _r35._r35_failed(value):
                    return _r35._FAILURE_VALUE
                pairs.append((key_value, value))

            selected_by_token: dict[str, _Value] = {}
            for key_value, value in pairs:
                for token in _r38_key_tokens(key_value):
                    selected_by_token[token] = value

            mapping_metadata: set[_Atom] = {_Atom("container-kind", "mapping")}
            for token, selected_value in selected_by_token.items():
                for value_atom in selected_value:
                    mapping_metadata.add(_r15._selected_slot_atom(token, value_atom))
                if _contains_kind(selected_value, "dangerous"):
                    mapping_metadata.add(_Atom("dangerous-key", token))
                if _contains_kind(selected_value, "builtins"):
                    mapping_metadata.add(_Atom("builtins-key", token))

            flattened = [
                _r15._semantic_atoms(item)
                for pair in pairs
                for item in pair
            ]
            return _merge_values(*flattened, frozenset(mapping_metadata))

        return super()._scan_expression(node, environment)

    def _evaluate_non_slice_subscript(
        self,
        receiver: _Value,
        key: _Value,
    ) -> _Value:
        if _r15._container_kind(receiver) is not None:
            matched, selected = _r38_selected_slots(receiver, key)
            return selected if matched else _UNKNOWN
        return super()._evaluate_non_slice_subscript(receiver, key)

    def _scan_call_arguments(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> tuple[list[_Value], bool]:
        positional: list[list[_Value] | None] = [None for _ in node.args]
        ordered: list[tuple[int, int, int, int | None, ast.expr, bool]] = []

        for index, argument in enumerate(node.args):
            is_starred = isinstance(argument, ast.Starred)
            expression = argument.value if is_starred else argument
            ordered.append(
                (
                    getattr(argument, "lineno", node.lineno),
                    getattr(argument, "col_offset", 0),
                    index,
                    index,
                    expression,
                    is_starred,
                )
            )

        keyword_offset = len(node.args)
        for keyword_index, keyword in enumerate(node.keywords):
            expression = keyword.value
            ordered.append(
                (
                    getattr(expression, "lineno", node.lineno),
                    getattr(expression, "col_offset", 0),
                    keyword_offset + keyword_index,
                    None,
                    expression,
                    False,
                )
            )

        ordered.sort(key=lambda item: (item[0], item[1], item[2]))

        for _, _, _, argument_index, expression, is_starred in ordered:
            value = self._scan_expression(expression, environment)
            if _r35._r35_failed(value):
                return [], True
            if argument_index is None:
                continue

            if is_starred:
                items = _r35._r35_exact_sequence_items(value)
                positional[argument_index] = list(items) if items is not None else [_UNKNOWN]
            else:
                positional[argument_index] = [value]

        arguments: list[_Value] = []
        for values in positional:
            arguments.extend(values if values is not None else [_UNKNOWN])
        return arguments, False

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
            if node.func.attr == "get" and kind == "sequence":
                return _r35._FAILURE_VALUE

            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE
            if not arguments:
                return _UNKNOWN

            if _contains_kind(receiver, "builtins"):
                if node.func.attr == "get":
                    if len(arguments) >= 2:
                        return _r38_builtins_get_value(arguments[0], arguments[1])
                    return _r15._builtins_member_value(arguments[0])
                return _r15._builtins_member_value(arguments[0])

            if kind == "mapping" or (
                kind == "sequence" and node.func.attr == "__getitem__"
            ):
                matched, selected = _r38_selected_slots(receiver, arguments[0])
                if matched:
                    return selected
                if (
                    kind == "mapping"
                    and node.func.attr == "get"
                    and len(arguments) >= 2
                ):
                    return arguments[1]
                return _UNKNOWN

            return _UNKNOWN

        return super()._evaluate_call(node, environment)


def _r38_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R38ArgumentExpansionAndMappingScanner().scan(source)


def test_r38_deepseek_exact_starred_call_arguments_are_expanded() -> None:
    source = """\
{}.get(*["missing", eval])("1+1")
{"present": len}.get(*["present", eval])("x")
"""

    assert _r38_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r38_nested_sequence_failure_blocks_later_elements() -> None:
    source = """\
def call_one(arg):
    pass

call_one(([][::0], eval("1+1")))
"""

    assert _r38_dynamic_execution_markers_from_source(source) == ()


def test_r38_reachable_composite_element_before_failure_remains_marked() -> None:
    source = """\
def call_one(arg):
    pass

call_one((eval("1+1"), [][::0]))
"""

    assert _r38_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r38_none_mapping_key_selects_exact_slot() -> None:
    dangerous = """\
{None: eval}[None]("1+1")
"""
    safe = """\
{None: len, "eval": eval}.get(None, eval)("x")
{None: eval, None: len}[None]("x")
"""

    assert _r38_dynamic_execution_markers_from_source(dangerous) == ("call:1",)
    assert _r38_dynamic_execution_markers_from_source(safe) == ()


def test_r38_builtins_get_exact_non_string_miss_uses_default() -> None:
    source = """\
import builtins
builtins.__dict__.get(0, eval)("1+1")
builtins.__dict__.get(None, exec)("pass")
"""

    assert _r38_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
    )


def test_r38_sequence_get_fails_before_arguments_and_outer_call() -> None:
    source = """\
[len, eval].get(1)("1+1")
[len, eval].get(eval("1+1"))("x")
"""

    assert _r38_dynamic_execution_markers_from_source(source) == ()


def test_r38_sequence_dunder_getitem_preserves_exact_selection() -> None:
    source = """\
[len, eval].__getitem__(1)("1+1")
"""

    assert _r38_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r38_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r38_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
