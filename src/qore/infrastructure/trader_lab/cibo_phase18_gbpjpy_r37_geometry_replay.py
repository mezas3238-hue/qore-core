"""CIBO Phase 18 GBPJPY exact geometry replay.

Derived from the frozen R37 validation implementation at
eb62226e05f63cf94c1940634de676c55285e6dd.  The execution algorithm is
preserved; this research-only variant serializes the causal geometry that the
historical R37 ledger omitted.  It never authorizes broker mutation.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r26_specialist_memory_brain as r26,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r34_coarse_causal_memory as r34,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r35_confidence_tier_ensemble as r35,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_specialist_cognitive_memory_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "CIBO_PHASE18_GBPJPY_R37_GEOMETRY_REPLAY_V1"
SOURCE_R37_IDENTITY = "TURTLE_SOUP_GBPJPY_R37_FROZEN_R36_5Y_VALIDATION_V1"
CANDIDATE_IDENTITY = "TURTLE_SOUP_GBPJPY_R36_CONFIDENCE_CANDIDATE_001"

EVAL_OPEN = datetime(2021, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

FROZEN_ENSEMBLE = "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
FROZEN_POLICY = "CONFIDENCE_100_050_010"
FROZEN_LAYERS = r35.ENSEMBLES[FROZEN_ENSEMBLE]

MIN_TRADES = 800
MIN_PF_010 = Decimal("1.50")
MAX_DD_010 = Decimal("6.0")
REQUIRED_POSITIVE_ANNUAL_BLOCKS = 5


@dataclass(frozen=True, slots=True)
class ScaledTrade:
    signal_at: str
    entry_at: str
    entry_price: str
    structural_stop: str
    technical_target: str
    exit_at: str
    side: str
    posture: str
    source_scheme: str
    authority_tier: str
    validation_class: str
    target_rank: int
    target_route: str
    exit_reason: str
    raw_net_010_r: str
    risk_scale: str
    scaled_net_010_r: str
    setup_context: dict[str, Any]
    regime: dict[str, str]


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_json(root: Path, name: str) -> dict[str, Any]:
    payload = json.loads(_single(root, name).read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be an object")
    return payload


def _verify_freeze(root: Path) -> dict[str, Any]:
    freeze = _load_json(root, "r36-candidate-freeze-manifest.json")
    if freeze["identity"] != CANDIDATE_IDENTITY:
        raise ValueError("candidate identity drift")
    if freeze["status"] != "FROZEN_FOR_5Y_VALIDATION":
        raise ValueError("candidate is not frozen for 5Y")

    contract = freeze["frozen_contract"]
    if contract["ensemble"] != FROZEN_ENSEMBLE:
        raise ValueError("ensemble drift")
    expected_layers = [
        {
            "scheme": scheme,
            "allowed_validation_classes": list(classes),
        }
        for scheme, classes in FROZEN_LAYERS
    ]
    if contract["layers"] != expected_layers:
        raise ValueError("authority-layer drift")
    if contract["risk_policy"] != FROZEN_POLICY:
        raise ValueError("risk-policy drift")

    expected_policy = r35.RISK_POLICIES[FROZEN_POLICY]
    params = contract["risk_policy_parameters"]
    if (
        str(params["core_scale"]) != str(expected_policy[0])
        or str(params["robust_expansion_scale"]) != str(expected_policy[1])
        or str(params["majority_expansion_scale"]) != str(expected_policy[2])
    ):
        raise ValueError("risk-policy parameter drift")

    required_true = (
        "r34_range_core_preserved",
        "expansion_only_when_higher_authority_layer_abstains",
        "actual_active_cibo_dol_price_used",
        "nearest_validated_dol_within_each_layer",
        "single_position_busy",
        "structural_rearm",
        "risk_governor_pretrade_memory_only",
    )
    if any(contract[key] is not True for key in required_true):
        raise ValueError("frozen structural contract drift")
    if contract["risk_governor_suppresses_trades"] is not False:
        raise ValueError("risk suppression drift")
    if contract["entry"] != "NEXT_SOURCE_OPEN":
        raise ValueError("entry drift")
    if contract["c2"] != "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE":
        raise ValueError("C2 drift")
    if contract["cisd"] != "CAUSAL":
        raise ValueError("CISD drift")
    if contract["stop"] != "EXACT_PROTECTED_SWING_NEVER_WIDEN":
        raise ValueError("stop drift")
    if freeze["next_stage"]["fresh_holdout_status"] != "SEALED_UNTOUCHED":
        raise ValueError("fresh holdout drift")
    if freeze["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout consumption drift")
    return freeze


def _raw_pf(values: Sequence[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _block_stats(rows: Sequence[ScaledTrade]) -> dict[str, Any]:
    values = [Decimal(row.scaled_net_010_r) for row in rows]
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    losing = 0
    max_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        else:
            losing = 0
    pf = _raw_pf(values)
    return {
        "trades": len(rows),
        "total_scaled_net_010_r": str(equity),
        "mean_scaled_net_010_r": (
            None if not rows else str(equity / Decimal(len(rows)))
        ),
        "profit_factor_scaled_net_010": None if pf is None else str(pf),
        "max_drawdown_within_block_r": str(max_dd),
        "max_losing_streak": max_losing,
        "positive_total": equity > 0,
    }


def _annual_blocks(rows: Sequence[ScaledTrade]) -> list[dict[str, Any]]:
    boundaries = [
        datetime(2021, 9, 17, tzinfo=UTC),
        datetime(2022, 9, 17, tzinfo=UTC),
        datetime(2023, 9, 17, tzinfo=UTC),
        datetime(2024, 9, 17, tzinfo=UTC),
        datetime(2025, 9, 17, tzinfo=UTC),
        datetime(2026, 9, 17, tzinfo=UTC),
    ]
    result: list[dict[str, Any]] = []
    for start, end in zip(boundaries[:-1], boundaries[1:], strict=True):
        members = [
            row
            for row in rows
            if start <= datetime.fromisoformat(row.entry_at) < end
        ]
        result.append(
            {
                "open": start.isoformat(),
                "close": end.isoformat(),
                **_block_stats(members),
            }
        )
    return result


def _group_stats(
    rows: Sequence[ScaledTrade],
    field: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[ScaledTrade]] = defaultdict(list)
    for row in rows:
        grouped[str(getattr(row, field))].append(row)
    return {
        key: _block_stats(members)
        for key, members in sorted(grouped.items())
    }


def run(
    raw_root: Path,
    target_root: Path,
    v2_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, Any]:
    freeze = _verify_freeze(freeze_root)
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "GBPJPY" or int(provenance["retained_bars"]) != 745478:
        raise ValueError("unexpected GBPJPY corpus")

    observations = r34._load_observations(v2_root)
    memories: dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            dict[tuple[str, str], r34.Profile],
            dict[str, Any],
        ],
    ] = {}
    for scheme, (fields, route_mode) in r34.SCHEMES.items():
        memory, summary = r34._build_memory(
            observations,
            fields=fields,
            route_mode=route_mode,
        )
        memories[scheme] = (fields, route_mode, memory, summary)

    target_rows = r26._load_targets(target_root)
    _episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    tick = Decimal(1).scaleb(-evidence.digits)
    h4 = build_h4(evidence.bars)
    frames: dict[str, tuple[SourceCandle, ...]] = {
        "H1": build_h1(evidence.bars),
        "H4": h4,
        "D1": build_daily(h4),
    }
    frame_closes = {
        timeframe: tuple(candle.closed_at for candle in candles)
        for timeframe, candles in frames.items()
    }

    busy_until = EVAL_OPEN
    trailing_exit_at: datetime | None = None
    rows: list[ScaledTrade] = []
    counts: Counter[str] = Counter()

    for setup in setups:
        signal = setup.context.signal
        if not (EVAL_OPEN <= signal.entry_at < EVAL_CLOSE):
            continue
        if not r26._structurally_rearmed(setup, trailing_exit_at):
            counts["ABSTAIN_NOT_STRUCTURALLY_REARMED"] += 1
            continue

        episode_id = source_index.get(
            (
                signal.cisd_at,
                signal.side.value,
                setup.context.timeframe,
                signal.target,
            )
        )
        if episode_id is None:
            counts["ABSTAIN_NO_CIBO_EPISODE"] += 1
            continue

        fill = r3._entry(setup, evidence, opens, "NEXT_SOURCE_OPEN")
        if fill is None:
            counts["ABSTAIN_NO_ENTRY"] += 1
            continue
        entry_at, entry = fill

        ladder = v1._active_ladder(
            target_rows.get(episode_id, ()),
            at=entry_at,
            side=signal.side,
            entry=entry,
            tick=tick,
        )
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL"] += 1
            continue

        regime = v2._regime_context(
            row={
                "strategy_entry_at": entry_at.isoformat(),
                "side": signal.side.value,
            },
            bars=evidence.bars,
            opens=opens,
            frames=frames,
            frame_closes=frame_closes,
        )
        decision = r35._choose(
            setup=setup,
            ladder=ladder,
            regime=regime,
            layers=FROZEN_LAYERS,
            memories=memories,
        )
        if decision is None:
            counts["ABSTAIN_NO_FROZEN_AUTHORITY"] += 1
            continue

        runtime = r26._simulate(
            setup,
            decision=r35._runtime_decision(decision),
            ladder=ladder,
            entry_at=entry_at,
            entry=entry,
            evidence=evidence,
            opens=opens,
        )
        if runtime is None:
            counts["ABSTAIN_INVALID_GEOMETRY"] += 1
            continue
        if runtime.entry_at < busy_until:
            counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            continue

        busy_until = runtime.exit_at
        if "TRAIL" in runtime.exit_reason:
            trailing_exit_at = runtime.exit_at

        scale = r35._risk_scale(decision, FROZEN_POLICY)
        scaled = runtime.net_010_r * scale
        setup_context = v1._setup_context(setup)
        rows.append(
            ScaledTrade(
                signal_at=signal.cisd_at.isoformat(),
                entry_at=runtime.entry_at.isoformat(),
                entry_price=str(entry),
                structural_stop=str(signal.protected_swing),
                technical_target=str(decision.target.level),
                exit_at=runtime.exit_at.isoformat(),
                side=runtime.side,
                posture=runtime.posture,
                source_scheme=decision.source_scheme,
                authority_tier=decision.authority_tier,
                validation_class=decision.classification,
                target_rank=runtime.target_rank,
                target_route=runtime.target_route,
                exit_reason=runtime.exit_reason,
                raw_net_010_r=str(runtime.net_010_r),
                risk_scale=str(scale),
                scaled_net_010_r=str(scaled),
                setup_context=setup_context,
                regime=regime,
            )
        )
        counts["EXECUTE"] += 1
        counts[f"SOURCE_{decision.source_scheme}"] += 1
        counts[f"TIER_{decision.authority_tier}"] += 1
        counts[f"CLASS_{decision.classification}"] += 1
        counts[f"SCALE_{scale}"] += 1

    overall = _block_stats(rows)
    annual = _annual_blocks(rows)
    positive_annual = sum(bool(item["positive_total"]) for item in annual)
    pf_raw = overall["profit_factor_scaled_net_010"]
    pf = None if pf_raw is None else Decimal(str(pf_raw))
    dd = Decimal(str(overall["max_drawdown_within_block_r"]))
    total = Decimal(str(overall["total_scaled_net_010_r"]))

    pass_gate = bool(
        len(rows) >= MIN_TRADES
        and pf is not None
        and pf >= MIN_PF_010
        and dd <= MAX_DD_010
        and total > 0
        and positive_annual == REQUIRED_POSITIVE_ANNUAL_BLOCKS
    )

    output.mkdir(parents=True, exist_ok=True)
    with (output / "phase18-gbpjpy-r37-geometry-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase18.gbpjpy_r37_geometry_replay.v1",
        "identity": IDENTITY,
        "candidate": {
            "identity": freeze["identity"],
            "freeze_status": freeze["status"],
            "ensemble": FROZEN_ENSEMBLE,
            "layers": freeze["frozen_contract"]["layers"],
            "risk_policy": FROZEN_POLICY,
            "risk_policy_parameters": freeze["frozen_contract"][
                "risk_policy_parameters"
            ],
        },
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "years": 5,
            "fresh_holdout": False,
            "historical_status": "CONSUMED_ROBUSTNESS_VALIDATION",
        },
        "frozen_contract_verification": {
            "entry_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "protected_swing_changed": False,
            "authority_layers_changed": False,
            "risk_policy_changed": False,
            "single_position_busy_changed": False,
            "structural_rearm_changed": False,
            "fresh_holdout_consumed": False,
        },
        "predeclared_acceptance": {
            "minimum_trades": MIN_TRADES,
            "minimum_scaled_net_010_profit_factor": str(MIN_PF_010),
            "maximum_scaled_net_010_drawdown_r": str(MAX_DD_010),
            "total_scaled_net_010_must_be_positive": True,
            "required_positive_annual_blocks": REQUIRED_POSITIVE_ANNUAL_BLOCKS,
        },
        "result": {
            **overall,
            "positive_annual_blocks": positive_annual,
            "annual_blocks": annual,
            "decision_counts": dict(counts),
            "acceptance_pass": pass_gate,
        },
        "diagnostics": {
            "by_source_scheme": _group_stats(rows, "source_scheme"),
            "by_authority_tier": _group_stats(rows, "authority_tier"),
            "by_validation_class": _group_stats(rows, "validation_class"),
            "by_side": _group_stats(rows, "side"),
            "by_target_rank": _group_stats(rows, "target_rank"),
            "by_target_route": _group_stats(rows, "target_route"),
            "by_risk_scale": _group_stats(rows, "risk_scale"),
        },
        "phase18_geometry": {
            "source_r37_identity": SOURCE_R37_IDENTITY,
            "source_r37_git_sha": "eb62226e05f63cf94c1940634de676c55285e6dd",
            "geometry_serialized": True,
            "signal_at_basis": "CAUSAL_CISD_CONFIRMED_AT",
            "entry_price_basis": "NEXT_SOURCE_OPEN",
            "structural_stop_basis": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "technical_target_basis": "ACTIVE_CIBO_DOL_DECISION_TARGET",
            "provider_economics_status": "CALIBRATION_REQUIRED",
            "broker_mutation_authorized": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "observations": len(observations),
            "setups_10y": len(setups),
            "funnel": funnel,
        },
        "governance": {
            "candidate_rules_frozen": True,
            "5y_validation_consumed": True,
            "fresh_holdout_consumed": False,
            "candidate_certified": False,
            "trader_certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    (output / "phase18-gbpjpy-r37-geometry-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: module RAW_ROOT TARGET_ROOT COGNITIVE_V2_ROOT "
            "FREEZE_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
                Path(sys.argv[5]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
