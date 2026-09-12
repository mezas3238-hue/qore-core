"""Failure forensics for the frozen VT-08 R3.8 B01 research baseline.

Consumes only retained R3.8 Trader Lab artifacts. It does not modify the Trader,
select markets for promotion, grant DEMO eligibility, or convert observed
correlations into methodology rules. The retained 760-day campaign is already
consumed research evidence and may only generate falsifiable hypotheses.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_b01_failure_forensics.r3.8.v1"
_SOURCE_SCHEMA = "qore.trader_lab.vt08_b01_diagnostics.r3.8.v1"
_EXPECTED_SYMBOLS = frozenset(
    {"AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD", "USDJPY"}
)
_FROZEN_RUN_ID = 34693803930
_FROZEN_HEAD = "a5b9b5a80a55314f74cc1e3ef632803a91972c3b"
_NY = ZoneInfo("America/New_York")


class Vt08B01FailureForensicsError(InfrastructureError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01FailureForensicsError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01FailureForensicsError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08B01FailureForensicsError(f"{name} must be non-empty text")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08B01FailureForensicsError(f"{name} must be bool")
    return value


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08B01FailureForensicsError(f"{name} must be Decimal text") from error
    if not result.is_finite():
        raise Vt08B01FailureForensicsError(f"{name} must be finite")
    return result


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        result = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08B01FailureForensicsError(f"{name} must be RFC3339") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise Vt08B01FailureForensicsError(f"{name} must be timezone-aware")
    return result


def _load(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08B01FailureForensicsError(f"cannot read {path}") from error
    payload = _object(decoded, name="Trader Lab report")
    if _text(payload.get("schema"), name="schema") != _SOURCE_SCHEMA:
        raise Vt08B01FailureForensicsError("unexpected Trader Lab report schema")
    if not _boolean(payload.get("research_only"), name="research_only"):
        raise Vt08B01FailureForensicsError("forensics accepts research-only evidence")
    if not _boolean(payload.get("read_only"), name="read_only"):
        raise Vt08B01FailureForensicsError("forensics accepts read-only evidence")
    if _text(payload.get("trader_code"), name="trader_code") != "vt-08":
        raise Vt08B01FailureForensicsError("report must belong to VT-08")
    return payload


def _metrics(values: list[Decimal]) -> dict[str, object]:
    sample = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = sample - wins - losses
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    mean = sum(values, Decimal(0)) / Decimal(sample) if sample else Decimal(0)
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
    return {
        "sample_size": sample,
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "win_rate": format(Decimal(wins) / Decimal(sample), "f") if sample else "0",
        "mean_return": format(mean, "f"),
        "gross_profit": format(gross_profit, "f"),
        "gross_loss": format(gross_loss, "f"),
        "profit_factor": format(profit_factor, "f") if profit_factor is not None else None,
    }


def _segmented_metrics(
    grouped: dict[str, list[Decimal]],
) -> dict[str, dict[str, object]]:
    return {key: _metrics(grouped[key]) for key in sorted(grouped)}


def run_vt08_b01_failure_forensics(paths: list[Path]) -> dict[str, object]:
    reports = [_load(path) for path in paths]
    if len(reports) != 7:
        raise Vt08B01FailureForensicsError("exactly seven market reports are required")

    symbols = {_text(item.get("symbol"), name="symbol") for item in reports}
    if symbols != _EXPECTED_SYMBOLS:
        raise Vt08B01FailureForensicsError("reports must cover the exact frozen seven markets")

    methodology_fingerprints = {
        _text(item.get("methodology_fingerprint"), name="methodology_fingerprint")
        for item in reports
    }
    if len(methodology_fingerprints) != 1:
        raise Vt08B01FailureForensicsError("methodology fingerprints must match")

    records: list[tuple[str, dict[str, object]]] = []
    market_means: dict[str, Decimal] = {}
    market_oos: dict[str, bool] = {}
    market_stress: dict[str, bool] = {}
    exit_counts: Counter[str] = Counter()
    for report in reports:
        symbol = _text(report.get("symbol"), name="symbol")
        full_period = _object(report.get("full_period"), name="full_period")
        walk_forward = _object(report.get("walk_forward"), name="walk_forward")
        market_means[symbol] = _decimal(full_period.get("mean_return"), name="mean_return")
        market_oos[symbol] = _boolean(walk_forward.get("oos_pass"), name="oos_pass")
        market_stress[symbol] = _boolean(walk_forward.get("stress_pass"), name="stress_pass")
        for raw in _array(report.get("trade_records"), name="trade_records"):
            record = _object(raw, name="trade_record")
            records.append((symbol, record))
            exit_counts[_text(record.get("exit_reason"), name="exit_reason")] += 1

    by_symbol: dict[str, list[Decimal]] = defaultdict(list)
    by_hour: dict[str, list[Decimal]] = defaultdict(list)
    by_weekday: dict[str, list[Decimal]] = defaultdict(list)
    by_side: dict[str, list[Decimal]] = defaultdict(list)
    by_exit: dict[str, list[Decimal]] = defaultdict(list)
    pooled: list[Decimal] = []
    for symbol, record in records:
        value = _decimal(record.get("return_rate"), name="return_rate")
        signal_at = _timestamp(record.get("signal_at"), name="signal_at").astimezone(_NY)
        side = _text(record.get("side"), name="side")
        exit_reason = _text(record.get("exit_reason"), name="exit_reason")
        pooled.append(value)
        by_symbol[symbol].append(value)
        by_hour[str(signal_at.hour)].append(value)
        by_weekday[signal_at.strftime("%A")].append(value)
        by_side[side].append(value)
        by_exit[exit_reason].append(value)

    pooled_metrics = _metrics(pooled)
    market_positive = sorted(symbol for symbol, value in market_means.items() if value > 0)
    market_negative = sorted(symbol for symbol, value in market_means.items() if value < 0)
    oos_pass = sorted(symbol for symbol, value in market_oos.items() if value)
    stress_pass = sorted(symbol for symbol, value in market_stress.items() if value)

    hypotheses: list[dict[str, object]] = []
    if exit_counts.get("stop", 0) * 2 > len(records):
        hypotheses.append(
            {
                "id": "VT08-R3.8-FF-H01",
                "family": "entry-and-protected-swing-quality",
                "status": "research_hypothesis_only",
                "evidence": "more than half of frozen trades terminate at the protected-swing stop",
                "falsification": "a pre-registered source-supported structural discriminator must reduce stop concentration on a previously unseen holdout without degrading OOS/stress policy",
                "forbidden_reuse": "run-34693803930",
            }
        )
    if market_positive and market_negative:
        hypotheses.append(
            {
                "id": "VT08-R3.8-FF-H02",
                "family": "instrument-dependency",
                "status": "research_hypothesis_only",
                "evidence": {"positive_mean_markets": market_positive, "negative_mean_markets": market_negative},
                "falsification": "instrument separation must reproduce on a previously unseen holdout; selecting winners from the frozen campaign is prohibited",
                "forbidden_reuse": "run-34693803930",
            }
        )
    hour_metrics = _segmented_metrics(by_hour)
    if "5" in hour_metrics:
        hypotheses.append(
            {
                "id": "VT08-R3.8-FF-H03",
                "family": "source-anchor-regime-interaction",
                "status": "research_hypothesis_only",
                "evidence": {"05_ny": hour_metrics["5"]},
                "falsification": "any anchor-specific hypothesis must be source-justified before change and validated on a fresh holdout",
                "forbidden_reuse": "run-34693803930",
            }
        )
    if exit_counts.get("h4_containment_exit", 0):
        hypotheses.append(
            {
                "id": "VT08-R3.8-FF-H04",
                "family": "operational-containment-effect",
                "status": "research_hypothesis_only",
                "evidence": {"h4_containment_exit_count": exit_counts["h4_containment_exit"]},
                "falsification": "compare pre-registered source-supported lifecycle alternatives on fresh evidence; do not choose the better policy from this consumed dataset",
                "forbidden_reuse": "run-34693803930",
            }
        )

    return {
        "schema": _SCHEMA,
        "trader_code": "vt-08",
        "bundle_id": "B01_SOURCE_FAITHFUL_HISTORICAL_REPLAY_V1",
        "baseline_pr": 521,
        "baseline_head": _FROZEN_HEAD,
        "baseline_run_id": _FROZEN_RUN_ID,
        "methodology_fingerprint": next(iter(methodology_fingerprints)),
        "research_only": True,
        "baseline_frozen": True,
        "current_evidence_consumed": True,
        "independent_validation_reuse_prohibited": True,
        "pooled": pooled_metrics,
        "exit_reason_counts": dict(sorted(exit_counts.items())),
        "by_symbol": _segmented_metrics(by_symbol),
        "by_signal_hour_ny": hour_metrics,
        "by_signal_weekday_ny": _segmented_metrics(by_weekday),
        "by_side": _segmented_metrics(by_side),
        "by_exit_reason": _segmented_metrics(by_exit),
        "oos_pass_markets": oos_pass,
        "stress_pass_markets": stress_pass,
        "failure_classifications": [
            "entry_or_geometry_quality_candidate",
            "instrument_dependency_candidate",
            "oos_generalization_failure",
            "stress_fragility",
        ],
        "hypothesis_register": hypotheses,
        "next_required_evidence": "previously-unseen holdout after source adjudication and pre-registration",
        "demo_eligible": False,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        print("usage: vt08_b01_failure_forensics_r3_8 <trader-lab.json>...", file=sys.stderr)
        return 2
    try:
        payload = run_vt08_b01_failure_forensics([Path(item) for item in arguments])
    except Vt08B01FailureForensicsError as error:
        print(f"VT-08 failure forensics failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
