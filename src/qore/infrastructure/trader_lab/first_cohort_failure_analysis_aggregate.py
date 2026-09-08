"""Cross-instrument aggregation of first-cohort failure-analysis evidence."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_failure_analysis import (
    FirstCohortFailureAnalysisError,
)

_SCHEMA = "qore.trader_lab.first_cohort_failure_analysis_aggregate.v1"
_ANALYSIS_SCHEMA = "qore.trader_lab.first_cohort_failure_analysis.v1"
_MULTI_SCHEMA = "qore.trader_lab.first_cohort_multi_pair_walk_forward.v1"
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_REQUIRED_INSTRUMENTS = 6


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortFailureAnalysisError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise FirstCohortFailureAnalysisError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortFailureAnalysisError(f"{name} must be a non-empty string")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortFailureAnalysisError(f"{name} must be bool")
    return value


def _read(path: Path, *, name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortFailureAnalysisError(f"cannot read {name}") from error
    return _object(decoded, name=name)


def _rows_by_code(payload: dict[str, object], *, name: str) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for item in _array(payload.get("results"), name=f"{name} results"):
        row = _object(item, name=f"{name} result")
        code = _text(row.get("trader_code"), name=f"{name} trader_code")
        rows[code] = row
    if tuple(rows) != _CODES:
        raise FirstCohortFailureAnalysisError(f"{name} first-cohort identity/order changed")
    return rows


def run_failure_analysis_aggregate(
    multi_pair_path: Path,
    analysis_paths: tuple[Path, ...],
) -> dict[str, object]:
    if len(analysis_paths) != _REQUIRED_INSTRUMENTS:
        raise FirstCohortFailureAnalysisError(
            "aggregate failure analysis requires exactly six instrument analyses"
        )
    multi = _read(multi_pair_path, name="multi-pair evidence")
    if _text(multi.get("schema"), name="multi-pair schema") != _MULTI_SCHEMA:
        raise FirstCohortFailureAnalysisError("unsupported multi-pair evidence schema")
    multi_rows = _rows_by_code(multi, name="multi-pair")

    analyses: list[tuple[str, dict[str, dict[str, object]]]] = []
    fingerprints: set[str] = set()
    for path in analysis_paths:
        payload = _read(path, name="failure analysis")
        if _text(payload.get("schema"), name="failure-analysis schema") != _ANALYSIS_SCHEMA:
            raise FirstCohortFailureAnalysisError("unsupported failure-analysis schema")
        if _text(payload.get("environment"), name="environment") != "demo":
            raise FirstCohortFailureAnalysisError("failure analysis must be DEMO")
        if not _boolean(payload.get("read_only"), name="read_only"):
            raise FirstCohortFailureAnalysisError("failure analysis must be read-only")
        symbol = _text(payload.get("symbol"), name="symbol")
        fingerprints.add(_text(payload.get("account_fingerprint"), name="account fingerprint"))
        analyses.append((symbol, _rows_by_code(payload, name=f"analysis {symbol}")))
    analyses.sort(key=lambda item: item[0])
    symbols = tuple(item[0] for item in analyses)
    if len(set(symbols)) != _REQUIRED_INSTRUMENTS:
        raise FirstCohortFailureAnalysisError("aggregate requires six distinct instruments")
    if len(fingerprints) != 1:
        raise FirstCohortFailureAnalysisError("all analyses must bind the same DEMO account")

    results: list[dict[str, object]] = []
    for code in _CODES:
        signal_counts: Counter[str] = Counter()
        stage_by_symbol: dict[str, str] = {}
        hypotheses: dict[str, dict[str, object]] = {}
        for symbol, rows in analyses:
            row = rows[code]
            stage_by_symbol[symbol] = _text(row.get("failure_stage"), name="failure_stage")
            for value in _array(row.get("diagnostic_signals"), name="diagnostic_signals"):
                signal_counts[_text(value, name="diagnostic signal")] += 1
            for value in _array(row.get("hypotheses_to_test"), name="hypotheses"):
                hypothesis = _object(value, name="hypothesis")
                signal = _text(hypothesis.get("signal"), name="hypothesis signal")
                hypotheses.setdefault(signal, hypothesis)

        multi_row = multi_rows[code]
        robust_pass = _boolean(multi_row.get("robust_pass"), name="robust_pass")
        recurring = tuple(sorted(signal for signal, count in signal_counts.items() if count >= 2))
        ordered_hypotheses = sorted(
            hypotheses.values(),
            key=lambda item: (
                -signal_counts[_text(item.get("signal"), name="hypothesis signal")],
                _text(item.get("signal"), name="hypothesis signal"),
            ),
        )
        results.append(
            {
                "trader_code": code,
                "robust_pass": robust_pass,
                "research_disposition": (
                    "retain_unchanged_for_canonical_gates"
                    if robust_pass
                    else "failure_analysis_required"
                ),
                "instrument_failure_stages": stage_by_symbol,
                "diagnostic_signal_counts": dict(sorted(signal_counts.items())),
                "recurring_signals": list(recurring),
                "ranked_hypotheses_to_test": ordered_hypotheses,
                "pooled_in_sample": multi_row.get("pooled_in_sample"),
                "pooled_oos": multi_row.get("pooled_oos"),
                "pooled_stressed_oos": multi_row.get("pooled_stressed_oos"),
                "oos_pair_pass_count": multi_row.get("oos_pair_pass_count"),
                "stress_pair_pass_count": multi_row.get("stress_pair_pass_count"),
            }
        )

    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "symbols": list(symbols),
        "instrument_count": len(symbols),
        "account_fingerprint": next(iter(fingerprints)),
        "holdout_governance": {
            "current_oos_may_be_used_for_diagnosis": True,
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "new_previously_unseen_holdout_required_after_any_hypothesis_change": True,
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 7:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_failure_analysis_aggregate "
            "MULTI_PAIR_JSON ANALYSIS_JSON... (exactly six)"
        )
        return 2
    try:
        payload = run_failure_analysis_aggregate(
            Path(arguments[0]),
            tuple(Path(value) for value in arguments[1:]),
        )
    except FirstCohortFailureAnalysisError as error:
        print(f"aggregate failure analysis failed: {error}", file=sys.stderr)
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
