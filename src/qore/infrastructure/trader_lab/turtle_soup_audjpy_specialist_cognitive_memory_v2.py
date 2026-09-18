"""Turtle Soup AUDJPY Specialist Cognitive Memory V2.

V2 keeps the immutable CIBO master and the official Specialist Raw Memory V1
unchanged.  It corrects the two research defects exposed by R26:

* situation identity is independent from target rank/route/RR;
* authority is structural.  PnL/gross/net/PF are never decision inputs.

Regime relevance is computed only from information available before entry:
completed H1/H4/D1 candles plus completed M5 path state.  No calendar-year rule
is used to decide whether the current regime is relevant.

Target support is based on Protected-Swing lifecycle reachability.  Management
posture is selected by structural non-inferiority versus STATIC: it may only
replace STATIC when it does not reduce target reach and does not increase stop
frequency.  Economic results remain replay validation only.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_audjpy_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_specialist_memory_v1 as v1,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_AUDJPY_SPECIALIST_COGNITIVE_MEMORY_V2"
SOURCE_V1_IDENTITY = v1.IDENTITY
SOURCE_V1_RUN_ID = 35382166428
SOURCE_V1_ARTIFACT_ID = 10562012174
SOURCE_V1_ARTIFACT_DIGEST = (
    "sha256:09c33bd18917d0bbf62eccce36836a4cd903acdce8b44a474bcf14ea9a9cf499"
)
SOURCE_V1_SHA = "6fb6898650a45e76d1173fe27470b3d291f659c4"

MIN_TARGET_OBSERVATIONS = 20
MIN_DISTINCT_QUARTERS = 4
MIN_STRUCTURAL_REACH_RATE = Decimal("0.50")

AUTHORITATIVE_LEVELS = ("exact_regime", "causal_core_regime", "anatomy_regime")
CONTEXT_ONLY_LEVELS = ("regime_journey",)

LEVELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "exact_regime",
        (
            "timeframe",
            "side",
            "session",
            "prior_body_alignment",
            "fvg_before_entry",
            "exact_equal_liquidity",
            "raid_depth_range_bucket",
            "reclaim_latency_bucket",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "body_fraction_bucket",
            "rejection_wick_bucket",
            "close_location_bucket",
            "h1_range_state",
            "h4_range_state",
            "d1_range_state",
            "h1_body_alignment",
            "h4_body_alignment",
            "d1_body_alignment",
            "m5_volatility_state",
            "m5_efficiency_state",
            "m5_displacement_alignment",
        ),
    ),
    (
        "causal_core_regime",
        (
            "timeframe",
            "side",
            "prior_body_alignment",
            "fvg_before_entry",
            "reclaim_latency_bucket",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "h4_range_state",
            "d1_range_state",
            "h4_body_alignment",
            "d1_body_alignment",
            "m5_volatility_state",
            "m5_displacement_alignment",
        ),
    ),
    (
        "anatomy_regime",
        (
            "timeframe",
            "prior_body_alignment",
            "fvg_before_entry",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "h4_range_state",
            "d1_range_state",
            "m5_volatility_state",
        ),
    ),
    (
        "regime_journey",
        (
            "timeframe",
            "h4_range_state",
            "d1_range_state",
            "m5_volatility_state",
            "m5_efficiency_state",
        ),
    ),
)


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _ratio_state(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value <= Decimal("0.75"):
        return "compressed"
    if value <= Decimal("1.25"):
        return "balanced"
    if value <= Decimal("2.0"):
        return "expanded"
    return "extreme"


def _efficiency_state(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value <= Decimal("0.20"):
        return "low"
    if value <= Decimal("0.45"):
        return "medium"
    if value <= Decimal("0.70"):
        return "high"
    return "directional"


def _alignment(open_price: Decimal, close_price: Decimal, side: str) -> str:
    if close_price == open_price:
        return "flat"
    with_side = close_price > open_price if side == Side.LONG.value else close_price < open_price
    return "with" if with_side else "opposed"


def _frame_state(
    candles: Sequence[SourceCandle],
    closes: Sequence[datetime],
    *,
    at: datetime,
    side: str,
) -> tuple[str, str]:
    cursor = bisect.bisect_right(closes, at) - 1
    if cursor < 1:
        return "missing", "missing"
    candle = candles[cursor]
    history = candles[max(0, cursor - 20):cursor]
    if not history:
        return "missing", _alignment(candle.open, candle.close, side)
    mean_range = sum((item.high - item.low for item in history), Decimal(0)) / Decimal(len(history))
    current_range = candle.high - candle.low
    ratio = None if mean_range <= 0 else current_range / mean_range
    return _ratio_state(ratio), _alignment(candle.open, candle.close, side)


def _m5_state(
    bars: Sequence[Bar],
    opens: Sequence[datetime],
    *,
    at: datetime,
    side: str,
) -> tuple[str, str, str]:
    cursor = bisect.bisect_left(opens, at)
    recent = list(bars[max(0, cursor - 12):cursor])
    baseline = list(bars[max(0, cursor - 84):max(0, cursor - 12)])
    if len(recent) < 6 or len(baseline) < 24:
        return "missing", "missing", "missing"
    recent_range = sum((bar.high - bar.low for bar in recent), Decimal(0)) / Decimal(len(recent))
    baseline_range = sum((bar.high - bar.low for bar in baseline), Decimal(0)) / Decimal(len(baseline))
    vol_ratio = None if baseline_range <= 0 else recent_range / baseline_range

    path = Decimal(0)
    previous = recent[0].open
    for bar in recent:
        path += abs(bar.close - previous)
        previous = bar.close
    displacement = recent[-1].close - recent[0].open
    efficiency = None if path <= 0 else abs(displacement) / path
    if displacement == 0:
        alignment = "flat"
    else:
        with_side = displacement > 0 if side == Side.LONG.value else displacement < 0
        alignment = "with" if with_side else "opposed"
    return _ratio_state(vol_ratio), _efficiency_state(efficiency), alignment


def _regime_context(
    *,
    row: dict[str, Any],
    bars: Sequence[Bar],
    opens: Sequence[datetime],
    frames: dict[str, tuple[SourceCandle, ...]],
    frame_closes: dict[str, tuple[datetime, ...]],
) -> dict[str, str]:
    at = _dt(str(row["strategy_entry_at"]))
    side = str(row["side"])
    h1_range, h1_body = _frame_state(frames["H1"], frame_closes["H1"], at=at, side=side)
    h4_range, h4_body = _frame_state(frames["H4"], frame_closes["H4"], at=at, side=side)
    d1_range, d1_body = _frame_state(frames["D1"], frame_closes["D1"], at=at, side=side)
    m5_vol, m5_eff, m5_align = _m5_state(bars, opens, at=at, side=side)
    return {
        "h1_range_state": h1_range,
        "h4_range_state": h4_range,
        "d1_range_state": d1_range,
        "h1_body_alignment": h1_body,
        "h4_body_alignment": h4_body,
        "d1_body_alignment": d1_body,
        "m5_volatility_state": m5_vol,
        "m5_efficiency_state": m5_eff,
        "m5_displacement_alignment": m5_align,
    }


def _quarter(at: datetime) -> str:
    return f"{at.year}-Q{((at.month - 1) // 3) + 1}"


def _key(row: dict[str, Any], fields: Sequence[str]) -> str:
    return "|".join(str(row[field]) for field in fields)


def _target_key(row: dict[str, Any]) -> str:
    return f"{row['target_rank']}|{row['target_route']}"


def _posture_stats(rows: Sequence[dict[str, Any]], posture: str) -> dict[str, Any]:
    n = len(rows)
    target = sum(bool(row[f"{posture}_target_reached"]) for row in rows)
    protected = sum(bool(row[f"{posture}_protected_exit"]) for row in rows)
    stopped = sum(bool(row[f"{posture}_stop_exit"]) for row in rows)
    return {
        "n": n,
        "target_rate": str(Decimal(target) / Decimal(n)),
        "protected_exit_rate": str(Decimal(protected) / Decimal(n)),
        "stop_rate": str(Decimal(stopped) / Decimal(n)),
    }


def _structural_posture(rows: Sequence[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    stats = {posture: _posture_stats(rows, posture) for posture in native.POSTURES}
    baseline = stats[native.POSTURE_STATIC]
    base_target = Decimal(str(baseline["target_rate"]))
    base_stop = Decimal(str(baseline["stop_rate"]))
    eligible = [native.POSTURE_STATIC]
    for posture in (native.POSTURE_LET_RUN, native.POSTURE_PROTECT):
        item = stats[posture]
        if (
            Decimal(str(item["target_rate"])) >= base_target
            and Decimal(str(item["stop_rate"])) <= base_stop
        ):
            eligible.append(posture)

    def priority(posture: str) -> tuple[Decimal, Decimal, Decimal, int]:
        item = stats[posture]
        return (
            Decimal(str(item["target_rate"])),
            -Decimal(str(item["stop_rate"])),
            Decimal(str(item["protected_exit_rate"])),
            1 if posture == native.POSTURE_STATIC else 0,
        )

    return max(eligible, key=priority), stats


def _target_profile(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    quarters = sorted({_quarter(_dt(str(row["strategy_entry_at"]))) for row in rows})
    static_reached = sum(bool(row[f"{native.POSTURE_STATIC}_target_reached"]) for row in rows)
    reach_rate = Decimal(static_reached) / Decimal(n)
    posture, posture_stats = _structural_posture(rows)
    supported = (
        n >= MIN_TARGET_OBSERVATIONS
        and len(quarters) >= MIN_DISTINCT_QUARTERS
        and reach_rate >= MIN_STRUCTURAL_REACH_RATE
    )
    return {
        "observations": n,
        "distinct_quarters": len(quarters),
        "first_quarter": quarters[0],
        "last_quarter": quarters[-1],
        "static_protected_swing_reach_rate": str(reach_rate),
        "structurally_supported": supported,
        "preferred_posture": posture,
        "posture_structural_stats": posture_stats,
        "decision_uses_economic_fields": False,
    }


def _build_cognitive(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    hierarchy: dict[str, Any] = {}
    for level, fields in LEVELS:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[_key(row, fields)].append(row)
        signatures: dict[str, Any] = {}
        for signature, members in sorted(grouped.items()):
            targets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in members:
                targets[_target_key(row)].append(row)
            target_profiles = {
                key: _target_profile(items)
                for key, items in sorted(targets.items())
            }
            signatures[signature] = {
                "fields": list(fields),
                "values": {field: members[0][field] for field in fields},
                "observations": len(members),
                "decision_authority": (
                    "AUTHORITATIVE" if level in AUTHORITATIVE_LEVELS else "CONTEXT_ONLY"
                ),
                "targets": target_profiles,
                "supported_target_count": sum(
                    bool(profile["structurally_supported"])
                    for profile in target_profiles.values()
                ),
            }
        hierarchy[level] = {
            "fields": list(fields),
            "decision_authority": (
                "AUTHORITATIVE" if level in AUTHORITATIVE_LEVELS else "CONTEXT_ONLY"
            ),
            "signatures": signatures,
        }
    return hierarchy


def resolve_authoritative(
    hierarchy: dict[str, Any],
    row: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    target_key = _target_key(row)
    for level, fields in LEVELS:
        signature = _key(row, fields)
        item = cast(dict[str, Any], hierarchy[level]["signatures"]).get(signature)
        if item is None or item["decision_authority"] != "AUTHORITATIVE":
            continue
        profile = cast(dict[str, Any], item["targets"]).get(target_key)
        if profile is None or not bool(profile["structurally_supported"]):
            continue
        return profile, level, signature
    return None, None, None


def build(raw_root: Path, v1_root: Path, output: Path) -> dict[str, Any]:
    source_report = json.loads(
        _single(v1_root, "turtle-soup-audjpy-specialist-memory-report.json").read_text()
    )
    if source_report["identity"] != SOURCE_V1_IDENTITY:
        raise ValueError("unexpected Specialist Memory V1 identity")
    git_sha = _single(v1_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_V1_SHA:
        raise ValueError("unexpected Specialist Memory V1 git binding")

    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "AUDJPY" or int(provenance["retained_bars"]) != 745468:
        raise ValueError("unexpected AUDJPY master corpus")

    observations: list[dict[str, Any]] = []
    source_path = _single(v1_root, "turtle-soup-audjpy-specialist-observations.jsonl")
    with source_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                observations.append(json.loads(line))
    if len(observations) != 41302:
        raise ValueError("Specialist Memory V1 observation drift")

    h4 = build_h4(evidence.bars)
    frames = {
        "H1": build_h1(evidence.bars),
        "H4": h4,
        "D1": build_daily(h4),
    }
    frame_closes = {
        timeframe: tuple(candle.closed_at for candle in candles)
        for timeframe, candles in frames.items()
    }
    opens = tuple(bar.opened_at for bar in evidence.bars)

    enriched: list[dict[str, Any]] = []
    for row in observations:
        enriched.append(
            {
                **row,
                **_regime_context(
                    row=row,
                    bars=evidence.bars,
                    opens=opens,
                    frames=frames,
                    frame_closes=frame_closes,
                ),
            }
        )

    cognitive = _build_cognitive(enriched)
    resolution: Counter[str] = Counter()
    for row in enriched:
        profile, level, _ = resolve_authoritative(cognitive, row)
        if profile is None or level is None:
            resolution["NO_AUTHORITATIVE_STRUCTURAL_MEMORY"] += 1
        else:
            resolution[level] += 1

    summary: dict[str, Any] = {}
    for level, payload in cognitive.items():
        signatures = cast(dict[str, Any], payload["signatures"])
        profiles = [
            profile
            for item in signatures.values()
            for profile in cast(dict[str, Any], item["targets"]).values()
        ]
        summary[level] = {
            "decision_authority": payload["decision_authority"],
            "signatures": len(signatures),
            "target_profiles": len(profiles),
            "supported_target_profiles": sum(
                bool(profile["structurally_supported"]) for profile in profiles
            ),
            "preferred_posture_counts": dict(
                Counter(
                    str(profile["preferred_posture"])
                    for profile in profiles
                    if profile["structurally_supported"]
                )
            ),
        }

    output.mkdir(parents=True, exist_ok=True)
    v1._write_jsonl(
        output / "turtle-soup-audjpy-specialist-observations-v2.jsonl",
        enriched,
    )
    (output / "turtle-soup-audjpy-specialist-cognitive-memory-v2.json").write_text(
        json.dumps(cognitive, indent=2, sort_keys=True) + "\n"
    )

    report = {
        "schema": "qore.turtle_soup_audjpy.specialist_cognitive_memory.v2",
        "identity": IDENTITY,
        "source_v1": {
            "identity": SOURCE_V1_IDENTITY,
            "run_id": SOURCE_V1_RUN_ID,
            "artifact_id": SOURCE_V1_ARTIFACT_ID,
            "artifact_digest": SOURCE_V1_ARTIFACT_DIGEST,
            "git_sha": SOURCE_V1_SHA,
        },
        "master_contract": {
            "cibo_master_modified": False,
            "specialist_raw_memory_v1_modified": False,
            "derived_cognitive_layer_only": True,
            "retained_m5_bars": int(provenance["retained_bars"]),
        },
        "decision_contract": {
            "situation_separate_from_target": True,
            "regime_similarity_uses_calendar_year": False,
            "regime_features_are_pre_entry_only": True,
            "economic_fields_authorize_trade": False,
            "gross_r_authorizes_trade": False,
            "net_r_authorizes_trade": False,
            "profit_factor_authorizes_trade": False,
            "minimum_target_observations": MIN_TARGET_OBSERVATIONS,
            "minimum_distinct_quarters": MIN_DISTINCT_QUARTERS,
            "minimum_structural_reach_rate": str(MIN_STRUCTURAL_REACH_RATE),
            "target_reach_definition": "STATIC_PROTECTED_SWING_TARGET_REACHED",
            "management_rule": "STRUCTURAL_NON_INFERIOR_TO_STATIC_ON_TARGET_REACH_AND_STOP_RATE",
            "authoritative_levels": list(AUTHORITATIVE_LEVELS),
            "context_only_levels": list(CONTEXT_ONLY_LEVELS),
        },
        "reproduction": {
            "source_observations": len(observations),
            "enriched_observations": len(enriched),
        },
        "cognitive_summary": summary,
        "authoritative_resolution_counts": dict(resolution),
        "governance": {
            "research_only": True,
            "r26_result_used_as_decision_input": False,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    (output / "turtle-soup-audjpy-specialist-cognitive-memory-v2-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module RAW_ROOT SPECIALIST_V1_ROOT OUTPUT_DIR")
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
