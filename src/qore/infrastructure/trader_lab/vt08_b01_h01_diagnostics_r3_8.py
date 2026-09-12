"""Pre-entry causal diagnostics for VT-08 R3.8 Failure Forensics H01.

This module consumes the frozen run-34693803930 research artifacts and
reconstructs every executed B01 candidate with the unchanged R3.8 evaluator.
It is descriptive forensics only: outcome is kept separate from the pre-entry
feature vector, no threshold is selected, and no methodology mutation is
authorized from consumed evidence.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt08_b01_backtest_r3_8 import _load
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    AUTHORIZED_FOREX_MARKETS,
    Vt08B01Bar,
    evaluate_b01_at_entry_indexed,
    methodology_fingerprint,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_b01_h01_pre_entry_diagnostics.r3.8.v1"
_BACKTEST_SCHEMA = "qore.trader_lab.vt08_b01_backtest.r3.8.v1"
_BASELINE_RUN_ID = 34693803930
_FORBIDDEN_REUSE = "run-34693803930"
_FEATURES = (
    "risk_norm_prior_h4",
    "sweep_depth_norm_prior_h4",
    "protected_swing_depth_norm_prior_h4",
    "cisd_confirmation_latency_minutes",
    "cisd_to_entry_minutes",
    "cisd_displacement_norm_prior_h4",
    "important_level_to_entry_norm_prior_h4",
    "cisd_level_to_entry_norm_prior_h4",
)


class Vt08B01H01DiagnosticsError(InfrastructureError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01H01DiagnosticsError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01H01DiagnosticsError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08B01H01DiagnosticsError(f"{name} must be non-empty text")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08B01H01DiagnosticsError(f"{name} must be bool")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise Vt08B01H01DiagnosticsError(f"{name} must be int")
    return value


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08B01H01DiagnosticsError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08B01H01DiagnosticsError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08B01H01DiagnosticsError(f"{name} must be Decimal text") from error
    if not parsed.is_finite():
        raise Vt08B01H01DiagnosticsError(f"{name} must be finite Decimal")
    return parsed


def _positive_decimal(value: object, *, name: str) -> Decimal:
    parsed = _decimal(value, name=name)
    if parsed <= 0:
        raise Vt08B01H01DiagnosticsError(f"{name} must be positive")
    return parsed


def _format(value: Decimal) -> str:
    return format(value, "f")


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise Vt08B01H01DiagnosticsError("cannot summarize an empty sample")
    return sum(values, Decimal(0)) / Decimal(len(values))


def _median(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise Vt08B01H01DiagnosticsError("cannot summarize an empty sample")
    ordered = tuple(sorted(values))
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def _cliffs_delta(
    winners: tuple[Decimal, ...],
    stopped: tuple[Decimal, ...],
) -> Decimal:
    if not winners or not stopped:
        raise Vt08B01H01DiagnosticsError("Cliff's delta requires both outcome groups")
    greater = 0
    lower = 0
    for winner in winners:
        for stopped_value in stopped:
            greater += winner > stopped_value
            lower += winner < stopped_value
    return Decimal(greater - lower) / Decimal(len(winners) * len(stopped))


def _load_backtest(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08B01H01DiagnosticsError(f"cannot read {path}") from error
    payload = _object(decoded, name="backtest")
    if _text(payload.get("schema"), name="schema") != _BACKTEST_SCHEMA:
        raise Vt08B01H01DiagnosticsError("unexpected backtest schema")
    if not _boolean(payload.get("read_only"), name="read_only"):
        raise Vt08B01H01DiagnosticsError("backtest must be read-only")
    if not _boolean(payload.get("research_only"), name="research_only"):
        raise Vt08B01H01DiagnosticsError("backtest must be research-only")
    if (
        _text(payload.get("methodology_fingerprint"), name="methodology_fingerprint")
        != methodology_fingerprint()
    ):
        raise Vt08B01H01DiagnosticsError("methodology fingerprint drifted")
    return payload


def _confirmation_bar(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    confirmed_at: datetime,
) -> Vt08B01Bar:
    opened_at = confirmed_at.astimezone(UTC) - timedelta(minutes=15)
    bar = bars_by_open.get(opened_at)
    if bar is None or bar.closed_at.astimezone(UTC) != confirmed_at.astimezone(UTC):
        raise Vt08B01H01DiagnosticsError("CISD confirmation bar is unavailable")
    return bar


def _normalized(value: Decimal, denominator: Decimal, *, name: str) -> Decimal:
    if denominator <= 0:
        raise Vt08B01H01DiagnosticsError("prior H4 range must be positive")
    result = value / denominator
    if not result.is_finite():
        raise Vt08B01H01DiagnosticsError(f"{name} normalization is non-finite")
    return result


def _record(
    *,
    symbol: str,
    bars_by_open: dict[datetime, Vt08B01Bar],
    raw_trade: object,
) -> dict[str, object]:
    trade = _object(raw_trade, name="trade")
    signal_at = _timestamp(trade.get("signal_at"), name="signal_at")
    evaluation = evaluate_b01_at_entry_indexed(
        symbol=symbol,
        bars_by_open=bars_by_open,
        decision_at=signal_at,
    )
    candidate = evaluation.candidate
    if candidate is None:
        raise Vt08B01H01DiagnosticsError(
            "frozen executed trade no longer revalidates as an R3.8 candidate"
        )

    side = _text(trade.get("side"), name="side")
    if side != candidate.side.value:
        raise Vt08B01H01DiagnosticsError("trade side contradicts reconstructed candidate")
    entry = _positive_decimal(trade.get("entry"), name="entry")
    stop = _positive_decimal(trade.get("stop"), name="stop")
    target = _positive_decimal(trade.get("target"), name="target")
    if entry != candidate.setup.entry_price:
        raise Vt08B01H01DiagnosticsError("trade entry contradicts candidate")
    if stop != candidate.setup.invalidation_price:
        raise Vt08B01H01DiagnosticsError("trade stop contradicts protected swing")
    if target != candidate.setup.take_profit_price:
        raise Vt08B01H01DiagnosticsError("trade target contradicts candidate")

    reference_range = candidate.reference_h4.high - candidate.reference_h4.low
    if reference_range <= 0:
        raise Vt08B01H01DiagnosticsError("reference H4 range must be positive")
    protected = candidate.protected_swing
    confirmation = _confirmation_bar(
        bars_by_open,
        confirmed_at=protected.confirmed_at,
    )
    risk = abs(entry - stop)

    if candidate.side is DemoTradingSetupSide.LONG:
        important_level = candidate.reference_h4.low
        important_level_provenance = "prior-h4-low"
        c2_class = "c2-low-sweep-close-back-inside"
        sweep_depth = candidate.reference_h4.low - candidate.candle2.low
        protected_depth = candidate.reference_h4.low - protected.price
        cisd_displacement = confirmation.close - protected.cisd_level
        important_to_entry = entry - important_level
        cisd_to_entry = entry - protected.cisd_level
    else:
        important_level = candidate.reference_h4.high
        important_level_provenance = "prior-h4-high"
        c2_class = "c2-high-sweep-close-back-inside"
        sweep_depth = candidate.candle2.high - candidate.reference_h4.high
        protected_depth = protected.price - candidate.reference_h4.high
        cisd_displacement = protected.cisd_level - confirmation.close
        important_to_entry = important_level - entry
        cisd_to_entry = protected.cisd_level - entry

    if sweep_depth <= 0 or protected_depth <= 0 or cisd_displacement <= 0:
        raise Vt08B01H01DiagnosticsError(
            "reconstructed source geometry contradicts executed B01 contract"
        )

    confirmation_latency = int(
        (protected.confirmed_at - protected.opposing_series_opened_at).total_seconds()
        // 60
    )
    cisd_to_entry_minutes = int(
        (candidate.decision_at - protected.confirmed_at).total_seconds() // 60
    )
    if confirmation_latency <= 0 or cisd_to_entry_minutes < 0:
        raise Vt08B01H01DiagnosticsError("CISD timing is causally invalid")

    return_rate = _decimal(trade.get("return_rate"), name="return_rate")
    exit_reason = _text(trade.get("exit_reason"), name="exit_reason")
    if exit_reason not in {"stop", "target", "h4_containment_exit"}:
        raise Vt08B01H01DiagnosticsError("unexpected frozen exit reason")

    return {
        "symbol": symbol,
        "signal_at": signal_at.isoformat(),
        "pre_entry": {
            "side": candidate.side.value,
            "anchor_hour_ny": candidate.entry_anchor_hour,
            "protected_swing_provenance": (
                "exactly-one-candle2-important-level-interaction-plus-causal-cisd"
            ),
            "protected_swing_candidate_count": 1,
            "protected_swing_price": _format(protected.price),
            "important_level": _format(important_level),
            "important_level_provenance": important_level_provenance,
            "c2_class": c2_class,
            "opposing_series_opened_at": protected.opposing_series_opened_at.astimezone(
                UTC
            ).isoformat(),
            "cisd_level": _format(protected.cisd_level),
            "cisd_confirmed_at": protected.confirmed_at.astimezone(UTC).isoformat(),
            "risk_norm_prior_h4": _format(
                _normalized(risk, reference_range, name="risk")
            ),
            "sweep_depth_norm_prior_h4": _format(
                _normalized(sweep_depth, reference_range, name="sweep depth")
            ),
            "protected_swing_depth_norm_prior_h4": _format(
                _normalized(protected_depth, reference_range, name="PS depth")
            ),
            "cisd_confirmation_latency_minutes": confirmation_latency,
            "cisd_to_entry_minutes": cisd_to_entry_minutes,
            "cisd_displacement_norm_prior_h4": _format(
                _normalized(cisd_displacement, reference_range, name="CISD displacement")
            ),
            "important_level_to_entry_norm_prior_h4": _format(
                _normalized(important_to_entry, reference_range, name="important to entry")
            ),
            "cisd_level_to_entry_norm_prior_h4": _format(
                _normalized(cisd_to_entry, reference_range, name="CISD to entry")
            ),
        },
        "outcome": {
            "exit_reason": exit_reason,
            "return_rate": _format(return_rate),
            "winner": return_rate > 0,
            "stopped": exit_reason == "stop",
        },
    }


def _feature_value(record: dict[str, object], feature: str) -> Decimal:
    pre_entry = _object(record.get("pre_entry"), name="pre_entry")
    value = pre_entry.get(feature)
    if type(value) is int:
        return Decimal(value)
    return _decimal(value, name=feature)


def _comparison(records: tuple[dict[str, object], ...]) -> dict[str, object]:
    result: dict[str, object] = {}
    for feature in _FEATURES:
        winners = tuple(
            _feature_value(record, feature)
            for record in records
            if _boolean(
                _object(record.get("outcome"), name="outcome").get("winner"),
                name="winner",
            )
        )
        stopped = tuple(
            _feature_value(record, feature)
            for record in records
            if _boolean(
                _object(record.get("outcome"), name="outcome").get("stopped"),
                name="stopped",
            )
        )
        if not winners or not stopped:
            raise Vt08B01H01DiagnosticsError("winner/stopped comparison is incomplete")

        per_market: dict[str, str] = {}
        for symbol in AUTHORIZED_FOREX_MARKETS:
            market_winners = tuple(
                _feature_value(record, feature)
                for record in records
                if record.get("symbol") == symbol
                and _boolean(
                    _object(record.get("outcome"), name="outcome").get("winner"),
                    name="winner",
                )
            )
            market_stopped = tuple(
                _feature_value(record, feature)
                for record in records
                if record.get("symbol") == symbol
                and _boolean(
                    _object(record.get("outcome"), name="outcome").get("stopped"),
                    name="stopped",
                )
            )
            if not market_winners or not market_stopped:
                raise Vt08B01H01DiagnosticsError(
                    f"{symbol} lacks both H01 outcome groups"
                )
            per_market[symbol] = _format(
                _cliffs_delta(market_winners, market_stopped)
            )

        result[feature] = {
            "winner_count": len(winners),
            "stopped_count": len(stopped),
            "winner_mean": _format(_mean(winners)),
            "stopped_mean": _format(_mean(stopped)),
            "winner_median": _format(_median(winners)),
            "stopped_median": _format(_median(stopped)),
            "cliffs_delta_winner_vs_stopped": _format(
                _cliffs_delta(winners, stopped)
            ),
            "per_market_cliffs_delta_winner_vs_stopped": per_market,
            "threshold_selected": False,
            "causal_rule_authorized": False,
        }
    return result


def compile_vt08_b01_h01_diagnostics(root: Path) -> dict[str, object]:
    backtests = tuple(sorted(root.rglob("b01-backtest.json")))
    if len(backtests) != len(AUTHORIZED_FOREX_MARKETS):
        raise Vt08B01H01DiagnosticsError(
            "H01 diagnostics require exactly seven frozen market artifacts"
        )

    records: list[dict[str, object]] = []
    seen_symbols: set[str] = set()
    reported_sample = 0
    for backtest_path in backtests:
        evidence_path = backtest_path.with_name("market-evidence.json")
        if not evidence_path.is_file():
            raise Vt08B01H01DiagnosticsError(
                f"missing market evidence beside {backtest_path}"
            )
        _, symbol, _, _, bars = _load(evidence_path)
        if symbol in seen_symbols:
            raise Vt08B01H01DiagnosticsError("duplicate frozen market artifact")
        seen_symbols.add(symbol)
        bars_by_open = {bar.opened_at.astimezone(UTC): bar for bar in bars}
        if len(bars_by_open) != len(bars):
            raise Vt08B01H01DiagnosticsError("M15 evidence contains duplicate bars")

        backtest = _load_backtest(backtest_path)
        if _text(backtest.get("symbol"), name="symbol") != symbol:
            raise Vt08B01H01DiagnosticsError("evidence/backtest symbol mismatch")
        trades = _array(backtest.get("trades"), name="trades")
        if _integer(backtest.get("sample_size"), name="sample_size") != len(trades):
            raise Vt08B01H01DiagnosticsError("backtest sample count is inconsistent")
        reported_sample += len(trades)
        records.extend(
            _record(symbol=symbol, bars_by_open=bars_by_open, raw_trade=trade)
            for trade in trades
        )

    if seen_symbols != set(AUTHORIZED_FOREX_MARKETS):
        raise Vt08B01H01DiagnosticsError("frozen seven-market set is incomplete")
    if len(records) != reported_sample:
        raise Vt08B01H01DiagnosticsError("not every frozen trade was revalidated")

    ordered = tuple(sorted(records, key=lambda item: (str(item["symbol"]), str(item["signal_at"]))))
    winner_count = sum(
        _boolean(_object(item["outcome"], name="outcome").get("winner"), name="winner")
        for item in ordered
    )
    stopped_count = sum(
        _boolean(_object(item["outcome"], name="outcome").get("stopped"), name="stopped")
        for item in ordered
    )
    non_stop_non_winner = len(ordered) - len(
        {
            (str(item["symbol"]), str(item["signal_at"]))
            for item in ordered
            if _boolean(
                _object(item["outcome"], name="outcome").get("winner"), name="winner"
            )
            or _boolean(
                _object(item["outcome"], name="outcome").get("stopped"), name="stopped"
            )
        }
    )

    market_counts: dict[str, int] = defaultdict(int)
    for item in ordered:
        market_counts[str(item["symbol"])] += 1

    return {
        "schema": _SCHEMA,
        "trader_code": "vt-08",
        "hypothesis_id": "VT08-R3.8-FF-H01",
        "baseline_run_id": _BASELINE_RUN_ID,
        "forbidden_reuse": _FORBIDDEN_REUSE,
        "methodology_fingerprint": methodology_fingerprint(),
        "research_only": True,
        "current_evidence_consumed": True,
        "independent_validation_reuse_prohibited": True,
        "source_adjudication_required": True,
        "methodology_mutation_authorized": False,
        "selection_authorized": False,
        "diagnostic_scope": "pre-entry-winners-vs-protected-swing-stop-exits",
        "post_entry_path_features_used_for_selection": False,
        "sample_size": len(ordered),
        "revalidated_trade_count": len(ordered),
        "winner_count": winner_count,
        "stopped_count": stopped_count,
        "non_stop_non_winner_count": non_stop_non_winner,
        "market_sample_counts": dict(sorted(market_counts.items())),
        "feature_comparison": _comparison(ordered),
        "records": list(ordered),
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: vt08_b01_h01_diagnostics_r3_8 <retained-artifact-root>")
    payload = compile_vt08_b01_h01_diagnostics(Path(sys.argv[1]))
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
