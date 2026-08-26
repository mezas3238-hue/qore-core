from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _function_local_names,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _builtins_member_value,
)
from test_universal_cross_asset_conformance_final_owner_r16_guards import (
    _r16_builtins_get_value,
    _R16DynamicExecutionScanner,
)


class _R17DynamicExecutionScanner(_R16DynamicExecutionScanner):
    def __init__(self) -> None:
        super().__init__()
        self._class_lexical_environments: list[dict[str, _Value]] = []

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        if not self._class_lexical_environments:
            super()._scan_function(node, environment)
            return

        for decorator in node.decorator_list:
            self._scan_expression(decorator, environment)
        for default in node.args.defaults:
            self._scan_expression(default, environment)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self._scan_expression(keyword_default, environment)

        child_environment = self._class_lexical_environments[-1].copy()
        for name in _function_local_names(node):
            child_environment[name] = _UNKNOWN

        lexical_environment = self._class_lexical_environments.pop()
        try:
            self._scan_block(node.body, child_environment)
        finally:
            self._class_lexical_environments.append(lexical_environment)

        environment[node.name] = _UNKNOWN

    def _scan_class_lambda(
        self,
        node: ast.Lambda,
        environment: dict[str, _Value],
    ) -> _Value:
        for default in node.args.defaults:
            self._scan_expression(default, environment)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self._scan_expression(keyword_default, environment)

        child_environment = self._class_lexical_environments[-1].copy()
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

        lexical_environment = self._class_lexical_environments.pop()
        try:
            self._scan_expression(node.body, child_environment)
        finally:
            self._class_lexical_environments.append(lexical_environment)
        return _UNKNOWN

    def _scan_class_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        environment: dict[str, _Value],
    ) -> _Value:
        first_generator = node.generators[0]
        self._scan_expression(first_generator.iter, environment)

        child_environment = self._class_lexical_environments[-1].copy()
        self._assign_target(
            first_generator.target,
            _UNKNOWN,
            child_environment,
        )

        lexical_environment = self._class_lexical_environments.pop()
        try:
            for condition in first_generator.ifs:
                self._scan_expression(condition, child_environment)

            for generator in node.generators[1:]:
                self._scan_expression(generator.iter, child_environment)
                self._assign_target(
                    generator.target,
                    _UNKNOWN,
                    child_environment,
                )
                for condition in generator.ifs:
                    self._scan_expression(condition, child_environment)

            if isinstance(node, ast.DictComp):
                self._scan_expression(node.key, child_environment)
                self._scan_expression(node.value, child_environment)
            else:
                self._scan_expression(node.elt, child_environment)
        finally:
            self._class_lexical_environments.append(lexical_environment)

        return _UNKNOWN

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if self._class_lexical_environments and isinstance(node, ast.Lambda):
            return self._scan_class_lambda(node, environment)

        if self._class_lexical_environments and isinstance(
            node,
            (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp),
        ):
            return self._scan_class_comprehension(node, environment)

        return super()._scan_expression(node, environment)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(node, ast.ClassDef):
            super()._scan_statement(node, environment)
            return

        for decorator in node.decorator_list:
            self._scan_expression(decorator, environment)
        for base in node.bases:
            self._scan_expression(base, environment)
        for keyword in node.keywords:
            self._scan_expression(keyword.value, environment)

        lexical_parent = (
            self._class_lexical_environments[-1]
            if self._class_lexical_environments
            else environment
        )
        class_environment = lexical_parent.copy()
        self._class_lexical_environments.append(lexical_parent.copy())
        try:
            self._scan_block(node.body, class_environment)
        finally:
            self._class_lexical_environments.pop()

        environment[node.name] = _UNKNOWN

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text in {"builtins-map:get", "builtins-map:__getitem__"}
            and arguments
        ):
            if helper.text == "builtins-map:get":
                if len(arguments) >= 2:
                    return _r16_builtins_get_value(
                        arguments[0],
                        arguments[1],
                    )
                return _builtins_member_value(arguments[0])
            return _builtins_member_value(arguments[0])

        return super()._evaluate_special_call(helper, arguments)


def _r17_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R17DynamicExecutionScanner().scan(source)


def test_r17_method_bodies_do_not_close_over_class_locals() -> None:
    source = """\
class Safe:
    eval = lambda value: value

    def run(self):
        eval("1+1")

class Conditional:
    exec = lambda value: value
    if True:
        def run(self):
            exec("pass")

class LambdaCarrier:
    __import__ = lambda value: value
    run = lambda self: __import__("math")
"""

    assert _r17_dynamic_execution_markers_from_source(source) == (
        "call:5",
        "call:11",
        "call:15",
    )


def test_r17_nested_classes_and_comprehensions_use_lexical_parent() -> None:
    source = """\
class Outer:
    eval = lambda value: value

    class Inner:
        def run(self):
            eval("1+1")

class ComprehensionCarrier:
    exec = lambda value: value
    values = [exec("pass") for _ in (0,)]
"""

    assert _r17_dynamic_execution_markers_from_source(source) == (
        "call:6",
        "call:10",
    )


def test_r17_class_body_and_function_local_shadowing_remain_safe() -> None:
    source = """\
class SafeClassBody:
    eval = lambda value: value
    eval("x")

class SafeMethodLocal:
    def run(self):
        eval = lambda value: value
        eval("x")
"""

    assert _r17_dynamic_execution_markers_from_source(source) == ()


def test_r17_class_header_dynamic_execution_is_scanned() -> None:
    source = """\
class DangerousBase(eval("object")):
    pass

class DangerousMeta(metaclass=exec("pass")):
    pass
"""

    assert _r17_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:4",
    )


def test_r17_bound_builtins_get_honors_present_member_dominance() -> None:
    source = """\
import builtins
import operator
getter = builtins.__dict__.get
getter("len", eval)("abc")
getter("missing", eval)("1+1")
getter("eval", len)("1+1")
getattr(builtins.__dict__, "get")("str", exec)("abc")
operator.attrgetter("get")(builtins.__dict__)("abs", eval)(1)
operator.attrgetter("get")(builtins.__dict__)("missing", exec)("pass")
"""

    assert _r17_dynamic_execution_markers_from_source(source) == (
        "call:5",
        "call:6",
        "call:9",
    )


def test_r17_bound_builtins_getitem_preserves_dangerous_members() -> None:
    source = """\
import builtins
getitem = builtins.__dict__.__getitem__
getitem("eval")("1+1")
getattr(builtins.__dict__, "__getitem__")("__import__")("math")
"""

    assert _r17_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:4",
    )


def test_r17_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r17_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
