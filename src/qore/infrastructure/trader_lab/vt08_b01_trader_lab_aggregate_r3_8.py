"""Seven-market aggregate for VT-08 R3.8 B01 Trader Lab diagnostics."""

from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_b01_diagnostics_aggregate.r3.8.v1"
_INPUT_SCHEMA = "qore.trader_lab.vt08_b01_diagnostics.r3.8.v1"
_EXPECTED_SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
)


class Vt08B01TraderLabAggregateError(InfrastructureError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01TraderLabAggregateError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01TraderLabAggregateError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08B01TraderLabAggregateError(f"{name} must be non-empty text")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt08B01TraderLabAggregateError(f"{name} must be a non-negative int")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08B01TraderLabAggregateError(f"{name} must be bool")
    return value


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08B01TraderLabAggregateError(f"{name} must be decimal text") from error
    if not parsed.is_finite():
        raise Vt08B01TraderLabAggregateError(f"{name} must be finite")
    return parsed


def _read(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08B01TraderLabAggregateError("cannot read Trader Lab evidence") from error
    return _object(decoded, name="Trader Lab evidence")


def _metrics(values: tuple[Decimal, ...]) -> dict[str, object]:
    if not values:
        return {
            "sample_size": 0,
            "mean_return": "0",
            "win_rate": "0",
            "population_variance": "0",
            "gross_profit": "0",
            "gross_loss": "0",
            "profit_factor": None,
            "compounded_return": "0",
            "maximum_drawdown": "0",
            "max_losing_streak": 0,
        }
    size = Decimal(len(values))
    mean = sum(values, Decimal(0)) / size
    variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / size
    positives = tuple(value for value in values if value > 0)
    negatives = tuple(value for value in values if value < 0)
    gross_profit = sum(positives, Decimal(0))
    gross_loss = abs(sum(negatives, Decimal(0)))
    equity = Decimal(1)
    peak = equity
    max_drawdown = Decimal(0)
    max_losing_streak = 0
    losing_streak = 0
    for value in values:
        equity *= Decimal(1) + value
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        if value <= 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
    return {
        "sample_size": len(values),
        "mean_return": format(mean, "f"),
        "win_rate": format(Decimal(len(positives)) / size, "f"),
        "population_variance": format(variance, "f"),
        "gross_profit": format(gross_profit, "f"),
        "gross_loss": format(gross_loss, "f"),
        "profit_factor": None if gross_loss == 0 else format(gross_profit / gross_loss, "f"),
        "compounded_return": format(equity - Decimal(1), "f"),
        "maximum_drawdown": format(max_drawdown, "f"),
        "max_losing_streak": max_losing_streak,
    }


def _market_summary(report: dict[str, object]) -> dict[str, object]:
    full_period = _object(report.get("full_period"), name="full_period")
    walk = _object(report.get("walk_forward"), name="walk_forward")
    failure = _object(report.get("failure_analysis"), name="failure_analysis")
    return {
        "symbol": _text(report.get("symbol"), name="symbol"),
        "sample_size": _integer(full_period.get("sample_size"), name="sample_size"),
        "mean_return": _text(full_period.get("mean_return"), name="mean_return"),
        "win_rate": _text(full_period.get("win_rate"), name="win_rate"),
        "profit_factor": full_period.get("profit_factor"),
        "maximum_drawdown": _text(
            full_period.get("maximum_drawdown"), name="maximum_drawdown"
        ),
        "in_sample_pass": _boolean(walk.get("in_sample_pass"), name="in_sample_pass"),
        "oos_pass": _boolean(walk.get("oos_pass"), name="oos_pass"),
        "stress_pass": _boolean(walk.get("stress_pass"), name="stress_pass"),
        "stage": _text(failure.get("stage"), name="stage"),
        "exit_reason_counts": _object(
            report.get("exit_reason_counts"), name="exit_reason_counts"
        ),
    }


def _hypothesis_register(
    *,
    market_reports: list[dict[str, object]],
    pooled_metrics: dict[str, object],
    exit_counts: Counter[str],
) -> list[dict[str, object]]:
    hypotheses: list[dict[str, object]] = []
    sample = _integer(pooled_metrics.get("sample_size"), name="sample_size")
    if sample > 0 and exit_counts.get("stop", 0) * 2 > sample:
        hypotheses.append(
            {
                "id": "VT08-R3.8-H01",
                "evidence": "stop exits dominate more than half of pooled trades",
                "mechanism": (
                    "B01 protected-swing entry/invalidation geometry may admit weak or late "
                    "positional structures; no stop widening is authorized by this evidence."
                ),
                "change_family": "source-authorized-entry-or-ps-quality",
                "predicted_improvement": (
                    "reduce stop dominance and make fresh-holdout expectancy non-negative"
                ),
                "falsification": (
                    "reject if a pre-registered source-supported filter does not improve a "
                    "new untouched holdout"
                ),
                "forbidden_reuse": "current 760-day evidence cannot be an independent holdout",
                "status": "research_hypothesis_only",
            }
        )
    positive_markets = [
        _text(item.get("symbol"), name="symbol")
        for item in market_reports
        if _decimal(item.get("mean_return"), name="mean_return") > 0
    ]
    negative_markets = [
        _text(item.get("symbol"), name="symbol")
        for item in market_reports
        if _decimal(item.get("mean_return"), name="mean_return") < 0
    ]
    if positive_markets and negative_markets:
        hypotheses.append(
            {
                "id": "VT08-R3.8-H02",
                "evidence": {
                    "positive_mean_markets": positive_markets,
                    "negative_mean_markets": negative_markets,
                },
                "mechanism": "the frozen B01 subset may be instrument dependent",
                "change_family": "instrument-or-regime-dependence",
                "predicted_improvement": (
                    "instrument/regime effect must reproduce on fresh markets or a new holdout"
                ),
                "falsification": (
                    "reject if the sign split disappears on independently acquired evidence"
                ),
                "forbidden_reuse": "do not select markets from this sample and call them OOS",
                "status": "research_hypothesis_only",
            }
        )
    containment = sum(
        _integer(
            _object(item.get("exit_reason_counts"), name="exit_reason_counts").get(
                "h4_containment_exit", 0
            ),
            name="h4_containment_exit",
        )
        for item in market_reports
    )
    if containment:
        hypotheses.append(
            {
                "id": "VT08-R3.8-H03",
                "evidence": {"h4_containment_exit_count": containment},
                "mechanism": (
                    "the explicit QORE H4-close containment can truncate source-unknown "
                    "position lifecycle and must be isolated from signal quality"
                ),
                "change_family": "execution-model-diagnostic",
                "predicted_improvement": (
                    "a separately versioned boundary experiment should reveal whether "
                    "containment truncates winners or prevents later losses"
                ),
                "falsification": (
                    "reject any lifecycle change that lacks source authority or fresh-holdout "
                    "improvement"
                ),
                "forbidden_reuse": "diagnostic only; no silent execution-model replacement",
                "status": "research_hypothesis_only",
            }
        )
    return hypotheses


def run_vt08_b01_trader_lab_aggregate(paths: list[Path]) -> dict[str, object]:
    if len(paths) != len(_EXPECTED_SYMBOLS):
        raise Vt08B01TraderLabAggregateError("exactly seven Trader Lab reports are required")
    reports = [_read(path) for path in paths]
    for report in reports:
        if _text(report.get("schema"), name="schema") != _INPUT_SCHEMA:
            raise Vt08B01TraderLabAggregateError("unexpected Trader Lab input schema")
        if _text(report.get("environment"), name="environment") != "demo":
            raise Vt08B01TraderLabAggregateError("Trader Lab evidence must be DEMO")
        if not _boolean(report.get("read_only"), name="read_only"):
            raise Vt08B01TraderLabAggregateError("Trader Lab evidence must be read-only")
        lifecycle = _object(report.get("lifecycle_gate"), name="lifecycle_gate")
        if _boolean(lifecycle.get("demo_eligible"), name="demo_eligible"):
            raise Vt08B01TraderLabAggregateError("research report cannot grant DEMO_ELIGIBLE")

    reports.sort(key=lambda item: _text(item.get("symbol"), name="symbol"))
    symbols = tuple(_text(item.get("symbol"), name="symbol") for item in reports)
    if symbols != _EXPECTED_SYMBOLS:
        raise Vt08B01TraderLabAggregateError("seven-market identity changed")
    account_fingerprints = {
        _text(item.get("account_fingerprint"), name="account_fingerprint") for item in reports
    }
    software_shas = {_text(item.get("software_sha"), name="software_sha") for item in reports}
    methodology_fingerprints = {
        _text(item.get("methodology_fingerprint"), name="methodology_fingerprint")
        for item in reports
    }
    if len(account_fingerprints) != 1 or len(software_shas) != 1:
        raise Vt08B01TraderLabAggregateError("market evidence lineage differs")
    if len(methodology_fingerprints) != 1:
        raise Vt08B01TraderLabAggregateError("methodology fingerprint differs")

    trade_records: list[dict[str, object]] = []
    exit_counts: Counter[str] = Counter()
    market_reports: list[dict[str, object]] = []
    pooled_abstentions: Counter[str] = Counter()
    for report in reports:
        market_reports.append(_market_summary(report))
        for value in _array(report.get("trade_records"), name="trade_records"):
            row = _object(value, name="trade_record")
            enriched = dict(row)
            enriched["symbol"] = _text(report.get("symbol"), name="symbol")
            trade_records.append(enriched)
            exit_counts[_text(row.get("exit_reason"), name="exit_reason")] += 1
        abstains = _object(report.get("abstain_reasons"), name="abstain_reasons")
        for reason, count in abstains.items():
            pooled_abstentions[reason] += _integer(count, name=f"abstain {reason}")

    trade_records.sort(
        key=lambda item: (
            _text(item.get("signal_at"), name="signal_at"),
            _text(item.get("symbol"), name="symbol"),
        )
    )
    values = tuple(
        _decimal(item.get("return_rate"), name="return_rate") for item in trade_records
    )
    pooled_metrics = _metrics(values)
    market_negative = sum(
        _decimal(item.get("mean_return"), name="mean_return") < 0 for item in market_reports
    )
    market_positive = sum(
        _decimal(item.get("mean_return"), name="mean_return") > 0 for item in market_reports
    )
    oos_pass_count = sum(
        _boolean(item.get("oos_pass"), name="oos_pass") for item in market_reports
    )
    stress_pass_count = sum(
        _boolean(item.get("stress_pass"), name="stress_pass") for item in market_reports
    )

    classifications: list[str] = []
    if _decimal(pooled_metrics.get("mean_return"), name="mean_return") < 0:
        classifications.append("structural_methodology_failure_candidate")
    if market_positive and market_negative:
        classifications.append("instrument_dependency_candidate")
    if oos_pass_count == 0:
        classifications.append("oos_generalization_failure")
    elif stress_pass_count < oos_pass_count:
        classifications.append("stress_fragility")
    if exit_counts.get("stop", 0) * 2 > len(trade_records):
        classifications.append("geometry_or_entry_quality_problem_candidate")

    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "trader_code": "vt-08",
        "profile": "author-clarified",
        "bundle_id": "B01_SOURCE_FAITHFUL_HISTORICAL_REPLAY_V1",
        "symbols": list(symbols),
        "market_count": len(reports),
        "account_fingerprint": next(iter(account_fingerprints)),
        "software_sha": next(iter(software_shas)),
        "methodology_fingerprint": next(iter(methodology_fingerprints)),
        "pooled": pooled_metrics,
        "market_reports": market_reports,
        "exit_reason_counts": dict(sorted(exit_counts.items())),
        "pooled_abstain_reasons": dict(sorted(pooled_abstentions.items())),
        "market_positive_mean_count": market_positive,
        "market_negative_mean_count": market_negative,
        "oos_pass_market_count": oos_pass_count,
        "stress_pass_market_count": stress_pass_count,
        "failure_classifications": classifications,
        "hypothesis_register": _hypothesis_register(
            market_reports=market_reports,
            pooled_metrics=pooled_metrics,
            exit_counts=exit_counts,
        ),
        "trader_lab_stage_summary": {
            "research": "complete",
            "replay": "complete",
            "fast_forward": "complete_as_full_chronological_replay",
            "oos": "fail" if oos_pass_count == 0 else "mixed",
            "stress": "fail" if stress_pass_count == 0 else "mixed",
            "monte_carlo": "blocked_by_prior_stage_failure",
            "risk_review": "blocked_by_prior_stage_failure",
            "cibo_review": "blocked_by_prior_stage_failure",
            "independent_validation": "blocked_by_prior_stage_failure",
            "economic_evidence": "failed_current_policy",
            "demo_eligible": False,
        },
        "holdout_governance": {
            "current_760_day_evidence_consumed_for_research": True,
            "new_previously_unseen_holdout_required_after_any_hypothesis_change": True,
            "market_selection_from_current_results_prohibited_as_independent_validation": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        payload = run_vt08_b01_trader_lab_aggregate([Path(item) for item in arguments])
    except Vt08B01TraderLabAggregateError as error:
        print(f"VT-08 B01 Trader Lab aggregate failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
