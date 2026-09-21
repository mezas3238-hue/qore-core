"""VT08 Index R108 — STANDARD source-retest execution replay.

R107 closed the main density and risk-demotion branches: the canonical signal
surface is already 2448 / 1017 / 773, while 98-99% of STANDARD trades are at
the 0.005R floor. R108 therefore changes one variable only: execution geometry
for STANDARD setups that offer the source-valid continuation retest already
frozen by R89/R107.

Preregistered causal contract:
- the setup must already exist on the canonical surface;
- retest is an alternate fill of that same setup, never a second signal;
- only STANDARD_WITHOUT_EXTRA_PS is rerouted; Explicit-PS rows remain unchanged;
- the retest level is the R89 continuation breakout level;
- the original Protected Swing remains the stop;
- target remains exactly 2.5R from the retest entry;
- if no causal retest occurs before Protected-Swing invalidation / H4 end, the
  canonical continuation-close fill remains in force;
- R102 control weights are frozen and are not recomputed from retest outcomes;
- because M15 OHLC cannot order a target touch versus the retest touch inside
  the same bar, the retest bar receives no target credit. Economic management
  starts on the next M15 bar. Portfolio MTM nevertheless marks exposure from
  the retest M15 window conservatively;
- no signal, market, side, anchor, POI, year, target, stop, or numeric risk grid
  is searched.

All three windows are consumed evidence. R108 can falsify or support this
execution path, but cannot certify a trader or authorize LIVE/real capital.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r8_priority_poi_rearm_reset as r8,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r80_source_2r_target_transport as r80,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r89_execution_path_coverage as r89,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r107_standard_economic_root_attribution as r107,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r108_standard_source_retest_execution_replay.v1"
IDENTITY = "VT08_INDEX_R108_STANDARD_SOURCE_RETEST_EXECUTION_REPLAY_001"

SOURCE_R107_RUN_ID = 35557537194
SOURCE_R107_ARTIFACT_ID = 10620513767
SOURCE_R107_ARTIFACT_DIGEST = (
    "sha256:ed8e7195ff6641ac23bbd30cac68e6ee3a3ed59f5f6ed60c1a7f06626c6dbe51"
)

TARGET_R = Decimal("2.5")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PRIMARY_PF_GATE = Decimal("1.50")
SECONDARY_PF_GATE = Decimal("1.30")
MAX_MTM_DD_R = Decimal("6")

EXPECTED_STANDARD = {"5Y": 1756, "2Y": 746, "R66": 546}
EXPECTED_RETEST = {"5Y": 1049, "2Y": 452, "R66": 318}
EXPECTED_CANONICAL = {"5Y": 2448, "2Y": 1017, "R66": 773}


def _target_price(
    *,
    entry: Decimal,
    stop: Decimal,
    side: DemoTradingSetupSide,
) -> Decimal:
    risk = abs(entry - stop)
    if side is DemoTradingSetupSide.LONG:
        return entry + TARGET_R * risk
    return entry - TARGET_R * risk


def _build_retest_signal(
    signal: v6.CandidateSignal,
    *,
    retest_level: Decimal,
    retest_window_opened_at: datetime,
) -> v6.CandidateSignal:
    if signal.stop != signal.protected_swing_extreme:
        raise ValueError("R108 canonical stop is not the Protected Swing")
    if signal.side is DemoTradingSetupSide.LONG and retest_level <= signal.stop:
        raise ValueError("R108 LONG retest must remain above Protected Swing")
    if signal.side is DemoTradingSetupSide.SHORT and retest_level >= signal.stop:
        raise ValueError("R108 SHORT retest must remain below Protected Swing")
    return replace(
        signal,
        signal_at=retest_window_opened_at.astimezone(UTC),
        entry=retest_level,
        stop=signal.stop,
        target=_target_price(
            entry=retest_level,
            stop=signal.stop,
            side=signal.side,
        ),
    )


def _manage_retest(
    signal: v6.CandidateSignal,
    *,
    fill_bar: Vt08IndexC2R1Bar,
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
) -> r5.ManagedTrade:
    """Replay from the next M15 bar; same-fill-bar target credit is forbidden."""

    management_signal = replace(
        signal,
        signal_at=fill_bar.closed_at.astimezone(UTC),
    )
    outcome = r5._manage_trade(
        management_signal,
        bars=bars,
        opened=opened,
        policy=r8._target_policy(TARGET_R),
    )
    return replace(
        outcome,
        signal_at=fill_bar.opened_at.astimezone(UTC),
    )


def _weighted_metrics(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return r80._weighted_metrics(assigned, stress=stress)


def _periods(
    assigned: Sequence[r15.AssignedTrade],
    *,
    window_id: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    boundaries = r80._boundaries(
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    prefix = "B" if window_id == "R66" else "Y"
    result: dict[str, Any] = {}
    for index in range(len(boundaries) - 1):
        block_start = boundaries[index]
        block_end = boundaries[index + 1]
        rows = [
            item
            for item in assigned
            if block_start
            <= item.exited_at.astimezone(v7._NY).date()
            < block_end
        ]
        result[f"{prefix}{index + 1}"] = {
            "start_date": block_start.isoformat(),
            "end_date_exclusive": block_end.isoformat(),
            "sample": len(rows),
            "primary": _weighted_metrics(rows, stress=PRIMARY_STRESS),
            "secondary": _weighted_metrics(rows, stress=SECONDARY_STRESS),
        }
    return result


def _bundle(
    assigned: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
    window_id: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    primary = _weighted_metrics(assigned, stress=PRIMARY_STRESS)
    secondary = _weighted_metrics(assigned, stress=SECONDARY_STRESS)
    primary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=PRIMARY_STRESS,
        adverse=True,
    )
    secondary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=SECONDARY_STRESS,
        adverse=True,
    )
    periods = _periods(
        assigned,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    all_primary_positive = all(
        Decimal(str(row["primary"]["total_r"])) > 0
        for row in periods.values()
    )
    all_secondary_positive = all(
        Decimal(str(row["secondary"]["total_r"])) > 0
        for row in periods.values()
    )
    return {
        "sample": len(assigned),
        "primary": primary,
        "secondary": secondary,
        "primary_conservative_mtm": primary_mtm,
        "secondary_conservative_mtm": secondary_mtm,
        "periods": periods,
        "all_primary_periods_positive": all_primary_positive,
        "all_secondary_periods_positive": all_secondary_positive,
    }


def _cohort_bundle(
    rows: Sequence[r15.AssignedTrade],
) -> dict[str, Any]:
    return {
        "sample": len(rows),
        "primary": _weighted_metrics(rows, stress=PRIMARY_STRESS),
        "secondary": _weighted_metrics(rows, stress=SECONDARY_STRESS),
    }


def _breakdowns(
    assigned: Sequence[r15.AssignedTrade],
    *,
    meta: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    selectors = {
        "family": lambda item: str(meta[item.trade_id]["execution_family"]),
        "market": lambda item: item.symbol,
        "side": lambda item: item.opportunity.signal.side.value,
        "anchor": lambda item: str(
            item.opportunity.signal.h4_opened_at.astimezone(v7._NY).hour
        ),
        "poi": lambda item: str(item.opportunity.source_poi_kind),
    }
    report: dict[str, Any] = {}
    for name, selector in selectors.items():
        grouped: dict[str, list[r15.AssignedTrade]] = defaultdict(list)
        for item in assigned:
            grouped[str(selector(item))].append(item)
        report[name] = {
            label: _cohort_bundle(rows)
            for label, rows in sorted(grouped.items())
        }
    return report


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = r74._window_contract(window_id)
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        key: tuple(value)
        for key, value in bars_by_symbol_raw.items()
    }
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        for symbol, bars in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _control_diag = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected or expected != EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R108 {window_id} canonical sample drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    if len(standard_ids) != EXPECTED_STANDARD[window_id]:
        raise ValueError(f"R108 {window_id} STANDARD sample drift")

    h4_cache = {
        symbol: r82._h4_bar_cache(symbol_bars)
        for symbol, symbol_bars in bars_by_symbol.items()
    }

    replayed: list[r15.AssignedTrade] = []
    meta: dict[int, dict[str, Any]] = {}
    retest_improvements: list[Decimal] = []
    retest_count = 0

    for item in control:
        identity = item.opportunity.identity()
        if identity not in standard_ids:
            replayed.append(item)
            meta[item.trade_id] = {
                "execution_family": "EXPLICIT_PS_UNCHANGED",
                "retest_available": False,
                "fallback_to_close": False,
            }
            continue

        signal = item.opportunity.signal
        inside = h4_cache[item.symbol].get(
            signal.h4_opened_at.astimezone(UTC)
        )
        if inside is None:
            raise ValueError("R108 canonical H4 not found")

        continuation_index = next(
            (
                index
                for index, bar in enumerate(inside)
                if bar.closed_at.astimezone(UTC)
                == signal.signal_at.astimezone(UTC)
            ),
            None,
        )
        if continuation_index is None or continuation_index <= 0:
            raise ValueError("R108 continuation bar not found")

        retest_index = r89._retest_fill_index(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
            protected_swing=signal.protected_swing_extreme,
            model_kind=signal.model_kind,
            h4_open=inside[0].open,
        )
        if retest_index is None:
            replayed.append(item)
            meta[item.trade_id] = {
                "execution_family": "STANDARD_CLOSE_FALLBACK",
                "retest_available": False,
                "fallback_to_close": True,
            }
            continue

        retest_level = r89._continuation_breakout_level(
            inside,
            continuation_index=continuation_index,
            side=signal.side,
        )
        fill_bar = inside[retest_index]
        new_signal = _build_retest_signal(
            signal,
            retest_level=retest_level,
            retest_window_opened_at=fill_bar.opened_at,
        )
        new_outcome = _manage_retest(
            new_signal,
            fill_bar=fill_bar,
            bars=bars_by_symbol[item.symbol],
            opened=opened_by_symbol[item.symbol],
        )
        new_opportunity = replace(
            item.opportunity,
            signal=new_signal,
        )
        replayed_item = replace(
            item,
            opportunity=new_opportunity,
            outcome=new_outcome,
        )
        replayed.append(replayed_item)

        original_risk = abs(signal.entry - signal.stop)
        new_risk = abs(new_signal.entry - new_signal.stop)
        improvement_fraction = (
            (original_risk - new_risk) / original_risk
            if original_risk > 0
            else Decimal()
        )
        retest_improvements.append(improvement_fraction)
        retest_count += 1
        meta[item.trade_id] = {
            "execution_family": "STANDARD_RETEST",
            "retest_available": True,
            "fallback_to_close": False,
            "retest_window_opened_at": (
                fill_bar.opened_at.astimezone(UTC).isoformat()
            ),
            "retest_level": str(retest_level),
            "entry_improvement_risk_fraction": str(improvement_fraction),
        }

    replayed_tuple = tuple(replayed)
    if len(replayed_tuple) != len(control):
        raise ValueError("R108 replay changed trade count")
    if retest_count != EXPECTED_RETEST[window_id]:
        raise ValueError(f"R108 {window_id} retest coverage drift")

    before_weights = {
        item.trade_id: item.weight
        for item in control
    }
    after_weights = {
        item.trade_id: item.weight
        for item in replayed_tuple
    }
    if before_weights != after_weights:
        raise ValueError("R108 frozen R102 weights changed")

    baseline = _bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    replay = _bundle(
        replayed_tuple,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )

    retest_rows = [
        item
        for item in replayed_tuple
        if meta[item.trade_id]["execution_family"] == "STANDARD_RETEST"
    ]
    fallback_rows = [
        item
        for item in replayed_tuple
        if meta[item.trade_id]["execution_family"]
        == "STANDARD_CLOSE_FALLBACK"
    ]
    explicit_rows = [
        item
        for item in replayed_tuple
        if meta[item.trade_id]["execution_family"] == "EXPLICIT_PS_UNCHANGED"
    ]

    primary_pf = Decimal(str(replay["primary"]["profit_factor"] or "0"))
    secondary_pf = Decimal(str(replay["secondary"]["profit_factor"] or "0"))
    primary_dd = Decimal(
        str(replay["primary_conservative_mtm"]["max_drawdown_r"])
    )
    secondary_dd = Decimal(
        str(replay["secondary_conservative_mtm"]["max_drawdown_r"])
    )
    gate = {
        "density_pass": len(replayed_tuple) == expected,
        "primary_pf_pass": primary_pf >= PRIMARY_PF_GATE,
        "secondary_pf_pass": secondary_pf >= SECONDARY_PF_GATE,
        "primary_mtm_dd_pass": primary_dd <= MAX_MTM_DD_R,
        "secondary_mtm_dd_pass": secondary_dd <= MAX_MTM_DD_R,
        "all_primary_periods_positive": replay[
            "all_primary_periods_positive"
        ],
        "all_secondary_periods_positive": replay[
            "all_secondary_periods_positive"
        ],
    }
    gate["economic_temporal_pass"] = all(gate.values())

    mean_improvement = (
        sum(retest_improvements, Decimal())
        / Decimal(len(retest_improvements))
        if retest_improvements
        else Decimal()
    )

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "standard_sample": len(standard_ids),
        "explicit_ps_sample": expected - len(standard_ids),
        "retest_execution": {
            "available_count": retest_count,
            "available_fraction_of_standard": str(
                Decimal(retest_count) / Decimal(len(standard_ids))
            ),
            "close_fallback_count": len(fallback_rows),
            "same_setup_trade_count_added": 0,
            "mean_entry_improvement_risk_fraction": str(mean_improvement),
            "retest_bar_target_credit_allowed": False,
            "fill_time_precision": "M15_WINDOW_CONSERVATIVE",
        },
        "baseline_fixed_r102_weights": baseline,
        "retest_fixed_r102_weights": replay,
        "cohorts": {
            "standard_retest": _cohort_bundle(retest_rows),
            "standard_close_fallback": _cohort_bundle(fallback_rows),
            "explicit_ps_unchanged": _cohort_bundle(explicit_rows),
        },
        "breakdowns": _breakdowns(
            replayed_tuple,
            meta=meta,
        ),
        "gate": gate,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r107.IDENTITY != (
        "VT08_INDEX_R107_STANDARD_ECONOMIC_ROOT_ATTRIBUTION_001"
    ):
        raise ValueError("R108 R107 identity drift")
    if r107.SOURCE_R106_RUN_ID != 35557035781:
        raise ValueError("R108 R107 predecessor drift")
    if r80.CANONICAL_TARGET_R != TARGET_R:
        raise ValueError("R108 canonical 2.5R target drift")
    if tuple(r4.V7_ANCHORS) != (22, 2, 6, 10):
        raise ValueError("R108 Owner anchor contract drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    r66_before_b2 = failed["baseline_fixed_r102_weights"]["periods"]["B2"][
        "secondary"
    ]
    r66_after_b2 = failed["retest_fixed_r102_weights"]["periods"]["B2"][
        "secondary"
    ]
    r66_b2_delta = (
        Decimal(str(r66_after_b2["total_r"]))
        - Decimal(str(r66_before_b2["total_r"]))
    )

    transport_pass = bool(five["gate"]["economic_temporal_pass"]) and bool(
        two["gate"]["economic_temporal_pass"]
    )
    r66_blocks_positive = bool(
        failed["retest_fixed_r102_weights"]["all_primary_periods_positive"]
    ) and bool(
        failed["retest_fixed_r102_weights"]["all_secondary_periods_positive"]
    )

    decision = (
        "R108_RETEST_EXECUTION_TRANSPORTS_ON_CONSUMED_WINDOWS_NO_CANDIDATE"
        if transport_pass and r66_blocks_positive
        else "R108_RETEST_EXECUTION_REPLAY_COMPLETE_NO_CANDIDATE"
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r107": {
            "run_id": SOURCE_R107_RUN_ID,
            "artifact_id": SOURCE_R107_ARTIFACT_ID,
            "artifact_digest": SOURCE_R107_ARTIFACT_DIGEST,
        },
        "preregistered_contract": {
            "same_setup_only": True,
            "retest_creates_second_trade": False,
            "standard_only_rerouted": True,
            "explicit_ps_unchanged": True,
            "no_retest_fallback": "CANONICAL_CONTINUATION_CLOSE",
            "stop": "SAME_PROTECTED_SWING",
            "target_r": str(TARGET_R),
            "risk_allocator": "R102_FIXED_WEIGHTS_NO_RECOMPUTE",
            "retest_bar_target_credit": False,
            "same_bar_rule_reason": (
                "M15 OHLC cannot order target touch versus intrabar retest fill"
            ),
            "target_grid_searched": False,
            "stop_grid_searched": False,
            "risk_grid_searched": False,
            "market_side_anchor_calendar_selection": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "r66_b2_secondary_total_r_delta": str(r66_b2_delta),
        "transport": {
            "five_year_gate_pass": five["gate"]["economic_temporal_pass"],
            "recent_two_year_gate_pass": two["gate"]["economic_temporal_pass"],
            "r66_both_blocks_positive_both_stresses": r66_blocks_positive,
            "consumed_window_transport_pass": (
                transport_pass and r66_blocks_positive
            ),
        },
        "decision": decision,
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "signal_surface_changed": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "retest_double_counted": False,
            "protected_swing_stop_changed": False,
            "target_r_changed": False,
            "risk_allocator_recomputed": False,
            "year_or_calendar_runtime_feature": False,
            "anchor_14_enabled": False,
            "candidate_created": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": {
                    "gate": report["five_year"]["gate"],
                    "retest": report["five_year"]["retest_execution"],
                    "economic": report["five_year"][
                        "retest_fixed_r102_weights"
                    ],
                },
                "recent_two_year": {
                    "gate": report["recent_two_year"]["gate"],
                    "retest": report["recent_two_year"]["retest_execution"],
                    "economic": report["recent_two_year"][
                        "retest_fixed_r102_weights"
                    ],
                },
                "r66": {
                    "gate": report["r66_failed_holdout"]["gate"],
                    "retest": report["r66_failed_holdout"][
                        "retest_execution"
                    ],
                    "economic": report["r66_failed_holdout"][
                        "retest_fixed_r102_weights"
                    ],
                },
                "transport": report["transport"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
