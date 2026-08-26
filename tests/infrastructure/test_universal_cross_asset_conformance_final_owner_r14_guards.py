from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _owner_paths,
    _static_integers,
    _static_strings,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r13_guards import (
    _R13DynamicExecutionScanner,
    _selects_dangerous_index,
)


def _merge_values(*values: _Value) -> _Value:
    merged: set[_Atom] = set()
    for value in values:
        merged.update(value)
    return frozenset(merged) if merged else _UNKNOWN


def _static_indices(value: _Value) -> set[int]:
    indices = _static_integers(value)
    indices.update(
        int(atom.text)
        for atom in value
        if atom.kind == "bool-index" and atom.text is not None
    )
    return indices


def _key_tokens(value: _Value) -> set[str]:
    tokens = {f"s:{item}" for item in _static_strings(value)}
    tokens.update(f"i:{item}" for item in _static_indices(value))
    return tokens


def _sequence_lengths(value: _Value) -> set[int]:
    return {
        int(atom.text)
        for atom in value
        if atom.kind == "sequence-length" and atom.text is not None
    }


def _selects_builtins_index(receiver: _Value, index: int) -> bool:
    if _contains_kind(receiver, "builtins-index", str(index)):
        return True
    if index >= 0:
        return False
    return any(
        0 <= length + index < length
        and _contains_kind(receiver, "builtins-index", str(length + index))
        for length in _sequence_lengths(receiver)
    )


class _R14DynamicExecutionScanner(_R13DynamicExecutionScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return frozenset({_Atom("bool-index", str(int(node.value)))})

        if isinstance(node, (ast.Tuple, ast.List)):
            values = [
                self._scan_expression(element, environment)
                for element in node.elts
            ]
            metadata: set[_Atom] = {
                _Atom("sequence-length", str(len(node.elts)))
            }
            for index, value in enumerate(values):
                if _contains_kind(value, "dangerous"):
                    metadata.add(_Atom("dangerous-index", str(index)))
                if _contains_kind(value, "builtins"):
                    metadata.add(_Atom("builtins-index", str(index)))
            return _merge_values(*values, frozenset(metadata))

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

            metadata: set[_Atom] = set()
            for key_value, value in pairs:
                for token in _key_tokens(key_value):
                    if _contains_kind(value, "dangerous"):
                        metadata.add(_Atom("dangerous-key", token))
                    if _contains_kind(value, "builtins"):
                        metadata.add(_Atom("builtins-key", token))

            flattened = [item for pair in pairs for item in pair]
            return _merge_values(*flattened, frozenset(metadata))

        return super()._scan_expression(node, environment)

    def _evaluate_subscript(
        self,
        node: ast.Subscript,
        environment: dict[str, _Value],
    ) -> _Value:
        result = super()._evaluate_subscript(node, environment)
        base = self._scan_expression(node.value, environment)
        key = self._scan_expression(node.slice, environment)
        additions: list[_Atom] = []

        for index in _static_indices(key):
            if _selects_dangerous_index(base, index):
                additions.append(_Atom("dangerous"))
            if _selects_builtins_index(base, index):
                additions.append(_Atom("builtins"))
            if _contains_kind(base, "dangerous-key", f"i:{index}"):
                additions.append(_Atom("dangerous"))
            if _contains_kind(base, "builtins-key", f"i:{index}"):
                additions.append(_Atom("builtins"))

        for key_value in _static_strings(key):
            if _contains_kind(base, "dangerous-key", f"s:{key_value}"):
                additions.append(_Atom("dangerous"))
            if _contains_kind(base, "builtins-key", f"s:{key_value}"):
                additions.append(_Atom("builtins"))

        return _merge_values(result, frozenset(additions)) if additions else result

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        result = super()._evaluate_special_call(helper, arguments)
        additions: list[_Atom] = []

        if (
            helper.kind == "helper"
            and helper.text == "getattr"
            and len(arguments) >= 2
            and _contains_kind(arguments[0], "builtins")
        ):
            for attribute_name in _static_strings(arguments[1]):
                if attribute_name in {"get", "__getitem__"}:
                    additions.append(
                        _Atom("helper", f"builtins-map:{attribute_name}")
                    )

        if (
            helper.kind == "helper"
            and helper.text == "getitem"
            and len(arguments) >= 2
        ):
            receiver, key = arguments[0], arguments[1]
            for index in _static_indices(key):
                if _selects_dangerous_index(receiver, index):
                    additions.append(_Atom("dangerous"))
                if _selects_builtins_index(receiver, index):
                    additions.append(_Atom("builtins"))
                if _contains_kind(receiver, "dangerous-key", f"i:{index}"):
                    additions.append(_Atom("dangerous"))
                if _contains_kind(receiver, "builtins-key", f"i:{index}"):
                    additions.append(_Atom("builtins"))
            for key_value in _static_strings(key):
                if _contains_kind(receiver, "dangerous-key", f"s:{key_value}"):
                    additions.append(_Atom("dangerous"))
                if _contains_kind(receiver, "builtins-key", f"s:{key_value}"):
                    additions.append(_Atom("builtins"))

        if helper.kind == "helper" and helper.text == "itemgetter" and arguments:
            for index in _static_indices(arguments[0]):
                additions.append(_Atom("itemgetter", f"i:{index}"))

        if (
            helper.kind == "itemgetter"
            and helper.text is not None
            and arguments
        ):
            receiver = arguments[0]
            token = helper.text
            if token.startswith("i:"):
                index = int(token[2:])
                if _selects_builtins_index(receiver, index):
                    additions.append(_Atom("builtins"))
                if _contains_kind(receiver, "builtins-key", f"i:{index}"):
                    additions.append(_Atom("builtins"))
            elif token.startswith("s:") and _contains_kind(
                receiver,
                "builtins-key",
                token,
            ):
                additions.append(_Atom("builtins"))

        if (
            helper.kind == "attrgetter"
            and helper.text in {"get", "__getitem__"}
            and arguments
            and _contains_kind(arguments[0], "builtins")
        ):
            additions.append(_Atom("helper", f"builtins-map:{helper.text}"))

        return _merge_values(result, frozenset(additions)) if additions else result


def _r14_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R14DynamicExecutionScanner().scan(source)


def test_r14_builtins_container_extraction_fails_closed() -> None:
    source = """\
import builtins as b
import operator
[b][0].eval("1+1")
operator.getitem([b], 0).exec("pass")
operator.itemgetter(0)([b]).__import__("math")
{"ns": b}["ns"].eval("1+1")
"""

    assert _r14_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:4",
        "call:5",
        "call:6",
    )


