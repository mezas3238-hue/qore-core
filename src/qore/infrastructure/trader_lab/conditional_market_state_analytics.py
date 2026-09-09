"""Five-Trader conditional market-state analytics report orchestration."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC
from pathlib import Path
from typing import TextIO, cast

from qore.infrastructure.trader_lab.conditional_market_state_features import (
    CLASSIFIER_VERSION,
    FORWARD_PATH_POLICY,
    SESSION_POLICY,
)
from qore.infrastructure.trader_lab.conditional_market_state_observations import (
    ConditionalMarketStateObservationError,
    analyze_trader,
)
from qore.infrastructure.trader_lab.first_cohort_backtest import _CODES, _load
from qore.infrastructure.traders.evaluators import cohort_evaluators
from qore.infrastructure.traders.instrument_binding import DemoTradingEvaluatorBoundary

_SCHEMA = "qore.trader_lab.conditional_market_state_analytics.v1"
_ANALYSIS_VERSION = "qore-trader-lab-conditional-edge-v1"


class ConditionalMarketStateAnalyticsError(ConditionalMarketStateObservationError):
    __slots__ = ()


def run_conditional_market_state_analytics(
    path: Path, observation_path: Path | None = None
) -> dict[str, object]:
    """Run causal market-state analytics for all five production cohort Traders."""
    series, fingerprint, symbol, checked_at, software_sha = _load(path)
    evaluators = cohort_evaluators()
    if tuple(evaluator.trader_code for evaluator in evaluators) != _CODES:
        raise ConditionalMarketStateAnalyticsError(
            "production cohort identity/order changed"
        )

    def _run(writer: TextIO | None) -> tuple[dict[str, object], ...]:
        return tuple(
            analyze_trader(
                cast(DemoTradingEvaluatorBoundary, evaluator),
                trader_code=code,
                symbol=symbol,
                software_sha=software_sha,
                series=series,
                observation_writer=writer,
            )
            for code, evaluator in zip(_CODES, evaluators, strict=True)
        )

    if observation_path is None:
        results = _run(None)
    else:
        observation_path.parent.mkdir(parents=True, exist_ok=True)
        with observation_path.open("w", encoding="utf-8", newline="\n") as writer:
            results = _run(writer)

    stream_material = "".join(
        cast(dict[str, str], result["observation_stream"])["sha256"]
        for result in results
    )
    report: dict[str, object] = {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "account_fingerprint": fingerprint,
        "symbol": symbol,
        "checked_at": checked_at.astimezone(UTC).isoformat(),
        "software_sha": software_sha,
        "classifier_version": CLASSIFIER_VERSION,
        "analysis_version": _ANALYSIS_VERSION,
        "session_policy": SESSION_POLICY,
        "forward_path_policy": FORWARD_PATH_POLICY,
        "observation_artifact": {
            "format": "canonical-json-lines-v1",
            "emitted": observation_path is not None,
            "bundle_fingerprint": hashlib.sha256(stream_material.encode()).hexdigest(),
            "row_count": sum(
                cast(
                    int,
                    cast(dict[str, object], result["observation_stream"])["row_count"],
                )
                for result in results
            ),
        },
        "anti_lookahead": {
            "decision_time_state_is_past_only": True,
            "post_decision_labels_are_separate": True,
            "future_path_is_oracle_only": True,
            "oos_discovery_requires_fresh_holdout": True,
        },
        "authority": {
            "may_promote_trader": False,
            "may_issue_orders": False,
            "may_grant_demo_or_live_authority": False,
        },
        "results": list(results),
    }
    canonical = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    report["reproducibility_fingerprint"] = hashlib.sha256(
        canonical.encode()
    ).hexdigest()
    return report


def to_json(report: dict[str, object]) -> str:
    return json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) not in {1, 2}:
        print(
            "usage: python -m qore.infrastructure.trader_lab."
            "conditional_market_state_analytics PATH [OBSERVATIONS_NDJSON]"
        )
        return 2
    observation_path = Path(arguments[1]) if len(arguments) == 2 else None
    try:
        report = run_conditional_market_state_analytics(
            Path(arguments[0]), observation_path
        )
    except ConditionalMarketStateAnalyticsError as error:
        print(f"conditional market-state analytics failed: {error}", file=sys.stderr)
        return 1
    print(to_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
