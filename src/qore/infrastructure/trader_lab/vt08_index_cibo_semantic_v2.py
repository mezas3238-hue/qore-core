"""Semantic V2 overlay for VT-08 Index CIBO consumed-evidence ledgers.

This module closes four semantic gaps left by the first materialized ledger pass:
source-true V7 departure timing, source-structure materialization, cross-index event
ordering, and explicit A-I trader/market diagnostic taxonomy.

It reconstructs frozen V7 signal mechanics from consumed M15 evidence by calling
the frozen V6/V7 helper functions. It never changes V7 economics, admission,
execution, stop, target, or governance.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.trader_lab.vt08_index_cibo_complete_ledgers import (
    _hit_payload,
)
from qore.infrastructure.trader_lab.vt08_index_market_journey_atlas import (
    Bar,
    _decimal,
    _dt,
    _fmt,
    _load_bars,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_cibo_semantic_v2.v1"
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


def _as_v7_bar(bar: Bar) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=bar.opened_at,
        closed_at=bar.closed_at,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _state(path: Path, symbol: str) -> dict[str, object]:
    bars = _load_bars(path, symbol)
    indexed = {bar.opened_at: _as_v7_bar(bar) for bar in bars}
    h4 = v6._build_h4(indexed)
    return {"bars": bars, "indexed": indexed, "h4": h4}


def _find_h4_open(
    *,
    signal_at: datetime,
    anchor_hour_new_york: int,
    h4: Mapping[datetime, Vt08IndexC2R1Bar],
) -> datetime:
    candidates = [
        opened
        for opened, bar in h4.items()
        if opened < signal_at <= bar.closed_at
        and opened.astimezone(_NY).hour == anchor_hour_new_york
    ]
    if len(candidates) != 1:
        raise ValueError(
            "expected exactly one H4 source bar for signal "
            f"{signal_at.isoformat()} anchor={anchor_hour_new_york}, got {len(candidates)}"
        )
    return candidates[0]


def _reconstruct_v7(
    trade: dict[str, object],
    state: Mapping[str, object],
) -> dict[str, object]:
    signal_at = _dt(trade["signal_at"])
    indexed = cast(dict[datetime, Vt08IndexC2R1Bar], state["indexed"])
    h4 = cast(dict[datetime, Vt08IndexC2R1Bar], state["h4"])
    h4_open = _find_h4_open(
        signal_at=signal_at,
        anchor_hour_new_york=int(str(trade["anchor_hour_new_york"])),
        h4=h4,
    )
    signal = v7._signal_for_h4(
        symbol=str(trade["symbol"]),
        indexed=indexed,
        h4=h4,
        h4_opened_at=h4_open,
    )
    if signal is None:
        raise ValueError(
            f"frozen V7 signal did not reconstruct for {trade['symbol']} {trade['signal_at']}"
        )
    if signal.signal_at != signal_at:
        raise ValueError(
            "reconstructed continuation does not equal frozen signal: "
            f"{trade['symbol']} expected={signal_at.isoformat()} "
            f"actual={signal.signal_at.isoformat()}"
        )
    if signal.side.value != str(trade["side"]):
        raise ValueError(
            f"reconstructed side mismatch for {trade['symbol']} {trade['signal_at']}"
        )
    if signal.model_kind.value != str(trade["model_kind"]):
        raise ValueError(
            f"reconstructed model mismatch for {trade['symbol']} {trade['signal_at']}"
        )
    if signal.poi.kind.value != str(trade["poi_kind"]):
        raise ValueError(
            f"reconstructed POI mismatch for {trade['symbol']} {trade['signal_at']}"
        )

    h4_bar = h4[h4_open]
    bars = v6._bars_between(indexed, start=h4_open, end=h4_bar.closed_at)
    touch_index = v6._poi_touch_index(bars, signal.poi)
    if touch_index is None:
        raise ValueError(
            f"frozen V7 POI touch missing for {trade['symbol']} {trade['signal_at']}"
        )
    poi_touch = bars[touch_index]
    return {
        "symbol": trade["symbol"],
        "side": trade["side"],
        "h4_opened_at": h4_open.isoformat(),
        "anchor_hour_new_york": trade["anchor_hour_new_york"],
        "model_kind_reconstructed": signal.model_kind.value,
        "source_poi": {
            **signal.poi.payload(),
            "first_touch_at": poi_touch.closed_at.isoformat(),
            "touch_bar_opened_at": poi_touch.opened_at.isoformat(),
        },
        "cisd_level": _fmt(signal.cisd_level),
        "cisd_confirmed_at": signal.cisd_confirmed_at.isoformat(),
        "protected_swing_extreme": _fmt(signal.protected_swing_extreme),
        "protected_swing_confirmed_at": signal.cisd_confirmed_at.isoformat(),
        "continuation_at": signal.signal_at.isoformat(),
        "continuation_entry": _fmt(signal.entry),
        "frozen_stop": _fmt(signal.stop),
        "frozen_target": _fmt(signal.target),
        "signal_at_matches_reconstruction": True,
    }


def _departure_row(
    trade: dict[str, object],
    reaction: dict[str, object],
    mechanics: dict[str, object],
) -> dict[str, object]:
    legacy = _hit_payload(trade, "0.5")
    reaction_at = reaction.get("reaction_at")
    cisd_at = str(mechanics["cisd_confirmed_at"])
    continuation_at = str(mechanics["continuation_at"])
    poi = cast(dict[str, object], mechanics["source_poi"])
    arrival_at = str(poi["first_touch_at"])
    return {
        "symbol": trade["symbol"],
        "side": trade["side"],
        "signal_at": trade["signal_at"],
        "weekday_new_york": trade["weekday_new_york"],
        "anchor_hour_new_york": trade["anchor_hour_new_york"],
        "reaction_at": reaction_at,
        "source_poi_arrival_at": arrival_at,
        "cisd_confirmed_at": cisd_at,
        "protected_swing_confirmed_at": mechanics["protected_swing_confirmed_at"],
        "continuation_at": continuation_at,
        "departure_definition": "frozen-v7-first-causal-m15-continuation-closure",
        "departure_at": continuation_at,
        "minutes_poi_arrival_to_cisd": int(
            (_dt(cisd_at) - _dt(arrival_at)).total_seconds() // 60
        ),
        "minutes_cisd_to_continuation": int(
            (_dt(continuation_at) - _dt(cisd_at)).total_seconds() // 60
        ),
        "minutes_reaction_to_continuation": (
            int((_dt(continuation_at) - _dt(reaction_at)).total_seconds() // 60)
            if reaction_at
            else None
        ),
        "legacy_0_5r_proxy": {
            "definition": "first favorable 0.5R after frozen V7 signal",
            "hit": legacy["hit"],
            "at": legacy.get("at"),
            "minutes_after_signal": legacy.get("minutes"),
            "is_departure_definition": False,
        },
    }


def _taxonomy(
    trade: dict[str, object],
    reaction: dict[str, object],
) -> dict[str, object]:
    stopped = str(trade["exit_reason"]) == "stop"
    hit05 = bool(_hit_payload(trade, "0.5")["hit"])
    hit1 = bool(_hit_payload(trade, "1")["hit"])
    hit3 = bool(_hit_payload(trade, "3")["hit"])
    afterlife = cast(dict[str, object] | None, trade.get("post_stop_afterlife"))
    later2 = False
    if afterlife:
        levels = cast(dict[str, object], afterlife.get("levels", {}))
        two = cast(dict[str, object], levels.get("2", {}))
        later2 = bool(two.get("hit"))
    horizons = cast(dict[str, object], trade["horizon_excursions"])
    day = cast(dict[str, object], horizons["1440"])
    adverse = _decimal(day["max_adverse_r"])
    reaction_combo = str(reaction.get("reaction_structure_combo", "none-detected"))
    poi_kind = str(trade["poi_kind"])
    peer_alignment = int(str(trade.get("peer_alignment_count", 0)))

    direction_candidate = stopped and not hit05 and adverse >= Decimal("1")
    structure_candidate = (
        stopped
        and reaction_combo != "none-detected"
        and poi_kind not in reaction_combo
    )
    cross_index_candidate = stopped and peer_alignment == 0
    correct_loss = stopped and not hit1 and not later2

    return {
        "A_DIRECTION_ERROR": {
            "status": "candidate" if direction_candidate else "not_indicated",
            "basis": "stop + no 0.5R favorable expansion + >=1R adverse excursion",
        },
        "B_TIMING_ERROR": {
            "status": "candidate" if stopped and later2 else "not_indicated",
            "basis": "stopped trade later reached original-entry 2R within afterlife horizon",
        },
        "C_STOP_LOCATION_ERROR": {
            "status": "candidate" if stopped and later2 else "not_indicated",
            "basis": "same observable signature as timing mismatch; causation unresolved",
        },
        "D_STRUCTURE_SELECTION_ERROR": {
            "status": "candidate" if structure_candidate else "not_indicated",
            "basis": "latest reaction structure family differs from frozen V7 POI family",
        },
        "E_CONFIRMATION_ERROR": {
            "status": "unresolved",
            "basis": "requires a separately frozen alternative confirmation definition",
        },
        "F_TARGET_ERROR": {
            "status": "candidate" if hit3 else "not_indicated",
            "basis": "market reached >=3R although frozen V7 target is 2R; descriptive only",
        },
        "G_REGIME_ERROR": {
            "status": "unresolved",
            "basis": "regime association alone is insufficient to call an error",
        },
        "H_CROSS_INDEX_CONTEXT_ERROR": {
            "status": "candidate" if cross_index_candidate else "not_indicated",
            "basis": "losing trade had zero aligned peers at frozen V7 signal time",
        },
        "I_CORRECT_LOSS": {
            "status": "candidate" if correct_loss else "not_indicated",
            "basis": "stop with no 1R favorable expansion and no later afterlife 2R recovery",
        },
        "non_causal_multi_label": True,
    }


def _sync_row(
    trade: dict[str, object],
    reaction: dict[str, object],
    mechanics: dict[str, object],
) -> dict[str, object]:
    horizons = cast(dict[str, object], trade["horizon_excursions"])
    day = cast(dict[str, object], horizons["1440"])
    return {
        "symbol": trade["symbol"],
        "side": trade["side"],
        "signal_at": trade["signal_at"],
        "anchor_hour_new_york": trade["anchor_hour_new_york"],
        "model_kind": trade["model_kind"],
        "poi_kind": trade["poi_kind"],
        "source_mechanics": mechanics,
        "reaction_structure_combo": reaction.get("reaction_structure_combo"),
        "reaction_event": reaction.get("reaction_event"),
        "trader_exit_reason": trade["exit_reason"],
        "trader_raw_r": trade["raw_r"],
        "trader_primary_r": trade["primary_r"],
        "market_max_favorable_r_24h": day["max_favorable_r"],
        "market_max_adverse_r_24h": day["max_adverse_r"],
        "post_stop_afterlife": trade["post_stop_afterlife"],
        "error_taxonomy": _taxonomy(trade, reaction),
    }


def _event_order(
    cohort: Sequence[dict[str, object]],
    mechanics_by_key: Mapping[tuple[str, str], dict[str, object]],
) -> dict[str, object]:
    def order(field: str, *, nested_poi: bool = False) -> dict[str, object]:
        observed: list[tuple[str, datetime]] = []
        for trade in cohort:
            key = (str(trade["symbol"]), str(trade["signal_at"]))
            mechanics = mechanics_by_key[key]
            if nested_poi:
                poi = cast(dict[str, object], mechanics["source_poi"])
                value = poi[field]
            else:
                value = mechanics[field]
            observed.append((str(trade["symbol"]), _dt(value)))
        observed.sort(key=lambda item: item[1])
        if not observed:
            return {"leader": None, "order": [], "lag_minutes": {}}
        base = observed[0][1]
        return {
            "leader": observed[0][0],
            "order": [symbol for symbol, _ in observed],
            "lag_minutes": {
                symbol: int((moment - base).total_seconds() // 60)
                for symbol, moment in observed
            },
        }

    return {
        "source_poi_arrival": order("first_touch_at", nested_poi=True),
        "cisd_confirmation": order("cisd_confirmed_at"),
        "continuation_departure": order("continuation_at"),
    }


def _cross_index(
    trades: Sequence[dict[str, object]],
    mechanics_by_key: Mapping[tuple[str, str], dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for trade in trades:
        local = _dt(trade["signal_at"]).astimezone(_NY)
        key = (local.date().isoformat(), int(str(trade["anchor_hour_new_york"])))
        grouped[key].append(trade)

    rows: list[dict[str, object]] = []
    for (day, anchor), cohort in sorted(grouped.items()):
        sides = {str(item["symbol"]): str(item["side"]) for item in cohort}
        rows.append(
            {
                "new_york_date": day,
                "anchor_hour_new_york": anchor,
                "symbols_present": sorted(sides),
                "side_agreement": len(set(sides.values())) <= 1,
                "sides": sides,
                "event_order": _event_order(cohort, mechanics_by_key),
                "relative_strength_rank": {
                    str(item["symbol"]): item["relative_strength_rank"]
                    for item in cohort
                },
                "peer_alignment_count": {
                    str(item["symbol"]): item["peer_alignment_count"]
                    for item in cohort
                },
            }
        )
    return rows


def _package(name: str, rows: Sequence[dict[str, object]], window_id: str) -> dict[str, object]:
    return {
        "schema": f"{SCHEMA}.{name.lower()}",
        "ledger": name,
        "window_id": window_id,
        "row_count": len(rows),
        "rows": list(rows),
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "changes_v7": False,
            "legacy_0_5r_is_departure": False,
            "automatic_rule_promotion_forbidden": True,
            "fresh_holdout_opened": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def build_window(
    *,
    journey_path: Path,
    reaction_path: Path,
    nas100_path: Path,
    sp500_path: Path,
    us30_path: Path,
    out_dir: Path,
) -> None:
    journey = _load(journey_path)
    reaction = _load(reaction_path)
    trades = cast(list[dict[str, object]], journey["trades"])
    reactions = {
        (str(item["symbol"]), str(item["signal_at"])): item
        for item in cast(list[dict[str, object]], reaction["episodes"])
    }
    states = {
        "NAS100": _state(nas100_path, "NAS100"),
        "SP500": _state(sp500_path, "SP500"),
        "US30": _state(us30_path, "US30"),
    }
    window_id = str(journey.get("window_id", journey.get("window", "unknown")))

    mechanics_rows: list[dict[str, object]] = []
    departure_rows: list[dict[str, object]] = []
    sync_rows: list[dict[str, object]] = []
    mechanics_by_key: dict[tuple[str, str], dict[str, object]] = {}

    for trade in trades:
        key = (str(trade["symbol"]), str(trade["signal_at"]))
        reaction_row = reactions[key]
        mechanics = _reconstruct_v7(trade, states[str(trade["symbol"])])
        mechanics_by_key[key] = mechanics
        mechanics_rows.append(mechanics)
        departure_rows.append(_departure_row(trade, reaction_row, mechanics))
        sync_rows.append(_sync_row(trade, reaction_row, mechanics))

    outputs = {
        "SOURCE_STRUCTURE_LEDGER_V2": mechanics_rows,
        "DEPARTURE_TIMING_LEDGER_V2": departure_rows,
        "CROSS_INDEX_JOURNEY_LEDGER_V2": _cross_index(trades, mechanics_by_key),
        "TRADER_MARKET_SYNC_LEDGER_V2": sync_rows,
    }
    for name, rows in outputs.items():
        _write(out_dir / f"{name}.json", _package(name, rows, window_id))


def combine_windows(input_dirs: Sequence[Path], out_dir: Path) -> None:
    names = (
        "SOURCE_STRUCTURE_LEDGER_V2",
        "DEPARTURE_TIMING_LEDGER_V2",
        "CROSS_INDEX_JOURNEY_LEDGER_V2",
        "TRADER_MARKET_SYNC_LEDGER_V2",
    )
    windows: list[str] = []
    for name in names:
        rows: list[dict[str, object]] = []
        current_windows: list[str] = []
        for root in input_dirs:
            payload = _load(root / f"{name}.json")
            current_windows.append(str(payload["window_id"]))
            rows.extend(cast(list[dict[str, object]], payload["rows"]))
        windows = current_windows
        result = _package(name, rows, "combined-consumed-2018-2026")
        result["windows"] = current_windows
        _write(out_dir / f"{name}.json", result)
    _write(
        out_dir / "CIBO_SEMANTIC_V2_MANIFEST.json",
        {
            "schema": SCHEMA,
            "ledgers": list(names),
            "windows": windows,
            "window_count": len(input_dirs),
            "contract": {
                "departure": "frozen-v7-first-causal-m15-continuation-closure",
                "protected_swing_confirmation": "same frozen CISD confirmation bar",
                "legacy_0_5r_proxy_retained_for_comparison_only": True,
                "taxonomy": "A-I non-causal multi-label diagnostic",
            },
            "governance": {
                "diagnostic_only": True,
                "consumed_evidence_only": True,
                "changes_v7": False,
                "fresh_holdout_opened": False,
            },
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    window = sub.add_parser("window")
    window.add_argument("--journey", type=Path, required=True)
    window.add_argument("--reaction", type=Path, required=True)
    window.add_argument("--nas100", type=Path, required=True)
    window.add_argument("--sp500", type=Path, required=True)
    window.add_argument("--us30", type=Path, required=True)
    window.add_argument("--out-dir", type=Path, required=True)
    combined = sub.add_parser("combine")
    combined.add_argument("input_dirs", nargs="+", type=Path)
    combined.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "window":
        build_window(
            journey_path=args.journey,
            reaction_path=args.reaction,
            nas100_path=args.nas100,
            sp500_path=args.sp500,
            us30_path=args.us30,
            out_dir=args.out_dir,
        )
    else:
        combine_windows(args.input_dirs, args.out_dir)


if __name__ == "__main__":
    main()
