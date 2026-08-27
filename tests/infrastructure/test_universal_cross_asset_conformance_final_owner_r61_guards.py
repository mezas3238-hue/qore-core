from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r38_guards as _r38
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
import test_universal_cross_asset_conformance_final_owner_r41_guards as _r41
import test_universal_cross_asset_conformance_final_owner_r60_guards as _r60
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _contains_kind,
    _owner_paths,
    _Value,
)

_SENSITIVE_MAPPING_RESULT_KINDS = frozenset(
    {"builtins", "dangerous", "helper", "itemgetter", "attrgetter"}
)


def _r61_receiver_can_expose_sensitive_callable(receiver: _Value) -> bool:
    return any(atom.kind in _SENSITIVE_MAPPING_RESULT_KINDS for atom in receiver)


class _R61UnknownStarredMappingAccessorScanner(
    _r60._R60StarredHelperArgumentScanner
):
    """Fail closed when unknown starred shapes can hide mapping callables.

    R60 intentionally delegated starred ``.get`` / ``.__getitem__`` calls to
    the inherited R41 mapping path.  That path expands exact starred shapes
    and respects definite failures, but an unknown positional shape degrades
    silently to ``_UNKNOWN``.  Preserve every exact/failure path while adding
    an explicit review marker only where the unresolved accessor can expose a
    callable: ``.get`` (whose unknown shape may carry a callable default), an
    unresolved receiver, or a known container containing sensitive callable
    material.
    """

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if not (
            any(isinstance(argument, ast.Starred) for argument in node.args)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
        ):
            return super()._evaluate_call(node, environment)

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

        if _r39._r39_has_unknown_positional_shape(arguments):
            unresolved_receiver = kind not in {"mapping", "sequence"}
            if (
                node.func.attr == "get"
                or unresolved_receiver
                or _r61_receiver_can_expose_sensitive_callable(receiver)
            ):
                self._markers.append(f"starred-mapping:{node.lineno}")
            return _UNKNOWN

        if kind == "mapping":
            matched, selected = _r41._r41_selected_slots(receiver, arguments[0])
            if matched:
                return selected
            if not _r41._r41_selection_tokens(receiver, arguments[0]):
                return _UNKNOWN
            if node.func.attr == "get" and len(arguments) >= 2:
                return arguments[1]
            return _UNKNOWN

        if kind == "sequence" and node.func.attr == "__getitem__":
            matched, selected = _r38._r38_selected_slots(receiver, arguments[0])
            return selected if matched else _UNKNOWN

        if _contains_kind(receiver, "builtins"):
            if node.func.attr == "get":
                if len(arguments) >= 2:
                    return _r41._r41_builtins_get_value(
                        arguments[0],
                        arguments[1],
                    )
                return _r15._builtins_member_value(arguments[0])
            return _r15._builtins_member_value(arguments[0])

        return _UNKNOWN


def _r61_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R61UnknownStarredMappingAccessorScanner().scan(source)


def test_r61_unknown_starred_builtins_dict_get_fails_closed() -> None:
    source = """\
import builtins
def reveal(arguments):
    return builtins.__dict__.get(*arguments)

reveal(("eval", None))("1+1")
"""

    assert _r61_dynamic_execution_markers_from_source(source) == (
        "starred-mapping:3",
    )


def test_r61_unknown_starred_builtins_dict_getitem_fails_closed() -> None:
    source = """\
import builtins
def reveal(arguments):
    return builtins.__dict__.__getitem__(*arguments)

reveal(("eval",))("2+2")
"""

    assert _r61_dynamic_execution_markers_from_source(source) == (
        "starred-mapping:3",
    )


def test_r61_unknown_starred_sensitive_literal_mapping_fails_closed() -> None:
    source = """\
def reveal(arguments):
    return {"danger": eval, "safe": len}.__getitem__(*arguments)

reveal(("danger",))("1+1")
"""

    assert _r61_dynamic_execution_markers_from_source(source) == (
        "starred-mapping:2",
    )


def test_r61_unknown_starred_safe_sequence_does_not_false_positive() -> None:
    source = """\
def reveal(arguments):
    return [len].__getitem__(*arguments)

reveal((0,))("abc")
"""

    assert _r61_dynamic_execution_markers_from_source(source) == ()


def test_r61_exact_starred_builtins_get_preserves_dangerous_detection() -> None:
    source = """\
import builtins
builtins.__dict__.get(*("eval", None))("1+1")
"""

    assert _r61_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r61_exact_safe_starred_builtins_get_does_not_false_positive() -> None:
    source = """\
import builtins
builtins.__dict__.get(*("len", None))("abc")
"""

    assert _r61_dynamic_execution_markers_from_source(source) == ()


def test_r61_non_iterable_star_fails_before_later_dangerous_default() -> None:
    source = """\
import builtins
builtins.__dict__.get(*None, eval)("1+1")
"""

    assert _r61_dynamic_execution_markers_from_source(source) == ()


def test_r61_r60_generic_unknown_starred_helper_regression_is_preserved() -> None:
    source = """\
def reveal(arguments):
    return getattr(*arguments)
"""

    assert _r61_dynamic_execution_markers_from_source(source) == (
        "starred-helper:2",
    )


def test_r61_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r61_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
