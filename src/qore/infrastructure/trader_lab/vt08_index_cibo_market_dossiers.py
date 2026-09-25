"""Market dossiers and temporal stability for VT-08 Index CIBO research.

Consumes only the validated complete-ledger V1 and semantic V2 artifacts over
already-consumed evidence. Produces one descriptive dossier per index plus a
cross-index dossier. No candidate selection, rule promotion, or fresh holdout use
is performed here.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import cast
from zoneinfo import ZoneInfo

SCHEMA = "qore.trader_lab.vt08_index_cibo_market_dossiers.v1"
SYMBOLS = ("NAS100", "SP500", "US30")
_NY = ZoneInfo("America/New_York")


def _load(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _median_int(values: Sequence[int]) -> int | None:
    return int(median(values)) if values else None


def _metrics_from_values(values: Sequence[Decimal]) -> dict[str, object]:
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    max_dd = Decimal()
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    total = sum(values, Decimal())
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_primary_r": _fmt(total),
        "mean_primary_r": _fmt(total / Decimal(len(values))) if values else "0",
        "profit_factor_primary": _fmt(gains / losses) if losses else None,
        "max_drawdown_primary_r": _fmt(max_dd),
        "max_losing_streak": max_streak,
    }


def _later_2r_after_stop(row: Mapping[str, object]) -> bool:
    afterlife = cast(dict[str, object] | None, row.get("post_stop_afterlife"))
    if not afterlife:
        return False
    levels = cast(dict[str, object], afterlife.get("levels", {}))
    level = cast(dict[str, object], levels.get("2", {}))
    return bool(level.get("hit"))


def _taxonomy_candidates(row: Mapping[str, object]) -> tuple[str, ...]:
    taxonomy = cast(dict[str, object], row["error_taxonomy"])
    result: list[str] = []
    for name, raw in taxonomy.items():
        if name == "non_causal_multi_label":
            continue
        payload = cast(dict[str, object], raw)
        if payload.get("status") == "candidate":
            result.append(name)
    return tuple(sorted(result))


def _metric_block(
    rows: Sequence[dict[str, object]],
    departures: Mapping[tuple[str, str], dict[str, object]],
    sync: Mapping[tuple[str, str], dict[str, object]],
) -> dict[str, object]:
    values = [_decimal(row["primary_r"]) for row in rows]
    base = _metrics_from_values(values)
    if not rows:
        return base
    stops = [row for row in rows if str(row["exit_reason"]) == "stop"]
    later2 = sum(_later_2r_after_stop(row) for row in stops)
    cisd_lats: list[int] = []
    arrival_lats: list[int] = []
    taxonomy = Counter[str]()
    for row in rows:
        key = (str(row["symbol"]), str(row["signal_at"]))
        departure = departures[key]
        cisd_lats.append(int(str(departure["minutes_cisd_to_continuation"])))
        arrival_lats.append(int(str(departure["minutes_poi_arrival_to_cisd"])))
        for label in _taxonomy_candidates(sync[key]):
            taxonomy[label] += 1
    sample = Decimal(len(rows))
    base.update(
        {
            "stop_rate": _fmt(Decimal(len(stops)) / sample),
            "stopped_then_later_2r_rate": (
                _fmt(Decimal(later2) / Decimal(len(stops))) if stops else "0"
            ),
            "median_minutes_poi_arrival_to_cisd": _median_int(arrival_lats),
            "median_minutes_cisd_to_continuation": _median_int(cisd_lats),
            "taxonomy_candidate_rates": {
                label: _fmt(Decimal(count) / sample)
                for label, count in sorted(taxonomy.items())
            },
        }
    )
    return base


def _group_metrics(
    rows: Sequence[dict[str, object]],
    departures: Mapping[tuple[str, str], dict[str, object]],
    sync: Mapping[tuple[str, str], dict[str, object]],
    label: Callable[[dict[str, object]], str],
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[label(row)].append(row)
    return {
        key: _metric_block(items, departures, sync)
        for key, items in sorted(grouped.items())
    }


def _year(row: dict[str, object]) -> str:
    return str(_dt(row["signal_at"]).astimezone(_NY).year)


def _semester(row: dict[str, object]) -> str:
    local = _dt(row["signal_at"]).astimezone(_NY)
    half = "H1" if local.month <= 6 else "H2"
    return f"{local.year}-{half}"


def _quarter(row: dict[str, object]) -> str:
    local = _dt(row["signal_at"]).astimezone(_NY)
    return f"{local.year}-Q{((local.month - 1) // 3) + 1}"


def _mix(rows: Iterable[dict[str, object]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key, "unknown")) for row in rows).items()))


def _daily_summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"sample": 0}
    efficiencies = [_decimal(row["directional_efficiency"]) for row in rows]
    ratios = [
        _decimal(row["range_ratio_to_prior20_median"])
        for row in rows
        if row["range_ratio_to_prior20_median"] is not None
    ]
    return {
        "sample": len(rows),
        "descriptor_mix": _mix(rows, "descriptor"),
        "weekday_mix": _mix(rows, "weekday_new_york"),
        "median_directional_efficiency": _fmt(Decimal(str(median(efficiencies)))),
        "median_range_ratio_to_prior20": (
            _fmt(Decimal(str(median(ratios)))) if ratios else None
        ),
    }


def _max_favorable_24h(row: Mapping[str, object]) -> Decimal:
    horizons = cast(dict[str, object], row["horizon_excursions"])
    day = cast(dict[str, object], horizons["1440"])
    return _decimal(day["max_favorable_r"])


def _market_dossier(
    *,
    symbol: str,
    journey_rows: Sequence[dict[str, object]],
    departure_rows: Sequence[dict[str, object]],
    sync_rows: Sequence[dict[str, object]],
    daily_rows: Sequence[dict[str, object]],
    by_window_rows: Mapping[str, Sequence[dict[str, object]]],
    by_window_departures: Mapping[str, Mapping[tuple[str, str], dict[str, object]]],
    by_window_sync: Mapping[str, Mapping[tuple[str, str], dict[str, object]]],
) -> dict[str, object]:
    rows = [row for row in journey_rows if str(row["symbol"]) == symbol]
    departures = {
        (str(row["symbol"]), str(row["signal_at"])): row
        for row in departure_rows
        if str(row["symbol"]) == symbol
    }
    sync = {
        (str(row["symbol"]), str(row["signal_at"])): row
        for row in sync_rows
        if str(row["symbol"]) == symbol
    }
    window_metrics: dict[str, object] = {}
    for window, all_rows in by_window_rows.items():
        items = [row for row in all_rows if str(row["symbol"]) == symbol]
        window_metrics[window] = _metric_block(
            items,
            by_window_departures[window],
            by_window_sync[window],
        )

    reaction_mix = Counter[str]()
    for row in rows:
        key = (symbol, str(row["signal_at"]))
        reaction_mix[str(sync[key].get("reaction_structure_combo", "unknown"))] += 1

    return {
        "schema": SCHEMA,
        "symbol": symbol,
        "overall": _metric_block(rows, departures, sync),
        "temporal_stability": {
            "by_consumed_window": window_metrics,
            "by_year": _group_metrics(rows, departures, sync, _year),
            "by_semester": _group_metrics(rows, departures, sync, _semester),
            "by_quarter": _group_metrics(rows, departures, sync, _quarter),
        },
        "behavior_slices": {
            "by_anchor": _group_metrics(
                rows,
                departures,
                sync,
                lambda row: str(row["anchor_hour_new_york"]),
            ),
            "by_side": _group_metrics(
                rows, departures, sync, lambda row: str(row["side"])
            ),
            "by_model": _group_metrics(
                rows, departures, sync, lambda row: str(row["model_kind"])
            ),
            "by_poi": _group_metrics(
                rows, departures, sync, lambda row: str(row["poi_kind"])
            ),
            "by_weekday": _group_metrics(
                rows,
                departures,
                sync,
                lambda row: str(row["weekday_new_york"]),
            ),
            "by_prior_h4_range_regime": _group_metrics(
                rows,
                departures,
                sync,
                lambda row: str(row["prior_h4_range_regime"]),
            ),
        },
        "structure_and_destination": {
            "poi_mix": _mix(rows, "poi_kind"),
            "model_mix": _mix(rows, "model_kind"),
            "reaction_structure_combo_mix": dict(sorted(reaction_mix.items())),
            "destination_band_mix": _mix(
                [
                    {
                        "band": (
                            "sub-1R"
                            if _max_favorable_24h(row) < 1
                            else "1R-to-2R"
                            if _max_favorable_24h(row) < 2
                            else "2R-to-3R"
                            if _max_favorable_24h(row) < 3
                            else "3R-plus"
                        )
                    }
                    for row in rows
                ],
                "band",
            ),
        },
        "daily_path": _daily_summary(
            [row for row in daily_rows if str(row["symbol"]) == symbol]
        ),
        "governance": {
            "descriptive_only": True,
            "consumed_evidence_only": True,
            "specialist_not_frozen": True,
            "fresh_holdout_opened": False,
            "automatic_rule_promotion_forbidden": True,
        },
    }


def _cross_summary(
    cross_rows: Sequence[dict[str, object]],
    journey_index: Mapping[tuple[str, str], dict[str, object]],
    v1_cross_index: Mapping[tuple[str, int], dict[str, object]],
) -> dict[str, object]:
    full_three = 0
    agreement = 0
    leaders: dict[str, Counter[str]] = {
        "source_poi_arrival": Counter(),
        "cisd_confirmation": Counter(),
        "continuation_departure": Counter(),
    }
    transitions = Counter[str]()
    multi_stop = 0
    same_side_multi_stop = 0
    for row in cross_rows:
        symbols = cast(list[str], row["symbols_present"])
        if len(symbols) == 3:
            full_three += 1
        if bool(row["side_agreement"]):
            agreement += 1
        event_order = cast(dict[str, object], row["event_order"])
        event_leaders: list[str] = []
        for event in leaders:
            payload = cast(dict[str, object], event_order[event])
            leader = str(payload.get("leader"))
            leaders[event][leader] += 1
            event_leaders.append(leader)
        transitions["->".join(event_leaders)] += 1

        key = (str(row["new_york_date"]), int(str(row["anchor_hour_new_york"])))
        v1 = v1_cross_index.get(key)
        if v1 is None:
            continue
        signals = cast(dict[str, object], v1["signals"])
        cohort = [
            journey_index[(symbol, str(signal))]
            for symbol, signal in signals.items()
            if (symbol, str(signal)) in journey_index
        ]
        stopped = [item for item in cohort if str(item["exit_reason"]) == "stop"]
        if len(stopped) >= 2:
            multi_stop += 1
            if len({str(item["side"]) for item in stopped}) == 1:
                same_side_multi_stop += 1

    sample = Decimal(len(cross_rows)) if cross_rows else Decimal(1)
    return {
        "cohort_count": len(cross_rows),
        "three_market_cohort_count": full_three,
        "three_market_cohort_rate": _fmt(Decimal(full_three) / sample),
        "side_agreement_rate": _fmt(Decimal(agreement) / sample),
        "leader_counts": {
            event: dict(sorted(counts.items()))
            for event, counts in leaders.items()
        },
        "leader_transition_counts": dict(sorted(transitions.items())),
        "multi_market_stop_cohorts": multi_stop,
        "same_side_multi_market_stop_cohorts": same_side_multi_stop,
        "same_side_share_of_multi_market_stop_cohorts": (
            _fmt(Decimal(same_side_multi_stop) / Decimal(multi_stop))
            if multi_stop
            else "0"
        ),
    }


def _load_ledger(root: Path, name: str) -> list[dict[str, object]]:
    payload = _load(root / f"{name}.json")
    return cast(list[dict[str, object]], payload["rows"])


def build_dossiers(*, complete_root: Path, semantic_root: Path, out_dir: Path) -> None:
    v1_combined = complete_root / "combined"
    v2_combined = semantic_root / "combined"
    journey = _load_ledger(v1_combined, "MARKET_JOURNEY_LEDGER")
    daily = _load_ledger(v1_combined, "DAILY_PATH_LEDGER")
    v1_cross_rows = _load_ledger(v1_combined, "CROSS_INDEX_JOURNEY_LEDGER")
    departures = _load_ledger(v2_combined, "DEPARTURE_TIMING_LEDGER_V2")
    sync = _load_ledger(v2_combined, "TRADER_MARKET_SYNC_LEDGER_V2")
    cross = _load_ledger(v2_combined, "CROSS_INDEX_JOURNEY_LEDGER_V2")

    combined_payload = _load(v1_combined / "MARKET_JOURNEY_LEDGER.json")
    windows = cast(list[str], combined_payload["windows"])
    by_window_rows: dict[str, list[dict[str, object]]] = {}
    by_window_departures: dict[str, dict[tuple[str, str], dict[str, object]]] = {}
    by_window_sync: dict[str, dict[tuple[str, str], dict[str, object]]] = {}
    for window in windows:
        rows = _load_ledger(
            complete_root / "windows" / window,
            "MARKET_JOURNEY_LEDGER",
        )
        departure_rows = _load_ledger(
            semantic_root / "windows" / window,
            "DEPARTURE_TIMING_LEDGER_V2",
        )
        sync_rows = _load_ledger(
            semantic_root / "windows" / window,
            "TRADER_MARKET_SYNC_LEDGER_V2",
        )
        by_window_rows[window] = rows
        by_window_departures[window] = {
            (str(row["symbol"]), str(row["signal_at"])): row
            for row in departure_rows
        }
        by_window_sync[window] = {
            (str(row["symbol"]), str(row["signal_at"])): row
            for row in sync_rows
        }

    for symbol in SYMBOLS:
        dossier = _market_dossier(
            symbol=symbol,
            journey_rows=journey,
            departure_rows=departures,
            sync_rows=sync,
            daily_rows=daily,
            by_window_rows=by_window_rows,
            by_window_departures=by_window_departures,
            by_window_sync=by_window_sync,
        )
        _write(out_dir / f"{symbol}_MARKET_DOSSIER.json", dossier)

    journey_index = {
        (str(row["symbol"]), str(row["signal_at"])): row for row in journey
    }
    v1_cross_index = {
        (str(row["new_york_date"]), int(str(row["anchor_hour_new_york"]))): row
        for row in v1_cross_rows
    }
    cross_dossier = {
        "schema": SCHEMA,
        "scope": "NAS100+SP500+US30",
        **_cross_summary(cross, journey_index, v1_cross_index),
        "governance": {
            "descriptive_only": True,
            "consumed_evidence_only": True,
            "cross_index_gate_not_selected": True,
            "fresh_holdout_opened": False,
        },
    }
    _write(out_dir / "CROSS_INDEX_MARKET_DOSSIER.json", cross_dossier)

    _write(
        out_dir / "CIBO_MARKET_DOSSIER_MANIFEST.json",
        {
            "schema": SCHEMA,
            "markets": list(SYMBOLS),
            "windows": windows,
            "market_episode_count": len(journey),
            "cross_index_cohort_count": len(cross),
            "governance": {
                "descriptive_only": True,
                "consumed_evidence_only": True,
                "specialists_frozen": False,
                "fresh_holdout_opened": False,
            },
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--complete-root", type=Path, required=True)
    parser.add_argument("--semantic-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    build_dossiers(
        complete_root=args.complete_root,
        semantic_root=args.semantic_root,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
