from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_script() -> ModuleType:
    path = Path("scripts/vt31_nas100_post_1r_persistence_forensics_v1.py")
    spec = importlib.util.spec_from_file_location("post_1r_forensics", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bar(*, high: str, low: str, close: str = "100") -> SimpleNamespace:
    return SimpleNamespace(
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_persistence_states_are_semantic_not_optimized_thresholds() -> None:
    module = _load_script()

    assert module._persistence_state(
        [Decimal("1.2"), Decimal("1.1")]
    ) == "PERSISTENT_1R_FLOOR"
    assert module._persistence_state(
        [Decimal("0.8"), Decimal("1.1")]
    ) == "RECOVERED_1R_FLOOR"
    assert module._persistence_state(
        [Decimal("1.1"), Decimal("0.4")]
    ) == "POSITIVE_BELOW_1R"
    assert module._persistence_state(
        [Decimal("0.5"), Decimal("-0.1")]
    ) == "ENTRY_OR_WORSE"


def test_first_1r_touch_censors_same_bar_stop_ambiguity() -> None:
    module = _load_script()

    index, status = module._first_unambiguous_1r_touch(
        [_bar(high="102", low="98")],
        side="long",
        entry=Decimal("100"),
        stop=Decimal("99"),
        risk=Decimal("2"),
    )

    assert index is None
    assert status == "censored-same-bar-1r-vs-stop"


def test_first_1r_touch_requires_thesis_alive() -> None:
    module = _load_script()

    index, status = module._first_unambiguous_1r_touch(
        [
            _bar(high="100.5", low="99.5"),
            _bar(high="102.1", low="99.5"),
        ],
        side="long",
        entry=Decimal("100"),
        stop=Decimal("99"),
        risk=Decimal("2"),
    )

    assert index == 1
    assert status == "observed"


def test_invalidation_before_1r_cannot_become_persistence_observation() -> None:
    module = _load_script()

    index, status = module._first_unambiguous_1r_touch(
        [
            _bar(high="100.5", low="98.5"),
            _bar(high="103", low="100"),
        ],
        side="long",
        entry=Decimal("100"),
        stop=Decimal("99"),
        risk=Decimal("2"),
    )

    assert index is None
    assert status == "invalidated-before-1r"


def test_predeclared_horizons_are_fixed_before_economics() -> None:
    module = _load_script()

    assert module.HORIZONS == (2, 3, 5)
