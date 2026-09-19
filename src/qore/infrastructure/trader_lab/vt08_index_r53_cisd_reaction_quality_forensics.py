"""VT08 Index R53 — source-complete CISD reaction-quality falsification.

R53 reuses the existing Reaction Structure Atlas on the exact R47 source-complete
surface. It does not create a candidate or change risk. The preregistered causal
hypothesis is intentionally narrow:

A CISD is reaction-supported when the latest favorable-side reaction observed
at or before entry is a liquidity sweep and that reaction closed no more than
15 minutes before signal_at.

The hypothesis originated in consumed Deep Behavior / Reaction Atlas evidence
and is cross-checked against independent CIBO general-market memory. R53 then
falsifies it on all R47 CISD opportunities in the consumed 5Y and recent 2Y
windows. No post-entry field is used as a predictor.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_market_journey_atlas as journey
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import vt08_index_r45_frozen_recent_2y_reproduction as r45
from qore.infrastructure.trader_lab import (
    vt08_index_r46_cross_window_transport_forensics as r46,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_reaction_structure_atlas as reaction
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r53_cisd_reaction_quality_forensics.v1"
IDENTITY = "VT08_INDEX_R53_SOURCE_COMPLETE_CISD_REACTION_QUALITY_FORENSICS_001"
SECONDARY_STRESS = Decimal("0.10")
REACTION_MAX_MINUTES = 15
MIN_FIVE_YEAR_SAMPLE = 50
MIN_TWO_YEAR_SAMPLE = 25
MIN_RAW_SECONDARY_PF = Decimal("1.10")

SOURCE_REACTION_RUN_ID = 35166186219
SOURCE_REACTION_ARTIFACT_ID = 10474204438
SOURCE_REACTION_ARTIFACT_DIGEST = (
    "sha256:60d8796762d58ad84822ed1040eea0bd011af112cf311f199329d5c3d4fd9422"
)
SOURCE_CIBO_MARKET_RUN_ID = 35300432246
SOURCE_CIBO_MARKET_ARTIFACT_ID = 10529467508
SOURCE_CIBO_MARKET_ARTIFACT_DIGEST = (
    "sha256:604a7d324842b46874179a39567b2cc982e03564ac18bfb3046f8e511dfe6a72"
)


def _parse_dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_reaction_bars(
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[journey.Bar, ...]:
    return tuple(
        journey.Bar(
            opened_at=bar.opened_at.astimezone(UTC),
            closed_at=bar.closed_at.astimezone(UTC),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
        )
        for bar in bars
    )


def _classify_latest_reaction(
    structures: Sequence[dict[str, object]],
    *,
    signal_at: datetime,
) -> dict[str, object]:
    eligible = [
        item
        for item in structures
        if _parse_dt(item["observed_at"]) <= signal_at.astimezone(UTC)
    ]
    if not eligible:
        return {
            "reaction_at": None,
            "reaction_event": "none-detected",
            "reaction_structure_combo": "none-detected",
            "minutes_reaction_to_signal": None,
            "fresh_liquidity_take_15m": False,
        }

    reaction_at = max(_parse_dt(item["observed_at"]) for item in eligible)
    latest = [
        item
        for item in eligible
        if _parse_dt(item["observed_at"]) == reaction_at
    ]
    event = (
        "liquidity-take"
        if any(str(item["kind"]) == "liquidity-sweep" for item in latest)
        else "structure-retest"
    )
    combo = "+".join(sorted({str(item["kind"]) for item in latest}))
    minutes = int(
        (signal_at.astimezone(UTC) - reaction_at).total_seconds() // 60
    )
    return {
        "reaction_at": reaction_at.isoformat(),
        "reaction_event": event,
        "reaction_structure_combo": combo,
        "minutes_reaction_to_signal": minutes,
        "fresh_liquidity_take_15m": (
            event == "liquidity-take"
            and 0 <= minutes <= REACTION_MAX_MINUTES
        ),
    }


def _reaction_context(
    item: r15.AssignedTrade,
    *,
    bars: Sequence[journey.Bar],
    opened: Sequence[datetime],
) -> dict[str, object]:
    signal = item.opportunity.signal
    signal_at = signal.signal_at.astimezone(UTC)
    window = reaction._slice(
        bars,
        opened,
        signal_at - timedelta(hours=24),
        signal_at,
    )
    structures = [
        *reaction._zone_retests(reaction._fvg_zones(window), window, signal_at),
        *reaction._zone_retests(
            reaction._order_block_zones(window),
            window,
            signal_at,
        ),
        *reaction._zone_retests(
            reaction._breaker_zones(window),
            window,
            signal_at,
        ),
        *reaction._liquidity_events(window, signal_at),
    ]
    wanted_side = "bullish" if signal.side.value == "long" else "bearish"
    aligned = [
        structure
        for structure in structures
        if str(structure["side"]) == wanted_side
    ]
    return _classify_latest_reaction(aligned, signal_at=signal_at)


def _metrics_rows(
    rows: Sequence[dict[str, object]],
    *,
    weighted: bool,
) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["exit_timestamp"]),
            str(row["symbol"]),
            str(row["timestamp"]),
        ),
    )
    values: list[Decimal] = []
    for row in ordered:
        value = Decimal(str(row["outcome_r"])) - SECONDARY_STRESS
        if weighted:
            value *= Decimal(str(row["effective_weight"]))
        values.append(value)
    return fx._metrics(tuple(values))


def _breakdown(
    rows: Sequence[dict[str, object]],
    *,
    key: str,
) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {
        label: {
            "raw_secondary": _metrics_rows(items, weighted=False),
            "governed_secondary": _metrics_rows(items, weighted=True),
        }
        for label, items in sorted(groups.items())
    }


def _window(
    *,
    assigned: Sequence[r15.AssignedTrade],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    window_id: str,
) -> dict[str, object]:
    reaction_bars = {
        symbol: _as_reaction_bars(tuple(bars))
        for symbol, bars in bars_by_symbol.items()
    }
    opened = {
        symbol: tuple(bar.opened_at for bar in bars)
        for symbol, bars in reaction_bars.items()
    }

    rows: list[dict[str, object]] = []
    for item in assigned:
        if str(item.opportunity.source_poi_kind) != "cisd":
            continue
        if item.weight != r47.MIN_EFFECTIVE_WEIGHT:
            raise ValueError("R53 expected every frozen R47 CISD at canonical floor")
        context = _reaction_context(
            item,
            bars=reaction_bars[item.symbol],
            opened=opened[item.symbol],
        )
        rows.append(
            {
                "window_id": window_id,
                "period_id": r46._period_id(window_id, item),
                "symbol": item.symbol,
                "timestamp": item.opportunity.signal.signal_at.astimezone(
                    UTC
                ).isoformat(),
                "exit_timestamp": item.exited_at.astimezone(UTC).isoformat(),
                "side": item.opportunity.signal.side.value,
                "anchor": str(
                    item.opportunity.signal.h4_opened_at.astimezone(
                        r46._NY
                    ).hour
                ),
                "outcome_r": str(item.outcome.r_multiple),
                "effective_weight": str(item.weight),
                **context,
            }
        )

    fresh = [row for row in rows if bool(row["fresh_liquidity_take_15m"])]
    complement = [
        row for row in rows if not bool(row["fresh_liquidity_take_15m"])
    ]
    return {
        "cisd_sample": len(rows),
        "all_cisd_at_floor": True,
        "fresh_liquidity_take_15m": {
            "sample": len(fresh),
            "raw_secondary": _metrics_rows(fresh, weighted=False),
            "governed_secondary": _metrics_rows(fresh, weighted=True),
            "by_symbol": _breakdown(fresh, key="symbol"),
            "by_side": _breakdown(fresh, key="side"),
            "by_anchor": _breakdown(fresh, key="anchor"),
            "by_period": _breakdown(fresh, key="period_id"),
        },
        "complement": {
            "sample": len(complement),
            "raw_secondary": _metrics_rows(complement, weighted=False),
            "governed_secondary": _metrics_rows(complement, weighted=True),
        },
        "reaction_event": _breakdown(rows, key="reaction_event"),
        "reaction_structure_combo": _breakdown(
            rows,
            key="reaction_structure_combo",
        ),
        "rows": rows,
    }


def _screen_pass(
    five: dict[str, object],
    two: dict[str, object],
) -> bool:
    five_fresh = five["fresh_liquidity_take_15m"]
    two_fresh = two["fresh_liquidity_take_15m"]
    if not isinstance(five_fresh, dict) or not isinstance(two_fresh, dict):
        return False
    five_metrics = five_fresh["raw_secondary"]
    two_metrics = two_fresh["raw_secondary"]
    if not isinstance(five_metrics, dict) or not isinstance(two_metrics, dict):
        return False
    return (
        int(five_fresh["sample"]) >= MIN_FIVE_YEAR_SAMPLE
        and int(two_fresh["sample"]) >= MIN_TWO_YEAR_SAMPLE
        and Decimal(str(five_metrics["total_r"])) > 0
        and Decimal(str(two_metrics["total_r"])) > 0
        and Decimal(str(five_metrics["profit_factor"] or "0"))
        >= MIN_RAW_SECONDARY_PF
        and Decimal(str(two_metrics["profit_factor"] or "0"))
        >= MIN_RAW_SECONDARY_PF
    )


def _r47_window(
    *,
    stream: Sequence[tuple[Any, Any]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[r15.AssignedTrade, ...]:
    r43_assigned, _trace = r46._frozen_assignment(stream)
    assigned, diagnostics = r47._apply_transport_rules(
        r43_assigned,
        bars_by_symbol=bars_by_symbol,
    )
    if int(diagnostics["suppressed_trade_count"]) != 0:
        raise ValueError("R53 source candidate unexpectedly suppressed trades")
    return assigned


def _verify_frozen_baseline(
    assigned: Sequence[r15.AssignedTrade],
    *,
    expected: dict[str, object],
) -> None:
    metrics = fx._metrics(
        r15._realized_values(tuple(assigned), stress=SECONDARY_STRESS)
    )
    if len(assigned) != int(expected["sample"]):
        raise ValueError("R53 frozen sample drift")
    if Decimal(str(metrics["total_r"])) != Decimal(
        str(expected["secondary_total_r"])
    ):
        raise ValueError("R53 frozen secondary total drift")
    if Decimal(str(metrics["profit_factor"])) != Decimal(
        str(expected["secondary_pf"])
    ):
        raise ValueError("R53 frozen secondary PF drift")


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R53 frozen R47 dependency contract drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    five_assigned = _r47_window(
        stream=five_stream,
        bars_by_symbol={key: tuple(value) for key, value in five_bars.items()},
    )
    two_assigned = _r47_window(
        stream=two_stream,
        bars_by_symbol={key: tuple(value) for key, value in two_bars.items()},
    )
    _verify_frozen_baseline(five_assigned, expected=freeze.FIVE_YEAR)
    _verify_frozen_baseline(two_assigned, expected=freeze.RECENT_TWO_YEAR)

    five = _window(
        assigned=five_assigned,
        bars_by_symbol={key: tuple(value) for key, value in five_bars.items()},
        window_id="5Y",
    )
    two = _window(
        assigned=two_assigned,
        bars_by_symbol={key: tuple(value) for key, value in two_bars.items()},
        window_id="2Y",
    )
    screen_pass = _screen_pass(five, two)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
            "rules_changed": False,
            "risk_changed": False,
            "candidate_created": False,
        },
        "hypothesis": {
            "name": "FRESH_FAVORABLE_LIQUIDITY_TAKE_15M_BEFORE_CISD",
            "poi_scope": "cisd-only",
            "lookback_hours": 24,
            "reaction_event": "liquidity-take",
            "maximum_minutes_reaction_to_signal": REACTION_MAX_MINUTES,
            "five_year_minimum_sample": MIN_FIVE_YEAR_SAMPLE,
            "two_year_minimum_sample": MIN_TWO_YEAR_SAMPLE,
            "raw_secondary_pf_minimum": str(MIN_RAW_SECONDARY_PF),
            "origin": "existing Reaction Structure Atlas plus CIBO market memory",
            "post_entry_feature_used": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "transport_screen_pass": screen_pass,
        "source_evidence": {
            "reaction_structure_atlas": {
                "run_id": SOURCE_REACTION_RUN_ID,
                "artifact_id": SOURCE_REACTION_ARTIFACT_ID,
                "artifact_digest": SOURCE_REACTION_ARTIFACT_DIGEST,
            },
            "cibo_general_market_memory": {
                "run_id": SOURCE_CIBO_MARKET_RUN_ID,
                "artifact_id": SOURCE_CIBO_MARKET_ARTIFACT_ID,
                "artifact_digest": SOURCE_CIBO_MARKET_ARTIFACT_DIGEST,
            },
            "r47_freeze": {
                "run_id": freeze.SOURCE_RUN_ID,
                "artifact_id": freeze.SOURCE_ARTIFACT_ID,
                "artifact_digest": freeze.SOURCE_ARTIFACT_DIGEST,
            },
        },
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "all_predictors_known_at_or_before_entry": True,
            "reaction_window_ends_at_signal": True,
            "post_arrival_phase_used": False,
            "post_entry_outcome_used_as_predictor": False,
            "calendar_or_year_used_as_runtime_feature": False,
            "optimization_grid_used": False,
            "automatic_rule_promotion": False,
            "signal_suppression_performed": False,
            "risk_retuning_performed": False,
            "candidate_created": False,
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
                "five_year_cisd_sample": report["five_year"]["cisd_sample"],
                "two_year_cisd_sample": report["recent_two_year"]["cisd_sample"],
                "five_year_fresh": report["five_year"][
                    "fresh_liquidity_take_15m"
                ],
                "two_year_fresh": report["recent_two_year"][
                    "fresh_liquidity_take_15m"
                ],
                "transport_screen_pass": report["transport_screen_pass"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
