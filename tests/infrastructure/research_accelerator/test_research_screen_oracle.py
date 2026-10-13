"""Frozen synthetic end-to-end screening parity against a chronological brute oracle.

This checks *all* event selections, forward horizons, missing timestamps,
regime diagnostic partitioning and local-extreme placebo, not profitability.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.research_accelerator.core import BidBar
from qore.infrastructure.research_accelerator.experiments import (
    ExperimentSpec,
    Signal,
    causal_local_extremes,
    day_block_interval,
    screen,
)
from qore.infrastructure.research_accelerator.regimes import Regime, label_regimes


def _chronological_oracle(
    bars: tuple[BidBar, ...],
    signals: tuple[Signal, ...],
    horizons: tuple[int, ...],
    regimes: tuple[Regime | None, ...],
    *,
    enforce_anchor: bool,
) -> tuple[
    dict[int, list[tuple[datetime, float]]],
    dict[int, dict[str, list[tuple[datetime, float]]]],
    int,
]:
    """O(N * signals * horizons) direct forward scan, no index or bisect."""
    outcomes: dict[int, list[tuple[datetime, float]]] = {h: [] for h in horizons}
    partitions: dict[int, dict[str, list[tuple[datetime, float]]]] = {
        h: {} for h in horizons
    }
    unmatched = 0
    for signal in signals:
        anchor_index = next(
            (i for i, bar in enumerate(bars) if bar.closed_at == signal.anchor_at),
            None,
        )
        if anchor_index is None:
            unmatched += 1
            continue
        anchor_bar = bars[anchor_index]
        if enforce_anchor:
            assert anchor_bar.close == signal.anchor_price
        for horizon in horizons:
            finish = signal.anchor_at + timedelta(minutes=horizon)
            target = next(
                (b for b in bars[anchor_index + 1:] if b.closed_at == finish),
                None,
            )
            if target is None:
                continue
            signed = 1 if signal.side == "long" else -1
            bps = float(
                (target.close / signal.anchor_price - Decimal("1")) * 10000
            ) * signed
            observation = (signal.anchor_at, bps)
            outcomes[horizon].append(observation)
            regime = regimes[anchor_index]
            if regime is not None:
                key = regime.trend + "/" + regime.volatility + "/" + regime.phase
                partitions[horizon].setdefault(key, []).append(observation)
    return outcomes, partitions, unmatched


def _fixture() -> tuple[tuple[BidBar, ...], tuple[Signal, ...], ExperimentSpec]:
    start = datetime(2024, 1, 8, 14, 30, tzinfo=UTC)
    bars: list[BidBar] = []
    for index in range(2400):
        # Deterministic missing whole-minute candles; MUST NOT interpolate.
        if index % 150 == 87:
            continue
        clock = start + timedelta(minutes=index)
        price = Decimal("100") + Decimal(index % 19) / 100
        bars.append(BidBar(
            clock, price, price + Decimal("0.20"),
            price - Decimal("0.15"), price,
        ))
    signals: list[Signal] = []
    for index in range(40, 2310, 7):
        clock = start + timedelta(minutes=index)
        match = next((b for b in bars if b.closed_at == clock), None)
        if match is None:
            continue
        signals.append(Signal(
            "frozen_" + str(index),
            clock, clock - timedelta(minutes=1),
            "long" if index % 2 else "short",
            match.close,
            {"ob": float(index % 10) / 10},
        ))
    # Last-session signal has a 1-minute witness but no 60-minute witness.
    late = bars[-5]
    signals.append(Signal(
        "truncated_forward", late.closed_at,
        late.closed_at - timedelta(minutes=1),
        "long", late.close, {"ob": .8},
    ))
    # Timestamp with no price witness, diagnostic unmatched not fabricated.
    missing_clock = start + timedelta(days=20)
    signals.append(Signal(
        "no_witness", missing_clock, missing_clock,
        "long", Decimal("100"), {"ob": .8},
    ))
    spec = ExperimentSpec(
        "parity-frozen", (1, 5, 15, 60),
        {"ob": .4}, ("local_extreme",), 100, 17,
    )
    return tuple(bars), tuple(signals), spec


def test_full_directional_screen_and_placebo_parity_against_chronology() -> None:
    bars, signals, spec = _fixture()
    actual = screen(spec, bars, signals)
    selected = tuple(
        s for s in signals
        if all(s.features.get(k, -1) >= v for k, v in spec.feature_min.items())
    )
    regimes = label_regimes(
        bars,
        lookback=spec.regime_lookback,
        trend_ratio_threshold=spec.regime_trend_threshold,
        high_vol_bps=spec.regime_high_vol_bps,
    )
    observed, grouped, unmatched = _chronological_oracle(
        bars, selected, spec.horizons_minutes, regimes, enforce_anchor=True,
    )
    assert actual["signals_total"] == len(signals)
    assert actual["signals_selected"] == len(selected)
    assert actual["unmatched_anchors"] == unmatched == 1

    expected_horizons = {
        str(h): day_block_interval(
            observed[h], draws=spec.block_bootstrap_draws, seed=spec.seed + h,
        ) for h in spec.horizons_minutes
    }
    expected_regimes = {
        str(h): {
            key: day_block_interval(
                values, draws=spec.block_bootstrap_draws, seed=spec.seed + h,
            ) for key, values in grouped[h].items()
        } for h in spec.horizons_minutes
    }
    assert actual["horizons"] == expected_horizons
    assert actual["regime_diagnostics"] == expected_regimes

    placebo = causal_local_extremes(bars)
    sides = {s.side for s in selected}
    placebo = tuple(s for s in placebo if s.side in sides)
    placebo_measurements, _, _ = _chronological_oracle(
        bars, placebo, spec.horizons_minutes, regimes, enforce_anchor=False,
    )
    expected_placebo = {
        str(h): day_block_interval(
            placebo_measurements[h], draws=spec.block_bootstrap_draws,
            seed=spec.seed + h,
        ) for h in spec.horizons_minutes
    }
    assert actual["controls"] == {"local_extreme": expected_placebo}
    assert expected_horizons["1"]["n"] != expected_horizons["60"]["n"]
