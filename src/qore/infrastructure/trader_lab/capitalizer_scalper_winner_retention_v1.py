"""Source-ID-preserving V49-control versus V50-G research winner retention.

Both controls require the same nine V49 opportunity ledgers. This auditor uses
completed retrospective outcomes only, AFTER simulation, never for admission.
V49 and V50-G have different stop laws; positive outcomes are not assumed
equal, nor is this an ICT/TTrades author source fidelity certification.
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

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _portfolio_select,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    POLICIES,
    V50GTrade,
    _portfolio,
)

IDENTITY = "QORE_SCALPER_V49_V50G_MATCHED_WINNER_RETENTION_V1"


def _key(
    symbol: str,
    session: str,
    operating_date: str,
    entry_at: str,
    entry_price: str,
    trigger_family: str,
    h1_basis: str,
) -> tuple[str, str, str, datetime, Decimal, str, str]:
    moment = datetime.fromisoformat(entry_at)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("trade requires timezone-aware timestamp")
    return (
        symbol,
        session,
        operating_date,
        moment,
        Decimal(entry_price),
        trigger_family,
        h1_basis,
    )


def _source_table(opportunities: tuple[V49Opportunity, ...]) -> dict[
    tuple[str, str, str, datetime, Decimal, str, str], tuple[str, ...]
]:
    matches: dict[
        tuple[str, str, str, datetime, Decimal, str, str], list[str]
    ] = defaultdict(list)
    for source in opportunities:
        matches[_key(
            source.symbol,
            source.session,
            source.operating_date,
            source.m1_trigger_confirmed_at,
            source.decision_reference_price,
            source.m1_trigger_family,
            source.h1_state_basis,
        )].append(source_id(source))
    return {key: tuple(value) for key, value in matches.items()}


def _origin(
    trade: V49EconomicTrade | V50GTrade,
    source_table: dict[
        tuple[str, str, str, datetime, Decimal, str, str], tuple[str, ...]
    ],
) -> str:
    basis = (
        trade.h1_state_basis
        if isinstance(trade, V49EconomicTrade)
        else trade.h1_basis
    )
    key = _key(
        trade.symbol, trade.session, trade.operating_date,
        trade.entry_at, trade.entry_price, trade.trigger_family, basis,
    )
    candidates = source_table.get(key, ())
    if len(candidates) != 1:
        raise ValueError("missing or ambiguous V49 trade-source parent")
    return candidates[0]


def _selected_r_by_source(
    selected: tuple[V49EconomicTrade, ...] | tuple[V50GTrade, ...],
    sources: dict[
        tuple[str, str, str, datetime, Decimal, str, str], tuple[str, ...]
    ],
) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for trade in selected:
        identifier = _origin(trade, sources)
        if identifier in out:
            raise ValueError("source ID executed twice in one selected portfolio")
        out[identifier] = Decimal(trade.realized_gross_r)
    return out


def compare_winner_mass(
    baseline: dict[str, Decimal],
    candidate: dict[str, Decimal],
) -> dict[str, Any]:
    """Count survivors of positive baseline trades, never outcome-aware select."""

    original = {key: value for key, value in baseline.items() if value > 0}
    new = {key: value for key, value in candidate.items() if value > 0}
    common = set(original) & set(new)
    original_r = sum(original.values(), Decimal(0))
    retained_original_r = sum((original[key] for key in common), Decimal(0))
    realized_candidate_r_for_same_winners = sum(
        (new[key] for key in common), Decimal(0)
    )
    if original:
        count_fraction = Decimal(len(common)) / Decimal(len(original))
        original_r_fraction = retained_original_r / original_r
        candidate_r_fraction = realized_candidate_r_for_same_winners / original_r
    else:
        count_fraction = None
        original_r_fraction = None
        candidate_r_fraction = None
    return {
        "baseline_selected": len(baseline),
        "candidate_selected": len(candidate),
        "baseline_positive_winners": len(original),
        "candidate_positive_winners": len(new),
        "baseline_winner_r": str(original_r),
        "retained_baseline_winning_source_ids": len(common),
        "preserved_original_winner_r": str(retained_original_r),
        "realized_candidate_r_on_same_winning_ids": str(
            realized_candidate_r_for_same_winners
        ),
        "winner_count_preservation_ratio": (
            str(count_fraction) if count_fraction is not None else None
        ),
        "original_winner_mass_preservation_ratio": (
            str(original_r_fraction) if original_r_fraction is not None else None
        ),
        "candidate_realized_winner_mass_ratio": (
            str(candidate_r_fraction) if candidate_r_fraction is not None else None
        ),
        "passes_80pct_winner_count": (
            count_fraction >= Decimal("0.80") if count_fraction is not None else False
        ),
        "passes_90pct_winner_mass": (
            original_r_fraction >= Decimal("0.90")
            if original_r_fraction is not None else False
        ),
        "new_candidate_winner_ids_not_in_baseline_selected": len(
            set(new) - set(baseline)
        ),
        "positive_baseline_ids_lost_or_negative": sorted(set(original) - common),
        "no_selection_or_admission_changed": True,
        "all_outcomes_retrospective_only": True,
    }


def _load_sources(root: Path, count: int) -> dict[str, tuple[V49Opportunity, ...]]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != count:
        raise ValueError("wrong V49 source market coverage")
    result: dict[str, tuple[V49Opportunity, ...]] = {}
    for path in paths:
        rows = tuple(V49Opportunity(**row) for row in _jsonl(path))
        if not rows or any(row.symbol != rows[0].symbol for row in rows):
            raise ValueError("V49 source market is empty or mixed")
        symbol = rows[0].symbol
        if symbol in result:
            raise ValueError("duplicated V49 market source")
        if path.name != f"capitalizer-{symbol.lower()}-v49-hf-capacity-opportunities.jsonl":
            raise ValueError("V49 file market mismatch")
        result[symbol] = rows
    return result


def _load_trades(
    root: Path,
    pattern: str,
    expected_markets: set[str],
    cls: type[V49EconomicTrade] | type[V50GTrade],
) -> tuple[V49EconomicTrade, ...] | tuple[V50GTrade, ...]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != len(expected_markets):
        raise ValueError("missing/duplicate economic ledgers")
    seen: set[str] = set()
    parsed: list[V49EconomicTrade | V50GTrade] = []
    for path in paths:
        name = path.name
        found = (
            [symbol for symbol in expected_markets if name.startswith(
                f"capitalizer-{symbol.lower()}-"
            )]
        )
        if len(found) != 1 or found[0] in seen:
            raise ValueError("repeated or foreign economic market")
        seen.add(found[0])
        rows = [cls(**row) for row in _jsonl(path)]
        if any(item.symbol != found[0] for item in rows):
            raise ValueError("trade market disagrees with ledger")
        parsed.extend(rows)
    if seen != expected_markets:
        raise ValueError("economic ledger market coverage mismatch")
    return tuple(parsed)  # type: ignore[return-value]


def build_retention(
    v49_control_root: Path,
    v50_g_root: Path,
    *,
    expected_markets: int = 9,
) -> dict[str, Any]:
    """Verify identical source universe before comparing economic survivorship."""

    source_v49 = _load_sources(v49_control_root, expected_markets)
    source_v50 = _load_sources(v50_g_root, expected_markets)
    if set(source_v49) != set(source_v50):
        raise ValueError("control/treatment market coverage mismatch")
    for symbol in source_v49:
        rows_left = sorted(
            (asdict(row) for row in source_v49[symbol]),
            key=lambda row: json.dumps(row, sort_keys=True),
        )
        rows_right = sorted(
            (asdict(row) for row in source_v50[symbol]),
            key=lambda row: json.dumps(row, sort_keys=True),
        )
        if rows_left != rows_right:
            raise ValueError("control and treatment V49 source opportunities differ")
    source_items = tuple(
        item for symbol in sorted(source_v49) for item in source_v49[symbol]
    )
    source_table = _source_table(source_items)
    ids = tuple(source_id(item) for item in source_items)
    if len(set(ids)) != len(ids):
        raise ValueError("ambiguous source identities")
    control_trades = _load_trades(
        v49_control_root,
        "capitalizer-*-v49-development-economics-trades.jsonl",
        set(source_v49),
        V49EconomicTrade,
    )
    treatment_trades = _load_trades(
        v50_g_root, "capitalizer-*-v50-g-trades.jsonl",
        set(source_v50), V50GTrade,
    )
    # Runtime type is guaranteed by the explicit dataclass parser above.
    frozen = _portfolio_select(control_trades)  # type: ignore[arg-type]
    control = _selected_r_by_source(
        tuple(trade for _, trade in frozen), source_table,
    )
    result: dict[str, Any] = {}
    for policy in POLICIES:
        candidate = _selected_r_by_source(
            _portfolio(treatment_trades, policy=policy), source_table,  # type: ignore[arg-type]
        )
        result[policy] = compare_winner_mass(control, candidate)
    return {
        "identity": IDENTITY,
        "market_count": expected_markets,
        "source_opportunities": len(source_items),
        "same_source_universe_confirmed": True,
        "frozen_v49_selected_trades": len(control),
        "policies": result,
        "gross_r_only_no_bid_ask_or_commission": True,
        "source_gates_unmodified": True,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v49_control_root", type=Path)
    parser.add_argument("v50_g_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_retention(args.v49_control_root, args.v50_g_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "scalper-v49-v50g-matched-winner-retention.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
