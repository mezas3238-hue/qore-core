"""QORE execution-translation falsification around frozen VT31 Silver Bullet.

Silver Bullet source is immutable in this lab.

The source contract explicitly leaves exact breaker/OB/FVG prices and family
priority unresolved.  QORE's Vt31R22ExecutionPolicy translates those unresolved
zones into executable prices with source_rule=False.  This lab falsifies a
small predeclared neighborhood of those QORE-only choices without changing:
- 09:00-10:00 NY reference;
- 10:00-11:00 source window;
- raid / structural confirmation;
- source stop;
- opposite-reference target;
- 3R -> breakeven management;
- one setup per source event.

It is a falsification lab, not policy selection or promotion.

The lab also measures whether observed losing streaks are exceptional temporal
clustering or are statistically expected from the observed binary loss rate.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_r1_candidate as baseline
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22EntryFamily,
    Vt31R22ExecutableSetup,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
)

SCHEMA = "qore.vt31.nas100.execution_translation_falsification.v1"
IDENTITY = "VT31_NAS100_EXECUTION_TRANSLATION_FALSIFICATION_V1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
NULL_PATHS = 20000
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"

PRICE_DEPTHS: dict[str, Decimal] = {
    "PROXIMAL": Decimal("0"),
    "MIDPOINT": Decimal("0.5"),
    "DISTAL": Decimal("1"),
}
FAMILY_MODES: dict[str, Vt31R22EntryFamily | None] = {
    "ANY": None,
    "BREAKER_ONLY": Vt31R22EntryFamily.BREAKER,
    "FVG_ONLY": Vt31R22EntryFamily.FAIR_VALUE_GAP,
    "ORDER_BLOCK_ONLY": Vt31R22EntryFamily.ORDER_BLOCK,
}
VARIANTS = tuple(
    f"{family}_{depth}"
    for family in FAMILY_MODES
    for depth in PRICE_DEPTHS
)
CURRENT_VARIANT = "ANY_MIDPOINT"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _variant_fingerprint(name: str) -> str:
    return hashlib.sha256(
        f"{IDENTITY}:{name}".encode()
    ).hexdigest()


def _zone_price(
    candidate: Vt31R22EntryEvidence,
    *,
    side: DemoTradingSetupSide,
    depth: Decimal,
) -> Decimal:
    lower = candidate.zone_lower
    upper = candidate.zone_upper
    width = upper - lower
    if side is DemoTradingSetupSide.SHORT:
        # A bearish retracement first reaches the lower / proximal zone edge.
        return lower + width * depth
    # A bullish retracement first reaches the upper / proximal zone edge.
    return upper - width * depth


def _make_research_setup(
    source: Vt31R22SourceSetup,
    *,
    family: Vt31R22EntryFamily | None,
    depth: Decimal,
    variant: str,
) -> Vt31R22ExecutableSetup | None:
    candidates = (
        tuple(item for item in source.candidates if item.family is family)
        if family is not None
        else source.candidates
    )
    if not candidates:
        return None

    earliest = min(item.formed_at for item in candidates)
    contemporaneous = tuple(
        item for item in candidates if item.formed_at == earliest
    )
    prices = tuple(
        _zone_price(item, side=source.side, depth=depth)
        for item in contemporaneous
    )
    if len(set(prices)) != 1:
        # Preserve the current policy's fail-closed confluence ambiguity.
        return None

    chosen = sorted(
        contemporaneous,
        key=lambda item: item.family.value,
    )[0]
    entry = prices[0]
    stop = source.structure.swing_extreme
    target = source.target_price

    if source.side is DemoTradingSetupSide.SHORT:
        valid = target < entry < stop
        three_r = entry - (stop - entry) * Decimal(3)
    else:
        valid = stop < entry < target
        three_r = entry + (entry - stop) * Decimal(3)
    if not valid:
        return None

    return Vt31R22ExecutableSetup(
        side=source.side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        three_r_price=three_r,
        selected_family=chosen.family,
        candidate_families=tuple(
            item.family for item in contemporaneous
        ),
        decision_at=earliest,
        pending_expires_at=source.pending_expires_at,
        source_setup=source,
        execution_policy_fingerprint=_variant_fingerprint(variant),
    )


def _scan_variant(
    *,
    reference: tuple[object, ...],
    session: tuple[object, ...],
    evidence: str,
    family: Vt31R22EntryFamily | None,
    depth: Decimal,
    variant: str,
) -> tuple[Vt31R22SourceSetup, Vt31R22ExecutableSetup] | None:
    prefix: list[object] = list(reference)
    for bar in session:
        prefix.append(bar)
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=getattr(bar, "closed_at"),
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if evaluation.both_sides_swept:
                return None
            continue

        source = evaluation.setup
        setup = _make_research_setup(
            source,
            family=family,
            depth=depth,
            variant=variant,
        )
        if setup is not None:
            return source, setup

        if family is None:
            # Current ANY policy fails closed at the first actionable source
            # if QORE cannot build one unambiguous executable setup.
            return None

    return None


def _max_loss_streak(rows: list[dict[str, object]]) -> int:
    current = 0
    maximum = 0
    for row in rows:
        if _d(row["net_r_after_friction"]) < 0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _max_run_binary(labels: list[bool]) -> int:
    current = 0
    maximum = 0
    for is_loss in labels:
        if is_loss:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _null_model(
    rows: list[dict[str, object]],
    *,
    partition: str,
) -> dict[str, object]:
    labels = [
        _d(row["net_r_after_friction"]) < 0
        for row in rows
    ]
    n = len(labels)
    if not labels:
        return {
            "paths": NULL_PATHS,
            "trade_count": 0,
            "loss_count": 0,
            "loss_rate": "0",
            "observed_max_losing_streak": 0,
            "p50_shuffled_max_losing_streak": 0,
            "p95_shuffled_max_losing_streak": 0,
            "tail_probability_shuffled_ge_observed": "0",
        }

    observed = _max_run_binary(labels)
    distribution: list[int] = []
    domain = f"{IDENTITY}:{partition}:streak-null".encode()

    for path_index in range(NULL_PATHS):
        seed = int.from_bytes(
            hashlib.sha256(
                domain + b":" + str(path_index).encode()
            ).digest(),
            "big",
        )
        shuffled = list(labels)
        random.Random(seed).shuffle(shuffled)
        distribution.append(_max_run_binary(shuffled))

    distribution.sort()
    tail = sum(value >= observed for value in distribution)
    losses = sum(labels)
    return {
        "algorithm": "deterministic-binary-sequence-permutation-v1",
        "paths": NULL_PATHS,
        "trade_count": n,
        "loss_count": losses,
        "loss_rate": format(Decimal(losses) / Decimal(n), "f"),
        "observed_max_losing_streak": observed,
        "p50_shuffled_max_losing_streak": distribution[
            (NULL_PATHS - 1) * 50 // 100
        ],
        "p95_shuffled_max_losing_streak": distribution[
            (NULL_PATHS - 1) * 95 // 100
        ],
        "tail_probability_shuffled_ge_observed": format(
            Decimal(tail) / Decimal(NULL_PATHS),
            "f",
        ),
    }


def _prob_no_loss_run_longer_than(
    *,
    trade_count: int,
    non_loss_rate: Decimal,
    maximum_loss_run: int,
) -> Decimal:
    # Exact Bernoulli dynamic program.  This is a mathematical engineering
    # bound, not a claim that real trades are independent.
    q = Decimal(1) - non_loss_rate
    states = [Decimal(0)] * (maximum_loss_run + 1)
    states[0] = Decimal(1)

    for _ in range(trade_count):
        next_states = [Decimal(0)] * (maximum_loss_run + 1)
        next_states[0] = sum(states, Decimal(0)) * non_loss_rate
        for trailing_losses in range(maximum_loss_run):
            next_states[trailing_losses + 1] += (
                states[trailing_losses] * q
            )
        states = next_states
    return sum(states, Decimal(0))


def _required_non_loss_rate(
    *,
    trade_count: int,
    maximum_loss_run: int,
    confidence: Decimal,
) -> Decimal:
    for basis_points in range(1, 10000):
        rate = Decimal(basis_points) / Decimal(10000)
        if (
            _prob_no_loss_run_longer_than(
                trade_count=trade_count,
                non_loss_rate=rate,
                maximum_loss_run=maximum_loss_run,
            )
            >= confidence
        ):
            return rate
    return Decimal(1)


def _metrics_for(rows: list[dict[str, object]]) -> dict[str, object]:
    converted = [
        {
            **row,
            "r_multiple": row["net_r_after_friction"],
        }
        for row in rows
    ]
    return _metrics(converted, friction=Decimal(0))


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("execution-translation lab requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    rows_by_variant: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }
    status_by_variant: dict[str, Counter[str]] = {
        variant: Counter() for variant in VARIANTS
    }

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars, (9, 0, 0), (10, 0, 0)
        )
        session = specialist._slice(
            day_bars, (10, 0, 0), (11, 0, 0)
        )
        if len(reference) != 60 or len(session) != 60:
            for variant in VARIANTS:
                status_by_variant[variant]["incomplete-day"] += 1
            continue

        for family_name, family in FAMILY_MODES.items():
            for depth_name, depth in PRICE_DEPTHS.items():
                variant = f"{family_name}_{depth_name}"
                selected = _scan_variant(
                    reference=reference,
                    session=session,
                    evidence=evidence,
                    family=family,
                    depth=depth,
                    variant=variant,
                )
                if selected is None:
                    status_by_variant[variant]["no-executable-source"] += 1
                    continue
                _, setup = selected
                outcome = baseline._simulate(day_bars, setup)
                status = cast(str, outcome["status"])
                status_by_variant[variant][f"outcome-{status}"] += 1
                if status != "terminal":
                    continue
                net_r = _d(outcome["r_multiple"]) - FRICTION
                rows_by_variant[variant].append(
                    {
                        **outcome,
                        "partition": partition,
                        "variant": variant,
                        "qore_execution_translation_only": True,
                        "silver_bullet_source_modified": False,
                        "net_r_after_friction": format(net_r, "f"),
                    }
                )

    variants: dict[str, object] = {}
    for variant in VARIANTS:
        rows = sorted(
            rows_by_variant[variant],
            key=lambda row: cast(str, row["signal_at"]),
        )
        metrics = _metrics_for(rows)
        losses = sum(
            _d(row["net_r_after_friction"]) < 0 for row in rows
        )
        variants[variant] = {
            "trade_count": len(rows),
            "loss_count": losses,
            "non_loss_count": len(rows) - losses,
            "non_loss_rate": (
                "0"
                if not rows
                else format(
                    Decimal(len(rows) - losses) / Decimal(len(rows)),
                    "f",
                )
            ),
            "metrics": metrics,
            "max_losing_streak": _max_loss_streak(rows),
            "status_counts": dict(
                sorted(status_by_variant[variant].items())
            ),
        }

    current_rows = sorted(
        rows_by_variant[CURRENT_VARIANT],
        key=lambda row: cast(str, row["signal_at"]),
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "silver_bullet_freeze": {
            "source_file": silver.SOURCE_FILE,
            "source_sha256": silver.SOURCE_SHA256,
            "methodology_id": silver.METHODOLOGY_ID,
            "source_fingerprint": silver.source_fingerprint(),
            "source_module_modified_by_lab": False,
        },
        "qore_translation_space": {
            "source_rule": False,
            "price_depths": {
                key: format(value, "f")
                for key, value in PRICE_DEPTHS.items()
            },
            "family_modes": list(FAMILY_MODES),
            "stop_changed": False,
            "target_changed": False,
            "three_r_breakeven_changed": False,
        },
        "variants": variants,
        "current_translation_streak_null_model": _null_model(
            current_rows,
            partition=partition,
        ),
        "streak_engineering_bound_300_trades": {
            "maximum_loss_run": 8,
            "non_loss_rate_for_50pct_no_run_gt_8": format(
                _required_non_loss_rate(
                    trade_count=300,
                    maximum_loss_run=8,
                    confidence=Decimal("0.50"),
                ),
                "f",
            ),
            "non_loss_rate_for_90pct_no_run_gt_8": format(
                _required_non_loss_rate(
                    trade_count=300,
                    maximum_loss_run=8,
                    confidence=Decimal("0.90"),
                ),
                "f",
            ),
            "non_loss_rate_for_95pct_no_run_gt_8": format(
                _required_non_loss_rate(
                    trade_count=300,
                    maximum_loss_run=8,
                    confidence=Decimal("0.95"),
                ),
                "f",
            ),
            "assumption": (
                "independent Bernoulli bound used only as engineering target; "
                "real trade dependence is tested separately by permutation"
            ),
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "silver_bullet_modified": False,
            "silver_bullet_source_frozen": True,
            "only_source_unresolved_execution_choices_varied": True,
            "h4_used_as_primary_causal_feature": False,
            "h1_trend_used_as_primary_causal_feature": False,
            "stop_changed": False,
            "target_changed": False,
            "three_r_breakeven_changed": False,
            "consumed_evidence_only": True,
            "grid_is_falsification_not_selection": True,
            "variant_promoted": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "opens_new_holdout": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "variants": payload["variants"],
                "current_translation_streak_null_model": payload[
                    "current_translation_streak_null_model"
                ],
                "streak_engineering_bound_300_trades": payload[
                    "streak_engineering_bound_300_trades"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
