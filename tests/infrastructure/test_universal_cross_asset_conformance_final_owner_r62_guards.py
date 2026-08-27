from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r61_guards as _r61
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)


def _r62_direct_keyword_dangerous_reference(
    expression: ast.expr,
    environment: dict[str, _Value],
) -> bool:
    if isinstance(expression, ast.Name):
        value = environment.get(
            expression.id,
            _r12._IMPLICIT_BINDINGS.get(expression.id, _UNKNOWN),
        )
        return _r12._contains_kind(value, "dangerous")

    if (
        isinstance(expression, ast.Attribute)
        and expression.attr in _r12._DYNAMIC_EXECUTION_CALL_NAMES
        and isinstance(expression.value, ast.Name)
    ):
        base = environment.get(
            expression.value.id,
            _r12._IMPLICIT_BINDINGS.get(expression.value.id, _UNKNOWN),
        )
        return _r12._contains_kind(base, "builtins")

    return False


class _R62OpaqueDangerousArgumentScanner(
    _r61._R61UnknownStarredMappingAccessorScanner
):
    """Fail closed when a dangerous callable escapes into an opaque call.

    The scanner already rejects direct execution and binding of dangerous
    builtins.  A direct dangerous callable can also be passed into a locally
    opaque callable and later returned through an abstract container path.
    Preserve all known helper/mapping semantics and add a review marker only
    for opaque ``Name`` calls whose successfully evaluated arguments contain a
    dangerous callable.  Definite argument failure still wins, so unreachable
    later arguments are not promoted to danger.
    """

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if not isinstance(node.func, ast.Name):
            return super()._evaluate_call(node, environment)

        function = self._scan_expression(node.func, environment)
        if function != _UNKNOWN:
            return super()._evaluate_call(node, environment)

        arguments, failed = self._scan_call_arguments(node, environment)
        if failed:
            return _r35._FAILURE_VALUE

        positional_escape = any(
            _r12._contains_kind(argument, "dangerous") for argument in arguments
        )
        keyword_escape = any(
            _r62_direct_keyword_dangerous_reference(keyword.value, environment)
            for keyword in node.keywords
        )
        if positional_escape or keyword_escape:
            self._markers.append(f"dangerous-escape:{node.lineno}")

        return _UNKNOWN


def _r62_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62OpaqueDangerousArgumentScanner().scan(source)


def test_r62_dangerous_callable_cannot_escape_through_opaque_mapping_helper() -> None:
    source = """\
def reveal(arguments, candidate):
    return {"x": candidate}.__getitem__(*arguments)

result = reveal(("x",), eval)("40+2")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 42
    assert _r62_dynamic_execution_markers_from_source(source) == (
        "dangerous-escape:4",
    )


def test_r62_keyword_dangerous_callable_escape_fails_closed() -> None:
    source = """\
def reveal(arguments, candidate):
    return {"x": candidate}.__getitem__(*arguments)

result = reveal(("x",), candidate=eval)("40+2")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 42
    assert _r62_dynamic_execution_markers_from_source(source) == (
        "dangerous-escape:4",
    )


def test_r62_safe_callable_escape_does_not_false_positive() -> None:
    source = """\
def reveal(arguments, candidate):
    return {"x": candidate}.__getitem__(*arguments)

result = reveal(("x",), len)("abcd")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 4
    assert _r62_dynamic_execution_markers_from_source(source) == ()


def test_r62_definite_star_failure_stops_later_dangerous_escape() -> None:
    source = """\
def reveal(*arguments):
    return arguments

reveal(*None, eval)
"""

    assert _r62_dynamic_execution_markers_from_source(source) == ()


def test_r62_known_helper_default_semantics_remain_authoritative() -> None:
    source = """\
import builtins
getattr(builtins, "len", eval)("abc")
"""

    assert _r62_dynamic_execution_markers_from_source(source) == ()


def test_r62_multiple_starred_segments_preserve_dangerous_escape() -> None:
    source = """\
def consume(*arguments):
    return arguments

consume(*("safe",), *(eval,))
"""

    assert _r62_dynamic_execution_markers_from_source(source) == (
        "dangerous-escape:4",
    )


def test_r62_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
