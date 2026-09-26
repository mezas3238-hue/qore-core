from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

_PATH = (
    Path(__file__).parents[3]
    / "scripts"
    / "cibo_phase18_vt08_r315_policy_replay.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "cibo_phase18_vt08_r315_policy_replay",
    _PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("unable to load VT08 Phase-18 policy replay")
policy = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = policy
_SPEC.loader.exec_module(policy)


def test_vt08_phase18_freezes_certified_sources() -> None:
    assert policy.RISK_SOURCE_SHA == "6a09be314a5c8b6a17822ea141a41d521aaf8655"
    assert policy.HOLDOUT_SOURCE_SHA == (
        "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
    )
    assert policy.REFERENCE_RISK_USD == Decimal("250")


def test_vt08_phase18_target_risk_slow_up_fast_down() -> None:
    at_base = policy.target_risk_bps(
        sleeve="a",
        equity=Decimal("100000"),
        peak_equity=Decimal("100000"),
    )
    in_profit = policy.target_risk_bps(
        sleeve="a",
        equity=Decimal("105000"),
        peak_equity=Decimal("105000"),
    )
    in_drawdown = policy.target_risk_bps(
        sleeve="a",
        equity=Decimal("99000"),
        peak_equity=Decimal("100000"),
    )
    assert at_base == Decimal("25")
    assert in_profit > at_base
    assert in_drawdown < at_base
    assert policy.apply_hysteresis(
        previous_bps=Decimal("25"),
        target_bps_value=Decimal("25.1"),
    ) == Decimal("25")
    assert policy.apply_hysteresis(
        previous_bps=Decimal("25"),
        target_bps_value=Decimal("28"),
    ) == Decimal("25.50")
    assert policy.apply_hysteresis(
        previous_bps=Decimal("25"),
        target_bps_value=Decimal("15"),
    ) == Decimal("20.00")


def test_vt08_phase18_raw_r_respects_geometry() -> None:
    assert policy._raw_r(
        side="long",
        entry=Decimal("100"),
        stop=Decimal("99"),
        exit_price=Decimal("99"),
    ) == Decimal("-1")
    assert policy._raw_r(
        side="short",
        entry=Decimal("100"),
        stop=Decimal("101"),
        exit_price=Decimal("98"),
    ) == Decimal("2")
