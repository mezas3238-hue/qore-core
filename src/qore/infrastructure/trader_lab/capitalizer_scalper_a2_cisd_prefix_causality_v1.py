"""Source-ID V49 full-window vs closed-M1 prefix CISD forensic.

This is OFFLINE RESEARCH, not a new author rule, trading signal or veto.
Full H1-state/M15-deadline windows can contain observations unavailable at
the original trigger close. Never feed any such output to Master Frame.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    _aggregate,
    _timed_m15,
)
from qore.infrastructure.trader_lab.capitalizer_h1_context_state_v49 import (
    IDENTITY as H1_STATE_IDENTITY,
    V49H1ContextState,
    V49H1StateEndReason,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
    _all_m15_setups,
    _side,
    _slice,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_timing_session_diagnostic_v1 import (
    aware,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    observe_first_m1_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48 import (
    observe_first_m1_fvg_cisd_continuation,
)

IDENTITY = "QORE_SCALPER_A2_CISD_PREFIX_CAUSALITY_RESEARCH_V1"


@dataclass(frozen=True, slots=True)
class RouteWitness:
    first_family: str | None
    first_at: str | None
    sweep_confirmed_at: str | None
    fvg_cisd_confirmed_at: str | None
    # A single candidate selection at end-of-closed-prefix. No trade authority.
    authorizes_entry: bool = False

    def __post_init__(self) -> None:
        if self.authorizes_entry:
            raise ValueError("CISD prefix diagnostics cannot authorize entries")


def observe_route_pair(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    thesis_at: Any,
    deadline_at: Any,
    direction: CapitalizerSourceDirection,
) -> RouteWitness:
    """Same two V48 observers + same (confirmation close, route family) priority."""

    sweep = observe_first_m1_cisd(
        bars, thesis_at=thesis_at, deadline_at=deadline_at,
        side=_side(direction),
    )
    fvg = observe_first_m1_fvg_cisd_continuation(
        bars, thesis_at=thesis_at, deadline_at=deadline_at,
        direction=direction,
    )
    candidates = []
    if sweep.confirmed and sweep.confirmed_at is not None:
        candidates.append((sweep.confirmed_at, "LIQUIDITY_SWEEP_CISD"))
    if fvg.confirmed and fvg.cisd_confirmed_at is not None:
        candidates.append((fvg.cisd_confirmed_at, "FVG_RETRACE_CISD"))
    first = min(candidates, key=lambda x: (x[0], x[1])) if candidates else None
    return RouteWitness(
        first_family=first[1] if first else None,
        first_at=first[0].isoformat() if first else None,
        sweep_confirmed_at=sweep.confirmed_at.isoformat()
        if sweep.confirmed_at else None,
        fvg_cisd_confirmed_at=fvg.cisd_confirmed_at.isoformat()
        if fvg.cisd_confirmed_at else None,
    )


def _state_key(s: V49Opportunity) -> tuple[str, str, str, str, str]:
    return (
        s.session, s.h1_state_from, s.h1_state_until,
        s.h1_state_direction, s.h1_state_basis,
    )


def _next_boundaries(
    source: V49Opportunity,
    *,
    m15: Any,
    m15_opened: tuple[Any, ...],
) -> dict[str, str]:
    """Reconstruct V49 M15 parent succession OFFLINE from source H1 state."""

    state = V49H1ContextState(
        identity=H1_STATE_IDENTITY,
        session=CapitalizerSession(source.session),
        direction=CapitalizerSourceDirection(source.h1_state_direction),
        active_from=aware(source.h1_state_from),
        active_until=aware(source.h1_state_until),
        established_by=source.h1_state_basis,
        end_reason=V49H1StateEndReason.SESSION_END,
    )
    m15_window = _slice(
        m15, m15_opened, start=state.active_from, end=state.active_until
    )
    setups = _all_m15_setups(m15_window, state=state)
    result: dict[str, str] = {}
    for i, setup in enumerate(setups):
        if setup.confirmed_at is None:
            raise ValueError("source-valid M15 has no confirmation")
        boundary = (
            setups[i+1].confirmed_at
            if i+1 < len(setups) else state.active_until
        )
        result[setup.confirmed_at.isoformat()] = boundary.isoformat()
    return result


def market(
    original_root: Path,
    sensor_root: Path,
    native_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    original_files = sorted(original_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    sensor_files = sorted(sensor_root.rglob("scalper-entry-sensors-rows.jsonl"))
    if len(original_files) != 1 or len(sensor_files) != 1:
        raise ValueError("one immutable original and one sensor file required")
    sources = tuple(V49Opportunity(**x) for x in _jsonl(original_files[0]))
    sensor_rows = tuple(_jsonl(sensor_files[0]))
    sensors = {r["source_opportunity_id"]: r for r in sensor_rows}
    if (
        not sources or len(sensors) != len(sources)
        or len(sensor_rows) != len(sources)
    ):
        raise ValueError("source and sensor ID population diverge")
    symbol = sources[0].symbol
    native = tuple(
        b for b in iter_cibo_m1(native_root)
        if DEV_WINDOW_START - timedelta(days=15) <= b.opened_at < DEV_WINDOW_END
    )
    if not native or any(b.symbol != symbol for b in native):
        raise ValueError("source/native symbol mismatch")
    if any(native[i].opened_at >= native[i+1].opened_at
           for i in range(len(native)-1)):
        raise ValueError("duplicate/unsorted provider native M1")
    m1_opened = tuple(b.opened_at for b in native)
    m15 = _timed_m15(_aggregate(native, minutes=15))
    m15_opened = tuple(b.opened_at for b in m15)

    cached: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    results: list[dict[str, Any]] = []
    ids: set[str] = set()
    classes: Counter[str] = Counter()
    full_source_match = 0
    prefix_sensor_match = 0
    for source in sources:
        sid = source_id(source)
        if sid in ids or sid not in sensors:
            raise ValueError("duplicate or absent source ID")
        ids.add(sid)
        sensor = sensors[sid]
        if (
            sensor["symbol"] != source.symbol
            or sensor["original_entry_at"] != source.m1_trigger_confirmed_at
            or sensor["original_trigger_family"] != source.m1_trigger_family
        ):
            raise ValueError("sensor original identity inconsistent")
        key = _state_key(source)
        if key not in cached:
            cached[key] = _next_boundaries(
                source, m15=m15, m15_opened=m15_opened
            )
        boundary = cached[key].get(source.m15_setup_confirmed_at)
        if boundary is None:
            # Missing independent M15 witness is a BLOCKER, not a trade veto.
            results.append({
                "source_opportunity_id": sid,
                "symbol": symbol,
                "classification": "M15_PARENT_NOT_RECONSTRUCTED",
                "source_entry_at": source.m1_trigger_confirmed_at,
                "source_family": source.m1_trigger_family,
                "changes_admission": False,
            })
            classes["M15_PARENT_NOT_RECONSTRUCTED"] += 1
            continue
        at = aware(source.m1_trigger_confirmed_at)
        m15_at = aware(source.m15_setup_confirmed_at)
        boundary_at = aware(boundary)
        if not m15_at < at <= boundary_at:
            raise ValueError("original trigger outside reconstructed M15 parent")
        direction = CapitalizerSourceDirection(source.h1_state_direction)
        full_bars = _slice(
            native, m1_opened, start=m15_at, end=boundary_at, context=0
        )
        prefix_bars = _slice(
            native, m1_opened, start=m15_at, end=at, context=0
        )
        if not prefix_bars or prefix_bars[-1].closed_at != at:
            raise ValueError("original M1 close missing from native source")
        full = observe_route_pair(
            full_bars, thesis_at=m15_at,
            deadline_at=boundary_at, direction=direction,
        )
        prefix = observe_route_pair(
            prefix_bars, thesis_at=m15_at,
            deadline_at=at, direction=direction,
        )
        matches_full = (
            full.first_at == source.m1_trigger_confirmed_at
            and full.first_family == source.m1_trigger_family
        )
        matches_prefix = (
            prefix.first_at == sensor["first_source_cisd_confirmed_at"]
            and prefix.first_family == sensor["first_source_cisd_family"]
        )
        full_source_match += matches_full
        prefix_sensor_match += matches_prefix
        disagreement = not (
            sensor["sensor_source_identity_match"]
        )
        if matches_full and matches_prefix:
            diagnosis = (
                "RECONSTRUCTED_FULL_VS_PREFIX_SELECTION"
                if disagreement else "MATCHED_BOTH_WINDOWS"
            )
        elif not matches_full and not matches_prefix:
            diagnosis = "BOTH_RECONSTRUCTIONS_DIFFER"
        elif not matches_full:
            diagnosis = "V49_FULL_WINDOW_RECONSTRUCTION_DIFFERS"
        else:
            diagnosis = "SHADOW_PREFIX_RECONSTRUCTION_DIFFERS"
        classes[diagnosis] += 1
        results.append({
            "source_opportunity_id": sid,
            "symbol": symbol,
            "source_entry_at": source.m1_trigger_confirmed_at,
            "source_family": source.m1_trigger_family,
            "sensor_first_at": sensor["first_source_cisd_confirmed_at"],
            "sensor_family": sensor["first_source_cisd_family"],
            "source_sensor_disagree": disagreement,
            "m15_confirmed_at": source.m15_setup_confirmed_at,
            "next_m15_or_h1_boundary": boundary,
            "full_window_witness": asdict(full),
            "closed_prefix_witness": asdict(prefix),
            "full_matches_original": matches_full,
            "prefix_matches_sensor": matches_prefix,
            "classification": diagnosis,
            "observers_are_v48_qore_not_author_certification": True,
            "full_window_contains_ex_post_evidence": True,
            "changes_admission": False,
        })
    if len(results) != len(sources):
        raise ValueError("some frozen source identities were lost")
    return {
        "identity": IDENTITY, "symbol": symbol, "sources": len(sources),
        "classified": dict(sorted(classes.items())),
        "full_matches_original": full_source_match,
        "prefix_matches_sensor": prefix_sensor_match,
        "changes_admission": 0, "uses_future_outcomes_to_admit": False,
        "trade_reexecuted": 0, "author_certified": False,
    }, tuple(results)


def aggregate(root: Path) -> dict[str, Any]:
    summaries = [json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted(root.rglob("scalper-cisd-prefix-market.json"))]
    if len(summaries) != 9 or len({r["symbol"] for r in summaries}) != 9:
        raise ValueError("require 9 distinct source-native markets")
    rows = [x for p in sorted(root.rglob("scalper-cisd-prefix-rows.jsonl"))
            for x in _jsonl(p)]
    if len(rows) != 2876 or len({
        r["source_opportunity_id"] for r in rows
    }) != 2876:
        raise ValueError("missing or duplicated frozen source identity")
    groups: Counter[str] = Counter(r["classification"] for r in rows)
    mismatched = [r for r in rows if r.get("source_sensor_disagree")]
    # Report every reconstructed/pending row instead of assuming the answer.
    return {
        "identity": IDENTITY,
        "markets": 9, "sources": len(rows),
        "diagnosis_counts": dict(sorted(groups.items())),
        "source_sensor_mismatches_in_reconstructed_rows": len(mismatched),
        "reconstructed_full_matches_original": sum(
            int(r["full_matches_original"]) for r in rows
            if "full_matches_original" in r
        ),
        "reconstructed_prefix_matches_sensor": sum(
            int(r["prefix_matches_sensor"]) for r in rows
            if "prefix_matches_sensor" in r
        ),
        "qore_observer_replay_not_author_fidelity": True,
        "outcome_free": True, "changes_admission": 0,
        "trading_enabled": False, "paper_pf": None, "paper_dd": None,
        "certification": "BLOCKED_AUTHOR_SOURCE_LINKAGE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    market_parser = sub.add_parser("market")
    for name in ("original", "sensor", "native", "output"):
        market_parser.add_argument(name, type=Path)
    matrix_parser = sub.add_parser("matrix")
    matrix_parser.add_argument("inputs", type=Path)
    matrix_parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == "market":
        report, rows = market(args.original, args.sensor, args.native)
        (args.output/"scalper-cisd-prefix-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n",
            encoding="utf-8",
        )
        with (args.output/"scalper-cisd-prefix-rows.jsonl").open(
            "w", encoding="utf-8"
        ) as file:
            for row in rows:
                file.write(json.dumps(row, sort_keys=True)+"\n")
    else:
        report = aggregate(args.inputs)
        (args.output/"scalper-cisd-prefix-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n",
            encoding="utf-8",
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
