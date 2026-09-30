"""CIBO Phase 18 GBPUSD exact geometry replay.

Derived from the frozen R39 validation implementation at
e02d9384fbe6521040fc2779a085c43b8d5f0f92. The execution algorithm is
preserved; this research-only variant serializes causal signal, entry,
structural stop and technical target geometry omitted by the historical R39
ledger. It never authorizes broker mutation.
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
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_gbpusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r26_specialist_memory_brain as r26,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r32_causal_memory_defragmentation as r32,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r37_structural_quality_governor as r37,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_specialist_cognitive_memory_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "CIBO_PHASE18_GBPUSD_R39_GEOMETRY_REPLAY_V1"
SOURCE_R39_IDENTITY = "TURTLE_SOUP_GBPUSD_R39_FROZEN_R37_5Y_VALIDATION_V1"
CANDIDATE_IDENTITY = "TURTLE_SOUP_GBPUSD_R37_STRUCTURAL_QUALITY_CANDIDATE_001"

EVAL_OPEN = datetime(2021, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

FAMILY_SET = "R37_G25_FIXED"
ALLOWED_FAMILIES = r37.FAMILY_SETS[FAMILY_SET]
STRUCTURAL_POLICY_NAME = "SQ3_H1_BALANCED"
DRAWDOWN_GOVERNOR_NAME = "DD_1_3_SCALE_075_025"
STRUCTURAL_POLICY = r37.STRUCTURAL_POLICIES[STRUCTURAL_POLICY_NAME]
DRAWDOWN_GOVERNOR = r37.GOVERNORS[DRAWDOWN_GOVERNOR_NAME]

MIN_TRADES = 800
MIN_PF_010 = Decimal("1.50")
MAX_DD_010 = Decimal("6.0")


@dataclass(frozen=True, slots=True)
class ScaledTrade:
    signal_at: str
    entry_at: str
    entry_price: str
    structural_stop: str
    technical_target: str
    exit_at: str
    side: str
    source: str
    family: str | None
    classification: str
    target_rank: int
    target_route: str
    posture: str
    exit_reason: str
    raw_net_010_r: str
    structural_scale: str
    drawdown_scale: str
    risk_scale: str
    scaled_net_010_r: str
    setup_context: dict[str, Any]
    regime: dict[str, str]


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_freeze(root: Path) -> dict[str, Any]:
    manifest = cast(
        dict[str, Any],
        json.loads(
            _single(root, "r38-candidate-freeze-manifest.json").read_text()
        ),
    )
    if manifest["identity"] != CANDIDATE_IDENTITY:
        raise ValueError("candidate identity drift")
    if manifest["status"] != "FROZEN_FOR_5Y_VALIDATION":
        raise ValueError("candidate is not frozen for 5Y")
    source = manifest["source"]
    if source["run_id"] != 35352145888:
        raise ValueError("R37 source run drift")
    if source["artifact_id"] != 10550221115:
        raise ValueError("R37 source artifact drift")
    if source["artifact_digest"] != (
        "sha256:544471a071b772e395d3ec9c4b54fa0a"
        "ecbdb5953730ab6e6f704c335639a5cd"
    ):
        raise ValueError("R37 source digest drift")
    if source["git_sha"] != (
        "75b70f877794f018a41e02f91626262079bbf15d"
    ):
        raise ValueError("R37 source git drift")
    contract = manifest["frozen_contract"]
    if contract["family_set"] != FAMILY_SET:
        raise ValueError("family-set drift")
    if tuple(contract["families"]) != tuple(ALLOWED_FAMILIES):
        raise ValueError("family membership drift")
    if contract["r32_core"] != "R32_REGIME_ROUTE_TYPES":
        raise ValueError("R32 core drift")
    if contract["structural_policy"] != STRUCTURAL_POLICY_NAME:
        raise ValueError("structural policy drift")
    if contract["drawdown_governor"] != DRAWDOWN_GOVERNOR_NAME:
        raise ValueError("drawdown governor drift")
    if contract["signals_suppressed"] is not False:
        raise ValueError("signal suppression drift")
    if contract["risk_governor_pretrade_context_only"] is not True:
        raise ValueError("risk causality drift")
    if contract["entry"] != "NEXT_SOURCE_OPEN":
        raise ValueError("entry drift")
    if contract["c2"] != "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE":
        raise ValueError("C2 drift")
    if contract["cisd"] != "CAUSAL":
        raise ValueError("CISD drift")
    if contract["stop"] != "EXACT_PROTECTED_SWING_NEVER_WIDEN":
        raise ValueError("stop drift")
    if contract["single_position_busy"] is not True:
        raise ValueError("single-position drift")
    if contract["structural_rearm"] is not True:
        raise ValueError("rearm drift")
    if manifest["next_stage"]["fresh_holdout_status"] != "SEALED_UNTOUCHED":
        raise ValueError("fresh holdout seal drift")
    if manifest["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout consumption drift")
    return manifest


def _pf(values: Sequence[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _stats(values: Sequence[Decimal]) -> dict[str, Any]:
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        elif value > 0:
            streak = 0
    pf = _pf(values)
    return {
        "trades": len(values),
        "total_scaled_net_010_r": str(equity),
        "mean_scaled_net_010_r": None if not values else str(equity / Decimal(len(values))),
        "profit_factor_scaled_net_010": None if pf is None else str(pf),
        "max_drawdown_scaled_r": str(max_dd),
        "max_losing_streak": max_streak,
    }


def _annual_blocks(rows: Sequence[ScaledTrade]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for year in range(5):
        start = datetime(2021 + year, 9, 17, tzinfo=UTC)
        end = datetime(2022 + year, 9, 17, tzinfo=UTC)
        members = [
            Decimal(row.scaled_net_010_r)
            for row in rows
            if start <= datetime.fromisoformat(row.entry_at) < end
        ]
        result.append({
            "open": start.isoformat(),
            "close": end.isoformat(),
            **_stats(members),
            "positive_total": sum(members, Decimal(0)) > 0,
        })
    return result


def _group_stats(rows: Sequence[ScaledTrade], field: str) -> dict[str, Any]:
    grouped: dict[str, list[Decimal]] = {}
    for row in rows:
        raw = getattr(row, field)
        key = "NONE" if raw is None else str(raw)
        grouped.setdefault(key, []).append(Decimal(row.scaled_net_010_r))
    return {key: _stats(values) for key, values in sorted(grouped.items())}


def run(
    raw_root: Path,
    target_root: Path,
    v2_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, Any]:
    freeze = _load_freeze(freeze_root)
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "GBPUSD" or int(provenance["retained_bars"]) != 745274:
        raise ValueError("unexpected GBPUSD corpus")

    observations = r32._load_observations(v2_root)
    fields, route_mode = r32.SCHEMES["R32_REGIME_ROUTE_TYPES"]
    memory, memory_summary = r32._build_memory(
        observations,
        fields=fields,
        route_mode=route_mode,
    )
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
            row={"strategy_entry_at": entry_at.isoformat(), "side": signal.side.value},
            bars=evidence.bars,
            opens=opens,
            frames=frames,
            frame_closes=frame_closes,
        )
        decision = r37._choose(
            setup=setup,
            ladder=ladder,
            regime=regime,
            allowed_families=ALLOWED_FAMILIES,
            fields=fields,
            route_mode=route_mode,
            memory=memory,
        )
        if decision is None:
            counts["ABSTAIN_NO_AUTHORITY_OR_SUBFAMILY"] += 1
            continue

        runtime = r26._simulate(
            setup,
            decision=r37._runtime_decision(decision),
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

        ctx = v1._setup_context(setup)
        features = {
            "protected_risk_range_bucket": str(ctx["protected_risk_range_bucket"]),
            "h1_range_state": str(regime.get("h1_range_state", "na")),
            "close_location_bucket": str(ctx["close_location_bucket"]),
            "classification": decision.classification,
        }
        structural_scale = r37._structural_scale(
            decision.source,
            decision.family,
            features,
            STRUCTURAL_POLICY,
        )
        drawdown_scale = r37._risk_scale(peak - equity, DRAWDOWN_GOVERNOR)
        risk_scale = structural_scale * drawdown_scale
        scaled = runtime.net_010_r * risk_scale

        equity += scaled
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

        rows.append(
            ScaledTrade(
                signal_at=signal.cisd_at.isoformat(),
                entry_at=runtime.entry_at.isoformat(),
                entry_price=str(entry),
                structural_stop=str(signal.protected_swing),
                technical_target=str(decision.target.level),
                exit_at=runtime.exit_at.isoformat(),
                side=runtime.side,
                source=decision.source,
                family=decision.family,
                classification=decision.classification,
                target_rank=runtime.target_rank,
                target_route=runtime.target_route,
                posture=runtime.posture,
                exit_reason=runtime.exit_reason,
                raw_net_010_r=str(runtime.net_010_r),
                structural_scale=str(structural_scale),
                drawdown_scale=str(drawdown_scale),
                risk_scale=str(risk_scale),
                scaled_net_010_r=str(scaled),
                setup_context=ctx,
                regime=regime,
            )
        )
        counts["EXECUTE"] += 1
        counts[f"SOURCE_{decision.source}"] += 1
        if decision.family is not None:
            counts[f"FAMILY_{decision.family}"] += 1
        counts[f"CLASS_{decision.classification}"] += 1
        counts[f"RISK_SCALE_{risk_scale}"] += 1

    values = [Decimal(row.scaled_net_010_r) for row in rows]
    result = _stats(values)
    if Decimal(result["max_drawdown_scaled_r"]) != max_dd:
        raise ValueError("drawdown accounting drift")
    pf_raw = result["profit_factor_scaled_net_010"]
    pf = None if pf_raw is None else Decimal(str(pf_raw))
    total = Decimal(str(result["total_scaled_net_010_r"]))
    acceptance = bool(
        len(rows) >= MIN_TRADES
        and pf is not None
        and pf >= MIN_PF_010
        and max_dd <= MAX_DD_010
        and total > 0
    )

    annual = _annual_blocks(rows)
    result["positive_annual_blocks"] = sum(bool(item["positive_total"]) for item in annual)
    result["acceptance_pass"] = acceptance

    output.mkdir(parents=True, exist_ok=True)
    trades_path = output / "phase18-gbpusd-r39-geometry-trades.jsonl"
    with trades_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase18.gbpusd_r39_geometry_replay.v1",
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "fresh_holdout": False,
            "consumed_robustness_validation": True,
        },
        "frozen_contract": freeze["frozen_contract"],
        "memory_binding": {
            "scheme": "R32_REGIME_ROUTE_TYPES",
            "memory_summary": memory_summary,
            "rules_reoptimized_for_5y": False,
        },
        "predeclared_acceptance": {
            "minimum_trades": MIN_TRADES,
            "minimum_profit_factor_scaled_net_010": str(MIN_PF_010),
            "maximum_drawdown_scaled_net_010_r": str(MAX_DD_010),
            "total_must_be_positive": True,
        },
        "result": result,
        "annual_blocks": annual,
        "forensics": {
            "by_source": _group_stats(rows, "source"),
            "by_family": _group_stats([row for row in rows if row.family is not None], "family"),
            "by_side": _group_stats(rows, "side"),
            "by_classification": _group_stats(rows, "classification"),
            "by_target_rank": _group_stats(rows, "target_rank"),
        },
        "decision_counts": dict(counts),
        "phase18_geometry": {
            "source_r39_identity": SOURCE_R39_IDENTITY,
            "source_r39_git_sha": "e02d9384fbe6521040fc2779a085c43b8d5f0f92",
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
            "setups_10y": len(setups),
            "funnel": funnel,
        },
        "governance": {
            "candidate_frozen": True,
            "candidate_certified": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    (output / "phase18-gbpusd-r39-geometry-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: module RAW_ROOT TARGET_ROOT COGNITIVE_V2_ROOT FREEZE_ROOT OUTPUT_DIR"
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
