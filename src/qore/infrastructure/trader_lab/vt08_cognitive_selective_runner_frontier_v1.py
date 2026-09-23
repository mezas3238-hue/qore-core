"""VT08-native selective structural runner frontier.

Pre-economic contract is frozen in
VT08_COGNITIVE_EXPANSION_5M_SELECTIVE_RUNNER_V1_FREEZE.md.

The lab transfers Core's *architecture* of structural acceptance + residual
runner while preserving VT08-native levels and the original fixed 2R target.
It uses consumed development evidence only and cannot authorize execution.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    load_market_evidence,
    metrics,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    evaluate_expansion_at_entry_indexed,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
    program_fingerprint,
)
from qore.infrastructure.trader_lab.vt08_cognitive_structural_bank_frontier_v1 import (
    _forward,
    _ordered_path,
    _r,
    _stop_touched,
    _touches,
    _window,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_selective_runner_frontier.v1"
TRAIN_FRACTION: Final = Decimal("0.70")
EQ_FRACTION: Final = Decimal("0.50")
DESTINATION_BANK_FRACTION: Final = Decimal("0.25")
RUNNER_FRACTION: Final = Decimal("0.25")


@dataclass(frozen=True, slots=True)
class SelectiveRunnerTrade:
    baseline: ExpansionTrade
    managed_r: Decimal
    status: str
    equilibrium_r: Decimal | None
    destination_r: Decimal | None
    runner_activated: bool

    def as_trade(self) -> ExpansionTrade:
        return ExpansionTrade(
            symbol=self.baseline.symbol,
            signal_at=self.baseline.signal_at,
            exited_at=self.baseline.exited_at,
            anchor_hour_ny=self.baseline.anchor_hour_ny,
            side=self.baseline.side,
            entry=self.baseline.entry,
            stop=self.baseline.stop,
            target=self.baseline.target,
            exit_price=self.baseline.exit_price,
            exit_reason=f"selective-runner:{self.status}",
            r_multiple=self.managed_r,
        )

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.baseline.symbol,
            "signal_at": self.baseline.signal_at.astimezone(UTC).isoformat(),
            "anchor_hour_ny": self.baseline.anchor_hour_ny,
            "side": self.baseline.side.value,
            "baseline_r": format(self.baseline.r_multiple, "f"),
            "managed_r": format(self.managed_r, "f"),
            "status": self.status,
            "equilibrium_r": (
                None
                if self.equilibrium_r is None
                else format(self.equilibrium_r, "f")
            ),
            "destination_r": (
                None
                if self.destination_r is None
                else format(self.destination_r, "f")
            ),
            "runner_activated": self.runner_activated,
        }


def destination_accepts(
    bar: Vt08B01Bar,
    *,
    side: DemoTradingSetupSide,
    destination: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.close >= destination
    return bar.close <= destination


def _runner_room(
    side: DemoTradingSetupSide,
    *,
    destination: Decimal,
    target: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return target > destination
    return target < destination


def simulate_selective_runner(
    candidate: Vt08ExpansionCandidate,
    *,
    bars_by_open: dict[object, Vt08B01Bar],
) -> SelectiveRunnerTrade | None:
    # Datetime keys are intentionally accepted through object typing so this
    # helper remains tightly coupled to the validated bar map supplied below.
    indexed = {key: value for key, value in bars_by_open.items()}
    baseline = model_trade(candidate, bars_by_open=indexed)  # type: ignore[arg-type]
    if baseline is None:
        return None

    reference = candidate.reference_h4
    equilibrium = (reference.high + reference.low) / Decimal("2")
    destination = (
        reference.high
        if candidate.side is DemoTradingSetupSide.LONG
        else reference.low
    )
    if not (
        _forward(candidate.side, entry=baseline.entry, level=equilibrium)
        and _forward(candidate.side, entry=baseline.entry, level=destination)
        and _ordered_path(
            candidate.side,
            entry=baseline.entry,
            equilibrium=equilibrium,
            destination=destination,
        )
    ):
        return SelectiveRunnerTrade(
            baseline,
            baseline.r_multiple,
            "NO_FORWARD_STRUCTURAL_LADDER",
            None,
            None,
            False,
        )

    eq_r = _r(
        candidate.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=equilibrium,
    )
    destination_r = _r(
        candidate.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=destination,
    )
    rows = _window(candidate, indexed)  # type: ignore[arg-type]
    if rows is None:
        return None

    eq_seen = False
    runner_active = False

    for index, bar in enumerate(rows):
        if _stop_touched(
            bar,
            side=candidate.side,
            stop=baseline.stop,
        ):
            if not eq_seen:
                managed = Decimal("-1")
                status = "INITIAL_STOP_BEFORE_EQ"
            elif runner_active:
                managed = (
                    EQ_FRACTION * eq_r
                    + DESTINATION_BANK_FRACTION * destination_r
                    + RUNNER_FRACTION * Decimal("-1")
                )
                status = "RUNNER_INITIAL_STOP"
            else:
                managed = (
                    EQ_FRACTION * eq_r
                    + (Decimal("1") - EQ_FRACTION) * Decimal("-1")
                )
                status = "EQ_BANK_THEN_INITIAL_STOP"
            return SelectiveRunnerTrade(
                baseline,
                managed,
                status,
                eq_r,
                destination_r,
                runner_active,
            )

        target_touched = _touches(
            bar,
            side=candidate.side,
            level=baseline.target,
        )

        if runner_active:
            if target_touched:
                managed = (
                    EQ_FRACTION * eq_r
                    + DESTINATION_BANK_FRACTION * destination_r
                    + RUNNER_FRACTION * Decimal("2")
                )
                return SelectiveRunnerTrade(
                    baseline,
                    managed,
                    "RUNNER_TO_ORIGINAL_2R",
                    eq_r,
                    destination_r,
                    True,
                )
            continue

        if not eq_seen:
            eq_touched = _touches(
                bar,
                side=candidate.side,
                level=equilibrium,
            )
            if not eq_touched:
                if target_touched:
                    return SelectiveRunnerTrade(
                        baseline,
                        Decimal("2"),
                        "BASELINE_TARGET_BEFORE_EQ",
                        eq_r,
                        destination_r,
                        False,
                    )
                continue
            eq_seen = True
            if target_touched:
                managed = EQ_FRACTION * eq_r + EQ_FRACTION * Decimal("2")
                return SelectiveRunnerTrade(
                    baseline,
                    managed,
                    "EQ_AND_BASELINE_TARGET_SAME_M15",
                    eq_r,
                    destination_r,
                    False,
                )
            continue

        destination_touched = _touches(
            bar,
            side=candidate.side,
            level=destination,
        )
        if target_touched:
            managed = EQ_FRACTION * eq_r + EQ_FRACTION * Decimal("2")
            return SelectiveRunnerTrade(
                baseline,
                managed,
                "EQ_BANK_THEN_BASELINE_TARGET",
                eq_r,
                destination_r,
                False,
            )
        if not destination_touched:
            continue

        accepts = destination_accepts(
            bar,
            side=candidate.side,
            destination=destination,
        )
        if (
            accepts
            and _runner_room(
                candidate.side,
                destination=destination,
                target=baseline.target,
            )
            and index + 1 < len(rows)
        ):
            # Acceptance is known only at this M15 close; runner is observed
            # from the next M15 iteration.
            runner_active = True
            continue

        managed = EQ_FRACTION * eq_r + EQ_FRACTION * destination_r
        return SelectiveRunnerTrade(
            baseline,
            managed,
            "EQ50_DESTINATION50_NO_RUNNER",
            eq_r,
            destination_r,
            False,
        )

    last = rows[-1]
    close_r = _r(
        candidate.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=last.close,
    )
    if not eq_seen:
        return SelectiveRunnerTrade(
            baseline,
            close_r,
            "H4_CLOSE_WITHOUT_EQ",
            eq_r,
            destination_r,
            False,
        )
    if runner_active:
        managed = (
            EQ_FRACTION * eq_r
            + DESTINATION_BANK_FRACTION * destination_r
            + RUNNER_FRACTION * close_r
        )
        status = "RUNNER_H4_CLOSE"
    else:
        managed = EQ_FRACTION * eq_r + EQ_FRACTION * close_r
        status = "EQ_BANK_PLUS_H4_CLOSE_REMAINDER"
    return SelectiveRunnerTrade(
        baseline,
        managed,
        status,
        eq_r,
        destination_r,
        runner_active,
    )


def runner_rows(path: Path) -> tuple[SelectiveRunnerTrade, ...]:
    _, symbol, _, _, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside VT08 5M selective-runner universe")
    bars_by_open = {bar.opened_at: bar for bar in bars}
    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)

    from zoneinfo import ZoneInfo

    ny = ZoneInfo("America/New_York")
    for bar in bars:
        local = bar.opened_at.astimezone(ny)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        evaluation = evaluate_expansion_at_entry_indexed(
            symbol=symbol,
            bars_by_open=bars_by_open,
            decision_at=bar.opened_at,
        )
        if evaluation.candidate is not None:
            candidates_by_day[local.date()].append(evaluation.candidate)

    result: list[SelectiveRunnerTrade] = []
    for local_day in sorted(candidates_by_day):
        candidates = candidates_by_day[local_day]
        if len(candidates) != 1:
            continue
        managed = simulate_selective_runner(
            candidates[0],
            bars_by_open=bars_by_open,
        )
        if managed is not None:
            result.append(managed)
    return tuple(sorted(result, key=lambda item: item.baseline.signal_at))


def _segment(rows: tuple[SelectiveRunnerTrade, ...]) -> dict[str, object]:
    baseline = tuple(row.baseline for row in rows)
    managed = tuple(row.as_trade() for row in rows)
    counts: dict[str, int] = defaultdict(int)
    runner_count = 0
    for row in rows:
        counts[row.status] += 1
        runner_count += int(row.runner_activated)
    return {
        "baseline": metrics(baseline),
        "selective_runner": metrics(managed),
        "status_counts": dict(sorted(counts.items())),
        "runner_activated_count": runner_count,
    }


def replay(path: Path) -> dict[str, object]:
    rows = runner_rows(path)
    if len(rows) < 2:
        raise ValueError("VT08 selective-runner frontier requires terminal trades")
    split = int(Decimal(len(rows)) * TRAIN_FRACTION)
    split = max(1, min(split, len(rows) - 1))
    train = rows[:split]
    consumed_temporal = rows[split:]
    return {
        "schema": SCHEMA,
        "program_fingerprint": program_fingerprint(),
        "market": rows[0].baseline.symbol,
        "research_only": True,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "policy": {
            "equilibrium_bank_fraction": format(EQ_FRACTION, "f"),
            "destination_bank_fraction_when_accepted": format(
                DESTINATION_BANK_FRACTION,
                "f",
            ),
            "runner_fraction": format(RUNNER_FRACTION, "f"),
            "acceptance": "DESTINATION_TOUCH_M15_CLOSES_BEYOND_DESTINATION",
            "runner_effective": "NEXT_M15",
            "runner_target": "ORIGINAL_VT08_FIXED_2R",
            "runner_stop": "ORIGINAL_VT08_STRUCTURAL_STOP",
            "parameter_scan": False,
        },
        "split": {
            "train_fraction": format(TRAIN_FRACTION, "f"),
            "train_count": len(train),
            "consumed_temporal_count": len(consumed_temporal),
            "split_signal_at": consumed_temporal[0].baseline.signal_at.isoformat(),
        },
        "train": _segment(train),
        "consumed_temporal": _segment(consumed_temporal),
        "rows": [row.payload() for row in rows],
        "governance": {
            "current_temporal_segment_fresh": False,
            "new_entry_created": False,
            "trade_count_changed": False,
            "initial_stop_changed": False,
            "stop_widened": False,
            "vt31_dol_definitions_copied": False,
            "vt31_reference_extension_copied": False,
            "vt31_comppressed_selector_copied": False,
            "terminal_pnl_runtime_input": False,
            "future_bar_runtime_input": False,
            "fresh_validation_required_for_promotion": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(replay(path), sort_keys=True, separators=(",", ":"))
