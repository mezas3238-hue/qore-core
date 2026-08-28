from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r62d_guards as _r62d
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _owner_paths,
    _static_strings,
    _Value,
)

_R62E_NAMESPACE_HELPERS = frozenset({"globals", "locals", "vars"})
_R62E_MODULE_NAMESPACE_KIND = "r62e-retained-namespace"
_R62E_RETAINED_NAMESPACE: _Value = frozenset(
    {
        _Atom(_R62E_MODULE_NAMESPACE_KIND),
        _Atom("container-kind", "mapping"),
    }
)


def _r62e_helper_value(name: str) -> _Value:
    return frozenset({_Atom("helper", name)})


def _r62e_contains_namespace_helper(value: _Value) -> bool:
    return any(
        _contains_kind(value, "helper", helper_name)
        for helper_name in _R62E_NAMESPACE_HELPERS
    )


class _R62ERetainedNamespaceDefaultScanner(
    _r62d._R62DCallableDefaultEgressScanner
):
    """Close namespace-retaining callable defaults without re-evaluation.

    ``globals()``, ``locals()`` and zero-argument ``vars()`` return live mapping
    objects that can retain execution authority. CPython stores a default object
    itself and exposes it through ``__defaults__`` even when the callable body
    ignores the parameter. The namespace-producing helper callable is likewise
    authority-bearing when retained as a default because it can be invoked after
    extraction.

    Model only the bounded builtin helper identities and their zero-argument
    result. R62D remains authoritative for one-pass default capture: this layer
    changes the abstract value returned by inherited expression evaluation and
    never rescans a default expression.
    """

    def _is_sensitive_default_value(self, value: _Value) -> bool:
        return (
            super()._is_sensitive_default_value(value)
            or _contains_kind(value, _R62E_MODULE_NAMESPACE_KIND)
            or _r62e_contains_namespace_helper(value)
        )

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node, ast.Name)
            and node.id in {"globals", "locals"}
            and node.id not in environment
        ):
            value = _r62e_helper_value(node.id)
            if self._r62d_default_capture_stack:
                self._r62d_default_capture_stack[-1][id(node)] = value
            return value
        return super()._scan_expression(node, environment)

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            node.attr in _R62E_NAMESPACE_HELPERS
            and isinstance(node.value, ast.Name)
        ):
            base = environment.get(
                node.value.id,
                _r12._IMPLICIT_BINDINGS.get(node.value.id, _UNKNOWN),
            )
            if _contains_kind(base, "builtins"):
                return _r62e_helper_value(node.attr)
        return super()._evaluate_attribute(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text in _R62E_NAMESPACE_HELPERS
            and not arguments
        ):
            return _R62E_RETAINED_NAMESPACE

        if (
            helper.kind == "helper"
            and helper.text == "getattr"
            and len(arguments) >= 2
            and _contains_kind(arguments[0], "builtins")
        ):
            attributes = _static_strings(arguments[1])
            namespace_helpers = attributes & _R62E_NAMESPACE_HELPERS
            if len(namespace_helpers) == 1:
                return _r62e_helper_value(next(iter(namespace_helpers)))

        if (
            helper.kind == "helper"
            and helper.text == "getitem"
            and len(arguments) >= 2
            and _contains_kind(arguments[0], "builtins")
        ):
            keys = _static_strings(arguments[1])
            namespace_helpers = keys & _R62E_NAMESPACE_HELPERS
            if len(namespace_helpers) == 1:
                return _r62e_helper_value(next(iter(namespace_helpers)))

        if (
            helper.kind == "itemgetter"
            and helper.text is not None
            and helper.text.startswith("s:")
            and arguments
            and _contains_kind(arguments[0], "builtins")
        ):
            helper_name = helper.text[2:]
            if helper_name in _R62E_NAMESPACE_HELPERS:
                return _r62e_helper_value(helper_name)

        if (
            helper.kind == "attrgetter"
            and helper.text is not None
            and helper.text in _R62E_NAMESPACE_HELPERS
            and arguments
            and _contains_kind(arguments[0], "builtins")
        ):
            return _r62e_helper_value(helper.text)

        return super()._evaluate_special_call(helper, arguments)


def _r62e_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62ERetainedNamespaceDefaultScanner().scan(source)


