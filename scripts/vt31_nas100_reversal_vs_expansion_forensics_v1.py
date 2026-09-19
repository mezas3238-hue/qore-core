"""Deep M1 falsification of NAS100 reversal completion vs source invalidation.

Silver Bullet source identity is frozen.  This lab does not change the source
methodology or select a production rule.

At the instant a Silver Bullet source becomes structurally confirmed, the lab
captures only information already observable from the frozen 09:00-10:00 NY
reference and closed M1 bars in the 10:00-11:00 NY source window.

It then labels the untouched future journey for research only:

- REVERSAL_COMPLETION:
  opposite frozen-reference boundary is reached before methodological swing
  invalidation;
- SOURCE_INVALIDATION_FIRST:
  methodological swing invalidation is reached before the opposite boundary;
- CENSORED_SAME_BAR_STOP_TARGET:
  stop and opposite boundary are both touched in one M1 bar and exact path is
  unknowable;
- UNRESOLVED_BY_16:
  neither event occurs before the 16:00 NY lifecycle.

The goal is to falsify whether the excessive losing streaks originate because
QORE is treating confirmed reversal sources as homogeneous even though their
native M1 geometry already separates reversal-completion from one-sided
continuation / invalidation.

Future labels are forbidden at runtime.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.reversal_vs_expansion_forensics.v1"
IDENTITY = "VT31_NAS100_REVERSAL_VS_EXPANSION_FORENSICS_V1"
MARKET = "NAS100"
LIFECYCLE_MINUTE = 16 * 60
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"

FEATURE_FIELDS = (
    "side",
    "entry_family",
    "candidate_combo",
    "candidate_count_bucket",
    "raid_minute_bucket",
    "confirmation_minute_bucket",
    "raid_to_confirmation_bucket",
    "sweep_depth_ref_bucket",
    "reclaim_depth_ref_bucket",
    "confirmation_penetration_ref_bucket",
    "risk_ref_bucket",
    "planned_target_r_bucket",
    "raid_to_confirmation_efficiency_bucket",
    "raid_to_confirmation_overlap_bucket",
    "raid_to_confirmation_body_ratio_bucket",
    "extreme_body_fraction_bucket",
    "confirmation_body_fraction_bucket",
    "confirmation_displacement_ref_bucket",
    "reference_width_pct_bucket",
    "reclaim_x_risk",
    "reclaim_x_latency",
    "reclaim_x_efficiency",
    "risk_x_planned_target",
    "side_x_reclaim",
    "family_x_reclaim",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _minute_10(value: datetime) -> int:
    local = value.astimezone(specialist._NY)
    return local.hour * 60 + local.minute - 10 * 60


def _bucket_minute(value: int) -> str:
    if value < 10:
        return "00_09"
    if value < 20:
        return "10_19"
    if value < 30:
        return "20_29"
    if value < 40:
        return "30_39"
    return "40_59"


def _bucket_minutes(value: int) -> str:
    if value <= 2:
        return "0_2m"
    if value <= 5:
        return "3_5m"
    if value <= 10:
        return "6_10m"
    if value <= 20:
        return "11_20m"
    return "21m_plus"


def _bucket_ratio(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value <= Decimal("0.10"):
        return "le_0_10"
    if value <= Decimal("0.25"):
        return "0_10_0_25"
    if value <= Decimal("0.50"):
        return "0_25_0_50"
    if value <= Decimal("1.00"):
        return "0_50_1_00"
    return "gt_1_00"


def _bucket_efficiency(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "lt_0_25"
    if value < Decimal("0.50"):
        return "0_25_0_50"
    if value < Decimal("0.75"):
        return "0_50_0_75"
    return "ge_0_75"


def _bucket_target(value: Decimal) -> str:
    if value <= Decimal("2"):
        return "le_2R"
    if value <= Decimal("3"):
        return "2_3R"
    if value <= Decimal("4"):
        return "3_4R"
    return "gt_4R"


def _bucket_count(value: int) -> str:
    return "1" if value == 1 else "2" if value == 2 else "3_plus"


def _path_efficiency(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal:
    if len(bars) < 2:
        return Decimal(0)
    closes = [_d(getattr(bar, "close")) for bar in bars]
    travelled = sum(
        (
            abs(closes[index] - closes[index - 1])
            for index in range(1, len(closes))
        ),
        Decimal(0),
    )
    if travelled <= 0:
        return Decimal(0)
    net = (
        closes[-1] - closes[0]
        if side == "long"
        else closes[0] - closes[-1]
    )
    return max(Decimal(0), net / travelled)


def _overlap_rate(bars: tuple[object, ...]) -> Decimal:
    if len(bars) < 2:
        return Decimal(0)
    overlap_count = 0
    eligible = 0
    for previous, current in zip(bars, bars[1:], strict=False):
        p_low = _d(getattr(previous, "low"))
        p_high = _d(getattr(previous, "high"))
        c_low = _d(getattr(current, "low"))
        c_high = _d(getattr(current, "high"))
        denominator = min(p_high - p_low, c_high - c_low)
        if denominator <= 0:
            continue
        eligible += 1
        overlap = max(
            Decimal(0),
            min(p_high, c_high) - max(p_low, c_low),
        )
        if overlap / denominator >= Decimal("0.50"):
            overlap_count += 1
    if eligible == 0:
        return Decimal(0)
    return Decimal(overlap_count) / Decimal(eligible)


def _directional_body_ratio(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal:
    if not bars:
        return Decimal(0)
    favorable = 0
    for bar in bars:
        opened = _d(getattr(bar, "open"))
        closed = _d(getattr(bar, "close"))
        if (side == "long" and closed > opened) or (
            side == "short" and closed < opened
        ):
            favorable += 1
    return Decimal(favorable) / Decimal(len(bars))


def _body_fraction(bar: object) -> Decimal:
    high = _d(getattr(bar, "high"))
    low = _d(getattr(bar, "low"))
    width = high - low
    if width <= 0:
        return Decimal(0)
    return abs(
        _d(getattr(bar, "close")) - _d(getattr(bar, "open"))
    ) / width


def _touches_stop(
    bar: object,
    *,
    side: str,
    stop: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= stop
    return _d(getattr(bar, "high")) >= stop


def _touches_target(
    bar: object,
    *,
    side: str,
    target: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= target
    return _d(getattr(bar, "low")) <= target


def _future_journey(
    day_bars: tuple[object, ...],
    *,
    source: Vt31R22SourceSetup,
) -> dict[str, object]:
    side = source.side.value
    confirmation_at = source.structure.confirmation_at
    stop = source.structure.swing_extreme
    target = source.target_price

    for bar in day_bars:
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        if opened_at < confirmation_at:
            continue
        if specialist.baseline._local_minute(bar) >= LIFECYCLE_MINUTE:
            break

        stop_hit = _touches_stop(bar, side=side, stop=stop)
        target_hit = _touches_target(bar, side=side, target=target)

        if stop_hit and target_hit:
            return {
                "journey_outcome": "CENSORED_SAME_BAR_STOP_TARGET",
                "resolved_at": cast(
                    datetime,
                    getattr(bar, "closed_at"),
                )
                .astimezone(UTC)
                .isoformat(),
            }
        if target_hit:
            return {
                "journey_outcome": "REVERSAL_COMPLETION",
                "resolved_at": cast(
                    datetime,
                    getattr(bar, "closed_at"),
                )
                .astimezone(UTC)
                .isoformat(),
            }
        if stop_hit:
            return {
                "journey_outcome": "SOURCE_INVALIDATION_FIRST",
                "resolved_at": cast(
                    datetime,
                    getattr(bar, "closed_at"),
                )
                .astimezone(UTC)
                .isoformat(),
            }

    return {
        "journey_outcome": "UNRESOLVED_BY_16",
        "resolved_at": None,
    }


def _features(
    *,
    day_bars: tuple[object, ...],
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
) -> dict[str, object]:
    side = source.side.value
    reference = source.reference
    ref_width = reference.high - reference.low
    ref_mid = (reference.high + reference.low) / Decimal(2)

    session = specialist._slice(
        day_bars,
        (10, 0, 0),
        (11, 0, 0),
    )
    raid_index = next(
        (
            index
            for index, bar in enumerate(session)
            if getattr(bar, "closed_at") == source.structure.raid_at
        ),
        None,
    )
    confirmation_index = next(
        (
            index
            for index, bar in enumerate(session)
            if getattr(bar, "closed_at")
            == source.structure.confirmation_at
        ),
        None,
    )
    if raid_index is None or confirmation_index is None:
        raise ValueError("raid/confirmation bar reconstruction failed")

    raid_bar = session[raid_index]
    confirmation_bar = session[confirmation_index]
    confirmation_path = tuple(
        session[raid_index : confirmation_index + 1]
    )

    raid_to_confirmation = int(
        (
            source.structure.confirmation_at
            - source.structure.raid_at
        ).total_seconds()
        // 60
    )

    if side == "short":
        sweep_depth = (
            source.structure.swing_extreme - reference.high
        ) / ref_width
        reclaim_depth = (
            reference.high - _d(getattr(confirmation_bar, "close"))
        ) / ref_width
        confirmation_penetration = (
            source.structure.structural_level
            - _d(getattr(confirmation_bar, "close"))
        ) / ref_width
    else:
        sweep_depth = (
            reference.low - source.structure.swing_extreme
        ) / ref_width
        reclaim_depth = (
            _d(getattr(confirmation_bar, "close")) - reference.low
        ) / ref_width
        confirmation_penetration = (
            _d(getattr(confirmation_bar, "close"))
            - source.structure.structural_level
        ) / ref_width

    sweep_depth = max(Decimal(0), sweep_depth)
    reclaim_depth = max(Decimal(0), reclaim_depth)
    confirmation_penetration = max(
        Decimal(0),
        confirmation_penetration,
    )

    risk_ref = (
        setup.initial_risk / ref_width
        if ref_width > 0
        else Decimal(0)
    )
    planned_target_r = (
        abs(setup.target_price - setup.entry_price) / setup.initial_risk
        if setup.initial_risk > 0
        else Decimal(0)
    )
    efficiency = _path_efficiency(
        confirmation_path,
        side=side,
    )
    overlap = _overlap_rate(confirmation_path)
    body_ratio = _directional_body_ratio(
        confirmation_path,
        side=side,
    )

    confirmation_range = (
        _d(getattr(confirmation_bar, "high"))
        - _d(getattr(confirmation_bar, "low"))
    )
    confirmation_displacement_ref = (
        confirmation_range / ref_width
        if ref_width > 0
        else Decimal(0)
    )

    ref_width_pct = (
        ref_width / ref_mid
        if ref_mid > 0
        else Decimal(0)
    )

    candidate_combo = "+".join(
        sorted(item.family.value for item in source.candidates)
    )

    reclaim_bucket = _bucket_ratio(reclaim_depth)
    risk_bucket = _bucket_ratio(risk_ref)
    latency_bucket = _bucket_minutes(raid_to_confirmation)
    efficiency_bucket = _bucket_efficiency(efficiency)
    target_bucket = _bucket_target(planned_target_r)

    return {
        "side": side,
        "entry_family": setup.selected_family.value,
        "candidate_combo": candidate_combo,
        "candidate_count": len(source.candidates),
        "candidate_count_bucket": _bucket_count(len(source.candidates)),
        "raid_minute": _minute_10(source.structure.raid_at),
        "raid_minute_bucket": _bucket_minute(
            _minute_10(source.structure.raid_at)
        ),
        "confirmation_minute": _minute_10(
            source.structure.confirmation_at
        ),
        "confirmation_minute_bucket": _bucket_minute(
            _minute_10(source.structure.confirmation_at)
        ),
        "raid_to_confirmation_minutes": raid_to_confirmation,
        "raid_to_confirmation_bucket": latency_bucket,
        "sweep_depth_ref": format(sweep_depth, "f"),
        "sweep_depth_ref_bucket": _bucket_ratio(sweep_depth),
        "reclaim_depth_ref": format(reclaim_depth, "f"),
        "reclaim_depth_ref_bucket": reclaim_bucket,
        "confirmation_penetration_ref": format(
            confirmation_penetration,
            "f",
        ),
        "confirmation_penetration_ref_bucket": _bucket_ratio(
            confirmation_penetration
        ),
        "risk_ref": format(risk_ref, "f"),
        "risk_ref_bucket": risk_bucket,
        "planned_target_r": format(planned_target_r, "f"),
        "planned_target_r_bucket": target_bucket,
        "raid_to_confirmation_efficiency": format(efficiency, "f"),
        "raid_to_confirmation_efficiency_bucket": efficiency_bucket,
        "raid_to_confirmation_overlap": format(overlap, "f"),
        "raid_to_confirmation_overlap_bucket": _bucket_efficiency(
            overlap
        ),
        "raid_to_confirmation_body_ratio": format(
            body_ratio,
            "f",
        ),
        "raid_to_confirmation_body_ratio_bucket": _bucket_efficiency(
            body_ratio
        ),
        "extreme_body_fraction": format(
            _body_fraction(raid_bar),
            "f",
        ),
        "extreme_body_fraction_bucket": _bucket_efficiency(
            _body_fraction(raid_bar)
        ),
        "confirmation_body_fraction": format(
            _body_fraction(confirmation_bar),
            "f",
        ),
        "confirmation_body_fraction_bucket": _bucket_efficiency(
            _body_fraction(confirmation_bar)
        ),
        "confirmation_displacement_ref": format(
            confirmation_displacement_ref,
            "f",
        ),
        "confirmation_displacement_ref_bucket": _bucket_ratio(
            confirmation_displacement_ref
        ),
        "reference_width_pct": format(ref_width_pct, "f"),
        "reference_width_pct_bucket": _bucket_ratio(
            ref_width_pct * Decimal(100)
        ),
        "reclaim_x_risk": f"{reclaim_bucket}|{risk_bucket}",
        "reclaim_x_latency": f"{reclaim_bucket}|{latency_bucket}",
        "reclaim_x_efficiency": (
            f"{reclaim_bucket}|{efficiency_bucket}"
        ),
        "risk_x_planned_target": f"{risk_bucket}|{target_bucket}",
        "side_x_reclaim": f"{side}|{reclaim_bucket}",
        "family_x_reclaim": (
            f"{setup.selected_family.value}|{reclaim_bucket}"
        ),
    }


def _group_stats(rows: list[dict[str, object]]) -> dict[str, object]:
    resolved = [
        row
        for row in rows
        if row["journey_outcome"]
        not in {"CENSORED_SAME_BAR_STOP_TARGET"}
    ]
    reversal = sum(
        row["journey_outcome"] == "REVERSAL_COMPLETION"
        for row in resolved
    )
    invalidation = sum(
        row["journey_outcome"] == "SOURCE_INVALIDATION_FIRST"
        for row in resolved
    )
    unresolved = sum(
        row["journey_outcome"] == "UNRESOLVED_BY_16"
        for row in resolved
    )
    n = len(resolved)

    return {
        "sample": len(rows),
        "resolved_sample": n,
        "reversal_completion": reversal,
        "reversal_completion_rate": (
            "0"
            if n == 0
            else format(Decimal(reversal) / Decimal(n), "f")
        ),
        "source_invalidation_first": invalidation,
        "source_invalidation_first_rate": (
            "0"
            if n == 0
            else format(Decimal(invalidation) / Decimal(n), "f")
        ),
        "unresolved_by_16": unresolved,
        "unresolved_by_16_rate": (
            "0"
            if n == 0
            else format(Decimal(unresolved) / Decimal(n), "f")
        ),
        "journey_outcomes": dict(
            sorted(
                Counter(
                    cast(str, row["journey_outcome"])
                    for row in rows
                ).items()
            )
        ),
    }


def _feature_diagnostics(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for field in FEATURE_FIELDS:
            grouped[f"{field}={row.get(field)}"].append(row)
    return {
        key: _group_stats(items)
        for key, items in sorted(grouped.items())
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("reversal-vs-expansion requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    policy = Vt31R22ExecutionPolicy()
    observations: list[dict[str, object]] = []
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars,
            (9, 0, 0),
            (10, 0, 0),
        )
        session = specialist._slice(
            day_bars,
            (10, 0, 0),
            (11, 0, 0),
        )
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        prefix = list(reference)
        selected_source: Vt31R22SourceSetup | None = None
        selected_setup: Vt31R22ExecutableSetup | None = None

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
                    status["both-sides-swept"] += 1
                    break
                continue

            executable, reason = make_executable_setup(
                evaluation.setup,
                policy,
            )
            if executable is None:
                status[f"not-executable-{reason}"] += 1
                break

            selected_source = evaluation.setup
            selected_setup = executable
            break

        if selected_source is None or selected_setup is None:
            status["no-executable-source"] += 1
            continue

        row = {
            "partition": partition,
            "local_date": local_day.isoformat(),
            "signal_at": (
                selected_source.structure.confirmation_at
                .astimezone(UTC)
                .isoformat()
            ),
            **_features(
                day_bars=day_bars,
                source=selected_source,
                setup=selected_setup,
            ),
            **_future_journey(
                day_bars,
                source=selected_source,
            ),
            "future_label_research_only": True,
        }
        observations.append(row)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "silver_bullet_freeze": {
            "source_sha256": silver.SOURCE_SHA256,
            "methodology_id": silver.METHODOLOGY_ID,
            "source_module_modified": False,
        },
        "overall": _group_stats(observations),
        "feature_diagnostics": _feature_diagnostics(observations),
        "observations": observations,
        "status_counts": dict(sorted(status.items())),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "silver_bullet_modified": False,
            "m1_source_confirmation_only": True,
            "h4_primary_causal_feature": False,
            "h1_trend_primary_causal_feature": False,
            "future_journey_label_research_only": True,
            "future_journey_label_allowed_at_runtime": False,
            "terminal_pnl_used_as_feature": False,
            "uses_fold_identity_at_runtime": False,
            "consumed_evidence_only": True,
            "opens_new_holdout": False,
            "policy_promoted": False,
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
                "overall": payload["overall"],
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
