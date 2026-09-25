"""Market-specific pattern discovery for the VT-08 Index behavior laboratory.

This module consumes the combined Deep Behavior Lab report. It never changes
V7 rules and never promotes a discovered pattern into a trading rule. Its job
is to describe repeatable pre-entry states, state transitions, loss precursors,
market fingerprints and temporal stability on already-consumed evidence.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import cast

SCHEMA = "qore.trader_lab.vt08_index_market_pattern_discovery.v1"
MIN_STATE_SUPPORT = 20
MIN_MOTIF_SUPPORT = 15


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return Decimal()
    return sum(values, Decimal()) / Decimal(len(values))


def _bucket_minutes(value: object) -> str:
    minutes = int(str(value))
    if minutes <= 60:
        return "le60"
    if minutes <= 120:
        return "61_120"
    if minutes <= 180:
        return "121_180"
    return "gt180"


def _state_token(row: dict[str, object]) -> str:
    fields = (
        str(row.get("anchor_hour_new_york", "?")),
        str(row.get("side", "?")),
        str(row.get("model_kind", "?")),
        str(row.get("poi_kind", "?")),
        str(row.get("prior_h4_range_regime", "?")),
        str(row.get("prior_h4_body_alignment", "?")),
        str(row.get("current_source_body_alignment", "?")),
        str(row.get("previous_source_body_alignment", "?")),
        str(row.get("peer_alignment_count", "?")),
        str(row.get("side_adjusted_relative_strength_rank", "?")),
        _bucket_minutes(row.get("cisd_latency_minutes", 9999)),
        _bucket_minutes(row.get("post_cisd_latency_minutes", 9999)),
    )
    return "|".join(fields)


def _window_for_signal(
    signal_at: str,
    windows: Sequence[dict[str, object]],
) -> str:
    day = signal_at[:10]
    for window in windows:
        partition = cast(dict[str, object], window["partition"])
        start = str(partition["start_date"])
        end = str(partition["end_date_exclusive"])
        if start <= day < end:
            return str(window["window_id"])
    return "unknown"


def _summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    values = [_decimal(row["primary_r"]) for row in rows]
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    stops = sum(_decimal(row["raw_r"]) < 0 for row in rows)
    return {
        "sample": len(rows),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "total_r": _fmt(sum(values, Decimal())),
        "mean_r": _fmt(_mean(values)),
        "profit_factor": _fmt(gains / losses) if losses else None,
        "stop_rate": _fmt(Decimal(stops) / Decimal(len(rows))) if rows else "0",
        "mean_mfe_r": _fmt(
            _mean([_decimal(row["mfe_r_conservative"]) for row in rows])
        ),
        "mean_mae_r": _fmt(
            _mean([_decimal(row["mae_r_conservative"]) for row in rows])
        ),
    }


def _distribution(rows: Sequence[dict[str, object]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key, "unknown")) for row in rows).items()))


def _market_fingerprint(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "performance": _summary(rows),
        "anchor_mix": _distribution(rows, "anchor_hour_new_york"),
        "side_mix": _distribution(rows, "side"),
        "model_mix": _distribution(rows, "model_kind"),
        "poi_mix": _distribution(rows, "poi_kind"),
        "range_regime_mix": _distribution(rows, "prior_h4_range_regime"),
        "peer_alignment_mix": _distribution(rows, "peer_alignment_count"),
        "relative_strength_rank_mix": _distribution(
            rows, "side_adjusted_relative_strength_rank"
        ),
        "entry_timing_mix": _distribution(rows, "entry_timing_bucket"),
        "stop_excursion_mix": _distribution(rows, "stop_excursion_bucket"),
        "duration_mix": _distribution(rows, "duration_bucket"),
    }


def _state_patterns(
    rows: Sequence[dict[str, object]],
    windows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[_state_token(row)].append(row)
    result: list[dict[str, object]] = []
    for token, items in grouped.items():
        if len(items) < MIN_STATE_SUPPORT:
            continue
        by_window: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in items:
            by_window[_window_for_signal(str(row["signal_at"]), windows)].append(row)
        window_stats: dict[str, object] = {
            window: _summary(group)
            for window, group in sorted(by_window.items())
        }
        supported_windows = [
            cast(dict[str, object], stats)
            for stats in window_stats.values()
            if int(str(cast(dict[str, object], stats)["sample"])) >= 5
        ]
        positive_supported = sum(
            _decimal(stats["mean_r"]) > 0 for stats in supported_windows
        )
        result.append(
            {
                "state": token,
                "overall": _summary(items),
                "windows": window_stats,
                "supported_windows": len(supported_windows),
                "positive_supported_windows": positive_supported,
                "positive_window_fraction": (
                    _fmt(Decimal(positive_supported) / Decimal(len(supported_windows)))
                    if supported_windows
                    else None
                ),
            }
        )
    result.sort(
        key=lambda item: (
            int(str(cast(dict[str, object], item["overall"])["sample"])),
            _decimal(cast(dict[str, object], item["overall"])["mean_r"]),
        ),
        reverse=True,
    )
    return result


def _sequence_motifs(
    rows: Sequence[dict[str, object]],
    windows: Sequence[dict[str, object]],
    length: int,
) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for index in range(length - 1, len(ordered)):
        segment = ordered[index - length + 1 : index + 1]
        motif = ">".join(_state_token(row) for row in segment)
        grouped[motif].append(ordered[index])
    result: list[dict[str, object]] = []
    for motif, endpoints in grouped.items():
        if len(endpoints) < MIN_MOTIF_SUPPORT:
            continue
        by_window: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in endpoints:
            by_window[_window_for_signal(str(row["signal_at"]), windows)].append(row)
        result.append(
            {
                "motif": motif,
                "length": length,
                "endpoint_outcome": _summary(endpoints),
                "windows": {
                    window: _summary(group)
                    for window, group in sorted(by_window.items())
                },
            }
        )
    result.sort(
        key=lambda item: int(
            str(cast(dict[str, object], item["endpoint_outcome"])["sample"])
        ),
        reverse=True,
    )
    return result


def _transition_matrix(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for previous, current in zip(ordered, ordered[1:], strict=False):
        source = _state_token(previous)
        target = _state_token(current)
        transitions[source][target] += 1
        outcome_rows[f"{source}>{target}"].append(current)
    payload: dict[str, object] = {}
    for source, counts in transitions.items():
        total = sum(counts.values())
        top = []
        for target, count in counts.most_common(10):
            key = f"{source}>{target}"
            top.append(
                {
                    "target": target,
                    "count": count,
                    "probability": _fmt(Decimal(count) / Decimal(total)),
                    "target_outcome": _summary(outcome_rows[key]),
                }
            )
        payload[source] = {"outgoing": total, "top_transitions": top}
    return payload


def _loss_precursors(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[_state_token(row)].append(row)
    result: list[dict[str, object]] = []
    for token, items in grouped.items():
        if len(items) < MIN_STATE_SUPPORT:
            continue
        summary = _summary(items)
        stop_rate = _decimal(summary["stop_rate"])
        if stop_rate < Decimal("0.60"):
            continue
        result.append({"state": token, "behavior": summary})
    result.sort(
        key=lambda item: (
            _decimal(cast(dict[str, object], item["behavior"])["stop_rate"]),
            int(str(cast(dict[str, object], item["behavior"])["sample"])),
        ),
        reverse=True,
    )
    return result


def _expansion_precursors(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[_state_token(row)].append(row)
    result: list[dict[str, object]] = []
    for token, items in grouped.items():
        if len(items) < MIN_STATE_SUPPORT:
            continue
        expansion_rate = Decimal(
            sum(_decimal(row["mfe_r_conservative"]) >= Decimal("2") for row in items)
        ) / Decimal(len(items))
        if expansion_rate < Decimal("0.40"):
            continue
        result.append(
            {
                "state": token,
                "sample": len(items),
                "mfe_ge_2r_rate": _fmt(expansion_rate),
                "behavior": _summary(items),
            }
        )
    result.sort(
        key=lambda item: (
            _decimal(item["mfe_ge_2r_rate"]),
            int(str(item["sample"])),
        ),
        reverse=True,
    )
    return result


def _cross_market_same_context(
    rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        context = "|".join(
            (
                str(row.get("anchor_hour_new_york", "?")),
                str(row.get("side", "?")),
                str(row.get("model_kind", "?")),
                str(row.get("poi_kind", "?")),
                str(row.get("prior_h4_range_regime", "?")),
                str(row.get("peer_alignment_count", "?")),
            )
        )
        grouped[context][str(row["symbol"])].append(row)
    result: list[dict[str, object]] = []
    for context, markets in grouped.items():
        supported = {
            market: items for market, items in markets.items() if len(items) >= 10
        }
        if len(supported) < 2:
            continue
        summaries = {market: _summary(items) for market, items in supported.items()}
        means = [_decimal(summary["mean_r"]) for summary in summaries.values()]
        dispersion = max(means) - min(means)
        result.append(
            {
                "context": context,
                "markets": summaries,
                "mean_dispersion_r": _fmt(dispersion),
            }
        )
    result.sort(key=lambda item: _decimal(item["mean_dispersion_r"]), reverse=True)
    return result


def discover(payload: dict[str, object]) -> dict[str, object]:
    rows = cast(list[dict[str, object]], payload["trades"])
    windows = cast(list[dict[str, object]], payload["windows"])
    by_symbol: dict[str, object] = {}
    for symbol in sorted({str(row["symbol"]) for row in rows}):
        market_rows = [row for row in rows if str(row["symbol"]) == symbol]
        by_symbol[symbol] = {
            "fingerprint": _market_fingerprint(market_rows),
            "state_patterns": _state_patterns(market_rows, windows),
            "motifs_2": _sequence_motifs(market_rows, windows, 2),
            "motifs_3": _sequence_motifs(market_rows, windows, 3),
            "transition_matrix": _transition_matrix(market_rows),
            "loss_precursors": _loss_precursors(market_rows),
            "expansion_precursors": _expansion_precursors(market_rows),
        }
    return {
        "schema": SCHEMA,
        "candidate_id": payload["candidate_id"],
        "rule_fingerprint": payload["rule_fingerprint"],
        "market_count": len(by_symbol),
        "trade_count": len(rows),
        "markets": by_symbol,
        "cross_market_same_context": _cross_market_same_context(rows),
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "patterns_are_probabilistic_not_deterministic": True,
            "automatic_rule_promotion_forbidden": True,
            "new_candidate_identity_required_for_any_rule_change": True,
            "fresh_validation_required_after_freeze": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = cast(
        dict[str, object], json.loads(args.input.read_text(encoding="utf-8"))
    )
    result = discover(payload)
    _write(args.out, result)
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "trade_count": result["trade_count"],
                "market_count": result["market_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
