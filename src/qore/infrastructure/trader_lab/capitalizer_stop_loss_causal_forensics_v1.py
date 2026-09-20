"""Nine-market stop-loss causal forensics for QORE Capitalizer.

Consumes the immutable three-session M5 geometry replay plus causal RAW M5 and
CIBO Market Journey evidence. This is post-outcome diagnostic research only.

The lab asks two separate questions:
1. Which pre-entry states repeatedly associate with STOP across all nine markets?
2. After a STOP, does the original target later trade in the same session, and how
   far beyond the original stop did price travel before any such recovery?

No result in this module is a stop-widening instruction, admission rule, source
methodology change, candidate freeze, fresh holdout, certification, or execution authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
    classify_microstructure_events,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)

IDENTITY = "QORE_CAPITALIZER_STOP_LOSS_CAUSAL_FORENSICS_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_CAUSE_MATRIX_V1"
NEW_YORK = ZoneInfo("America/New_York")
H1_MINUTES = 60
SESSION_START_MINUTE = {
    CapitalizerSession.ASIA: 20 * 60,
    CapitalizerSession.LONDON: 2 * 60,
    CapitalizerSession.NEW_YORK: 8 * 60 + 30,
}
RISK_QUARTILES = ("Q1_TIGHTEST", "Q2", "Q3", "Q4_WIDEST")


@dataclass(frozen=True, slots=True)
class CapitalizerStopCausalCohort:
    dimension: str
    key: str
    trades: int
    stops: int
    stop_rate: str
    baseline_stop_rate: str
    relative_lift: str


@dataclass(frozen=True, slots=True)
class CapitalizerPostStopRecovery:
    stops: int
    later_target_reached: int
    later_target_reached_rate: str
    recovered_le_0_25r: int
    recovered_le_0_5r: int
    recovered_le_1_0r: int
    recovered_overshoot_median_r: str | None
    recovered_overshoot_p90_r: str | None
    not_recovered_extension_median_r: str | None
    not_recovered_extension_p90_r: str | None


@dataclass(frozen=True, slots=True)
class CapitalizerStopCauseMarketReport:
    identity: str
    symbol: str
    session: str
    trades: int
    stops: int
    baseline_stop_rate: str
    cohorts: tuple[CapitalizerStopCausalCohort, ...]
    post_stop_recovery: CapitalizerPostStopRecovery
    source_replay_status: str = "M5_GEOMETRY_PROXY"
    source_strategy_status: str = "WAIT_M1_EVIDENCE"
    outcome_aware_forensics: bool = True
    causal_claimed: bool = False
    rule_promotion_allowed: bool = False
    stop_widening_authorized: bool = False
    source_methodology_modified: bool = False
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketStopCoincidence:
    dimension: str
    key: str
    markets_observed: int
    markets_above_baseline: int
    markets_at_least_5pct_above_baseline: int
    markets_at_most_5pct_below_baseline: int
    median_relative_lift: str
    min_relative_lift: str
    max_relative_lift: str


@dataclass(frozen=True, slots=True)
class CapitalizerNineMarketStopCauseMatrix:
    identity: str
    markets: tuple[CapitalizerStopCauseMarketReport, ...]
    complete_nine_market_universe: bool
    coincidences: tuple[CapitalizerCrossMarketStopCoincidence, ...]
    universal_elevated: tuple[str, ...]
    universal_reduced: tuple[str, ...]
    outcome_aware_forensics: bool = True
    causal_claimed: bool = False
    rule_promotion_allowed: bool = False
    stop_widening_authorized: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


def _rate(stops: int, trades: int) -> Decimal:
    if trades <= 0:
        raise ValueError("rate requires positive trade count")
    return Decimal(stops) / Decimal(trades)


def _event_signature(row: dict[str, Any]) -> str:
    labels = row.get("event_labels")
    if not isinstance(labels, list) or not labels:
        raise ValueError("trade row requires event_labels")
    if not all(isinstance(item, str) for item in labels):
        raise ValueError("event labels must be strings")
    return "+".join(labels)


def _event_family(row: dict[str, Any]) -> str:
    labels = tuple(str(item) for item in row["event_labels"])
    acceptance = any("ACCEPTANCE" in item for item in labels)
    rejection = any("RAID_REJECTION" in item for item in labels)
    if acceptance and rejection:
        return "MIXED"
    if acceptance:
        return "ACCEPTANCE"
    if rejection:
        return "RAID_REJECTION"
    return "OTHER"


def _reward_band(row: dict[str, Any]) -> str:
    value = Decimal(str(row["planned_reward_r"]))
    if value < 1:
        return "LT_1R"
    if value < Decimal("1.5"):
        return "1_TO_LT_1_5R"
    if value < 2:
        return "1_5_TO_LT_2R"
    if value < 3:
        return "2_TO_LT_3R"
    return "GE_3R"


def _entry_ny(row: dict[str, Any]) -> datetime:
    value = datetime.fromisoformat(str(row["entry_at"]))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("entry timestamp must be aware")
    return value.astimezone(NEW_YORK)


def _session_elapsed_hour(row: dict[str, Any]) -> str:
    session = CapitalizerSession(str(row["session"]))
    local = _entry_ny(row)
    minute = local.hour * 60 + local.minute
    start = SESSION_START_MINUTE[session]
    if session is CapitalizerSession.ASIA and minute < 2 * 60:
        minute += 24 * 60
    elapsed = (minute - start) // 60
    if elapsed < 0:
        raise ValueError("trade precedes frozen session start")
    return f"H{elapsed}"


def _load_trade_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"market stop forensics requires one replay ledger, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("replay row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("forensics require non-outcome-selected replay")
            rows.append(raw)
    if not rows:
        raise ValueError("market stop forensics requires trades")
    return tuple(rows)


def _risk_quartile_index(rows: tuple[dict[str, Any], ...]) -> dict[int, str]:
    ordered = sorted(
        range(len(rows)),
        key=lambda index: (
            Decimal(str(rows[index]["initial_risk_price"]))
            / Decimal(str(rows[index]["entry_price"])),
            str(rows[index]["entry_at"]),
            str(rows[index]["side"]),
        ),
    )
    result: dict[int, str] = {}
    count = len(ordered)
    for rank, row_index in enumerate(ordered):
        result[row_index] = RISK_QUARTILES[min(3, rank * 4 // count)]
    return result


def _h1_bucket(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _journey_index(
    root: Path,
) -> tuple[
    dict[tuple[str, str], tuple[dict[str, Any], ...]],
    dict[str, tuple[int, int]],
]:
    path = root / "MARKET_JOURNEY_LEDGER.jsonl"
    timing_path = root / "DEPARTURE_TIMING_LEDGER.jsonl"
    if not path.exists() or not timing_path.exists():
        raise ValueError("Market Journey causal ledgers missing")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("journey row must be object")
            if row.get("causal_feature") is not True or row.get("outcome_only") is not False:
                raise ValueError("journey row must remain causal")
            if row.get("source_timeframe") != "H1" or row.get("departure_at") is None:
                continue
            side = str(row.get("side")).upper()
            grouped[(str(row["departure_at"]), side)].append(row)

    timing: dict[str, tuple[int, int]] = {}
    with timing_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("timing row must be object")
            if row.get("departure_at") is None:
                continue
            source = row.get("minutes_source_event_to_departure")
            cisd = row.get("cisd_latency_minutes")
            if not isinstance(source, int) or not isinstance(cisd, int):
                continue
            timing[str(row["episode_id"])] = (source, cisd)
    return ({key: tuple(value) for key, value in grouped.items()}, timing)


def _source_age(signal_at: datetime, episodes: tuple[dict[str, Any], ...]) -> str:
    states: set[str] = set()
    for episode in episodes:
        created = datetime.fromisoformat(str(episode["source_boundary_created_at"]))
        distance = int((_h1_bucket(signal_at) - _h1_bucket(created)).total_seconds() // 3600)
        if distance < 0:
            raise ValueError("future H1 source boundary")
        states.add(
            "CURRENT_H1_SOURCE"
            if distance == 0
            else "PRIOR_H1_SOURCE"
            if distance == 1
            else "OLDER_H1_SOURCE"
        )
    return next(iter(states)) if len(states) == 1 else "MIXED_H1_SOURCE_AGE"


def _reclaim_state(signal_at: datetime, episodes: tuple[dict[str, Any], ...]) -> str:
    states: list[bool] = []
    for episode in episodes:
        raw = episode.get("reclaim_at")
        states.append(raw is not None and datetime.fromisoformat(str(raw)) <= signal_at)
    if all(states):
        return "RECLAIM_ALL"
    if any(states):
        return "RECLAIM_MIXED"
    return "NO_RECLAIM"


def _timing_state(
    episodes: tuple[dict[str, Any], ...],
    timing: dict[str, tuple[int, int]],
    *,
    position: int,
) -> str:
    values: list[int] = []
    for episode in episodes:
        raw = timing.get(str(episode["episode_id"]))
        if raw is None:
            return "TIMING_UNRESOLVED"
        values.append(raw[position])
    return "ALL_WITHIN_H1" if all(value < H1_MINUTES for value in values) else "ANY_CROSS_H1"


def _repeat_state(
    *,
    signal_at: datetime,
    side: CapitalizerSide,
    bars: tuple[CapitalizerM5Bar, ...],
    by_close: dict[datetime, int],
) -> str:
    index = by_close.get(signal_at.astimezone(UTC))
    if index is None or index < 2:
        return "UNRESOLVED"
    previous = bars[index - 1]
    previous_previous = bars[index - 2]
    events = classify_microstructure_events(previous, previous_previous)
    same = (
        CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE
        if side is CapitalizerSide.LONG
        else CapitalizerMicrostructureEvent.LOW_ACCEPTANCE
    )
    return "REPEAT" if same in events else "FRESH"


def _percentile(values: tuple[Decimal, ...], quantile: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (Decimal(len(ordered) - 1)) * quantile
    low = int(position)
    high = min(len(ordered) - 1, low + 1)
    weight = position - Decimal(low)
    return ordered[low] * (1 - weight) + ordered[high] * weight


def _cohorts(
    rows: tuple[dict[str, Any], ...],
    *,
    baseline: Decimal,
    dimension: str,
    key_fn: Callable[[dict[str, Any]], str],
) -> tuple[CapitalizerStopCausalCohort, ...]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(row)
    result: list[CapitalizerStopCausalCohort] = []
    for key in sorted(grouped):
        items = grouped[key]
        stops = sum(bool(item["_is_stop"]) for item in items)
        rate = _rate(stops, len(items))
        result.append(
            CapitalizerStopCausalCohort(
                dimension=dimension,
                key=key,
                trades=len(items),
                stops=stops,
                stop_rate=str(rate),
                baseline_stop_rate=str(baseline),
                relative_lift=str(rate / baseline),
            )
        )
    return tuple(result)


def _post_stop_recovery(
    stop_rows: tuple[dict[str, Any], ...],
    *,
    bars: tuple[CapitalizerM5Bar, ...],
    by_open: dict[datetime, int],
    session: CapitalizerSession,
) -> CapitalizerPostStopRecovery:
    recovered: list[Decimal] = []
    not_recovered: list[Decimal] = []
    le_025 = le_05 = le_10 = 0

    for row in stop_rows:
        exit_at = datetime.fromisoformat(str(row["exit_at"])).astimezone(UTC)
        start = by_open.get(exit_at)
        risk = Decimal(str(row["initial_risk_price"]))
        stop = Decimal(str(row["stop_price"]))
        target = Decimal(str(row["target_price"]))
        side = CapitalizerSide(str(row["side"]))
        later_target = False
        extension = Decimal("0")

        if start is not None:
            for bar in bars[start:]:
                if capitalizer_session_at(bar.opened_at) is not session:
                    break
                if side is CapitalizerSide.LONG:
                    later_target = later_target or bar.high >= target
                    extension = max(extension, max(Decimal("0"), stop - bar.low) / risk)
                else:
                    later_target = later_target or bar.low <= target
                    extension = max(extension, max(Decimal("0"), bar.high - stop) / risk)

        if later_target:
            recovered.append(extension)
            le_025 += extension <= Decimal("0.25")
            le_05 += extension <= Decimal("0.5")
            le_10 += extension <= Decimal("1")
        else:
            not_recovered.append(extension)

    stop_count = len(stop_rows)
    return CapitalizerPostStopRecovery(
        stops=stop_count,
        later_target_reached=len(recovered),
        later_target_reached_rate=str(_rate(len(recovered), stop_count)),
        recovered_le_0_25r=le_025,
        recovered_le_0_5r=le_05,
        recovered_le_1_0r=le_10,
        recovered_overshoot_median_r=(
            None if not recovered else str(_percentile(tuple(recovered), Decimal("0.5")))
        ),
        recovered_overshoot_p90_r=(
            None if not recovered else str(_percentile(tuple(recovered), Decimal("0.9")))
        ),
        not_recovered_extension_median_r=(
            None
            if not not_recovered
            else str(_percentile(tuple(not_recovered), Decimal("0.5")))
        ),
        not_recovered_extension_p90_r=(
            None
            if not not_recovered
            else str(_percentile(tuple(not_recovered), Decimal("0.9")))
        ),
    )


def build_market_report(
    *,
    replay_root: Path,
    m5_root: Path,
    journey_root: Path,
) -> CapitalizerStopCauseMarketReport:
    raw_rows = _load_trade_rows(replay_root)
    symbols = {str(row["symbol"]) for row in raw_rows}
    sessions = {str(row["session"]) for row in raw_rows}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("one stop-cause report requires one market/session")
    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))
    if symbol not in allowed_markets(session):
        raise ValueError("market/session drift")

    bars = tuple(iter_atlas_m5(m5_root))
    by_close = {bar.closed_at: index for index, bar in enumerate(bars)}
    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}
    journey, timing = _journey_index(journey_root)
    quartiles = _risk_quartile_index(raw_rows)

    enriched: list[dict[str, Any]] = []
    stop_rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        row = dict(raw)
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        side = CapitalizerSide(str(row["side"]))
        episodes = journey.get((str(row["signal_at"]), side.value), ())
        if episodes:
            reclaim = _reclaim_state(signal_at, episodes)
            age = _source_age(signal_at, episodes)
            episode_tag = "SINGLE_EPISODE" if len(episodes) == 1 else "MULTI_EPISODE"
            boundaries = {
                (str(item["source_boundary"]), str(item["source_boundary_created_at"]))
                for item in episodes
            }
            boundary_tag = (
                "SINGLE_SOURCE_BOUNDARY"
                if len(boundaries) == 1
                else "MULTI_SOURCE_BOUNDARY"
            )
            source_timing = _timing_state(episodes, timing, position=0)
            cisd_timing = _timing_state(episodes, timing, position=1)
        else:
            reclaim = age = episode_tag = boundary_tag = "NO_EXACT_H1_EPISODE"
            source_timing = cisd_timing = "NO_EXACT_H1_EPISODE"

        repeat = _repeat_state(
            signal_at=signal_at,
            side=side,
            bars=bars,
            by_close=by_close,
        )
        local = _entry_ny(row)
        row["_is_stop"] = str(row["exit_reason"]) == "STOP"
        row["_weekday"] = local.strftime("%A").upper()
        row["_ny_hour"] = f"{local.hour:02d}"
        row["_elapsed"] = _session_elapsed_hour(row)
        row["_event_signature"] = _event_signature(row)
        row["_event_family"] = _event_family(row)
        row["_reward_band"] = _reward_band(row)
        row["_risk_quartile"] = quartiles[index]
        row["_repeat"] = repeat
        row["_reclaim"] = reclaim
        row["_source_age"] = age
        row["_episode_multiplicity"] = episode_tag
        row["_boundary_multiplicity"] = boundary_tag
        row["_source_timing"] = source_timing
        row["_cisd_timing"] = cisd_timing
        row["_repeat_x_reclaim"] = f"{repeat}|{reclaim}"
        row["_risk_x_elapsed"] = f"{quartiles[index]}|{row['_elapsed']}"
        row["_risk_x_repeat"] = f"{quartiles[index]}|{repeat}"
        row["_event_x_repeat"] = f"{row['_event_family']}|{repeat}"
        enriched.append(row)
        if row["_is_stop"]:
            stop_rows.append(row)

    baseline = _rate(len(stop_rows), len(enriched))
    dimensions: tuple[tuple[str, str], ...] = (
        ("WEEKDAY", "_weekday"),
        ("NY_HOUR", "_ny_hour"),
        ("SESSION_ELAPSED_HOUR", "_elapsed"),
        ("SIDE", "side"),
        ("EVENT_SIGNATURE", "_event_signature"),
        ("EVENT_FAMILY", "_event_family"),
        ("PLANNED_REWARD_BAND", "_reward_band"),
        ("RELATIVE_STOP_WIDTH_QUARTILE", "_risk_quartile"),
        ("REPEAT_STATE", "_repeat"),
        ("RECLAIM_STATE", "_reclaim"),
        ("H1_SOURCE_AGE", "_source_age"),
        ("H1_EPISODE_MULTIPLICITY", "_episode_multiplicity"),
        ("H1_BOUNDARY_MULTIPLICITY", "_boundary_multiplicity"),
        ("SOURCE_TIMING", "_source_timing"),
        ("CISD_TIMING", "_cisd_timing"),
        ("REPEAT_X_RECLAIM", "_repeat_x_reclaim"),
        ("RISK_X_ELAPSED", "_risk_x_elapsed"),
        ("RISK_X_REPEAT", "_risk_x_repeat"),
        ("EVENT_X_REPEAT", "_event_x_repeat"),
    )
    cohorts = tuple(
        cohort
        for dimension, field in dimensions
        for cohort in _cohorts(
            tuple(enriched),
            baseline=baseline,
            dimension=dimension,
            key_fn=lambda item, field=field: str(item[field]),
        )
    )

    return CapitalizerStopCauseMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        trades=len(enriched),
        stops=len(stop_rows),
        baseline_stop_rate=str(baseline),
        cohorts=cohorts,
        post_stop_recovery=_post_stop_recovery(
            tuple(stop_rows),
            bars=bars,
            by_open=by_open,
            session=session,
        ),
    )


def write_market_report(report: CapitalizerStopCauseMarketReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-stop-loss-causal-forensics-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_market_reports(root: Path) -> tuple[CapitalizerStopCauseMarketReport, ...]:
    paths = sorted(root.rglob("capitalizer-*-stop-loss-causal-forensics-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"nine-market stop matrix requires 9 reports, got {len(paths)}")
    reports: list[CapitalizerStopCauseMarketReport] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        reports.append(
            CapitalizerStopCauseMarketReport(
                **{
                    **raw,
                    "cohorts": tuple(
                        CapitalizerStopCausalCohort(**item) for item in raw["cohorts"]
                    ),
                    "post_stop_recovery": CapitalizerPostStopRecovery(
                        **raw["post_stop_recovery"]
                    ),
                }
            )
        )
    return tuple(sorted(reports, key=lambda item: item.symbol))


def build_matrix_from_reports(
    reports: tuple[CapitalizerStopCauseMarketReport, ...],
) -> CapitalizerNineMarketStopCauseMatrix:
    expected = {
        symbol
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    if {report.symbol for report in reports} != expected:
        raise ValueError("nine-market stop-cause universe mismatch")

    indexed: dict[tuple[str, str], list[CapitalizerStopCausalCohort]] = defaultdict(list)
    for report in reports:
        for cohort in report.cohorts:
            indexed[(cohort.dimension, cohort.key)].append(cohort)

    coincidences: list[CapitalizerCrossMarketStopCoincidence] = []
    for (dimension, key), raw in sorted(indexed.items()):
        lifts = tuple(Decimal(item.relative_lift) for item in raw)
        coincidences.append(
            CapitalizerCrossMarketStopCoincidence(
                dimension=dimension,
                key=key,
                markets_observed=len(raw),
                markets_above_baseline=sum(value > 1 for value in lifts),
                markets_at_least_5pct_above_baseline=sum(
                    value >= Decimal("1.05") for value in lifts
                ),
                markets_at_most_5pct_below_baseline=sum(
                    value <= Decimal("0.95") for value in lifts
                ),
                median_relative_lift=str(median(lifts)),
                min_relative_lift=str(min(lifts)),
                max_relative_lift=str(max(lifts)),
            )
        )

    coincidence_tuple = tuple(coincidences)
    return CapitalizerNineMarketStopCauseMatrix(
        identity=MATRIX_IDENTITY,
        markets=reports,
        complete_nine_market_universe=True,
        coincidences=coincidence_tuple,
        universal_elevated=tuple(
            f"{item.dimension}:{item.key}"
            for item in coincidence_tuple
            if item.markets_observed == 9
            and item.markets_at_least_5pct_above_baseline == 9
        ),
        universal_reduced=tuple(
            f"{item.dimension}:{item.key}"
            for item in coincidence_tuple
            if item.markets_observed == 9
            and item.markets_at_most_5pct_below_baseline == 9
        ),
    )


def build_matrix(root: Path) -> CapitalizerNineMarketStopCauseMatrix:
    return build_matrix_from_reports(_load_market_reports(root))


def write_matrix(report: CapitalizerNineMarketStopCauseMatrix, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-stop-cause-matrix-v1.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# QORE Capitalizer — Nine-Market Stop Cause Matrix V1",
        "",
        "- Consumed research evidence only.",
        "- M5 geometry proxy remains WAIT_M1_EVIDENCE.",
        "- No stop widening, rule promotion, candidate freeze or certification.",
        "",
        "| Market | Session | Trades | Stops | Stop rate | Later target after STOP |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for market in report.markets:
        lines.append(
            f"| {market.symbol} | {market.session} | {market.trades} | "
            f"{market.stops} | {Decimal(market.baseline_stop_rate) * 100:.2f}% | "
            f"{Decimal(market.post_stop_recovery.later_target_reached_rate) * 100:.2f}% |"
        )
    lines.extend(["", "## Universal elevated stop coincidences", ""])
    lines.extend(f"- {item}" for item in report.universal_elevated)
    lines.extend(["", "## Universal reduced stop coincidences", ""])
    lines.extend(f"- {item}" for item in report.universal_reduced)
    (output / "capitalizer-nine-market-stop-cause-matrix-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer stop-loss causal forensics")
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("m5_root", type=Path)
    market.add_argument("journey_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report = build_market_report(
            replay_root=args.replay_root,
            m5_root=args.m5_root,
            journey_root=args.journey_root,
        )
        write_market_report(report, args.output)
        print(
            json.dumps(
                {
                    "symbol": report.symbol,
                    "trades": report.trades,
                    "stops": report.stops,
                    "stop_rate": report.baseline_stop_rate,
                    "later_target_reached_rate": (
                        report.post_stop_recovery.later_target_reached_rate
                    ),
                },
                sort_keys=True,
            )
        )
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "markets": len(report.markets),
                "universal_elevated": list(report.universal_elevated),
                "universal_reduced": list(report.universal_reduced),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
