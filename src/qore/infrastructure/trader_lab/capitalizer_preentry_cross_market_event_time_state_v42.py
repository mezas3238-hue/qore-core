"""Frozen cross-market event-time set representation for Capitalizer V42.

V42 uses only the latest completed provider-native M1 bar from *other* markets
at the candidate decision timestamp. Peer bars older than one M1 duration are
excluded from price-derived aggregates; they are never forward-filled or
imputed, and the candidate entrant is never dropped because a peer is closed.

The exact 18D representation was predeclared in PR #623 comment 5881287609
before STOP/TARGET labels were evaluated for V42.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_separability_v38 as v38,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_10y_m1_clone_v1 import (
    TARGET_SYMBOLS,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerSide,
    factor_exposures,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_CROSS_MARKET_EVENT_TIME_STATE_V42"
MAX_FRESH_AGE_SECONDS = 60
PERIOD_SPECS = (
    ("DEVELOPMENT_2024_2026", "development", 948),
    ("CONSUMED_VALIDATION_2022_2024", "validation", 1034),
    ("CONSUMED_RESERVED_2020_2022", "reserved", 1088),
)

FEATURE_NAMES = (
    "available_peer_fraction",
    "peer_signed_body_mean",
    "peer_abs_body_mean",
    "peer_positive_body_fraction",
    "peer_negative_body_fraction",
    "peer_signed_body_dispersion",
    "peer_range_fraction_mean",
    "peer_range_fraction_max",
    "peer_wick_skew_mean",
    "peer_wick_skew_dispersion",
    "shared_factor_contribution_fraction",
    "factor_support_fraction",
    "factor_conflict_fraction",
    "factor_aligned_signal_mean",
    "factor_aligned_abs_signal_mean",
    "factor_support_signal_max",
    "factor_conflict_magnitude_max",
    "factor_signal_dispersion",
)


@dataclass(frozen=True, slots=True)
class PeerEventSnapshot:
    period: str
    candidate_symbol: str
    candidate_side: str
    entry_at: str
    peer_symbol: str
    available: bool
    age_seconds: int | None
    signed_body_fraction: str | None
    range_fraction: str | None
    wick_skew: str | None
    feature_timestamp_le_entry: bool = True
    future_bar_used: bool = False
    interpolation_used: bool = False
    synthetic_value_used: bool = False
    outcome_used: bool = False
    exit_used: bool = False
    mae_mfe_used: bool = False

    def __post_init__(self) -> None:
        if self.peer_symbol not in TARGET_SYMBOLS:
            raise ValueError("V42 peer symbol outside Capitalizer universe")
        if self.candidate_symbol not in TARGET_SYMBOLS:
            raise ValueError("V42 candidate symbol outside Capitalizer universe")
        if self.candidate_side not in ("LONG", "SHORT"):
            raise ValueError("V42 candidate side must be LONG/SHORT")
        if not self.feature_timestamp_le_entry or any(
            (
                self.future_bar_used,
                self.interpolation_used,
                self.synthetic_value_used,
                self.outcome_used,
                self.exit_used,
                self.mae_mfe_used,
            )
        ):
            raise ValueError("V42 peer causal/governance invariant violated")
        values = (
            self.signed_body_fraction,
            self.range_fraction,
            self.wick_skew,
        )
        if self.available:
            if self.age_seconds is None:
                raise ValueError("V42 available peer requires bar age")
            if not 0 <= self.age_seconds <= MAX_FRESH_AGE_SECONDS:
                raise ValueError("V42 available peer exceeds 60s freshness")
            if any(value is None for value in values):
                raise ValueError("V42 available peer requires primitives")
        elif any(value is not None for value in values):
            raise ValueError("V42 stale peer must not retain price primitives")


@dataclass(frozen=True, slots=True)
class CrossMarketEventTimeState:
    period: str
    symbol: str
    side: str
    entry_at: str
    feature_names: tuple[str, ...]
    vector: tuple[str, ...]
    feature_count: int
    available_peer_count: int
    stale_peer_count: int
    candidate_market_excluded: bool = True
    stale_peer_prices_excluded: bool = True
    feature_timestamp_le_entry: bool = True
    future_bar_used: bool = False
    interpolation_used: bool = False
    synthetic_value_used: bool = False
    outcome_used: bool = False
    exit_used: bool = False
    mae_mfe_used: bool = False
    symbol_identity_in_vector: bool = False
    peer_symbol_identity_bits_in_vector: bool = False
    date_identity_in_vector: bool = False
    session_identity_in_vector: bool = False

    def __post_init__(self) -> None:
        if self.feature_names != FEATURE_NAMES:
            raise ValueError("V42 feature-name contract drift")
        if len(self.vector) != len(FEATURE_NAMES):
            raise ValueError("V42 vector dimension drift")
        if self.feature_count != len(FEATURE_NAMES):
            raise ValueError("V42 feature_count mismatch")
        if self.available_peer_count + self.stale_peer_count != 8:
            raise ValueError("V42 must account for exactly eight peer markets")
        if not (
            self.candidate_market_excluded
            and self.stale_peer_prices_excluded
            and self.feature_timestamp_le_entry
        ):
            raise ValueError("V42 set-boundary invariant violated")
        if any(
            (
                self.future_bar_used,
                self.interpolation_used,
                self.synthetic_value_used,
                self.outcome_used,
                self.exit_used,
                self.mae_mfe_used,
                self.symbol_identity_in_vector,
                self.peer_symbol_identity_bits_in_vector,
                self.date_identity_in_vector,
                self.session_identity_in_vector,
            )
        ):
            raise ValueError("V42 causal/governance invariant violated")


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("V42 requires timezone-aware timestamps")
    return parsed.astimezone(UTC)


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _dispersion(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        return Decimal("0")
    center = _mean(values)
    variance = _mean(tuple((value - center) ** 2 for value in values))
    return variance.sqrt()


def _peer_primitives(bar: CapitalizerM1Bar) -> tuple[Decimal, Decimal, Decimal]:
    span = bar.range
    if span == 0:
        signed_body = Decimal("0")
        wick_skew = Decimal("0")
    else:
        signed_body = (bar.close - bar.open) / span
        lower = min(bar.open, bar.close) - bar.low
        upper = bar.high - max(bar.open, bar.close)
        wick_skew = (lower - upper) / span
    return signed_body, span / bar.open, wick_skew


def _snapshot_for_entry(
    *,
    period: str,
    candidate_symbol: str,
    candidate_side: str,
    entry_at: datetime,
    peer_symbol: str,
    bars: tuple[CapitalizerM1Bar, ...],
    closed_times: tuple[datetime, ...],
) -> PeerEventSnapshot:
    index = bisect_right(closed_times, entry_at) - 1
    if index < 0:
        return PeerEventSnapshot(
            period=period,
            candidate_symbol=candidate_symbol,
            candidate_side=candidate_side,
            entry_at=entry_at.isoformat(),
            peer_symbol=peer_symbol,
            available=False,
            age_seconds=None,
            signed_body_fraction=None,
            range_fraction=None,
            wick_skew=None,
        )
    bar = bars[index]
    if bar.closed_at > entry_at:
        raise ValueError("V42 attempted future-bar use")
    age_seconds = int((entry_at - bar.closed_at).total_seconds())
    if age_seconds < 0:
        raise ValueError("V42 negative peer-bar age")
    if age_seconds > MAX_FRESH_AGE_SECONDS:
        return PeerEventSnapshot(
            period=period,
            candidate_symbol=candidate_symbol,
            candidate_side=candidate_side,
            entry_at=entry_at.isoformat(),
            peer_symbol=peer_symbol,
            available=False,
            age_seconds=age_seconds,
            signed_body_fraction=None,
            range_fraction=None,
            wick_skew=None,
        )
    body, range_fraction, wick = _peer_primitives(bar)
    return PeerEventSnapshot(
        period=period,
        candidate_symbol=candidate_symbol,
        candidate_side=candidate_side,
        entry_at=entry_at.isoformat(),
        peer_symbol=peer_symbol,
        available=True,
        age_seconds=age_seconds,
        signed_body_fraction=str(body),
        range_fraction=str(range_fraction),
        wick_skew=str(wick),
    )


def collect_peer_market(
    *,
    peer_symbol: str,
    m1_root: Path,
    selected_geometry_root: Path,
    output: Path,
) -> dict[str, object]:
    if peer_symbol not in TARGET_SYMBOLS:
        raise ValueError("V42 peer market outside Capitalizer universe")
    bars = tuple(iter_cibo_m1(m1_root))
    if not bars or {bar.symbol for bar in bars} != {peer_symbol}:
        raise ValueError("V42 peer M1 source mismatch")
    closed_times = tuple(bar.closed_at for bar in bars)
    if tuple(sorted(closed_times)) != closed_times:
        raise ValueError("V42 peer M1 chronology drift")

    output.mkdir(parents=True, exist_ok=True)
    counts: dict[str, dict[str, int]] = {}
    total_rows = 0
    stem = f"capitalizer-v42-peer-{peer_symbol.lower()}-event-state"
    with (output / f"{stem}.jsonl").open("w", encoding="utf-8") as handle:
        for period, slug, expected in PERIOD_SPECS:
            selected = v38._load_period_geometry(
                selected_geometry_root,
                slug=slug,
            )
            if len(selected) != expected:
                raise ValueError("V42 selected population count drift")
            period_rows: list[PeerEventSnapshot] = []
            for row in sorted(
                selected.values(),
                key=lambda item: (_aware(item.entry_at), item.symbol),
            ):
                period_rows.append(
                    _snapshot_for_entry(
                        period=period,
                        candidate_symbol=row.symbol,
                        candidate_side=row.side,
                        entry_at=_aware(row.entry_at),
                        peer_symbol=peer_symbol,
                        bars=bars,
                        closed_times=closed_times,
                    )
                )
            if len(period_rows) != expected:
                raise ValueError("V42 peer snapshot count drift")
            for snapshot in period_rows:
                handle.write(json.dumps(asdict(snapshot), sort_keys=True) + "\n")
            counts[period] = {
                "rows": len(period_rows),
                "fresh": sum(row.available for row in period_rows),
                "stale_or_missing": sum(not row.available for row in period_rows),
            }
            total_rows += len(period_rows)

    report: dict[str, object] = {
        "identity": IDENTITY,
        "peer_symbol": peer_symbol,
        "state_role": "PEER_EVENT_SNAPSHOT_ONLY",
        "max_fresh_age_seconds": MAX_FRESH_AGE_SECONDS,
        "period_counts": counts,
        "total_rows": total_rows,
        "candidate_market_exclusion_deferred_to_set_builder": True,
        "stale_peer_price_imputation_used": False,
        "future_bar_used": False,
        "outcome_used": False,
        "exit_used": False,
        "mae_mfe_used": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "trader_certified": False,
    }
    (output / f"{stem}-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _load_peer_snapshots(
    root: Path,
    *,
    period: str,
) -> dict[tuple[str, str], tuple[PeerEventSnapshot, ...]]:
    paths = sorted(root.rglob("capitalizer-v42-peer-*-event-state.jsonl"))
    if len(paths) != len(TARGET_SYMBOLS):
        raise ValueError(f"V42 requires nine peer ledgers, got {len(paths)}")
    grouped: dict[tuple[str, str], list[PeerEventSnapshot]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("V42 peer row must be JSON object")
                snapshot = PeerEventSnapshot(**payload)
                if snapshot.period != period:
                    continue
                key = (snapshot.candidate_symbol, snapshot.entry_at)
                grouped.setdefault(key, []).append(snapshot)
    result: dict[tuple[str, str], tuple[PeerEventSnapshot, ...]] = {}
    for key, rows in grouped.items():
        peer_symbols = {row.peer_symbol for row in rows}
        if peer_symbols != set(TARGET_SYMBOLS):
            raise ValueError("V42 entrant does not have all nine peer ledgers")
        result[key] = tuple(sorted(rows, key=lambda row: row.peer_symbol))
    if not result:
        raise ValueError(f"V42 has no peer snapshots for {period}")
    return result


def _factor_map(symbol: str, side: str) -> dict[str, Decimal]:
    position = CapitalizerExposurePosition(
        symbol=symbol,
        side=CapitalizerSide(side),
        risk_r=Decimal("1"),
    )
    return {row.factor: row.net_r for row in factor_exposures((position,))}


def _build_set_state(
    *,
    period: str,
    symbol: str,
    side: str,
    entry_at: str,
    snapshots: tuple[PeerEventSnapshot, ...],
) -> CrossMarketEventTimeState:
    if {row.peer_symbol for row in snapshots} != set(TARGET_SYMBOLS):
        raise ValueError("V42 set builder requires all nine peer snapshots")
    peers = tuple(row for row in snapshots if row.peer_symbol != symbol)
    if len(peers) != 8:
        raise ValueError("V42 candidate-market exclusion drift")
    available = tuple(row for row in peers if row.available)

    bodies = tuple(
        Decimal(row.signed_body_fraction)
        for row in available
        if row.signed_body_fraction is not None
    )
    ranges = tuple(
        Decimal(row.range_fraction)
        for row in available
        if row.range_fraction is not None
    )
    wicks = tuple(
        Decimal(row.wick_skew)
        for row in available
        if row.wick_skew is not None
    )
    if not (len(bodies) == len(ranges) == len(wicks) == len(available)):
        raise ValueError("V42 available peer primitive drift")

    if available:
        peer_values = (
            Decimal(len(available)) / Decimal("8"),
            _mean(bodies),
            _mean(tuple(abs(value) for value in bodies)),
            Decimal(sum(value > 0 for value in bodies)) / Decimal(len(bodies)),
            Decimal(sum(value < 0 for value in bodies)) / Decimal(len(bodies)),
            _dispersion(bodies),
            _mean(ranges),
            max(ranges),
            _mean(wicks),
            _dispersion(wicks),
        )
    else:
        peer_values = (Decimal("0"),) * 10

    candidate_factors = _factor_map(symbol, side)
    contributions: list[Decimal] = []
    for row in available:
        if row.signed_body_fraction is None:
            raise AssertionError("V42 available peer lost body primitive")
        body = Decimal(row.signed_body_fraction)
        peer_factors = _factor_map(row.peer_symbol, "LONG")
        for factor in set(candidate_factors) & set(peer_factors):
            contributions.append(
                candidate_factors[factor] * peer_factors[factor] * body
            )
    factor_values_tuple = tuple(contributions)
    if factor_values_tuple:
        support = tuple(value for value in factor_values_tuple if value > 0)
        conflict = tuple(value for value in factor_values_tuple if value < 0)
        factor_values = (
            Decimal(len(factor_values_tuple)) / Decimal("16"),
            Decimal(len(support)) / Decimal(len(factor_values_tuple)),
            Decimal(len(conflict)) / Decimal(len(factor_values_tuple)),
            _mean(factor_values_tuple),
            _mean(tuple(abs(value) for value in factor_values_tuple)),
            max(support, default=Decimal("0")),
            abs(min(conflict, default=Decimal("0"))),
            _dispersion(factor_values_tuple),
        )
    else:
        factor_values = (Decimal("0"),) * 8

    values = (*peer_values, *factor_values)
    if len(values) != len(FEATURE_NAMES):
        raise ValueError("V42 internal feature dimension drift")
    if any(not value.is_finite() for value in values):
        raise ValueError("V42 vector contains non-finite value")

    return CrossMarketEventTimeState(
        period=period,
        symbol=symbol,
        side=side,
        entry_at=entry_at,
        feature_names=FEATURE_NAMES,
        vector=tuple(str(value) for value in values),
        feature_count=len(FEATURE_NAMES),
        available_peer_count=len(available),
        stale_peer_count=8 - len(available),
    )


def build_period_states(
    snapshot_root: Path,
    *,
    period: str,
) -> dict[tuple[str, str], CrossMarketEventTimeState]:
    grouped = _load_peer_snapshots(snapshot_root, period=period)
    result: dict[tuple[str, str], CrossMarketEventTimeState] = {}
    for key, snapshots in grouped.items():
        symbol, entry_at = key
        sides = {row.candidate_side for row in snapshots}
        if len(sides) != 1:
            raise ValueError("V42 candidate side drift across peer ledgers")
        state = _build_set_state(
            period=period,
            symbol=symbol,
            side=next(iter(sides)),
            entry_at=entry_at,
            snapshots=snapshots,
        )
        if key in result:
            raise ValueError("V42 duplicate entrant state")
        result[key] = state
    return result


def state_from_json_dict(payload: dict[str, Any]) -> CrossMarketEventTimeState:
    normalized = dict(payload)
    for field in ("feature_names", "vector"):
        value = normalized.get(field)
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"V42 {field} must be sequence")
        normalized[field] = tuple(str(item) for item in value)
    return CrossMarketEventTimeState(**normalized)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("peer_symbol", choices=TARGET_SYMBOLS)
    parser.add_argument("m1_root", type=Path)
    parser.add_argument("selected_geometry_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = collect_peer_market(
        peer_symbol=args.peer_symbol,
        m1_root=args.m1_root,
        selected_geometry_root=args.selected_geometry_root,
        output=args.output,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
