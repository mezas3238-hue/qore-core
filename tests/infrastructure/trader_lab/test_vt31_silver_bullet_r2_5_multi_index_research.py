from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    _market_provider_root,
    _select_provider_symbol_name,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_adjudication import (
    adjudicate,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    HYPOTHESIS_COUNT,
    MARKETS,
    VARIANTS,
    Vt31R25ResearchError,
    _entry,
    _metrics,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22EntryFamily,
    Vt31R22EvidenceClass,
)


@pytest.mark.parametrize(
    ("market", "provider", "root"),
    [
        ("NAS100", "USTEC.cash", "USTEC"),
        ("SP500", "US500.cash", "US500"),
        ("US30", "DJ30", "DJ30"),
    ],
)
def test_multi_index_provider_aliases_are_explicit(
    market: str, provider: str, root: str
) -> None:
    assert _market_provider_root(market, provider) == root


def test_market_alias_selection_rejects_cross_market_and_ambiguity() -> None:
    assert _select_provider_symbol_name(
        "SP500", (("USTEC", True), ("US500", True), ("DJ30", True))
    ) == "US500"
    with pytest.raises(CTraderDemoLabProbeError, match="no enabled explicit"):
        _select_provider_symbol_name("US30", (("US500", True),))
    with pytest.raises(CTraderDemoLabProbeError, match="ambiguous"):
        _select_provider_symbol_name("SP500", (("SP500", True), ("US500", True)))


def _candidate() -> Vt31R22EntryEvidence:
    return Vt31R22EntryEvidence(
        family=Vt31R22EntryFamily.FAIR_VALUE_GAP,
        formed_at=datetime(2026, 1, 2, 15, 5, tzinfo=UTC),
        source_candle_open=Decimal("103"),
        source_candle_high=Decimal("104"),
        source_candle_low=Decimal("102"),
        source_candle_close=Decimal("103"),
        zone_lower=Decimal("100"),
        zone_upper=Decimal("102"),
        zone_class=Vt31R22EvidenceClass.SOURCE_EXPLICIT,
        source_timestamps=("02:26-02:56",),
    )


def test_zone_locations_are_directionally_identical_across_markets() -> None:
    candidate = _candidate()
    assert _entry(candidate, DemoTradingSetupSide.SHORT, "near-stop") == Decimal(102)
    assert _entry(candidate, DemoTradingSetupSide.LONG, "near-stop") == Decimal(100)
    assert _entry(candidate, DemoTradingSetupSide.SHORT, "midpoint") == Decimal(101)
    assert _entry(candidate, DemoTradingSetupSide.LONG, "near-target") == Decimal(102)


def test_predeclared_hypothesis_family_is_complete_and_fingerprinted() -> None:
    assert MARKETS == frozenset({"NAS100", "SP500", "US30"})
    assert HYPOTHESIS_COUNT == 9 == len(VARIANTS)
    assert len({item.variant_id for item in VARIANTS}) == 9
    assert len({item.fingerprint() for item in VARIANTS}) == 9


def test_metrics_apply_friction_per_terminal_trade() -> None:
    trades: list[dict[str, object]] = [
        {"r_multiple": "2"},
        {"r_multiple": "-1"},
        {"r_multiple": "0"},
        {"r_multiple": None},
    ]
    result = _metrics(trades, friction=Decimal("0.05"))
    assert result["sample"] == 3
    assert result["total_r"] == "0.85"
    assert result["mean_r"] == "0.2833333333333333333333333333"


def test_adjudication_requires_all_three_market_reports(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    missing.write_text("{}", encoding="utf-8")
    with pytest.raises(Vt31R25ResearchError, match="unexpected research report schema"):
        adjudicate((missing, missing, missing))
