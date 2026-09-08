"""Cross-instrument aggregation for deep first-cohort characterization."""

from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_characterization import (
    FirstCohortCharacterizationError,
)

_SCHEMA = "qore.trader_lab.first_cohort_characterization_aggregate.v1"
_INPUT_SCHEMA = "qore.trader_lab.first_cohort_characterization.v1"
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_REQUIRED_INSTRUMENTS = 6


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortCharacterizationError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise FirstCohortCharacterizationError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortCharacterizationError(f"{field_name} must be a non-empty string")
    return value


def _strict_int(value: object, *, field_name: str) -> int:
    if type(value) is not int:
        raise FirstCohortCharacterizationError(f"{field_name} must be an int")
    return value


def _decimal(value: object, *, field_name: str) -> Decimal:
    raw = _text(value, field_name=field_name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise FirstCohortCharacterizationError(f"{field_name} must be decimal") from error
    if not parsed.is_finite():
        raise FirstCohortCharacterizationError(f"{field_name} must be finite")
    return parsed


def _read(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortCharacterizationError("cannot read characterization evidence") from error
    payload = _object(decoded, field_name="characterization evidence")
    if _text(payload.get("schema"), field_name="schema") != _INPUT_SCHEMA:
        raise FirstCohortCharacterizationError("unexpected characterization schema")
    if _text(payload.get("environment"), field_name="environment") != "demo":
        raise FirstCohortCharacterizationError("characterization evidence must be DEMO")
    return payload


def _counter(value: object, *, field_name: str) -> Counter[str]:
    payload = _object(value, field_name=field_name)
    result: Counter[str] = Counter()
    for key, item in payload.items():
        result[key] = _strict_int(item, field_name=f"{field_name}.{key}")
    return result


def _combine_outcomes(rows: list[dict[str, object]]) -> dict[str, object]:
    total = 0
    total_sum = Decimal(0)
    total_sum_squares = Decimal(0)
    total_wins = Decimal(0)
    for row in rows:
        count = _strict_int(row.get("count"), field_name="outcome count")
        mean = _decimal(row.get("mean"), field_name="outcome mean")
        variance = _decimal(
            row.get("population_variance"), field_name="outcome variance"
        )
        win_rate = _decimal(row.get("win_rate"), field_name="outcome win rate")
        total += count
        total_sum += Decimal(count) * mean
        total_sum_squares += Decimal(count) * (variance + mean * mean)
        total_wins += Decimal(count) * win_rate
    if total == 0:
        return {
            "count": 0,
            "mean": "0",
            "population_variance": "0",
            "win_rate": "0",
        }
    size = Decimal(total)
    mean = total_sum / size
    variance = max(Decimal(0), total_sum_squares / size - mean * mean)
    return {
        "count": total,
        "mean": format(mean, "f"),
        "population_variance": format(variance, "f"),
        "win_rate": format(total_wins / size, "f"),
    }


def _combine_buckets(rows: list[dict[str, object]]) -> dict[str, object]:
    setup_count = sum(
        _strict_int(row.get("setup_count"), field_name="bucket setup_count") for row in rows
    )
    filled_count = sum(
        _strict_int(row.get("filled_count"), field_name="bucket filled_count") for row in rows
    )
    outcomes = [
        _object(row.get("outcomes"), field_name="bucket outcomes") for row in rows
    ]
    return {
        "setup_count": setup_count,
        "filled_count": filled_count,
        "unfilled_count": setup_count - filled_count,
        "fill_rate": (
            format(Decimal(filled_count) / Decimal(setup_count), "f")
            if setup_count
            else "0"
        ),
        "outcomes": _combine_outcomes(outcomes),
    }


def _aggregate_category(
    profiles: list[dict[str, object]], *, field_name: str
) -> dict[str, object]:
    categories: dict[str, list[dict[str, object]]] = {}
    for profile in profiles:
        mapping = _object(profile.get(field_name), field_name=field_name)
        for key, value in mapping.items():
            categories.setdefault(key, []).append(
                _object(value, field_name=f"{field_name}.{key}")
            )
    return {
        key: _combine_buckets(rows) for key, rows in sorted(categories.items())
    }


def _aggregate_profile(
    label: str,
    market_profiles: list[tuple[str, dict[str, object]]],
) -> dict[str, object]:
    profiles = [item[1] for item in market_profiles]
    setup_count = sum(
        _strict_int(item.get("setup_count"), field_name="setup_count") for item in profiles
    )
    filled_count = sum(
        _strict_int(item.get("filled_setup_count"), field_name="filled_setup_count")
        for item in profiles
    )
    outcomes = [
        _object(item.get("outcomes"), field_name="outcomes") for item in profiles
    ]
    abstain = Counter[str]()
    sides = Counter[str]()
    exits = Counter[str]()
    setup_reasons = Counter[str]()
    positive_markets = 0
    high_fill_markets = 0
    for _symbol, profile in market_profiles:
        abstain.update(_counter(profile.get("abstain_reason_counts"), field_name="abstains"))
        sides.update(_counter(profile.get("side_counts"), field_name="sides"))
        exits.update(_counter(profile.get("exit_reason_counts"), field_name="exits"))
        setup_reasons.update(
            _counter(profile.get("setup_reason_counts"), field_name="setup reasons")
        )
        market_outcome = _object(profile.get("outcomes"), field_name="outcomes")
        if _decimal(market_outcome.get("mean"), field_name="market mean") > 0:
            positive_markets += 1
        if _decimal(profile.get("fill_rate"), field_name="fill_rate") >= Decimal("0.50"):
            high_fill_markets += 1

    return {
        "profile": label,
        "instrument_count": len(market_profiles),
        "symbols": sorted(symbol for symbol, _profile in market_profiles),
        "setup_count": setup_count,
        "filled_setup_count": filled_count,
        "unfilled_setup_count": setup_count - filled_count,
        "fill_rate": (
            format(Decimal(filled_count) / Decimal(setup_count), "f")
            if setup_count
            else "0"
        ),
        "pooled_outcomes": _combine_outcomes(outcomes),
        "positive_expectancy_instrument_count": positive_markets,
        "fill_rate_at_least_50pct_instrument_count": high_fill_markets,
        "abstain_reason_counts": dict(sorted(abstain.items())),
        "side_counts": dict(sorted(sides.items())),
        "exit_reason_counts": dict(sorted(exits.items())),
        "setup_reason_counts": dict(sorted(setup_reasons.items())),
        "by_trend_regime": _aggregate_category(
            profiles, field_name="by_trend_regime"
        ),
        "by_volatility_regime": _aggregate_category(
            profiles, field_name="by_volatility_regime"
        ),
        "by_chronological_quartile": _aggregate_category(
            profiles, field_name="by_chronological_quartile"
        ),
    }


def run_characterization_aggregate(paths: tuple[Path, ...]) -> dict[str, object]:
    if len(paths) != _REQUIRED_INSTRUMENTS:
        raise FirstCohortCharacterizationError(
            "characterization aggregate requires exactly six instruments"
        )
    payloads = tuple(_read(path) for path in paths)
    symbols = tuple(_text(item.get("symbol"), field_name="symbol") for item in payloads)
    if len(set(symbols)) != _REQUIRED_INSTRUMENTS:
        raise FirstCohortCharacterizationError(
            "characterization aggregate requires six distinct symbols"
        )
    fingerprints = {
        _text(item.get("account_fingerprint"), field_name="account_fingerprint")
        for item in payloads
    }
    if len(fingerprints) != 1:
        raise FirstCohortCharacterizationError(
            "characterization evidence must bind one DEMO account"
        )

    by_trader: dict[str, dict[str, list[tuple[str, dict[str, object]]]]] = {
        code: {} for code in _CODES
    }
    for payload in payloads:
        symbol = _text(payload.get("symbol"), field_name="symbol")
        rows = _array(payload.get("results"), field_name="results")
        codes: list[str] = []
        for value in rows:
            row = _object(value, field_name="trader characterization")
            code = _text(row.get("trader_code"), field_name="trader_code")
            codes.append(code)
            if code not in by_trader:
                raise FirstCohortCharacterizationError("unknown characterization Trader")
            profiles = _array(row.get("profiles"), field_name="profiles")
            for profile_value in profiles:
                profile = _object(profile_value, field_name="profile")
                label = _text(profile.get("profile"), field_name="profile label")
                by_trader[code].setdefault(label, []).append((symbol, profile))
        if tuple(codes) != _CODES:
            raise FirstCohortCharacterizationError(
                "characterization cohort identity/order changed"
            )

    results: list[dict[str, object]] = []
    for code in _CODES:
        profile_groups = by_trader[code]
        default_rows = profile_groups.get("production-default", [])
        if len(default_rows) != _REQUIRED_INSTRUMENTS:
            raise FirstCohortCharacterizationError(
                "each Trader requires six production-default characterizations"
            )
        profiles = [
            _aggregate_profile(label, rows)
            for label, rows in sorted(profile_groups.items())
        ]
        results.append({"trader_code": code, "profiles": profiles})

    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "instrument_count": _REQUIRED_INSTRUMENTS,
        "symbols": sorted(symbols),
        "account_fingerprint": next(iter(fingerprints)),
        "results": results,
        "research_rule": (
            "cross-market patterns generate hypotheses only; any methodology change "
            "requires a fresh unseen holdout"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != _REQUIRED_INSTRUMENTS:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_characterization_aggregate "
            "CHARACTERIZATION_1 ... CHARACTERIZATION_6",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_characterization_aggregate(tuple(Path(item) for item in arguments))
    except FirstCohortCharacterizationError as error:
        print(f"characterization aggregate failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
