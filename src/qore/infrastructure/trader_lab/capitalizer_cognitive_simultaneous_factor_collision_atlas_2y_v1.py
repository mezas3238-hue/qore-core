"""Simultaneous factor-collision falsification for Capitalizer 2Y.

This consumed-window lab addresses a blind spot left by the V2 evidence binding:
candidates with the *same entry timestamp* do not see one another as already-active
positions, so correlated tickets can pass the baseline exposure reconstruction
simultaneously.

The lab:
1. freezes one already-observed third-slot development hypothesis from the
   Cross-Feature Atlas (NEGATIVE prior-session realized sign + OB_FVG_RETEST);
2. finds exact-timestamp, same-session candidate collisions that share at least
   one underlying factor in the same economic direction;
3. evaluates several deterministic, outcome-blind single-ticket tie controls;
4. measures standalone and combined economic counterfactuals.

No tie control is selected or promoted. This is consumed-window falsification only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerSide,
    factor_exposures,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_SIMULTANEOUS_FACTOR_COLLISION_ATLAS_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"
SOURCE_CROSS_RUN_ID = 36075482217
SOURCE_CROSS_SHA = "fce6f4e1dea05c4f3e36902c3baf9b3c434080d7"

THIRD_SLOT_JOURNEY_FEATURE = "PRIOR_SESSION_REALIZED_SIGN"
THIRD_SLOT_JOURNEY_VALUE = "NEGATIVE"
THIRD_SLOT_PREENTRY_FEATURE = "ENTRY_MODE"
THIRD_SLOT_PREENTRY_VALUE = "OB_FVG_RETEST"

POLICIES = (
    "LEXICOGRAPHIC_FIRST",
    "LEXICOGRAPHIC_LAST",
    "EARLIER_MSS",
    "LATER_MSS",
    "EARLIER_FVG",
    "LATER_FVG",
)


@dataclass(frozen=True, slots=True)
class CollisionCandidate:
    symbol: str
    session: str
    side: str
    entry_at: str
    mss_at: str
    fvg_at: str


@dataclass(frozen=True, slots=True)
class CollisionCluster:
    entry_at: str
    session: str
    shared_same_direction_factors: tuple[str, ...]
    candidates: tuple[CollisionCandidate, ...]


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_binding(root: Path) -> tuple[dict[str, Any], ...]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("collision atlas requires one V2 binding artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected binding identity")
    coverage = report.get("binding_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("binding coverage missing")
    if int(coverage.get("source_microstructure", -1)) != int(
        report.get("control_trades", -2)
    ):
        raise ValueError("collision atlas requires full source binding")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("collision atlas rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("binding row must be object")
                rows.append(raw)
    return tuple(rows)


def _load_cross_reference(root: Path) -> dict[str, Any]:
    paths = sorted(
        root.rglob("capitalizer-cognitive-third-slot-cross-feature-atlas-2y-v1.json")
    )
    if len(paths) != 1:
        raise ValueError("collision atlas requires one Cross-Feature report")
    report = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("cross-feature report must be object")

    matches = [
        row
        for row in report.get("cells", ())
        if row.get("journey_feature") == THIRD_SLOT_JOURNEY_FEATURE
        and row.get("journey_value") == THIRD_SLOT_JOURNEY_VALUE
        and row.get("preentry_feature") == THIRD_SLOT_PREENTRY_FEATURE
        and row.get("preentry_value") == THIRD_SLOT_PREENTRY_VALUE
    ]
    if len(matches) != 1:
        raise ValueError("frozen third-slot reference cell must be unique")
    return dict(matches[0])


def _token_map(row: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in row.get("microstructure_observations", ()):
        token = str(raw)
        if ":" not in token:
            continue
        key, value = token.split(":", 1)
        if key in result and result[key] != value:
            raise ValueError(f"conflicting token: {key}")
        result[key] = value
    return result


def _mss_fvg(row: dict[str, Any]) -> tuple[datetime, datetime]:
    tokens = _token_map(row)
    mss_raw = (
        tokens.get("NEW_MSS_AT")
        or tokens.get("M3_MSS_AT")
        or tokens.get("SOURCE_FIRST_MSS_AT")
    )
    fvg_raw = tokens.get("NEW_FVG_AT") or tokens.get("M1_FVG_CONFIRMED_AT")
    if mss_raw is None or fvg_raw is None:
        raise ValueError("collision candidate requires causal MSS and FVG timestamps")
    mss = _aware(mss_raw, field="mss_at")
    fvg = _aware(fvg_raw, field="fvg_at")
    entry = _aware(row["entry_at"], field="entry_at")
    if mss > entry or fvg > entry:
        raise ValueError("collision evidence cannot be after entry")
    return mss, fvg


def _factor_signed_map(row: dict[str, Any]) -> dict[str, Decimal]:
    exposures = factor_exposures(
        (
            CapitalizerExposurePosition(
                symbol=str(row["symbol"]),
                side=CapitalizerSide(str(row["side"])),
                risk_r=Decimal("1"),
            ),
        )
    )
    return {item.factor: item.net_r for item in exposures}


def _shared_same_direction_factors(
    rows: tuple[dict[str, Any], ...],
) -> tuple[str, ...]:
    if len(rows) < 2:
        return ()
    shared: set[str] | None = None
    signed: list[dict[str, Decimal]] = []
    for row in rows:
        item = _factor_signed_map(row)
        signed.append(item)
        shared = set(item) if shared is None else shared & set(item)
    if not shared:
        return ()
    factors = [
        factor
        for factor in shared
        if len({Decimal("1") if item[factor] > 0 else Decimal("-1") for item in signed})
        == 1
    ]
    return tuple(sorted(factors))


def _build_clusters(
    control: tuple[dict[str, Any], ...],
    binding_by_key: dict[tuple[str, str], dict[str, Any]],
) -> tuple[CollisionCluster, ...]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in control:
        grouped[(str(row["session"]), str(row["entry_at"]))].append(row)

    clusters: list[CollisionCluster] = []
    for (session, entry_at), raw_rows in sorted(grouped.items()):
        if len(raw_rows) < 2:
            continue
        rows = tuple(sorted(raw_rows, key=lambda row: str(row["symbol"])))
        factors = _shared_same_direction_factors(rows)
        if not factors:
            continue

        candidates: list[CollisionCandidate] = []
        for row in rows:
            binding = binding_by_key[_join_key(row)]
            mss, fvg = _mss_fvg(binding)
            candidates.append(
                CollisionCandidate(
                    symbol=str(row["symbol"]),
                    session=session,
                    side=str(row["side"]),
                    entry_at=entry_at,
                    mss_at=mss.isoformat(),
                    fvg_at=fvg.isoformat(),
                )
            )
        clusters.append(
            CollisionCluster(
                entry_at=entry_at,
                session=session,
                shared_same_direction_factors=factors,
                candidates=tuple(candidates),
            )
        )
    return tuple(clusters)


def _prior_session_realized_sign(
    current: dict[str, Any],
    control: tuple[dict[str, Any], ...],
) -> str:
    entry = _aware(current["entry_at"], field="entry_at")
    value = sum(
        (
            Decimal(str(row["realized_gross_r"]))
            for row in control
            if str(row["operating_date"]) == str(current["operating_date"])
            and str(row["session"]) == str(current["session"])
            and _aware(row["entry_at"], field="entry_at") < entry
            and _aware(row["exit_at"], field="exit_at") <= entry
        ),
        Decimal("0"),
    )
    if value < 0:
        return "NEGATIVE"
    if value > 0:
        return "POSITIVE"
    return "ZERO"


def _third_slot_hypothesis_keys(
    control: tuple[dict[str, Any], ...],
    binding_by_key: dict[tuple[str, str], dict[str, Any]],
) -> frozenset[tuple[str, str]]:
    selected: set[tuple[str, str]] = set()
    for row in control:
        binding = binding_by_key[_join_key(row)]
        if int(binding["prior_same_session_selected"]) != 2:
            continue
        if _prior_session_realized_sign(row, control) != THIRD_SLOT_JOURNEY_VALUE:
            continue
        mode = _token_map(binding).get("ENTRY_MODE", "UNKNOWN")
        if mode != THIRD_SLOT_PREENTRY_VALUE:
            continue
        selected.add(_join_key(row))
    return frozenset(selected)


def _winner(cluster: CollisionCluster, policy: str) -> CollisionCandidate:
    candidates = cluster.candidates
    if policy == "LEXICOGRAPHIC_FIRST":
        return min(candidates, key=lambda item: item.symbol)
    if policy == "LEXICOGRAPHIC_LAST":
        return max(candidates, key=lambda item: item.symbol)
    if policy == "EARLIER_MSS":
        return min(candidates, key=lambda item: (_aware(item.mss_at, field="mss_at"), item.symbol))
    if policy == "LATER_MSS":
        latest = max(_aware(item.mss_at, field="mss_at") for item in candidates)
        return min(
            (item for item in candidates if _aware(item.mss_at, field="mss_at") == latest),
            key=lambda item: item.symbol,
        )
    if policy == "EARLIER_FVG":
        return min(candidates, key=lambda item: (_aware(item.fvg_at, field="fvg_at"), item.symbol))
    if policy == "LATER_FVG":
        latest = max(_aware(item.fvg_at, field="fvg_at") for item in candidates)
        return min(
            (item for item in candidates if _aware(item.fvg_at, field="fvg_at") == latest),
            key=lambda item: item.symbol,
        )
    raise ValueError(f"unknown collision policy: {policy}")


def _collision_drop_keys(
    clusters: tuple[CollisionCluster, ...],
    *,
    policy: str,
) -> frozenset[tuple[str, str]]:
    dropped: set[tuple[str, str]] = set()
    for cluster in clusters:
        keep = _winner(cluster, policy)
        for candidate in cluster.candidates:
            if candidate != keep:
                dropped.add((candidate.symbol, candidate.entry_at))
    return frozenset(dropped)


def _metrics(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (
                _aware(row["entry_at"], field="entry_at"),
                str(row["symbol"]),
            ),
        )
    )
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(ordered),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(str(row["exit_reason"]) == "STOP" for row in ordered),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def _apply_drop(
    control: tuple[dict[str, Any], ...],
    drop: frozenset[tuple[str, str]],
) -> tuple[dict[str, Any], ...]:
    return tuple(row for row in control if _join_key(row) not in drop)


def build_report(
    binding_root: Path,
    target_root: Path,
    cross_root: Path,
) -> dict[str, Any]:
    bindings = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    cross_reference = _load_cross_reference(cross_root)

    binding_by_key = {_join_key(row): row for row in bindings}
    if len(binding_by_key) != len(bindings):
        raise ValueError("binding identity not unique")
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("binding/control identities differ")

    third_slot_drop = _third_slot_hypothesis_keys(control, binding_by_key)
    if len(third_slot_drop) != int(cross_reference["third_slot_trades"]):
        raise ValueError("third-slot hypothesis does not reproduce Cross-Feature cell")

    clusters = _build_clusters(control, binding_by_key)
    factor_counts = Counter(
        factor for cluster in clusters for factor in cluster.shared_same_direction_factors
    )

    policies: list[dict[str, Any]] = []
    for policy in POLICIES:
        collision_drop = _collision_drop_keys(clusters, policy=policy)
        combined_drop = frozenset((*third_slot_drop, *collision_drop))
        standalone = _apply_drop(control, collision_drop)
        combined = _apply_drop(control, combined_drop)
        policies.append(
            {
                "policy": policy,
                "collision_dropped_trades": len(collision_drop),
                "standalone_metrics": _metrics(standalone),
                "combined_dropped_trades": len(combined_drop),
                "combined_metrics": _metrics(combined),
                "combined_density_retention": str(
                    Decimal(len(combined)) / Decimal(len(control))
                ),
            }
        )

    critical = [
        {
            "entry_at": cluster.entry_at,
            "session": cluster.session,
            "shared_same_direction_factors": cluster.shared_same_direction_factors,
            "symbols": tuple(candidate.symbol for candidate in cluster.candidates),
            "post_audit_outcomes": tuple(
                str(
                    next(
                        row["realized_gross_r"]
                        for row in control
                        if str(row["symbol"]) == candidate.symbol
                        and str(row["entry_at"]) == candidate.entry_at
                    )
                )
                for candidate in cluster.candidates
            ),
        }
        for cluster in clusters
    ]

    return {
        "identity": IDENTITY,
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_binding_sha": SOURCE_BINDING_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "source_cross_run_id": SOURCE_CROSS_RUN_ID,
        "source_cross_sha": SOURCE_CROSS_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_trades": len(control),
        "control_metrics": _metrics(control),
        "third_slot_reference": {
            "journey_feature": THIRD_SLOT_JOURNEY_FEATURE,
            "journey_value": THIRD_SLOT_JOURNEY_VALUE,
            "preentry_feature": THIRD_SLOT_PREENTRY_FEATURE,
            "preentry_value": THIRD_SLOT_PREENTRY_VALUE,
            "trades": len(third_slot_drop),
            "cross_feature_counterfactual_metrics": cross_reference[
                "full_portfolio_if_abstained_metrics"
            ],
            "development_hypothesis_only": True,
            "runtime_rule_selected": False,
        },
        "collision_cluster_count": len(clusters),
        "collision_candidate_count": sum(len(cluster.candidates) for cluster in clusters),
        "collision_factor_counts": dict(sorted(factor_counts.items())),
        "all_collision_evidence_known_by_entry": True,
        "same_timestamp_candidates_compete_before_active_exposure_exists": True,
        "collision_clusters": critical,
        "policies": policies,
        "policy_count": len(policies),
        "all_policies_outcome_blind": True,
        "outcomes_used_only_for_post_audit_metrics": True,
        "collision_policy_selected": False,
        "combined_rule_selected": False,
        "automatic_promotion_allowed": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "BIND_OPPORTUNITY_COMPETITION_AND_FALSIFY_ON_FRESH_HOLDOUT",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-simultaneous-factor-collision-atlas-2y-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binding_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("cross_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(
        args.binding_root,
        args.target_root,
        args.cross_root,
    )
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
