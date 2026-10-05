"""Edge-only certification primitives for VT31 NAS100.

The trader is evaluated from equal-weight structural R outcomes. Capital
allocation fields may be present in source rows for provenance, but they are
never authoritative inputs to edge metrics.

Research and certification development only. This module opens no holdout and
grants no LIVE, real-capital, or production authority.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

_DECIMAL = Context(prec=34, rounding=ROUND_HALF_EVEN)

IDENTITY = "VT31_NAS100_EDGE_CERT_V1_DEV"
MINIMUM_COMPATIBLE_VOLUME = Decimal("0.01")

FORBIDDEN_CAPITAL_FIELDS = frozenset(
    {
        "capital_weighted_net_r",
        "requested_risk_r",
        "global_risk_scalar",
        "position_size",
        "lot_size",
        "volume",
        "leverage",
        "compound_multiplier",
        "monthly_risk_budget",
        "portfolio_weight",
    }
)

DEFAULT_COST_STRESS_R = (
    Decimal("0"),
    Decimal("0.02"),
    Decimal("0.05"),
    Decimal("0.10"),
)

GATES = {
    "profit_factor_per_era_min": Decimal("1.50"),
    "profit_factor_combined_min": Decimal("1.70"),
    "expectancy_min_exclusive": Decimal("0"),
    "max_drawdown_r_target": Decimal("10"),
    "max_drawdown_r_reject": Decimal("15"),
    "sharpe_min": Decimal("1.50"),
    "sortino_min": Decimal("2.00"),
    "payoff_min": Decimal("1.20"),
    "mc_positive_terminal_min": Decimal("0.90"),
    "mc_p95_drawdown_max": Decimal("15"),
    "severe_cost_pf_min_exclusive": Decimal("1.00"),
    "winner_count_preservation_min": Decimal("0.80"),
    "winner_r_preservation_min": Decimal("0.90"),
}


def _d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("edge metric values must be finite")
    return result


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def normalized_trade_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    friction_r: Decimal = Decimal("0"),
) -> list[dict[str, object]]:
    """Build equal-weight terminal trade rows from structural r_multiple only."""
    friction = _d(friction_r)
    if friction < 0:
        raise ValueError("friction_r cannot be negative")

    normalized: list[dict[str, object]] = []
    for index, source in enumerate(rows):
        if "r_multiple" not in source:
            raise ValueError(
                "each terminal trade requires structural r_multiple"
            )
        raw_r = _d(source["r_multiple"])
        ignored = {
            key: source[key]
            for key in sorted(FORBIDDEN_CAPITAL_FIELDS.intersection(source))
        }
        row = dict(source)
        for key in FORBIDDEN_CAPITAL_FIELDS:
            row.pop(key, None)
        row["edge_trade_index"] = index
        row["raw_structural_r"] = format(raw_r, "f")
        row["normalized_trade_r"] = format(raw_r - friction, "f")
        row["friction_r"] = format(friction, "f")
        row["ignored_capital_fields"] = ignored
        normalized.append(row)
    return normalized


def _values(rows: Sequence[Mapping[str, object]]) -> list[Decimal]:
    return [_d(row["normalized_trade_r"]) for row in rows]


def _profit_factor(values: Sequence[Decimal]) -> Decimal | None:
    gross_profit = sum(
        (value for value in values if value > 0),
        Decimal(0),
    )
    gross_loss = -sum(
        (value for value in values if value < 0),
        Decimal(0),
    )
    if gross_loss == 0:
        return None
    with localcontext(_DECIMAL):
        return gross_profit / gross_loss


def _max_drawdown(values: Sequence[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _sample_stddev(values: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    with localcontext(_DECIMAL):
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        variance = sum(
            ((value - mean) * (value - mean) for value in values),
            Decimal(0),
        ) / Decimal(len(values) - 1)
        return variance.sqrt()


def _sharpe(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    stddev = _sample_stddev(values)
    if stddev is None or stddev == 0:
        return None
    with localcontext(_DECIMAL):
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        return mean / stddev


def _sortino(values: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    with localcontext(_DECIMAL):
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        downside_variance = sum(
            (
                min(Decimal(0), value) * min(Decimal(0), value)
                for value in values
            ),
            Decimal(0),
        ) / Decimal(len(values))
        downside = downside_variance.sqrt()
        if downside == 0:
            return None
        return mean / downside


def _payoff(values: Sequence[Decimal]) -> Decimal | None:
    wins = [value for value in values if value > 0]
    losses = [-value for value in values if value < 0]
    if not wins or not losses:
        return None
    with localcontext(_DECIMAL):
        average_win = sum(wins, Decimal(0)) / Decimal(len(wins))
        average_loss = sum(losses, Decimal(0)) / Decimal(len(losses))
        return average_win / average_loss


def sequence_metrics(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    values = _values(rows)
    count = len(values)
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    total = sum(values, Decimal(0))
    expectancy = None if count == 0 else total / Decimal(count)
    return {
        "trade_count": count,
        "winner_count": len(wins),
        "loser_count": len(losses),
        "total_r": _fmt(total),
        "expectancy_r": _fmt(expectancy),
        "profit_factor": _fmt(_profit_factor(values)),
        "max_drawdown_r": _fmt(_max_drawdown(values)),
        "sharpe_trade_period": _fmt(_sharpe(values)),
        "sortino_trade_period": _fmt(_sortino(values)),
        "payoff_ratio": _fmt(_payoff(values)),
    }


def _trade_key(row: Mapping[str, object]) -> str:
    for key in ("trade_id", "episode_id", "signal_at"):
        value = row.get(key)
        if value is not None:
            return f"{key}:{value}"
    raise ValueError(
        "winner preservation requires trade_id, episode_id, or signal_at"
    )


def winner_preservation(
    baseline_rows: Sequence[Mapping[str, object]],
    managed_rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    baseline = {
        _trade_key(row): _d(row["normalized_trade_r"])
        for row in baseline_rows
    }
    managed = {
        _trade_key(row): _d(row["normalized_trade_r"])
        for row in managed_rows
    }
    baseline_winners = {
        key: value for key, value in baseline.items() if value > 0
    }
    if not baseline_winners:
        return {
            "baseline_winner_count": 0,
            "retained_winner_count": 0,
            "winner_count_preservation": None,
            "winner_r_preservation": None,
        }

    retained = {
        key: managed[key]
        for key in baseline_winners
        if key in managed and managed[key] > 0
    }
    with localcontext(_DECIMAL):
        count_rate = Decimal(len(retained)) / Decimal(len(baseline_winners))
        baseline_r = sum(baseline_winners.values(), Decimal(0))
        retained_r = sum(retained.values(), Decimal(0))
        r_rate = retained_r / baseline_r
    return {
        "baseline_winner_count": len(baseline_winners),
        "retained_winner_count": len(retained),
        "winner_count_preservation": _fmt(count_rate),
        "winner_r_preservation": _fmt(r_rate),
    }


def deterministic_block_bootstrap(
    rows: Sequence[Mapping[str, object]],
    *,
    paths: int = 10_000,
    block_length: int = 5,
) -> dict[str, object]:
    if paths < 1:
        raise ValueError("paths must be positive")
    if block_length < 1:
        raise ValueError("block_length must be positive")
    values = _values(rows)
    n = len(values)
    if n == 0:
        return {
            "paths": paths,
            "block_length": block_length,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }

    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    domain = IDENTITY.encode()
    for path_index in range(paths):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(
                values[(start + offset) % n]
                for offset in range(block_length)
            )
            block_index += 1
        selected = sampled[:n]
        terminals.append(sum(selected, Decimal(0)))
        drawdowns.append(_max_drawdown(selected))

    terminals.sort()
    drawdowns.sort()
    positive = (
        Decimal(sum(value > 0 for value in terminals))
        / Decimal(paths)
    )
    return {
        "algorithm": "sha256-moving-block-bootstrap-v1",
        "paths": paths,
        "block_length": block_length,
        "positive_terminal_probability": _fmt(positive),
        "p05_terminal_r": _fmt(terminals[(paths - 1) * 5 // 100]),
        "p50_terminal_r": _fmt(terminals[(paths - 1) * 50 // 100]),
        "p95_max_drawdown_r": _fmt(
            drawdowns[(paths - 1) * 95 // 100]
        ),
    }


def _period(row: Mapping[str, object], key: str) -> str | None:
    value = row.get(key)
    return None if value in (None, "") else str(value)


def _year(row: Mapping[str, object]) -> str | None:
    raw = row.get("local_date") or row.get("signal_at")
    if raw is None:
        return None
    text = str(raw)
    try:
        return str(datetime.fromisoformat(text).year)
    except ValueError:
        return text[:4] if len(text) >= 4 else None


def temporal_metrics(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, dict[str, object]]]:
    dimensions: dict[
        str,
        dict[str, list[Mapping[str, object]]],
    ] = {
        "year": defaultdict(list),
        "era": defaultdict(list),
        "fold": defaultdict(list),
    }
    for row in rows:
        year = _year(row)
        if year is not None:
            dimensions["year"][year].append(row)
        for key in ("era", "fold"):
            value = _period(row, key)
            if value is not None:
                dimensions[key][value].append(row)

    return {
        dimension: {
            key: sequence_metrics(group)
            for key, group in sorted(groups.items())
        }
        for dimension, groups in dimensions.items()
    }


def cost_stress_metrics(
    source_rows: Sequence[Mapping[str, object]],
    *,
    stress_levels_r: Sequence[Decimal] = DEFAULT_COST_STRESS_R,
) -> dict[str, dict[str, object]]:
    return {
        format(_d(cost), "f"): sequence_metrics(
            normalized_trade_rows(
                source_rows,
                friction_r=_d(cost),
            )
        )
        for cost in stress_levels_r
    }


def _decimal_metric(
    metrics: Mapping[str, object],
    key: str,
) -> Decimal | None:
    value = metrics.get(key)
    return None if value is None else _d(value)


def _pf_pass(
    value: Decimal | None,
    threshold: Decimal,
) -> bool:
    return True if value is None else value >= threshold


def build_edge_only_report(
    source_rows: Sequence[Mapping[str, object]],
    *,
    baseline_rows: Sequence[Mapping[str, object]] | None = None,
    friction_r: Decimal = Decimal("0"),
    monte_carlo_paths: int = 10_000,
) -> dict[str, object]:
    normalized = normalized_trade_rows(
        source_rows,
        friction_r=friction_r,
    )
    metrics = sequence_metrics(normalized)
    temporal = temporal_metrics(normalized)
    mc = deterministic_block_bootstrap(
        normalized,
        paths=monte_carlo_paths,
    )
    stress = cost_stress_metrics(source_rows)
    preservation = (
        None
        if baseline_rows is None
        else winner_preservation(
            normalized_trade_rows(
                baseline_rows,
                friction_r=friction_r,
            ),
            normalized,
        )
    )

    pf = _decimal_metric(metrics, "profit_factor")
    expectancy = _decimal_metric(metrics, "expectancy_r")
    drawdown = _decimal_metric(metrics, "max_drawdown_r")
    payoff = _decimal_metric(metrics, "payoff_ratio")
    mc_positive = _d(mc["positive_terminal_probability"])
    mc_dd = _d(mc["p95_max_drawdown_r"])
    severe_pf = _decimal_metric(stress["0.10"], "profit_factor")

    era_pfs = [
        _decimal_metric(item, "profit_factor")
        for item in temporal["era"].values()
    ]
    era_gate = (
        None
        if not era_pfs
        else all(
            _pf_pass(
                value,
                GATES["profit_factor_per_era_min"],
            )
            for value in era_pfs
        )
    )
    year_totals = [
        _decimal_metric(item, "total_r")
        for item in temporal["year"].values()
    ]
    annual_gate = (
        None
        if not year_totals
        else all(
            value is not None and value > 0
            for value in year_totals
        )
    )

    gates: dict[str, bool | None] = {
        "combined_pf": _pf_pass(
            pf,
            GATES["profit_factor_combined_min"],
        ),
        "expectancy_positive": (
            expectancy is not None
            and expectancy > GATES["expectancy_min_exclusive"]
        ),
        "drawdown_at_most_10r": (
            drawdown is not None
            and drawdown <= GATES["max_drawdown_r_target"]
        ),
        "drawdown_reject_ceiling": (
            drawdown is not None
            and drawdown <= GATES["max_drawdown_r_reject"]
        ),
        # Final certification convention is intentionally unbound here.
        # The descriptive trade-period ratios above are not silently treated
        # as annualized certification metrics.
        "sharpe": None,
        "sortino": None,
        "payoff": (
            payoff is not None
            and payoff >= GATES["payoff_min"]
        ),
        "mc_positive_terminal": (
            mc_positive >= GATES["mc_positive_terminal_min"]
        ),
        "mc_p95_drawdown": (
            mc_dd <= GATES["mc_p95_drawdown_max"]
        ),
        "severe_cost_pf": (
            severe_pf is None
            or severe_pf > GATES["severe_cost_pf_min_exclusive"]
        ),
        "all_eras_pf": era_gate,
        "all_years_positive": annual_gate,
        "winner_count_preservation": None,
        "winner_r_preservation": None,
    }
    if preservation is not None:
        count_rate = preservation["winner_count_preservation"]
        r_rate = preservation["winner_r_preservation"]
        gates["winner_count_preservation"] = (
            count_rate is not None
            and _d(count_rate)
            >= GATES["winner_count_preservation_min"]
        )
        gates["winner_r_preservation"] = (
            r_rate is not None
            and _d(r_rate)
            >= GATES["winner_r_preservation_min"]
        )

    required = [
        value for value in gates.values()
        if value is not None
    ]
    return {
        "identity": IDENTITY,
        "market": "NAS100",
        "minimum_compatible_volume": format(
            MINIMUM_COMPATIBLE_VOLUME,
            "f",
        ),
        "volume_used_for_edge_metrics": False,
        "capital_fields_used_for_edge_metrics": [],
        "normalized_trade_basis": "equal-1R-structural-outcome",
        "friction_r": format(_d(friction_r), "f"),
        "metrics": metrics,
        "temporal_metrics": temporal,
        "monte_carlo": mc,
        "cost_stress": stress,
        "winner_preservation": preservation,
        "gates": gates,
        "passes_available_development_gates": (
            bool(required) and all(required)
        ),
        "risk_adjusted_metric_binding": {
            "sharpe": {
                "status": "UNBOUND_FINAL_CERTIFICATION_CONVENTION",
                "descriptive_trade_period_value": metrics[
                    "sharpe_trade_period"
                ],
                "minimum_final_gate": format(GATES["sharpe_min"], "f"),
            },
            "sortino": {
                "status": "UNBOUND_FINAL_CERTIFICATION_CONVENTION",
                "descriptive_trade_period_value": metrics[
                    "sortino_trade_period"
                ],
                "minimum_final_gate": format(GATES["sortino_min"], "f"),
            },
        },
        "risk_adjusted_certification_binding_complete": False,
        "ready_for_candidate_freeze": False,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "candidate_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
