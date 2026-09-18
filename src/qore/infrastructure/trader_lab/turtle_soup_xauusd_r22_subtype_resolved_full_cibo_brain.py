"""R22 subtype-resolved full-CIBO brain replay.

Consumed-evidence characterization only.

This replay consumes the frozen R21 CAUTIOUS/MIXED subtype memory and applies
it before execution:

SUPPORTIVE:
    keep the R20 full-CIBO path.
CAUTIOUS / MIXED:
    RECOVERABLE_NOW -> execute the current setup.
    WAIT_FOR_CONFIRMATION -> use CISD_THRESHOLD_RETEST only if such a stable
        subtype exists in the frozen memory.
    ABSTAIN_STRUCTURAL -> reject the current setup.
    UNRESOLVED -> WAIT_NEW_EVENT: do not force the current setup; the trader
        waits for a new strategy event instead of inventing a generic retest.

R20 adaptive trailing and structural rearm remain unchanged, so the economic
comparison isolates the effect of causal subtype resolution.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_xauusd_trader_memory_bridge_v1 as cibo_memory,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r13_autonomous_2y_behavior_replay as recognition,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r11_situation_recognition_engine as r11,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r15_cibo_first_market_brain as r15,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r18_memory_driven_cibo_brain as r18,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r19_full_cibo_memory_trailing_brain as r19,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r20_adaptive_cibo_trailing_rearm as r20,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r21_cautious_mixed_subtype_memory as r21,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R22_SUBTYPE_RESOLVED_FULL_CIBO_BRAIN_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

R21_RUN_ID = 35294750075
R21_ARTIFACT_ID = 10527441545
R21_DIGEST = "sha256:7e0282b11d6447e3270be7fa63d243191b6771f594430d8addd2f4d80d826f7d"


def _find(root: Path, name: str) -> Path:
    direct = root / name
    if direct.exists():
        return direct
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_subtype_memory(root: Path) -> dict[str, dict[str, Any]]:
    report = json.loads(
        _find(root, "r21-cautious-mixed-subtype-report.json").read_text()
    )
    if report["identity"] != r21.IDENTITY:
        raise ValueError("unexpected R21 subtype-memory identity")
    if report["classification_contract"]["pnl_used"] is not False:
        raise ValueError("R21 subtype memory unexpectedly uses PnL")
    return cast(
        dict[str, dict[str, Any]],
        json.loads(_find(root, "r21-subtype-memory.json").read_text()),
    )


def _subtype_signature(
    *,
    memory_state: str,
    setup: r3.Setup,
    posture: str,
) -> str:
    row = {
        "memory_state": memory_state,
        "source_timeframe": setup.context.timeframe,
        "fvg_before_entry": setup.context.fvg_before_entry,
        "cisd_progress_bucket": setup.context.cisd_progress_bucket,
        "protected_risk_range_bucket": (
            setup.context.protected_risk_range_bucket
        ),
        "source_range_state_bucket": setup.context.source_range_state_bucket,
        "brain_posture": posture,
    }
    return r21._signature(row)


def _resolve_entry_policy(
    *,
    memory_state: str,
    signature: str,
    subtype_memory: dict[str, dict[str, Any]],
) -> tuple[str | None, str]:
    if memory_state == "SUPPORTIVE":
        return "NEXT_SOURCE_OPEN", "SUPPORTIVE_EXECUTE"

    item = subtype_memory.get(signature)
    classification = (
        r21.UNRESOLVED if item is None else str(item["classification"])
    )
    if classification == r21.RECOVERABLE:
        return "NEXT_SOURCE_OPEN", "SUBTYPE_RECOVERABLE_EXECUTE"
    if classification == r21.WAIT:
        return "CISD_THRESHOLD_RETEST", "SUBTYPE_WAIT_FOR_CONFIRMATION"
    if classification == r21.ABSTAIN:
        return None, "SUBTYPE_ABSTAIN_STRUCTURAL"
    return None, "SUBTYPE_UNRESOLVED_WAIT_NEW_EVENT"


def _stats(
    trades: Sequence[r3.RoutedTrade],
    attr: str = "primary_net_r",
) -> dict[str, Any]:
    return r3._stat(trades, attr)


def _summary(executed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    trades = [item["trade"] for item in executed]
    trail_events = [
        event
        for item in executed
        for event in item["trail_events"]
    ]
    by_subtype: dict[str, Any] = {}
    for subtype in sorted({str(item["subtype_policy"]) for item in executed}):
        rows = [
            item["trade"]
            for item in executed
            if item["subtype_policy"] == subtype
        ]
        by_subtype[subtype] = {
            "trades": len(rows),
            "gross": _stats(rows, "gross_r"),
            "primary_005r": _stats(rows, "primary_net_r"),
            "stress_010r": _stats(rows, "stress_net_r"),
        }
    by_memory: dict[str, Any] = {}
    for state in ("SUPPORTIVE", "MIXED", "CAUTIOUS"):
        rows = [
            item["trade"] for item in executed if item["memory_state"] == state
        ]
        by_memory[state] = {
            "trades": len(rows),
            "gross": _stats(rows, "gross_r"),
            "primary_005r": _stats(rows, "primary_net_r"),
            "stress_010r": _stats(rows, "stress_net_r"),
        }
    return {
        "executed_trades": len(trades),
        "gross": _stats(trades, "gross_r"),
        "primary_005r": _stats(trades, "primary_net_r"),
        "stress_010r": _stats(trades, "stress_net_r"),
        "trail_moves": len(trail_events),
        "positions_with_trail": sum(
            bool(item["trail_events"]) for item in executed
        ),
        "exit_reason_counts": dict(
            Counter(trade.exit_reason for trade in trades)
        ),
        "memory_state_counts": dict(
            Counter(str(item["memory_state"]) for item in executed)
        ),
        "subtype_policy_counts": dict(
            Counter(str(item["subtype_policy"]) for item in executed)
        ),
        "entry_mode_counts": dict(
            Counter(trade.entry_mode for trade in trades)
        ),
        "target_rank_counts": dict(
            Counter(str(item["target_ladder_rank"]) for item in executed)
        ),
        "by_subtype_policy": by_subtype,
        "by_memory_state": by_memory,
    }


def _json_item(item: dict[str, Any]) -> dict[str, Any]:
    trade: r3.RoutedTrade = item["trade"]
    raw = asdict(trade)
    converted = {
        key: (
            value.isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, Decimal)
            else value
        )
        for key, value in raw.items()
    }
    converted.update(
        {
            "trail_events": [
                event.as_json() for event in item["trail_events"]
            ],
            "memory_state": item["memory_state"],
            "subtype_signature": item["subtype_signature"],
            "subtype_classification": item["subtype_classification"],
            "subtype_policy": item["subtype_policy"],
            "brain_reason": item["brain_reason"],
            "target_ladder_rank": item["target_ladder_rank"],
            "intelligence_state": item["intelligence_state"],
            "brain_posture": item["brain_posture"],
            "weekday": item["weekday"],
            "session": item["session"],
        }
    )
    return converted


def run(
    source_root: Path,
    target_root: Path,
    dossier_root: Path,
    r21_root: Path,
    r20_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    memory_store, dossier_manifest = cibo_memory.build_memory_store(dossier_root)
    subtype_memory = _load_subtype_memory(r21_root)

    r20_report = json.loads(
        _find(r20_root, "r20-adaptive-trailing-rearm-report.json").read_text()
    )
    if r20_report["identity"] != r20.IDENTITY:
        raise ValueError("unexpected R20 reference identity")

    episodes_raw, source_index = repair._load_targets_fail_closed(target_root)
    episodes: dict[str, list[r3.TargetCandidate]] = {
        key: list(value) for key, value in episodes_raw.items()
    }

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    recognition_ctx = recognition._prepare_recognition_context(evidence)
    d1 = recognition_ctx["d1_regime"]
    h4 = recognition_ctx["h4_regime"]

    counts: Counter[str] = Counter()
    executed: list[dict[str, Any]] = []
    busy_until = EVAL_OPEN
    trailing_exit_at: datetime | None = None

    for setup in setups:
        signal = setup.context.signal
        if not (EVAL_OPEN <= signal.entry_at < EVAL_CLOSE):
            continue

        if not r20._structurally_rearmed(
            setup=setup,
            trailing_exit_at=trailing_exit_at,
        ):
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
            counts["ABSTAIN_NO_CAUSAL_CIBO_EPISODE"] += 1
            continue

        regime = r5._regime_features(
            {"entry_at": signal.entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = r15._market_posture(regime)

        memory = cibo_memory.context_memory(
            memory_store,
            timeframe=setup.context.timeframe,
            side=signal.side.value,
            session=setup.context.session,
            prior_body_alignment=setup.context.prior_body_alignment,
            fvg_before_entry=setup.context.fvg_before_entry,
            exact_equal_liquidity=setup.context.exact_equal_liquidity,
        )

        signature = _subtype_signature(
            memory_state=memory.state,
            setup=setup,
            posture=posture,
        )
        subtype_item = subtype_memory.get(signature)
        subtype_classification = (
            "SUPPORTIVE"
            if memory.state == "SUPPORTIVE"
            else (
                r21.UNRESOLVED
                if subtype_item is None
                else str(subtype_item["classification"])
            )
        )
        entry_mode, subtype_policy = _resolve_entry_policy(
            memory_state=memory.state,
            signature=signature,
            subtype_memory=subtype_memory,
        )
        counts[subtype_policy] += 1
        if entry_mode is None:
            continue

        if (
            setup.context.protected_risk_range_bucket
            in r18.LOW_CAPACITY_RISK_BUCKETS
        ):
            counts["ABSTAIN_LOW_CAPACITY_PROTECTED_SWING"] += 1
            continue

        fill = r3._entry(setup, evidence, opens, entry_mode)
        if fill is None:
            counts["ABSTAIN_SELECTED_ENTRY_NOT_FILLED"] += 1
            continue
        entry_at, entry = fill

        target_rows = episodes[episode_id]
        active = r15._all_active_targets(
            target_rows,
            at=entry_at,
            side=signal.side,
            anchor=entry,
        )
        ladder = r15._distinct_target_ladder(active, anchor=entry)
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL"] += 1
            continue

        provisional = r15._provisional_trade(
            setup,
            entry_mode=entry_mode,
            entry_at=entry_at,
            entry=entry,
            target=ladder[0],
        )
        assessment, _recognition_row = recognition._assess(
            setup=setup,
            trade=provisional,
            evidence=evidence,
            opens=opens,
            episodes=episodes,
            ctx=recognition_ctx,
        )
        if assessment.state is r11.SituationState.KNOWN_INVALID:
            counts["ABSTAIN_KNOWN_INVALID"] += 1
            continue
        if assessment.state is r11.SituationState.CONFLICTED:
            counts["ABSTAIN_CONFLICTED"] += 1
            continue

        rank, brain_reason = r19._memory_target_depth(
            setup=setup,
            regime=regime,
            ladder_size=len(ladder),
            memory=memory,
        )
        target = ladder[rank - 1]

        simulation = r20._simulate_adaptive(
            setup,
            entry_at=entry_at,
            entry=entry,
            target_row=target,
            target_rank=rank,
            ladder=ladder,
            memory_state=memory.state,
            evidence=evidence,
            opens=opens,
        )
        if simulation is None:
            counts["ABSTAIN_INVALID_EXECUTION_GEOMETRY"] += 1
            continue

        trade = simulation.trade
        # Preserve the selected entry identity when WAIT becomes valid.
        if trade.entry_mode != entry_mode:
            trade = r3.RoutedTrade(
                source_timeframe=trade.source_timeframe,
                side=trade.side,
                entry_mode=entry_mode,
                target_route=trade.target_route,
                episode_id=trade.episode_id,
                entry_at=trade.entry_at,
                exit_at=trade.exit_at,
                entry=trade.entry,
                stop=trade.stop,
                target=trade.target,
                target_kind=trade.target_kind,
                target_timeframe=trade.target_timeframe,
                gross_r=trade.gross_r,
                primary_net_r=trade.primary_net_r,
                stress_net_r=trade.stress_net_r,
                exit_reason=trade.exit_reason,
                session_bucket=trade.session_bucket,
                prior_body_alignment=trade.prior_body_alignment,
            )

        if trade.entry_at < busy_until:
            counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            continue

        busy_until = trade.exit_at
        if trade.exit_reason in r20.TRAIL_EXIT_REASONS:
            trailing_exit_at = trade.exit_at
        counts["EXECUTE"] += 1

        executed.append(
            {
                "trade": trade,
                "trail_events": simulation.trail_events,
                "memory_state": memory.state,
                "subtype_signature": signature,
                "subtype_classification": subtype_classification,
                "subtype_policy": subtype_policy,
                "brain_reason": brain_reason,
                "target_ladder_rank": rank,
                "intelligence_state": assessment.state.value,
                "brain_posture": posture,
                "weekday": setup.context.weekday,
                "session": setup.context.session,
            }
        )

    summary = _summary(executed)

    payload = {
        "schema": "qore.turtle_soup_xauusd_r22.subtype_resolved_full_cibo_brain.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "subtype_memory": {
            "identity": r21.IDENTITY,
            "run_id": R21_RUN_ID,
            "artifact_id": R21_ARTIFACT_ID,
            "digest": R21_DIGEST,
            "stable_recoverable_signatures": sum(
                item["classification"] == r21.RECOVERABLE
                for item in subtype_memory.values()
            ),
            "stable_wait_signatures": sum(
                item["classification"] == r21.WAIT
                for item in subtype_memory.values()
            ),
            "stable_abstain_signatures": sum(
                item["classification"] == r21.ABSTAIN
                for item in subtype_memory.values()
            ),
            "unresolved_is_forced_entry": False,
            "unresolved_policy": "WAIT_FOR_NEW_STRATEGY_EVENT",
        },
        "decision_contract": {
            "supportive_uses_subtype_gate": False,
            "cautious_mixed_use_subtype_gate": True,
            "recoverable_executes_now": True,
            "wait_uses_cisd_retest_only_if_stable_memory_exists": True,
            "abstain_rejects_current_setup": True,
            "unresolved_rejects_current_setup_and_waits_new_event": True,
            "generic_retest_for_unresolved": False,
            "r11_known_invalid_respected": True,
            "r11_conflicted_respected": True,
            "adaptive_trailing_from_r20_preserved": True,
            "structural_rearm_from_r20_preserved": True,
            "pnl_used_for_subtype_decision": False,
            "fresh_holdout_used": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups_10y": len(setups),
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "reference_r20": {
            "run_id": 35293022991,
            "artifact_id": 10527157710,
            "adaptive_rearm": r20_report["variants"]["ADAPTIVE_REARM"],
        },
        "behavior": {
            "decision_counts": dict(counts),
            **summary,
        },
        "dossier_manifest": dossier_manifest,
        "governance": {
            "research_only": True,
            "consumed_same_window_characterization": True,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "funnel": funnel,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r22-subtype-resolved-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r22-subtype-resolved-trades.json").write_text(
        json.dumps([_json_item(item) for item in executed], indent=2, sort_keys=True)
        + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 7:
        raise SystemExit(
            "usage: module SOURCE_ROOT TARGET_ROOT DOSSIER_ROOT R21_ROOT R20_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
                Path(sys.argv[5]),
                Path(sys.argv[6]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
