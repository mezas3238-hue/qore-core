"""R34 frozen R33 five-year historical validation.

This is a robustness extension over already-consumed historical data, not a
fresh holdout.  The R33 candidate is loaded from its immutable freeze artifact
and replayed without changing signal, destination, management, or risk rules.

Window: 2021-09-17 <= entry < 2026-09-17 UTC.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r26_specialist_memory_brain as r26,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r33_subfamily_risk_governor as r33,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_specialist_cognitive_memory_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R34_FROZEN_R33_5Y_VALIDATION_V1"
CANDIDATE_IDENTITY = (
    "TURTLE_SOUP_XAUUSD_R33_FIVE_FAMILY_RISK_GOVERNOR_CANDIDATE_001"
)
EVAL_OPEN = datetime(2021, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

FAMILY_SET = "R33_FIVE_FAMILY"
GOVERNOR = "DD_2_4_SCALE_075_025"
ALLOWED_FAMILIES = r33.FAMILY_SETS[FAMILY_SET]
GOVERNOR_RULE = r33.GOVERNORS[GOVERNOR]

MIN_TRADES = 800
MIN_PF_010 = Decimal("1.50")
MAX_DD_010 = Decimal("10.0")


@dataclass(frozen=True, slots=True)
class ScaledTrade:
    entry_at: str
    exit_at: str
    side: str
    source: str
    family: str | None
    target_rank: int
    target_route: str
    posture: str
    exit_reason: str
    raw_net_010_r: str
    pretrade_drawdown_r: str
    risk_scale: str
    scaled_net_010_r: str


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
    freeze = _load_json(root, "r33-candidate-freeze-manifest.json")
    if freeze["identity"] != CANDIDATE_IDENTITY:
        raise ValueError("R33 candidate identity drift")
    if freeze["status"] != "FROZEN_FOR_5Y_VALIDATION":
        raise ValueError("R33 is not frozen for 5Y validation")

    contract = freeze["frozen_contract"]
    if contract["family_set"] != FAMILY_SET:
        raise ValueError("family set drift")
    if tuple(contract["families"]) != tuple(ALLOWED_FAMILIES):
        raise ValueError("frozen family membership drift")
    if contract["risk_governor"] != GOVERNOR:
        raise ValueError("risk governor drift")
    expected_governor = {
        "first_drawdown_r": str(GOVERNOR_RULE[0]),
        "second_drawdown_r": str(GOVERNOR_RULE[1]),
        "middle_scale": str(GOVERNOR_RULE[2]),
        "deep_scale": str(GOVERNOR_RULE[3]),
    }
    if contract["risk_governor_parameters"] != expected_governor:
        raise ValueError("risk governor parameter drift")
    if contract["expansion_target_rank"] != 1:
        raise ValueError("expansion target-rank drift")
    if contract["actual_active_cibo_dol_price_used"] is not True:
        raise ValueError("DOL contract drift")
    if contract["entry"] != "NEXT_SOURCE_OPEN":
        raise ValueError("entry contract drift")
    if contract["c2"] != "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE":
        raise ValueError("C2 contract drift")
    if contract["cisd"] != "CAUSAL":
        raise ValueError("CISD contract drift")
    if contract["stop"] != "EXACT_PROTECTED_SWING_NEVER_WIDEN":
        raise ValueError("stop contract drift")
    if contract["expansion_posture"] != "STATIC":
        raise ValueError("expansion posture drift")
    if contract["risk_governor_suppresses_trades"] is not False:
        raise ValueError("risk governor suppression drift")
    if freeze["next_stage"]["fresh_holdout_status"] != "SEALED_UNTOUCHED":
        raise ValueError("fresh holdout is no longer sealed")
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
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    pf = _raw_pf(values)
    return {
        "trades": len(rows),
        "total_scaled_net_010_r": str(equity),
        "mean_scaled_net_010_r": (
            None if not rows else str(equity / Decimal(len(rows)))
        ),
        "profit_factor_scaled_net_010": None if pf is None else str(pf),
        "max_drawdown_within_block_r": str(max_dd),
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


def run(
    raw_root: Path,
    target_root: Path,
    cognitive_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, Any]:
    freeze = _verify_freeze(freeze_root)
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "XAUUSD" or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    cognitive = r33._load_cognitive(cognitive_root)
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
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    counts: Counter[str] = Counter()
    rows: list[ScaledTrade] = []

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
        decision = r33._choose(
            cognitive=cognitive,
            setup=setup,
            ladder=ladder,
            regime=regime,
            allowed_families=ALLOWED_FAMILIES,
        )
        if decision is None:
            counts["ABSTAIN_NO_AUTHORITY_OR_SUBFAMILY"] += 1
            continue

        runtime = r26._simulate(
            setup,
            decision=r33._runtime_decision(decision),
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

        pretrade_dd = peak - equity
        scale = r33._risk_scale(pretrade_dd, GOVERNOR_RULE)
        scaled = runtime.net_010_r * scale
        equity += scaled
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

        rows.append(
            ScaledTrade(
                entry_at=runtime.entry_at.isoformat(),
                exit_at=runtime.exit_at.isoformat(),
                side=runtime.side,
                source=decision.source,
                family=decision.family,
                target_rank=runtime.target_rank,
                target_route=runtime.target_route,
                posture=runtime.posture,
                exit_reason=runtime.exit_reason,
                raw_net_010_r=str(runtime.net_010_r),
                pretrade_drawdown_r=str(pretrade_dd),
                risk_scale=str(scale),
                scaled_net_010_r=str(scaled),
            )
        )
        counts["EXECUTE"] += 1
        counts[f"SOURCE_{decision.source}"] += 1
        if decision.family is not None:
            counts[f"FAMILY_{decision.family}"] += 1
        counts[f"SCALE_{scale}"] += 1

    values = [Decimal(row.scaled_net_010_r) for row in rows]
    pf = _raw_pf(values)
    total = sum(values, Decimal(0))
    annual = _annual_blocks(rows)
    pass_gate = bool(
        len(rows) >= MIN_TRADES
        and pf is not None
        and pf >= MIN_PF_010
        and max_dd <= MAX_DD_010
        and total > 0
    )

    output.mkdir(parents=True, exist_ok=True)
    trade_path = output / "r34-5y-scaled-trades.jsonl"
    with trade_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    report: dict[str, Any] = {
        "schema": "qore.turtle_soup_xauusd.r34_frozen_r33_5y_validation.v1",
        "identity": IDENTITY,
        "candidate": {
            "identity": freeze["identity"],
            "freeze_status": freeze["status"],
            "family_set": FAMILY_SET,
            "families": list(ALLOWED_FAMILIES),
            "risk_governor": GOVERNOR,
            "risk_governor_parameters": freeze["frozen_contract"][
                "risk_governor_parameters"
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
            "family_set_changed": False,
            "governor_changed": False,
            "fresh_holdout_consumed": False,
        },
        "predeclared_acceptance": {
            "minimum_trades": MIN_TRADES,
            "minimum_scaled_net_010_profit_factor": str(MIN_PF_010),
            "maximum_scaled_net_010_drawdown_r": str(MAX_DD_010),
            "total_scaled_net_010_must_be_positive": True,
            "annual_blocks": "REPORTED_DIAGNOSTIC",
        },
        "result": {
            "trades": len(rows),
            "total_scaled_net_010_r": str(total),
            "mean_scaled_net_010_r": (
                None if not rows else str(total / Decimal(len(rows)))
            ),
            "profit_factor_scaled_net_010": None if pf is None else str(pf),
            "max_drawdown_scaled_r": str(max_dd),
            "positive_annual_blocks": sum(
                bool(item["positive_total"]) for item in annual
            ),
            "annual_blocks": annual,
            "decision_counts": dict(counts),
            "acceptance_pass": pass_gate,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups_10y": len(setups),
            "funnel": funnel,
        },
        "governance": {
            "candidate_rules_frozen": True,
            "5y_validation_consumed": True,
            "fresh_holdout_consumed": False,
            "candidate_certified": False,
            "wfo_authorized_next_only_if_acceptance_pass": pass_gate,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    (output / "r34-5y-validation-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: module RAW_ROOT TARGET_ROOT COGNITIVE_V3_ROOT FREEZE_ROOT OUTPUT_DIR"
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