def test_r14_builtins_mapping_aliases_via_accessors_fail_closed() -> None:
    source = """\
import builtins
import operator
a = getattr(builtins.__dict__, "get")
a("eval")("1+1")
b = getattr(vars(builtins), "__getitem__")
b("__import__")("math")
c = operator.attrgetter("get")(builtins.__dict__)
c("exec")("pass")
"""

    assert _r14_dynamic_execution_markers_from_source(source) == (
        "call:4",
        "call:6",
        "call:8",
    )


def test_r14_boolean_static_indices_fail_closed() -> None:
    source = """\
import operator
[len, eval][True]("1+1")
operator.itemgetter(True)([len, eval])("1+1")
operator.getitem([len, eval], True)("1+1")
[eval, len][False]("1+1")
"""

    assert _r14_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
        "call:4",
        "call:5",
    )


def test_r14_safe_static_selections_and_accessors_do_not_false_positive() -> None:
    source = """\
import builtins as b
import operator
[len, b][0]("x")
operator.itemgetter(-1)([b, len])("x")
operator.getitem([b, len], -1)("x")
[eval, len][True]("x")
operator.itemgetter(False)([len, eval])("x")
mapping = {"eval": len}
getter = getattr(mapping, "get")
getter("eval")("x")
"""

    assert _r14_dynamic_execution_markers_from_source(source) == ()


def test_r14_preserves_r13_accepted_witnesses() -> None:
    source = """\
import builtins
import operator
operator.itemgetter(-1)([eval])("1+1")
operator.getitem([eval], -1)("1+1")
a = builtins.__dict__.get
a("eval")("1+1")
b = vars(builtins).__getitem__
b("__import__")("math")
"""

    assert _r14_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:4",
        "call:6",
        "call:8",
    )


def test_r14_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r14_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