def test_r62e_predecessor_reproduces_r76_module_namespace_false_negatives() -> None:
    sources = (
        """\
import builtins
def hold(namespace=globals()):
    return None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
import builtins
def hold(namespace=vars()):
    return None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
import builtins
hold = lambda namespace=globals(): None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
import builtins
hold = lambda namespace=vars(): None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
    )

    for source in sources:
        namespace: dict[str, object] = {}
        exec(source, namespace)
        assert namespace["result"] == 2
        assert _r62d._r62d_dynamic_execution_markers_from_source(source) == ()


def test_r62e_module_namespace_function_defaults_fail_closed() -> None:
    sources = (
        """\
import builtins
def hold(namespace=globals()):
    return None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
import builtins
def hold(namespace=locals()):
    return None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
import builtins
def hold(namespace=vars()):
    return None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
    )

    for source in sources:
        namespace: dict[str, object] = {}
        exec(source, namespace)
        assert namespace["result"] == 2
        assert _r62e_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r62e_module_namespace_lambda_defaults_fail_closed() -> None:
    sources = (
        """\
import builtins
hold = lambda namespace=globals(): None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
import builtins
hold = lambda namespace=locals(): None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
import builtins
hold = lambda namespace=vars(): None
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
    )

    for source in sources:
        namespace: dict[str, object] = {}
        exec(source, namespace)
        assert namespace["result"] == 2
        assert _r62e_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r62e_nested_scope_namespace_defaults_fail_closed() -> None:
    sources = (
        """\
import builtins
def outer():
    def hold(namespace=globals()):
        return None
    return hold
hold = outer()
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
def outer():
    import builtins
    def hold(namespace=locals()):
        return None
    return hold
hold = outer()
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
def outer():
    import builtins
    def hold(namespace=vars()):
        return None
    return hold
hold = outer()
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
    )

    for source in sources:
        namespace: dict[str, object] = {}
        exec(source, namespace)
        assert namespace["result"] == 2
        assert "binding:3" in _r62e_dynamic_execution_markers_from_source(source)


def test_r62e_retained_namespace_helper_callables_fail_closed() -> None:
    sources = (
        """\
def hold(candidate=globals):
    return None
namespace = hold.__defaults__[0]()
namespace["__builtins__"]
""",
        """\
def hold(candidate=locals):
    return None
namespace = hold.__defaults__[0]()
namespace["__builtins__"]
""",
        """\
def hold(candidate=vars):
    return None
namespace = hold.__defaults__[0]()
namespace["__builtins__"]
""",
    )

    for source in sources:
        assert _r62e_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62e_builtins_namespace_helpers_fail_closed_as_defaults() -> None:
    sources = (
        "import builtins\ndef hold(candidate=builtins.globals):\n    return None\n",
        "import builtins\ndef hold(candidate=builtins.locals):\n    return None\n",
        "import builtins\ndef hold(candidate=builtins.vars):\n    return None\n",
        'import builtins\ndef hold(candidate=getattr(builtins, "globals")):\n    return None\n',
        'import builtins\ndef hold(candidate=getattr(builtins, "locals")):\n    return None\n',
        'import builtins\ndef hold(candidate=getattr(builtins, "vars")):\n    return None\n',
    )

    for source in sources:
        assert _r62e_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r62e_container_namespace_defaults_fail_closed() -> None:
    sources = (
        "def hold(namespaces=(globals(),)):\n    return None\n",
        'def hold(namespaces={"current": locals()}):\n    return None\n',
        "def hold(helpers=(vars,)):\n    return None\n",
    )

    for source in sources:
        assert _r62e_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62e_shadowed_namespace_helpers_stay_clean() -> None:
    source = """\
def globals():
    return {}
def locals():
    return {}
def vars():
    return {}
def hold(a=globals(), b=locals(), c=vars()):
    return a, b, c
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    hold = namespace["hold"]
    assert callable(hold)
    assert _r62e_dynamic_execution_markers_from_source(source) == ()


def test_r62e_vars_with_explicit_safe_argument_stays_clean() -> None:
    source = """\
class Safe:
    pass
safe = Safe()
def hold(namespace=vars(safe)):
    return None
"""

    assert _r62e_dynamic_execution_markers_from_source(source) == ()


def test_r62e_r62d_regressions_remain_authoritative() -> None:
    direct_default = "def hold(candidate=eval):\n    return None\n"
    importlib_namespace = "import importlib\ndef hold(namespace=importlib):\n    return None\n"
    safe_default = "def hold(candidate=len):\n    return None\n"
    failed_star_keyword = """\
def consume(*arguments, **keywords):
    return arguments, keywords
consume(*None, candidate=eval("1+1"))
"""

    assert _r62e_dynamic_execution_markers_from_source(direct_default) == (
        "binding:1",
    )
    assert _r62e_dynamic_execution_markers_from_source(importlib_namespace) == (
        "binding:2",
    )
    assert _r62e_dynamic_execution_markers_from_source(safe_default) == ()
    assert _r62e_dynamic_execution_markers_from_source(failed_star_keyword) == (
        "call:3",
    )


def test_r62e_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62e_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
