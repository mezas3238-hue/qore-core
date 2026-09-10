"""Final, governed research dossiers for the first DEMO Trader cohort.

The builder joins the six independent instrument artifacts with their pooled
analysis.  It is deliberately descriptive: a robust research result is not an
authority decision and cannot grant DEMO_ELIGIBLE.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.cohort import FirstCohortTraderLabEntry
from qore.infrastructure.trader_lab.first_cohort_failure_analysis import (
    FirstCohortFailureAnalysisError,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
)
from qore.infrastructure.trader_lab.promotion import (
    TraderLabPromotionStatus,
    evaluate_demo_eligibility,
)

_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_SYMBOLS = ("AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDJPY", "XAUUSD")
_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_ACCOUNT_PATTERN = re.compile(r"[0-9a-f]{64}")
_SCHEMA = "qore.trader_lab.first_cohort_deep_dossier.v1"
_COMPARATIVE_SCHEMA = "qore.trader_lab.first_cohort_comparative_report.v1"
_HOLDOUT_SCHEMA = "qore.trader_lab.first_cohort_holdout_register.v1"
_PROMOTION_SCHEMA = "qore.trader_lab.first_cohort_promotion_report.v1"
_MINIMUM_EFFECTIVE_SECONDS = 730 * 24 * 60 * 60

#: The 10 mandatory governed Trader Lab lifecycle stages, in canonical order.
#: These are materialized only by the governed authority chain and are distinct
#: from the descriptive research battery recorded under ``evaluation_battery``.
_LIFECYCLE_STAGE_ORDER: tuple[str, ...] = tuple(stage.value for stage in MANDATORY_STAGES)

#: Lifecycle stages governed by an owning authority with no in-repo self-mint.
_EXTERNAL_GOVERNED_STAGES: frozenset[str] = frozenset(
    {"stress", "risk_review", "cibo_review", "independent_validation"}
)


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


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise FirstCohortFailureAnalysisError(f"{name} must be an integer")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortFailureAnalysisError(f"{name} must be bool")
    return value


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise FirstCohortFailureAnalysisError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FirstCohortFailureAnalysisError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _lifecycle_stage_statuses(
    lifecycle: TraderLabLifecycle | None,
) -> dict[str, str]:
    """Map the 10 mandatory lifecycle stages to their actual governed status.

    A research-only dossier (no lifecycle supplied) reports every stage as
    ``not_supplied``: the research battery never materializes lifecycle stage
    evidence. When a governed lifecycle is supplied, stages already completed are
    ``completed``; external-governed stages (stress/Risk/CIBO/independent
    validation) still missing after Monte Carlo are ``blocked_external`` (they
    require an owning authority's issued proof); everything else is
    ``not_started``. This never fabricates a ``completed`` authority stage.
    """

    if lifecycle is None:
        return {stage: "not_supplied" for stage in _LIFECYCLE_STAGE_ORDER}
    completed = {stage.value for stage in lifecycle.completed_stages}
    statuses: dict[str, str] = {}
    for stage in _LIFECYCLE_STAGE_ORDER:
        if stage in completed:
            statuses[stage] = "completed"
        elif stage in _EXTERNAL_GOVERNED_STAGES and "monte_carlo" in completed:
            statuses[stage] = "blocked_external"
        else:
            statuses[stage] = "not_started"
    return statuses


def _read(path: Path, *, name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortFailureAnalysisError(f"cannot read {name}") from error
    return _object(decoded, name=name)


def _rows(payload: dict[str, object], *, name: str) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for value in _array(payload.get("results"), name=f"{name} results"):
        row = _object(value, name=f"{name} result")
        code = _text(row.get("trader_code"), name=f"{name} trader_code")
        if code in rows:
            raise FirstCohortFailureAnalysisError(f"duplicate {name} Trader")
        rows[code] = row
    if tuple(rows) != _CODES:
        raise FirstCohortFailureAnalysisError(f"{name} cohort identity/order changed")
    return rows


def _profile(row: dict[str, object], *, default: bool) -> dict[str, object]:
    profiles = [
        _object(value, name="characterization profile")
        for value in _array(row.get("profiles"), name="characterization profiles")
    ]
    label = "production-default"
    if not default:
        selected = [
            profile
            for profile in profiles
            if _boolean(
                profile.get("selected_by_in_sample_only"),
                name="selected_by_in_sample_only",
            )
        ]
        if selected:
            if len(selected) != 1:
                raise FirstCohortFailureAnalysisError(
                    "multiple in-sample-selected characterization profiles"
                )
            return selected[0]
    matches = [profile for profile in profiles if profile.get("profile") == label]
    if len(matches) != 1:
        raise FirstCohortFailureAnalysisError("missing unique production-default profile")
    return matches[0]


def _quantile(values: list[Decimal], fraction: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    index = int((Decimal(len(ordered) - 1) * fraction).to_integral_value())
    return ordered[index]


def _performance(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {
            "sample_size": 0,
            "mean_return": "0",
            "win_rate": "0",
            "profit_factor": None,
            "payoff_ratio": None,
            "maximum_drawdown": "0",
            "tail": {"p01": "0", "p05": "0", "expected_shortfall_5pct": "0"},
        }
    positive = [value for value in values if value > 0]
    negative = [value for value in values if value < 0]
    gross_profit = sum(positive, Decimal(0))
    gross_loss = abs(sum(negative, Decimal(0)))
    equity = Decimal(1)
    peak = equity
    drawdown = Decimal(0)
    for value in values:
        equity *= Decimal(1) + value
        peak = max(peak, equity)
        if peak > 0:
            drawdown = max(drawdown, (peak - equity) / peak)
    p05 = _quantile(values, Decimal("0.05"))
    tail = [value for value in values if value <= p05]
    return {
        "sample_size": len(values),
        "mean_return": format(sum(values, Decimal(0)) / Decimal(len(values)), "f"),
        "win_rate": format(Decimal(sum(value > 0 for value in values)) / len(values), "f"),
        "profit_factor": None if gross_loss == 0 else format(gross_profit / gross_loss, "f"),
        "payoff_ratio": (
            None
            if not positive or not negative
            else format(
                (sum(positive, Decimal(0)) / len(positive))
                / abs(sum(negative, Decimal(0)) / len(negative)),
                "f",
            )
        ),
        "compounded_return": format(equity - Decimal(1), "f"),
        "maximum_drawdown": format(drawdown, "f"),
        "tail": {
            "p01": format(_quantile(values, Decimal("0.01")), "f"),
            "p05": format(p05, "f"),
            "expected_shortfall_5pct": format(
                sum(tail, Decimal(0)) / Decimal(len(tail)), "f"
            ),
            "worst": format(min(values), "f"),
            "best": format(max(values), "f"),
        },
    }


def _maximum_drawdown(values: list[Decimal]) -> Decimal:
    equity = Decimal(1)
    peak = equity
    drawdown = Decimal(0)
    for value in values:
        equity *= Decimal(1) + value
        peak = max(peak, equity)
        if peak > 0:
            drawdown = max(drawdown, (peak - equity) / peak)
    return drawdown


def _monte_carlo(values: list[Decimal], *, identity: str) -> dict[str, object]:
    minimum = 30
    if len(values) < minimum:
        return {
            "applicable": False,
            "minimum_sample": minimum,
            "observed_sample": len(values),
            "reason": "insufficient_filled_trade_sample",
        }
    seed = int(hashlib.sha256(identity.encode("ascii")).hexdigest()[:16], 16)
    state = seed
    modulus_mask = (1 << 64) - 1

    def next_index() -> int:
        nonlocal state
        state = (6_364_136_223_846_793_005 * state + 1_442_695_040_888_963_407) & (
            modulus_mask
        )
        return state % len(values)

    simulations = 1000
    means: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for _ in range(simulations):
        sample = [values[next_index()] for _ in values]
        means.append(sum(sample, Decimal(0)) / Decimal(len(sample)))
        drawdowns.append(_maximum_drawdown(sample))
    return {
        "applicable": True,
        "policy_id": "iid-trade-bootstrap-1000-v1",
        "limitations": "IID bootstrap does not preserve serial or cross-market dependence",
        "seed_sha256_prefix": f"{seed:016x}",
        "simulations": simulations,
        "mean_return": {
            "p05": format(_quantile(means, Decimal("0.05")), "f"),
            "p50": format(_quantile(means, Decimal("0.50")), "f"),
            "p95": format(_quantile(means, Decimal("0.95")), "f"),
            "probability_positive": format(
                Decimal(sum(value > 0 for value in means)) / simulations, "f"
            ),
        },
        "maximum_drawdown": {
            "p50": format(_quantile(drawdowns, Decimal("0.50")), "f"),
            "p95": format(_quantile(drawdowns, Decimal("0.95")), "f"),
        },
    }


def _instrument_payloads(
    evidence_root: Path, *, software_sha: str
) -> dict[str, dict[str, dict[str, object]]]:
    files: dict[str, dict[str, dict[str, object]]] = {}
    for name in (
        "market-evidence.json",
        "backtest.json",
        "walk-forward.json",
        "characterization.json",
        "failure-analysis.json",
    ):
        paths = sorted(evidence_root.rglob(name))
        if len(paths) != len(_SYMBOLS):
            raise FirstCohortFailureAnalysisError(
                f"expected exactly six {name} files, found {len(paths)}"
            )
        for path in paths:
            payload = _read(path, name=name)
            if _text(payload.get("software_sha"), name=f"{name} software_sha") != software_sha:
                raise FirstCohortFailureAnalysisError(
                    f"{name} does not bind exact software SHA"
                )
            symbol_value = payload.get("symbol")
            symbol = (
                _text(_object(symbol_value, name="market symbol").get("symbol_name"), name="symbol")
                if type(symbol_value) is dict
                else _text(symbol_value, name="symbol")
            )
            files.setdefault(symbol, {})[name] = payload
    if tuple(sorted(files)) != _SYMBOLS or any(len(value) != 5 for value in files.values()):
        raise FirstCohortFailureAnalysisError("instrument artifact identity is incomplete")
    return files


def _aggregate_payloads(
    aggregate_dir: Path, *, software_sha: str
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name in (
        "multi-pair-walk-forward.json",
        "characterization-aggregate.json",
        "failure-analysis-aggregate.json",
        "hypothesis-register.json",
    ):
        payload = _read(aggregate_dir / name, name=name)
        if _text(payload.get("software_sha"), name=f"{name} software_sha") != software_sha:
            raise FirstCohortFailureAnalysisError(
                f"{name} does not bind exact software SHA"
            )
        result[name] = payload
    return result


def build_research_reports(
    evidence_root: Path,
    aggregate_dir: Path,
    *,
    software_sha: str,
    lifecycle_by_trader: Mapping[str, FirstCohortTraderLabEntry] | None = None,
) -> dict[str, dict[str, object]]:
    """Join the complete experiment into five dossiers and three registers.

    The research dossier is descriptive and cannot grant DEMO_ELIGIBLE. When
    ``lifecycle_by_trader`` is supplied, the governed lifecycle and the canonical
    ``evaluate_demo_eligibility`` decision are reflected per Trader; without it
    (the research-only CLI) every governed lifecycle stage is reported
    ``not_supplied`` and ``demo_eligible`` stays ``False``. No authority is ever
    inferred from a research artifact.
    """
    if _SHA_PATTERN.fullmatch(software_sha) is None:
        raise FirstCohortFailureAnalysisError("software_sha must be a lowercase Git SHA")
    if lifecycle_by_trader is not None:
        if not isinstance(lifecycle_by_trader, Mapping) or any(
            type(key) is not str for key in lifecycle_by_trader
        ):
            raise FirstCohortFailureAnalysisError(
                "lifecycle_by_trader must be a string-keyed mapping"
            )
        if not set(lifecycle_by_trader) <= set(_CODES):
            raise FirstCohortFailureAnalysisError(
                "lifecycle_by_trader keys must be first-cohort Trader codes"
            )
        for code, candidate_entry in lifecycle_by_trader.items():
            if not isinstance(candidate_entry, FirstCohortTraderLabEntry):
                raise FirstCohortFailureAnalysisError(
                    "lifecycle_by_trader values must be FirstCohortTraderLabEntry"
                )
            if candidate_entry.trader_code.value != code:
                raise FirstCohortFailureAnalysisError(
                    f"lifecycle_by_trader[{code!r}] binds a mismatched Trader code"
                )
            bound_codes = tuple(
                parameter.value
                for parameter in candidate_entry.candidate.strategy_binding.manifest.parameters
                if parameter.name == "trader.code"
            )
            if (
                len(bound_codes) != 1
                or type(bound_codes[0]) is not str
                or bound_codes[0] != code
            ):
                raise FirstCohortFailureAnalysisError(
                    f"lifecycle_by_trader[{code!r}] binds a mismatched Trader code"
                )
    instruments = _instrument_payloads(evidence_root, software_sha=software_sha)
    aggregates = _aggregate_payloads(aggregate_dir, software_sha=software_sha)
    multi_rows = _rows(aggregates["multi-pair-walk-forward.json"], name="multi-pair")
    aggregate_rows = _rows(
        aggregates["characterization-aggregate.json"], name="characterization aggregate"
    )
    failure_rows = _rows(
        aggregates["failure-analysis-aggregate.json"], name="failure aggregate"
    )
    hypotheses = _array(
        aggregates["hypothesis-register.json"].get("hypotheses"), name="hypotheses"
    )
    hypotheses_by_code = {
        code: [
            _object(value, name="hypothesis")
            for value in hypotheses
            if _object(value, name="hypothesis").get("trader") == code
        ]
        for code in _CODES
    }

    coverages: dict[str, object] = {}
    instrument_rows: dict[str, dict[str, dict[str, object]]] = {code: {} for code in _CODES}
    returns: dict[str, list[tuple[str, Decimal]]] = {code: [] for code in _CODES}
    accounts: set[str] = set()
    for symbol, payloads in sorted(instruments.items()):
        market = payloads["market-evidence.json"]
        if _text(market.get("environment"), name="environment") != "demo":
            raise FirstCohortFailureAnalysisError(
                f"{symbol} market evidence must be DEMO"
            )
        if not _boolean(market.get("read_only"), name="read_only"):
            raise FirstCohortFailureAnalysisError(
                f"{symbol} market evidence must be read-only"
            )
        if _boolean(market.get("account_is_live"), name="account_is_live"):
            raise FirstCohortFailureAnalysisError(
                f"{symbol} LIVE account evidence is prohibited"
            )
        if not _boolean(
            market.get("trading_permission_verified"),
            name="trading_permission_verified",
        ):
            raise FirstCohortFailureAnalysisError(
                f"{symbol} DEMO trading permission must be verified"
            )
        account = _text(market.get("account_fingerprint"), name="account_fingerprint")
        if _ACCOUNT_PATTERN.fullmatch(account) is None:
            raise FirstCohortFailureAnalysisError(
                f"{symbol} account fingerprint must be 64 lowercase hex"
            )
        accounts.add(account)
        coverage = _object(market.get("coverage"), name="coverage")
        actual: dict[str, object] = {}
        for period in ("M5", "M15", "H4"):
            item = _object(coverage.get(period), name=f"{period} coverage")
            seconds = _integer(item.get("span_seconds"), name=f"{period} span_seconds")
            first = _timestamp(
                item.get("first_opened_at"), name=f"{period} first_opened_at"
            )
            last = _timestamp(
                item.get("last_closed_at"), name=f"{period} last_closed_at"
            )
            if last <= first:
                raise FirstCohortFailureAnalysisError(
                    f"{symbol} {period} coverage boundaries inverted"
                )
            actual_seconds = int((last - first).total_seconds())
            if actual_seconds < _MINIMUM_EFFECTIVE_SECONDS:
                raise FirstCohortFailureAnalysisError(
                    f"{symbol} {period} has less than 730 effective days"
                )
            if actual_seconds != seconds:
                raise FirstCohortFailureAnalysisError(
                    f"{symbol} {period} coverage span mismatch"
                )
            actual[period] = item
        coverages[symbol] = actual
        characterization_rows = _rows(
            payloads["characterization.json"], name=f"{symbol} characterization"
        )
        failure = _rows(payloads["failure-analysis.json"], name=f"{symbol} failure")
        for code in _CODES:
            default = _profile(characterization_rows[code], default=True)
            instrument_rows[code][symbol] = {
                "default_characterization": default,
                "failure_analysis": failure[code],
            }
            for value in _array(default.get("setups"), name="setups"):
                setup = _object(value, name="setup")
                returned = setup.get("return_rate")
                if type(returned) is str:
                    returns[code].append(
                        (_text(setup.get("exit_at"), name="exit_at"), Decimal(returned))
                    )
    if len(accounts) != 1:
        raise FirstCohortFailureAnalysisError("instrument evidence mixed DEMO accounts")
    account = next(iter(accounts))
    for payload in aggregates.values():
        if _text(payload.get("account_fingerprint"), name="aggregate account") != account:
            raise FirstCohortFailureAnalysisError("aggregate evidence account mismatch")

    dossiers: dict[str, dict[str, object]] = {}
    promotion_states: dict[str, dict[str, object]] = {}
    for code in _CODES:
        aggregate = aggregate_rows[code]
        default = _profile(aggregate, default=True)
        methodology = _object(default.get("methodology_identity"), name="methodology")
        multi = multi_rows[code]
        trader_failure = failure_rows[code]
        ordered_returns = [value for _at, value in sorted(returns[code])]
        robust = _boolean(multi.get("robust_pass"), name="robust_pass")
        entry = lifecycle_by_trader.get(code) if lifecycle_by_trader is not None else None
        lifecycle_stages = _lifecycle_stage_statuses(
            entry.lifecycle if entry is not None else None
        )
        if entry is None:
            blockers = [
                "risk_review_not_supplied",
                "cibo_review_not_supplied",
                "independent_validation_not_supplied",
                "economic_evidence_authority_not_supplied",
            ]
            if not robust:
                blockers.insert(0, "multi_market_research_gate_failed")
            promotion: dict[str, object] = {
                "state": "research_only",
                "robust_research_pass": robust,
                "demo_eligible": False,
                "blockers": blockers,
                "recommendation": (
                    "retain unchanged for the remaining governed authorities"
                    if robust
                    else "investigate registered hypotheses; require fresh holdout after change"
                ),
            }
        else:
            decision = evaluate_demo_eligibility(
                entry.lifecycle, economic_evidence=entry.economic_evidence
            )
            eligible = decision.status is TraderLabPromotionStatus.DEMO_ELIGIBLE
            blockers = list(decision.reasons)
            if not eligible and not blockers:
                blockers.append(f"promotion_status_{decision.status.value}")
            promotion = {
                "state": entry.lifecycle.state.value,
                "promotion_status": decision.status.value,
                "robust_research_pass": robust,
                "demo_eligible": eligible,
                "blockers": tuple(blockers),
                "recommendation": (
                    "eligible_for_demo" if eligible else "blocked_see_blockers"
                ),
            }
        dossiers[code] = {
            "schema": _SCHEMA,
            "trader_code": code,
            "environment": "demo",
            "research_only": True,
            "software_sha": software_sha,
            "account_fingerprint": account,
            "identity": {
                **methodology,
                "config_fingerprint": default.get("config_fingerprint"),
                "parameters": default.get("parameters"),
            },
            "methodology_component_map": _rows(
                instruments[_SYMBOLS[0]]["characterization.json"],
                name="characterization",
            )[code].get("methodology_component_map"),
            "data_provenance": {
                "symbols": list(_SYMBOLS),
                "effective_coverage": coverages,
                "minimum_required_days": 730,
                "software_sha": software_sha,
            },
            "results_by_market": instrument_rows[code],
            "aggregate_characterization": default,
            "failure_dossier": trader_failure,
            "parameter_behavior": {
                "profiles": aggregate.get("profiles"),
                "classification": trader_failure.get("classification_labels"),
            },
            "performance": _performance(ordered_returns),
            "monte_carlo": _monte_carlo(
                ordered_returns,
                identity=f"{software_sha}:{code}:{default.get('config_fingerprint')}",
            ),
            "hypotheses": hypotheses_by_code[code],
            "holdout_governance": {
                "current_oos_state": "consumed_for_research",
                "consumed_holdout_cannot_certify_modified_strategy": True,
                "fresh_previously_unseen_holdout_required_after_change": True,
                "lineage": (
                    "parent trader version -> evidence -> hypothesis -> change -> "
                    "new trader version -> fresh holdout"
                ),
            },
            "evaluation_battery": {
                "closed_bar_characterization": "completed",
                "backtest": "completed",
                "in_sample": "completed",
                "walk_forward": "completed",
                "untouched_oos": "completed_then_consumed_for_research",
                "multi_market": "completed",
                "multi_regime": "completed_past_only",
                "stressed_oos": "completed",
                "parameter_perturbation": "completed",
                "failure_analysis": "completed",
                "descriptive_monte_carlo": (
                    "completed" if len(ordered_returns) >= 30 else "not_applicable_underpowered"
                ),
            },
            "lifecycle_stages": lifecycle_stages,
            "research_vs_lifecycle": {
                "research_battery_completed": True,
                "lifecycle_materialized": entry is not None,
                "note": (
                    "evaluation_battery records the descriptive research battery "
                    "(closed-bar backtest, walk-forward, characterization, failure "
                    "analysis, descriptive Monte Carlo). lifecycle_stages records the "
                    "10 mandatory governed Trader Lab stages (RESEARCH -> REPLAY -> "
                    "FAST_FORWARD -> OOS -> STRESS -> MONTE_CARLO -> RISK_REVIEW -> "
                    "CIBO_REVIEW -> INDEPENDENT_VALIDATION -> ECONOMIC_EVIDENCE), "
                    "materialized only by the governed authority chain. The formal "
                    "REPLAY gate requires event-level REPLAY_CHRONOLOGY evidence and "
                    "is distinct from the closed-bar research battery."
                ),
            },
            "evidence_limitations": [
                "OHLC cannot establish intrabar order; stop-first policy is conservative",
                "regime labels use only information available at as_of",
                "research observation consumes current OOS for any derived change",
                "correlation is not treated as causal proof",
            ],
            "promotion": promotion,
        }
        promotion_states[code] = promotion

    comparative = {
        "schema": _COMPARATIVE_SCHEMA,
        "environment": "demo",
        "research_only": True,
        "software_sha": software_sha,
        "account_fingerprint": account,
        "comparison_order": list(_CODES),
        "five_dossiers_complete": True,
        "traders": {
            code: {
                "performance": dossiers[code]["performance"],
                "monte_carlo": dossiers[code]["monte_carlo"],
                "classification": failure_rows[code].get("classification_labels"),
                "pooled_in_sample": multi_rows[code].get("pooled_in_sample"),
                "pooled_oos": multi_rows[code].get("pooled_oos"),
                "pooled_stressed_oos": multi_rows[code].get("pooled_stressed_oos"),
                "robust_research_pass": multi_rows[code].get("robust_pass"),
            }
            for code in _CODES
        },
        "comparison_rule": "pooled statistics are sample-weighted, never averages of averages",
    }
    holdout = {
        "schema": _HOLDOUT_SCHEMA,
        "software_sha": software_sha,
        "account_fingerprint": account,
        "symbols": list(_SYMBOLS),
        "current_holdout_state": "consumed_for_research",
        "applies_to": list(_CODES),
        "forbidden_reuse": ["current OOS", "current pooled OOS", "current stressed OOS"],
        "fresh_evidence_required_after_methodology_or_parameter_change": True,
        "required_identity_bindings": [
            "trader_version",
            "methodology_fingerprint",
            "config_fingerprint",
            "software_sha",
            "dataset_lineage",
        ],
    }
    promotion = {
        "schema": _PROMOTION_SCHEMA,
        "software_sha": software_sha,
        "demo_eligible_count": sum(
            1
            for state in promotion_states.values()
            if state.get("demo_eligible") is True
        ),
        "authority_rule": (
            "research artifacts cannot grant DEMO_ELIGIBLE; ECONOMIC_EVIDENCE is a distinct "
            "mandatory lifecycle stage after INDEPENDENT_VALIDATION"
        ),
        "traders": promotion_states,
    }
    return {
        **{f"{code}-deep-characterization-dossier.json": value for code, value in dossiers.items()},
        "first-cohort-comparative-deep-characterization-report.json": comparative,
        "holdout-register.json": holdout,
        "promotion-report.json": promotion,
    }


def _write_reports(output_dir: Path, reports: dict[str, dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in sorted(reports.items()):
        (output_dir / name).write_text(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 4:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_research_dossiers "
            "EVIDENCE_ROOT AGGREGATE_DIR OUTPUT_DIR SOFTWARE_SHA",
            file=sys.stderr,
        )
        return 2
    try:
        reports = build_research_reports(
            Path(arguments[0]), Path(arguments[1]), software_sha=arguments[3]
        )
        _write_reports(Path(arguments[2]), reports)
    except FirstCohortFailureAnalysisError as error:
        print(f"first-cohort dossier generation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
