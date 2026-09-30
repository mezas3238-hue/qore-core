"""V52 winner-preserving admission-filter falsification lab.

This lab uses the already-built V50 decision-time feature atlas plus the frozen V49 development
economic ledgers. It tests whether any ONE categorical, decision-time admission block can repair
V49 economics while respecting winner-preservation.

The current/future outcome is never part of selection. Outcomes are labels used only after each
counterfactual chronological MAX3 replay is complete.

This is diagnostic/falsification research. It cannot promote a runtime policy.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_feature_atlas import (
    V50CognitiveFeatureRow,
)

IDENTITY = "QORE_CAPITALIZER_V52_WINNER_PRESERVING_FILTER_FALSIFICATION"

FEATURE_FIELDS = (
    "h1_freshness",
    "execution_freshness",
    "session_runway",
    "stop_noise_state",
    "destination_state",
    "structural_disposition",
    "trigger_family",
)

WINNER_COUNT_PRESERVATION_MIN = Decimal("0.80")
WINNER_R_PRESERVATION_MIN = Decimal("0.90")
PF_EXISTENCE_MIN_EXCLUSIVE = Decimal("1")
EXPECTANCY_MIN_EXCLUSIVE = Decimal("0")


def _load_atlas(root: Path) -> dict[tuple[str, str], V50CognitiveFeatureRow]:
    paths = sorted(root.rglob("capitalizer-*-v50-cognitive-feature-atlas-rows.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V52 requires nine feature-atlas ledgers, got {len(paths)}")
    rows: dict[tuple[str, str], V50CognitiveFeatureRow] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = V50CognitiveFeatureRow(**json.loads(line))
                key = (row.symbol, row.entry_at)
                if key in rows:
                    raise ValueError("duplicate V52 atlas key")
                rows[key] = row
    return rows


def _load_trades(root: Path) -> tuple[V49EconomicTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V52 requires nine V49 economic ledgers, got {len(paths)}")
    rows: list[V49EconomicTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V49EconomicTrade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
                item.trigger_family,
            ),
        )
    )


def _feature_value(row: V50CognitiveFeatureRow, field: str) -> str:
    value = getattr(row, field)
    return str(value)


def _portfolio(
    trades: tuple[V49EconomicTrade, ...],
    atlas: dict[tuple[str, str], V50CognitiveFeatureRow],
    *,
    blocked_field: str | None = None,
    blocked_value: str | None = None,
) -> tuple[V49EconomicTrade, ...]:
    grouped: dict[tuple[str, str], list[V49EconomicTrade]] = defaultdict(list)
    for trade in trades:
        row = atlas[(trade.symbol, trade.entry_at)]
        if (
            blocked_field is not None
            and blocked_value is not None
            and _feature_value(row, blocked_field) == blocked_value
        ):
            continue
        grouped[(trade.session, trade.operating_date)].append(trade)

    selected: list[V49EconomicTrade] = []
    for key in sorted(grouped):
        candidates = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
                item.trigger_family,
            ),
        )
        selected.extend(candidates[:3])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _key(item: V49EconomicTrade) -> tuple[str, str, str, str, str]:
    return (
        item.session,
        item.operating_date,
        item.symbol,
        item.entry_at,
        item.trigger_family,
    )


def _preservation(
    baseline: tuple[V49EconomicTrade, ...],
    candidate: tuple[V49EconomicTrade, ...],
) -> dict[str, Any]:
    baseline_keys = {_key(item) for item in baseline}
    candidate_keys = {_key(item) for item in candidate}

    winners = tuple(
        item for item in baseline if Decimal(item.realized_gross_r) > 0
    )
    losses = tuple(
        item for item in baseline if Decimal(item.realized_gross_r) < 0
    )
    full_stops = tuple(item for item in baseline if item.exit_reason == "STOP")

    preserved_winners = tuple(item for item in winners if _key(item) in candidate_keys)
    preserved_losses = tuple(item for item in losses if _key(item) in candidate_keys)
    preserved_stops = tuple(item for item in full_stops if _key(item) in candidate_keys)

    winner_r = sum(
        (Decimal(item.realized_gross_r) for item in winners),
        Decimal("0"),
    )
    preserved_winner_r = sum(
        (Decimal(item.realized_gross_r) for item in preserved_winners),
        Decimal("0"),
    )

    return {
        "density_retention": str(Decimal(len(candidate)) / Decimal(len(baseline))),
        "winner_count_preservation": str(
            Decimal(len(preserved_winners)) / Decimal(len(winners))
        ),
        "winner_r_preservation": str(preserved_winner_r / winner_r),
        "loss_recall": str(
            Decimal(len(losses) - len(preserved_losses)) / Decimal(len(losses))
        ),
        "full_stop_recall": str(
            Decimal(len(full_stops) - len(preserved_stops))
            / Decimal(len(full_stops))
        ),
        "new_recompetition_entries": sum(
            _key(item) not in baseline_keys for item in candidate
        ),
    }


def _metrics_dict(rows: tuple[V49EconomicTrade, ...]) -> dict[str, Any]:
    return asdict(_metrics(rows))


def build_report(
    *,
    atlas_root: Path,
    economic_root: Path,
) -> dict[str, Any]:
    atlas = _load_atlas(atlas_root)
    trades = _load_trades(economic_root)
    if len(atlas) != len(trades):
        raise ValueError("V52 atlas/economic population mismatch")

    baseline = _portfolio(trades, atlas)
    baseline_metrics = _metrics_dict(baseline)

    policies: list[dict[str, Any]] = []
    for field in FEATURE_FIELDS:
        values = sorted({_feature_value(row, field) for row in atlas.values()})
        for value in values:
            candidate = _portfolio(
                trades,
                atlas,
                blocked_field=field,
                blocked_value=value,
            )
            metrics = _metrics_dict(candidate)
            preservation = _preservation(baseline, candidate)

            pf = (
                None
                if metrics["profit_factor"] is None
                else Decimal(metrics["profit_factor"])
            )
            expectancy = Decimal(metrics["expectancy_r"])
            winner_count = Decimal(preservation["winner_count_preservation"])
            winner_r = Decimal(preservation["winner_r_preservation"])

            preservation_pass = (
                winner_count >= WINNER_COUNT_PRESERVATION_MIN
                and winner_r >= WINNER_R_PRESERVATION_MIN
            )
            edge_exists = (
                pf is not None
                and pf > PF_EXISTENCE_MIN_EXCLUSIVE
                and expectancy > EXPECTANCY_MIN_EXCLUSIVE
            )
            policies.append(
                {
                    "blocked_field": field,
                    "blocked_value": value,
                    "metrics": metrics,
                    "preservation": preservation,
                    "winner_preservation_pass": preservation_pass,
                    "gross_edge_exists": edge_exists,
                    "candidate_for_promotion": False,
                }
            )

    preservation_survivors = tuple(
        row for row in policies if row["winner_preservation_pass"]
    )
    edge_survivors = tuple(
        row
        for row in preservation_survivors
        if row["gross_edge_exists"]
    )

    return {
        "identity": IDENTITY,
        "baseline": baseline_metrics,
        "raw_source_opportunities": len(trades),
        "baseline_max3_trades": len(baseline),
        "feature_fields": list(FEATURE_FIELDS),
        "policies_tested": len(policies),
        "winner_preservation_survivors": len(preservation_survivors),
        "winner_preservation_plus_edge_survivors": len(edge_survivors),
        "policies": policies,
        "decision_features_known_at_entry": True,
        "current_outcome_visible_to_selection": False,
        "future_outcome_visible_to_selection": False,
        "chronological_max3_recompetition": True,
        "symbol_or_session_identity_used_as_block_feature": False,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("atlas_root", type=Path)
    parser.add_argument("economic_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report = build_report(
        atlas_root=args.atlas_root,
        economic_root=args.economic_root,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v52-winner-preserving-filter-falsification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
