"""Pre-registered fresh-holdout, stress, and Monte-Carlo validation for VT-08 Index V2."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterable, Sequence
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_v2_fresh_validation.v1"
HOLDOUT_ID = "VT08_INDEX_V2_FRESH_2023_09_15_TO_2024_08_13"
HOLDOUT_START = "2023-09-15"
HOLDOUT_END_EXCLUSIVE = "2024-08-13"
CANDIDATE_ID = "VT08_INDEX_V2_QORE_CANDIDATE_001"
SELECTION_ID = "V-32e621c9282c"
MARKETS = ("NAS100", "SP500", "US30")
ANCHORS = (2, 6, 10)
MIN_SAMPLE = 90
MIN_MARKET_SAMPLE = 20
MIN_ANCHOR_SAMPLE = 15
MIN_PROFIT_FACTOR = Decimal("1.05")
MAX_DRAWDOWN_R = Decimal("12")
MIN_POSITIVE_QUARTILES = 3
STRESS_FRICTION_R = Decimal("0.05")
STRESS_MAX_DRAWDOWN_R = Decimal("15")
MONTE_CARLO_PATHS = 10_000
MONTE_CARLO_BLOCK_LENGTH = 5
MONTE_CARLO_SEED = 20260913
MONTE_CARLO_ALGORITHM = "sha256-domain-separated-moving-block-bootstrap-v1"
MONTE_CARLO_MIN_POSITIVE_TERMINAL_PROBABILITY = Decimal("0.70")
MONTE_CARLO_MAX_P95_DRAWDOWN_R = Decimal("20")
_BOOTSTRAP_DOMAIN = b"qore-vt08-index-v2-moving-block-bootstrap-v1"


class Vt08IndexV2FreshValidationError(InfrastructureError):
    __slots__ = ()


def _object(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08IndexV2FreshValidationError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08IndexV2FreshValidationError(f"{field} must be an array")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08IndexV2FreshValidationError(f"{field} must be non-empty text")
    return value


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise Vt08IndexV2FreshValidationError(f"{field} must be int")
    return value


def _decimal(value: object, field: str) -> Decimal:
    if type(value) is not str:
        raise Vt08IndexV2FreshValidationError(f"{field} must be decimal text")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise Vt08IndexV2FreshValidationError(f"{field} must be decimal text") from error
    if not result.is_finite():
        raise Vt08IndexV2FreshValidationError(f"{field} must be finite")
    return result


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal()) / len(values) if values else Decimal()


def _max_drawdown(values: Iterable[Decimal]) -> Decimal:
    equity = Decimal()
    peak = Decimal()
    worst = Decimal()
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _metrics(values: Sequence[Decimal]) -> dict[str, object]:
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    gross_win = sum(wins, Decimal())
    gross_loss = -sum(losses, Decimal())
    total = sum(values, Decimal())
    return {
        "sample": len(values),
        "wins": len(wins),
        "losses": len(losses),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(_mean(values)),
        "profit_factor": str(gross_win / gross_loss) if gross_loss else None,
        "max_drawdown_r": str(_max_drawdown(values)),
    }


def _trade_rows(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    rows = tuple(
        _object(item, "trade") for item in _array(payload.get("trades"), "trades")
    )
    if any(row.get("symbol") not in MARKETS for row in rows):
        raise Vt08IndexV2FreshValidationError("holdout contains an unauthorized market")
    if any(row.get("anchor_hour_new_york") not in ANCHORS for row in rows):
        raise Vt08IndexV2FreshValidationError("holdout contains an unauthorized anchor")
    return rows


def _structural_checks(
    rows: tuple[dict[str, object], ...],
) -> tuple[dict[str, bool], dict[str, object]]:
    values = tuple(_decimal(row.get("r_multiple"), "r_multiple") for row in rows)
    market_counts = Counter(_text(row.get("symbol"), "symbol") for row in rows)
    anchor_counts = Counter(
        _integer(row.get("anchor_hour_new_york"), "anchor_hour_new_york")
        for row in rows
    )
    n = len(rows)
    quartiles = tuple(values[(n * i) // 4 : (n * (i + 1)) // 4] for i in range(4))
    quartile_means = tuple(_mean(part) for part in quartiles)
    second_half = _mean(values[n // 2 :])
    loo_market = {
        market: _mean(
            tuple(
                _decimal(row.get("r_multiple"), "r_multiple")
                for row in rows
                if row["symbol"] != market
            )
        )
        for market in MARKETS
    }
    loo_anchor = {
        str(anchor): _mean(
            tuple(
                _decimal(row.get("r_multiple"), "r_multiple")
                for row in rows
                if row["anchor_hour_new_york"] != anchor
            )
        )
        for anchor in ANCHORS
    }
    metrics = _metrics(values)
    pf_raw = metrics["profit_factor"]
    profit_factor = (
        Decimal(str(pf_raw)) if pf_raw is not None else Decimal("Infinity")
    )
    positive_quartiles = sum(value > 0 for value in quartile_means)
    checks = {
        "sample": n >= MIN_SAMPLE,
        "market_samples": all(
            market_counts[market] >= MIN_MARKET_SAMPLE for market in MARKETS
        ),
        "anchor_samples": all(
            anchor_counts[anchor] >= MIN_ANCHOR_SAMPLE for anchor in ANCHORS
        ),
        "aggregate_mean": _mean(values) > 0,
        "profit_factor": profit_factor >= MIN_PROFIT_FACTOR,
        "second_half": second_half > 0,
        "quartiles": positive_quartiles >= MIN_POSITIVE_QUARTILES,
        "leave_one_market": all(value > 0 for value in loo_market.values()),
        "leave_one_anchor": all(value > 0 for value in loo_anchor.values()),
        "drawdown": _max_drawdown(values) <= MAX_DRAWDOWN_R,
    }
    details: dict[str, object] = {
        "metrics": metrics,
        "market_counts": {market: market_counts[market] for market in MARKETS},
        "anchor_counts": {str(anchor): anchor_counts[anchor] for anchor in ANCHORS},
        "quartile_mean_r": [str(value) for value in quartile_means],
        "positive_quartiles": positive_quartiles,
        "second_half_mean_r": str(second_half),
        "leave_one_market_out_mean_r": {
            key: str(value) for key, value in loo_market.items()
        },
        "leave_one_anchor_out_mean_r": {
            key: str(value) for key, value in loo_anchor.items()
        },
    }
    return checks, details


def _stress(values: Sequence[Decimal]) -> dict[str, object]:
    stressed = tuple(value - STRESS_FRICTION_R for value in values)
    metrics = _metrics(stressed)
    checks = {
        "mean_positive_after_0_05r_friction": _mean(stressed) > 0,
        "max_drawdown_at_most_15r": (
            _max_drawdown(stressed) <= STRESS_MAX_DRAWDOWN_R
        ),
    }
    return {
        "friction_r_per_trade": str(STRESS_FRICTION_R),
        "metrics": metrics,
        "checks": checks,
        "pass": all(checks.values()),
    }


def _draw_block_start(
    *,
    seed: int,
    replicate: int,
    draw: int,
    start_count: int,
) -> int:
    payload = (
        _BOOTSTRAP_DOMAIN
        + b":"
        + str(seed).encode("ascii")
        + b":"
        + str(replicate).encode("ascii")
        + b":"
        + str(draw).encode("ascii")
    )
    return int.from_bytes(sha256(payload).digest(), "big") % start_count


def _bootstrap_path(
    values: Sequence[Decimal],
    *,
    seed: int,
    replicate: int,
    block_length: int,
) -> tuple[Decimal, ...]:
    if not values:
        return ()
    block = min(block_length, len(values))
    result: list[Decimal] = []
    start_count = len(values) - block + 1
    draw = 0
    while len(result) < len(values):
        start = _draw_block_start(
            seed=seed,
            replicate=replicate,
            draw=draw,
            start_count=start_count,
        )
        result.extend(values[start : start + block])
        draw += 1
    return tuple(result[: len(values)])


def _monte_carlo(values: Sequence[Decimal]) -> dict[str, object]:
    if len(values) < MONTE_CARLO_BLOCK_LENGTH:
        raise Vt08IndexV2FreshValidationError(
            "insufficient observations for block bootstrap"
        )
    stressed = tuple(value - STRESS_FRICTION_R for value in values)
    terminal_values: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for replicate in range(MONTE_CARLO_PATHS):
        path = _bootstrap_path(
            stressed,
            seed=MONTE_CARLO_SEED,
            replicate=replicate,
            block_length=MONTE_CARLO_BLOCK_LENGTH,
        )
        terminal_values.append(sum(path, Decimal()))
        drawdowns.append(_max_drawdown(path))
    positive = Decimal(sum(value > 0 for value in terminal_values)) / Decimal(
        MONTE_CARLO_PATHS
    )
    ordered_drawdowns = sorted(drawdowns)
    index = max(0, (95 * MONTE_CARLO_PATHS + 99) // 100 - 1)
    p95_drawdown = ordered_drawdowns[index]
    checks = {
        "positive_terminal_probability": (
            positive >= MONTE_CARLO_MIN_POSITIVE_TERMINAL_PROBABILITY
        ),
        "p95_drawdown": p95_drawdown <= MONTE_CARLO_MAX_P95_DRAWDOWN_R,
    }
    return {
        "algorithm": MONTE_CARLO_ALGORITHM,
        "paths": MONTE_CARLO_PATHS,
        "block_length": MONTE_CARLO_BLOCK_LENGTH,
        "seed": MONTE_CARLO_SEED,
        "input_friction_r_per_trade": str(STRESS_FRICTION_R),
        "positive_terminal_probability": str(positive),
        "p95_max_drawdown_r": str(p95_drawdown),
        "checks": checks,
        "pass": all(checks.values()),
    }


def validate_fresh_holdout(payload: dict[str, object]) -> dict[str, object]:
    if payload.get("schema") != "qore.trader_lab.vt08_index_v2_candidate.v1":
        raise Vt08IndexV2FreshValidationError("unexpected candidate report schema")
    if payload.get("candidate_id") != CANDIDATE_ID:
        raise Vt08IndexV2FreshValidationError("candidate identity mismatch")
    if payload.get("development_selection_id") != SELECTION_ID:
        raise Vt08IndexV2FreshValidationError("development selection mismatch")
    variant = _object(payload.get("variant"), "variant")
    if variant.get("variant_id") != SELECTION_ID:
        raise Vt08IndexV2FreshValidationError("variant identity mismatch")
    partition = _object(payload.get("partition"), "partition")
    if partition != {
        "start_date": HOLDOUT_START,
        "end_date_exclusive": HOLDOUT_END_EXCLUSIVE,
    }:
        raise Vt08IndexV2FreshValidationError("fresh holdout partition mismatch")
    provenance = _object(payload.get("provenance"), "provenance")
    if set(provenance) != set(MARKETS):
        raise Vt08IndexV2FreshValidationError(
            "fresh holdout market provenance mismatch"
        )
    account_fingerprints = {
        _text(
            _object(provenance[market], f"{market} provenance").get(
                "account_fingerprint"
            ),
            f"{market} account_fingerprint",
        )
        for market in MARKETS
    }
    if len(account_fingerprints) != 1:
        raise Vt08IndexV2FreshValidationError(
            "fresh holdout must use one DEMO account"
        )

    rows = _trade_rows(payload)
    values = tuple(_decimal(row.get("r_multiple"), "r_multiple") for row in rows)
    structural_checks, structural = _structural_checks(rows)
    stress = _stress(values)
    monte_carlo = _monte_carlo(values)
    structural_pass = all(structural_checks.values())
    robustness_pass = bool(stress["pass"]) and bool(monte_carlo["pass"])
    final_pass = structural_pass and robustness_pass
    return {
        "schema": SCHEMA,
        "holdout_id": HOLDOUT_ID,
        "candidate_id": CANDIDATE_ID,
        "development_selection_id": SELECTION_ID,
        "partition": partition,
        "fresh_holdout_opened": True,
        "pre_registered_thresholds": {
            "min_sample": MIN_SAMPLE,
            "min_market_sample": MIN_MARKET_SAMPLE,
            "min_anchor_sample": MIN_ANCHOR_SAMPLE,
            "min_profit_factor": str(MIN_PROFIT_FACTOR),
            "max_drawdown_r": str(MAX_DRAWDOWN_R),
            "min_positive_quartiles": MIN_POSITIVE_QUARTILES,
            "stress_friction_r_per_trade": str(STRESS_FRICTION_R),
            "stress_max_drawdown_r": str(STRESS_MAX_DRAWDOWN_R),
            "monte_carlo_paths": MONTE_CARLO_PATHS,
            "monte_carlo_block_length": MONTE_CARLO_BLOCK_LENGTH,
            "monte_carlo_seed": MONTE_CARLO_SEED,
            "monte_carlo_algorithm": MONTE_CARLO_ALGORITHM,
            "monte_carlo_min_positive_terminal_probability": str(
                MONTE_CARLO_MIN_POSITIVE_TERMINAL_PROBABILITY
            ),
            "monte_carlo_max_p95_drawdown_r": str(
                MONTE_CARLO_MAX_P95_DRAWDOWN_R
            ),
        },
        "structural": {
            **structural,
            "checks": structural_checks,
            "pass": structural_pass,
        },
        "stress": stress,
        "monte_carlo": monte_carlo,
        "fresh_holdout_pass": final_pass,
        "governance": {
            "methodology_mutated_after_holdout": False,
            "cibo_used_for_signal_selection": False,
            "risk_used_for_signal_selection": False,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw: object = json.loads(args.candidate_report.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexV2FreshValidationError(
            "cannot read fresh candidate report"
        ) from error
    payload = _object(raw, "candidate report")
    report = validate_fresh_holdout(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "holdout_id": HOLDOUT_ID,
                "pass": report["fresh_holdout_pass"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
